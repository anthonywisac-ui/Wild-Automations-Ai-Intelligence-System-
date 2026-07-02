USER MANAGEMENT
1. User Management Overview
1.1 Architecture
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      USER MANAGEMENT ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    USER SERVICES                                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Auth       │  │  Profile    │  │  Preferences│  │  Activity │  │  │
│  │  │  Service    │  │  Service    │  │  Service    │  │  Service  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    USER STORE                                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Users      │  │  Profiles   │  │  Preferences│  │  Sessions │  │  │
│  │  │  Table      │  │  Table      │  │  Table      │  │  Table    │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    USER EVENTS                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Created    │  │  Updated    │  │  Deleted    │  │  Logged   │  │  │
│  │  │             │  │             │  │             │  │  In/Out   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
2. Authentication System
2.1 Authentication Service
python
# services/auth_service.py
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import jwt
import bcrypt

class AuthenticationService:
    def __init__(self, user_repo: UserRepository, token_config: Dict):
        self.user_repo = user_repo
        self.secret_key = token_config.get('secret_key')
        self.algorithm = token_config.get('algorithm', 'HS256')
        self.access_token_expiry = token_config.get('access_token_expiry', 3600)
        self.refresh_token_expiry = token_config.get('refresh_token_expiry', 86400 * 7)
    
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        
        user = await self.user_repo.get_by_email(email)
        if not user:
            return None
        
        if not self._verify_password(password, user.password_hash):
            return None
        
        if not user.active:
            raise UserInactiveError("User account is inactive")
        
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise UserLockedError(f"Account locked until {user.locked_until}")
        
        # Update last login
        await self.user_repo.update_last_login(user.id)
        
        return user
    
    async def register(self, user_data: Dict) -> User:
        """Register a new user"""
        
        # Validate email
        if not self._validate_email(user_data.get('email')):
            raise ValidationError("Invalid email format")
        
        # Check existing user
        existing = await self.user_repo.get_by_email(user_data.get('email'))
        if existing:
            raise ConflictError("User already exists")
        
        # Hash password
        hashed_password = self._hash_password(user_data.get('password'))
        
        # Create user
        user = User(
            email=user_data['email'],
            password_hash=hashed_password,
            full_name=user_data.get('full_name'),
            phone=user_data.get('phone'),
            created_at=datetime.utcnow()
        )
        
        # Save user
        user = await self.user_repo.create(user)
        
        # Create default profile
        await self._create_default_profile(user.id)
        
        # Send welcome email
        await self._send_welcome_email(user.email)
        
        return user
    
    async def generate_tokens(self, user_id: str) -> Dict:
        """Generate access and refresh tokens"""
        
        access_token = self._create_token(
            user_id=user_id,
            token_type='access',
            expiry=self.access_token_expiry
        )
        
        refresh_token = self._create_token(
            user_id=user_id,
            token_type='refresh',
            expiry=self.refresh_token_expiry
        )
        
        # Store refresh token
        await self._store_refresh_token(user_id, refresh_token)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': self.access_token_expiry,
            'token_type': 'Bearer'
        }
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token"""
        
        # Verify refresh token
        payload = self._decode_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            raise InvalidTokenError("Invalid refresh token")
        
        user_id = payload.get('user_id')
        if not user_id:
            raise InvalidTokenError("Invalid token payload")
        
        # Check stored refresh token
        stored = await self._get_refresh_token(user_id)
        if stored != refresh_token:
            raise InvalidTokenError("Refresh token mismatch")
        
        # Generate new tokens
        return await self.generate_tokens(user_id)
    
    async def logout(self, user_id: str, access_token: str) -> bool:
        """Logout user and invalidate tokens"""
        
        # Blacklist access token
        await self._blacklist_token(access_token)
        
        # Remove refresh token
        await self._remove_refresh_token(user_id)
        
        return True
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    
    def _create_token(self, user_id: str, token_type: str, expiry: int) -> str:
        """Create JWT token"""
        payload = {
            'user_id': user_id,
            'type': token_type,
            'exp': datetime.utcnow() + timedelta(seconds=expiry),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _decode_token(self, token: str) -> Optional[Dict]:
        """Decode JWT token"""
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.InvalidTokenError:
            return None
2.2 Password Reset Flow
python
# services/password_reset_service.py
from typing import Optional
from datetime import datetime, timedelta
import secrets

class PasswordResetService:
    def __init__(self, user_repo: UserRepository, email_service: EmailService):
        self.user_repo = user_repo
        self.email_service = email_service
        self.token_expiry = 3600  # 1 hour
    
    async def initiate_reset(self, email: str) -> bool:
        """Initiate password reset flow"""
        
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal if user exists
            return True
        
        # Generate reset token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(seconds=self.token_expiry)
        
        # Store token
        await self.user_repo.store_reset_token(user.id, token, expires_at)
        
        # Send reset email
        await self._send_reset_email(user.email, token)
        
        return True
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token"""
        
        # Validate token
        reset_data = await self.user_repo.get_reset_token(token)
        if not reset_data:
            raise InvalidTokenError("Invalid or expired reset token")
        
        if reset_data['expires_at'] < datetime.utcnow():
            raise InvalidTokenError("Token has expired")
        
        # Update password
        user_id = reset_data['user_id']
        hashed_password = self._hash_password(new_password)
        
        await self.user_repo.update_password(user_id, hashed_password)
        
        # Invalidate reset token
        await self.user_repo.invalidate_reset_token(token)
        
        # Send confirmation email
        await self._send_confirmation_email(
            reset_data['email'],
            datetime.utcnow()
        )
        
        return True
    
    async def _send_reset_email(self, email: str, token: str):
        """Send password reset email"""
        
        reset_url = f"https://wildautomations.com/reset-password?token={token}"
        
        await self.email_service.send_email(
            to=email,
            subject="Password Reset Request",
            template="reset_password",
            context={
                "reset_url": reset_url,
                "expires_in": self.token_expiry // 60
            }
        )
3. Profile Management
3.1 Profile Service
python
# services/profile_service.py
from typing import Dict, Optional, List
from datetime import datetime

class ProfileService:
    def __init__(self, profile_repo: ProfileRepository):
        self.profile_repo = profile_repo
    
    async def get_profile(self, user_id: str) -> UserProfile:
        """Get user profile"""
        
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile:
            # Create default profile
            profile = await self._create_default_profile(user_id)
        
        return profile
    
    async def update_profile(self, user_id: str, data: Dict) -> UserProfile:
        """Update user profile"""
        
        profile = await self.get_profile(user_id)
        
        # Update fields
        for key, value in data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        # Validate education
        if 'education' in data:
            await self._validate_education(data['education'])
        
        # Validate experience
        if 'experience' in data:
            await self._validate_experience(data['experience'])
        
        # Validate skills
        if 'skills' in data:
            await self._validate_skills(data['skills'])
        
        profile.updated_at = datetime.utcnow()
        
        await self.profile_repo.update(profile)
        
        return profile
    
    async def _validate_education(self, education: Dict):
        """Validate education data"""
        
        if education.get('level'):
            valid_levels = ['high_school', 'bachelor', 'master', 'phd', 'diploma']
            if education['level'] not in valid_levels:
                raise ValidationError(f"Invalid education level: {education['level']}")
        
        if education.get('graduation_year'):
            year = education['graduation_year']
            current_year = datetime.utcnow().year
            if year < 1900 or year > current_year + 5:
                raise ValidationError(f"Invalid graduation year: {year}")
    
    async def _validate_experience(self, experience: Dict):
        """Validate experience data"""
        
        if experience.get('years'):
            years = experience['years']
            if years < 0 or years > 50:
                raise ValidationError(f"Invalid experience years: {years}")
        
        if experience.get('level'):
            valid_levels = ['entry', 'mid', 'senior', 'lead', 'executive']
            if experience['level'] not in valid_levels:
                raise ValidationError(f"Invalid experience level: {experience['level']}")
    
    async def _validate_skills(self, skills: List[str]):
        """Validate skills data"""
        
        if len(skills) > 50:
            raise ValidationError("Too many skills (max 50)")
        
        for skill in skills:
            if len(skill) > 50:
                raise ValidationError(f"Skill name too long: {skill}")
    
    async def _create_default_profile(self, user_id: str) -> UserProfile:
        """Create default profile for user"""
        
        profile = UserProfile(
            user_id=user_id,
            country="",
            city="",
            education={},
            experience={},
            skills=[],
            languages=[],
            preferences={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return await self.profile_repo.create(profile)
3.2 Preference Management
python
# services/preference_service.py
from typing import Dict, List, Optional
from datetime import datetime

class PreferenceService:
    def __init__(self, preference_repo: PreferenceRepository):
        self.preference_repo = preference_repo
    
    async def get_preferences(self, user_id: str) -> Dict:
        """Get user preferences"""
        
        preferences = await self.preference_repo.get_by_user_id(user_id)
        if not preferences:
            # Create default preferences
            preferences = await self._create_default_preferences(user_id)
        
        return preferences
    
    async def update_preferences(self, user_id: str, data: Dict) -> Dict:
        """Update user preferences"""
        
        preferences = await self.get_preferences(user_id)
        
        # Update notification preferences
        if 'notifications' in data:
            await self._validate_notifications(data['notifications'])
            preferences['notifications'] = data['notifications']
        
        # Update domain preferences
        if 'domains' in data:
            await self._validate_domains(data['domains'])
            preferences['domains'] = data['domains']
        
        # Update search preferences
        if 'search' in data:
            await self._validate_search_preferences(data['search'])
            preferences['search'] = data['search']
        
        # Update privacy preferences
        if 'privacy' in data:
            await self._validate_privacy(data['privacy'])
            preferences['privacy'] = data['privacy']
        
        preferences['updated_at'] = datetime.utcnow()
        
        await self.preference_repo.update(preferences)
        
        return preferences
    
    async def _validate_notifications(self, notifications: Dict):
        """Validate notification preferences"""
        
        # Validate channels
        if 'channels' in notifications:
            valid_channels = ['email', 'whatsapp', 'push', 'web']
            for channel in notifications['channels']:
                if channel not in valid_channels:
                    raise ValidationError(f"Invalid notification channel: {channel}")
        
        # Validate frequency
        if 'frequency' in notifications:
            valid_frequencies = ['real_time', 'daily', 'weekly', 'never']
            if notifications['frequency'] not in valid_frequencies:
                raise ValidationError(f"Invalid frequency: {notifications['frequency']}")
    
    async def _validate_domains(self, domains: List[str]):
        """Validate domain preferences"""
        
        valid_domains = [
            'jobs', 'real_estate', 'vehicles', 'education',
            'immigration', 'scholarships', 'auctions', 'business'
        ]
        
        for domain in domains:
            if domain not in valid_domains:
                raise ValidationError(f"Invalid domain: {domain}")
    
    async def _validate_search_preferences(self, search: Dict):
        """Validate search preferences"""
        
        if 'default_country' in search:
            # Validate country code
            pass
        
        if 'default_currency' in search:
            # Validate currency code
            pass
    
    async def _validate_privacy(self, privacy: Dict):
        """Validate privacy preferences"""
        
        if 'data_sharing' in privacy:
            valid_options = ['all', 'anonymous', 'none']
            if privacy['data_sharing'] not in valid_options:
                raise ValidationError(f"Invalid data sharing option: {privacy['data_sharing']}")
    
    async def _create_default_preferences(self, user_id: str) -> Dict:
        """Create default preferences for user"""
        
        preferences = {
            'user_id': user_id,
            'notifications': {
                'enabled': True,
                'channels': ['email', 'whatsapp'],
                'frequency': 'daily',
                'real_time_alerts': True
            },
            'domains': ['jobs', 'real_estate', 'vehicles'],
            'search': {
                'default_country': 'US',
                'default_currency': 'USD',
                'results_per_page': 20
            },
            'privacy': {
                'data_sharing': 'anonymous',
                'profile_visibility': 'private'
            },
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        return await self.preference_repo.create(preferences)
4. Activity Tracking
python
# services/activity_service.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class ActivityService:
    def __init__(self, activity_repo: ActivityRepository):
        self.activity_repo = activity_repo
    
    async def track_activity(self, user_id: str, activity_type: str, data: Dict) -> None:
        """Track user activity"""
        
        activity = {
            'user_id': user_id,
            'type': activity_type,
            'data': data,
            'timestamp': datetime.utcnow(),
            'session_id': data.get('session_id')
        }
        
        await self.activity_repo.create(activity)
        
        # Update user stats
        await self._update_user_stats(user_id, activity_type)
    
    async def get_user_activity(
        self,
        user_id: str,
        activity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get user activity history"""
        
        return await self.activity_repo.get_by_user_id(
            user_id=user_id,
            activity_type=activity_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics"""
        
        # Get counts
        searches = await self.activity_repo.count_by_type(user_id, 'search')
        notifications = await self.activity_repo.count_by_type(user_id, 'notification')
        saves = await self.activity_repo.count_by_type(user_id, 'save')
        
        # Get last activity
        last_activity = await self.activity_repo.get_last_activity(user_id)
        
        # Get daily activity for last 30 days
        daily_activity = await self._get_daily_activity(user_id, days=30)
        
        return {
            'total_searches': searches,
            'total_notifications': notifications,
            'total_saves': saves,
            'last_activity': last_activity,
            'daily_activity': daily_activity,
            'engagement_score': self._calculate_engagement_score(searches, notifications, saves)
        }
    
    async def _update_user_stats(self, user_id: str, activity_type: str):
        """Update user statistics"""
        
        stats = await self.activity_repo.get_stats(user_id) or {}
        
        if activity_type == 'search':
            stats['total_searches'] = stats.get('total_searches', 0) + 1
        elif activity_type == 'notification':
            stats['total_notifications'] = stats.get('total_notifications', 0) + 1
        elif activity_type == 'save':
            stats['total_saves'] = stats.get('total_saves', 0) + 1
        
        stats['last_activity'] = datetime.utcnow()
        
        await self.activity_repo.update_stats(user_id, stats)
    
    async def _get_daily_activity(self, user_id: str, days: int) -> List[Dict]:
        """Get daily activity for last N days"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        daily = await self.activity_repo.get_daily_counts(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Fill missing dates
        result = []
        current = start_date
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            result.append({
                'date': date_str,
                'count': daily.get(date_str, 0)
            })
            current += timedelta(days=1)
        
        return result
    
    def _calculate_engagement_score(self, searches: int, notifications: int, saves: int) -> float:
        """Calculate user engagement score"""
        
        # Simple engagement score
        score = 0.0
        
        if searches >= 10:
            score += 0.3
        elif searches >= 5:
            score += 0.15
        
        if notifications >= 10:
            score += 0.3
        elif notifications >= 5:
            score += 0.15
        
        if saves >= 5:
            score += 0.4
        elif saves >= 1:
            score += 0.2
        
        return min(score, 1.0)
5. User Onboarding
5.1 Onboarding Flow
python
# services/onboarding_service.py
from typing import Dict, Optional
from enum import Enum

class OnboardingStep(Enum):
    WELCOME = "welcome"
    PROFILE = "profile"
    PREFERENCES = "preferences"
    DOMAINS = "domains"
    NOTIFICATIONS = "notifications"
    COMPLETE = "complete"

class OnboardingService:
    def __init__(self, user_repo: UserRepository, profile_service: ProfileService):
        self.user_repo = user_repo
        self.profile_service = profile_service
    
    async def get_onboarding_status(self, user_id: str) -> Dict:
        """Get onboarding status for user"""
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        current_step = user.onboarding_step or OnboardingStep.WELCOME.value
        
        return {
            'step': current_step,
            'completed': user.onboarding_complete,
            'progress': self._calculate_progress(current_step)
        }
    
    async def update_onboarding_step(self, user_id: str, step: str, data: Dict) -> Dict:
        """Update onboarding step with data"""
        
        # Validate step
        try:
            OnboardingStep(step)
        except ValueError:
            raise ValidationError(f"Invalid onboarding step: {step}")
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        # Process step data
        if step == OnboardingStep.PROFILE.value:
            await self._process_profile_step(user_id, data)
        elif step == OnboardingStep.PREFERENCES.value:
            await self._process_preferences_step(user_id, data)
        elif step == OnboardingStep.DOMAINS.value:
            await self._process_domains_step(user_id, data)
        elif step == OnboardingStep.NOTIFICATIONS.value:
            await self._process_notifications_step(user_id, data)
        elif step == OnboardingStep.COMPLETE.value:
            await self._complete_onboarding(user_id)
        
        # Update user step
        user.onboarding_step = step
        user.onboarding_complete = step == OnboardingStep.COMPLETE.value
        await self.user_repo.update(user)
        
        return {
            'step': step,
            'completed': user.onboarding_complete,
            'progress': self._calculate_progress(step)
        }
    
    async def _process_profile_step(self, user_id: str, data: Dict):
        """Process profile step data"""
        
        # Update profile
        await self.profile_service.update_profile(user_id, data)
    
    async def _process_preferences_step(self, user_id: str, data: Dict):
        """Process preferences step data"""
        
        # Update preferences
        preference_service = PreferenceService()
        await preference_service.update_preferences(user_id, data)
    
    async def _complete_onboarding(self, user_id: str):
        """Complete onboarding"""
        
        # Send welcome message
        await self._send_welcome_message(user_id)
        
        # Create initial notifications
        await self._create_initial_notifications(user_id)
        
        # Track completion
        await self._track_onboarding_completion(user_id)
    
    def _calculate_progress(self, current_step: str) -> int:
        """Calculate onboarding progress percentage"""
        
        steps = [step.value for step in OnboardingStep]
        if current_step not in steps:
            return 0
        
        current_index = steps.index(current_step)
        total_steps = len(steps)
        
        if current_index == total_steps - 1:  # Complete step
            return 100
        
        return int((current_index / (total_steps - 1)) * 100)
