NOTIFICATION ENGINE
1. Notification Architecture
1.1 Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION ENGINE ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    TRIGGER LAYER                                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  New        │  │  Schedule   │  │  User       │  │  System   │  │  │
│  │  │  Opportunity│  │  Event      │  │  Action     │  │  Event    │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    MATCHING LAYER                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Profile    │  │  Preference │  │  Behavior   │  │  Scoring  │  │  │
│  │  │  Matching   │  │  Matching   │  │  Matching   │  │  Engine   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    DELIVERY LAYER                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Email     │  │  WhatsApp   │  │   Web       │  │   Push    │  │  │
│  │  │  Provider   │  │  Provider   │  │  Provider   │  │  Provider │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    TRACKING LAYER                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Delivery   │  │  Open/Read  │  │  Click      │  │  Analytics│  │  │
│  │  │  Tracking   │  │  Tracking   │  │  Tracking   │  │  Engine   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
1.2 Notification Flow
text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  New         │───►│  Matching    │───►│  Queue       │───►│  Delivery    │
│  Opportunity │    │  Engine      │    │  Manager     │    │  Engine      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                       │
                                                                       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Notification│◄───│  Delivery    │◄───│  Format      │◄───│  Template    │
│  Tracking    │    │  Status      │    │  Message     │    │  Engine      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
2. Matching Engine
2.1 Profile-Based Matching
python
# matching/profile_matcher.py
from typing import Dict, List, Optional
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class ProfileMatcher:
    def __init__(self):
        self.location_weight = 0.25
        self.budget_weight = 0.20
        self.skills_weight = 0.20
        self.education_weight = 0.15
        self.experience_weight = 0.10
        self.visa_weight = 0.10
    
    async def match_opportunity(
        self,
        profile: Dict,
        opportunity: Dict,
        domain: str
    ) -> Dict:
        """Match opportunity against user profile"""
        
        if domain == 'jobs':
            return await self._match_job(profile, opportunity)
        elif domain == 'real_estate':
            return await self._match_real_estate(profile, opportunity)
        elif domain == 'vehicles':
            return await self._match_vehicle(profile, opportunity)
        else:
            return await self._match_general(profile, opportunity)
    
    async def _match_job(self, profile: Dict, job: Dict) -> Dict:
        """Match job against profile"""
        
        scores = {}
        
        # Location match
        scores['location'] = await self._match_location(
            profile.get('preferred_countries', []),
            job.get('location', {})
        )
        
        # Budget/Salary match
        scores['budget'] = await self._match_budget(
            profile.get('salary_range', {}),
            job.get('salary', {})
        )
        
        # Skills match
        scores['skills'] = await self._match_skills(
            profile.get('skills', []),
            job.get('skills_required', [])
        )
        
        # Education match
        scores['education'] = await self._match_education(
            profile.get('education', {}),
            job.get('education_level', '')
        )
        
        # Experience match
        scores['experience'] = await self._match_experience(
            profile.get('experience_years', 0),
            job.get('experience_level', '')
        )
        
        # Visa sponsorship match
        scores['visa'] = await self._match_visa(
            profile.get('visa_status', ''),
            job.get('visa_sponsorship', False)
        )
        
        # Calculate overall score
        overall = (
            scores['location'] * self.location_weight +
            scores['budget'] * self.budget_weight +
            scores['skills'] * self.skills_weight +
            scores['education'] * self.education_weight +
            scores['experience'] * self.experience_weight +
            scores['visa'] * self.visa_weight
        )
        
        return {
            'overall_score': overall,
            'dimensions': scores,
            'domain': 'jobs'
        }
    
    async def _match_location(self, preferred_countries: List[str], location: Dict) -> float:
        """Calculate location match score"""
        
        if not preferred_countries:
            return 0.5
        
        country = location.get('country', '')
        if not country:
            return 0.3
        
        if country in preferred_countries:
            return 1.0
        
        # Check for country variations
        for preferred in preferred_countries:
            if preferred.lower() in country.lower():
                return 0.8
        
        return 0.0
    
    async def _match_budget(self, salary_range: Dict, job_salary: Dict) -> float:
        """Calculate budget/salary match score"""
        
        if not salary_range or not job_salary:
            return 0.5
        
        # Normalize currencies (simplified)
        if salary_range.get('currency') != job_salary.get('currency'):
            # Could convert currency here
            pass
        
        # Check if salary range overlaps
        user_min = salary_range.get('min', 0)
        user_max = salary_range.get('max', float('inf'))
        
        job_min = job_salary.get('min', 0)
        job_max = job_salary.get('max', float('inf'))
        
        # Calculate overlap
        overlap_min = max(user_min, job_min)
        overlap_max = min(user_max, job_max)
        
        if overlap_min > overlap_max:
            return 0.0
        
        # Calculate score based on overlap
        if job_max == float('inf') and user_max == float('inf'):
            return 0.5
        
        if job_max == float('inf'):
            # Only user has max
            return 0.6
        
        if user_max == float('inf'):
            # Only job has max
            return 0.6
        
        return min(1.0, (overlap_max - overlap_min) / (user_max - user_min))
    
    async def _match_skills(self, user_skills: List[str], required_skills: List[str]) -> float:
        """Calculate skills match score"""
        
        if not required_skills:
            return 0.5
        
        if not user_skills:
            return 0.0
        
        # Normalize skills
        user_skills = [s.lower().strip() for s in user_skills]
        required_skills = [s.lower().strip() for s in required_skills]
        
        # Calculate Jaccard similarity
        intersection = set(user_skills).intersection(set(required_skills))
        union = set(user_skills).union(set(required_skills))
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    async def _match_education(self, user_education: Dict, required_education: str) -> float:
        """Calculate education match score"""
        
        if not required_education:
            return 0.5
        
        if not user_education:
            return 0.0
        
        # Education level mapping
        level_map = {
            'high_school': 1,
            'bachelor': 2,
            'master': 3,
            'phd': 4,
            'diploma': 2
        }
        
        user_level = user_education.get('level', '')
        user_level_score = level_map.get(user_level, 0)
        
        required_level = required_education.lower()
        required_level_score = level_map.get(required_level, 0)
        
        if user_level_score == 0:
            return 0.0
        
        if user_level_score >= required_level_score:
            return 1.0
        
        return user_level_score / required_level_score
    
    async def _match_experience(self, user_years: int, required_level: str) -> float:
        """Calculate experience match score"""
        
        if not required_level:
            return 0.5
        
        # Experience level mapping
        level_map = {
            'entry': 2,
            'mid': 5,
            'senior': 8,
            'lead': 10,
            'executive': 12
        }
        
        required_years = level_map.get(required_level.lower(), 0)
        
        if required_years == 0:
            return 0.5
        
        if user_years >= required_years:
            return 1.0
        
        return user_years / required_years
    
    async def _match_visa(self, user_visa: str, visa_sponsorship: bool) -> float:
        """Calculate visa match score"""
        
        if not visa_sponsorship:
            return 1.0
        
        if not user_visa:
            return 0.5
        
        if user_visa.lower() in ['none', 'visitor']:
            return 1.0 if visa_sponsorship else 0.0
        
        return 0.5
3. Delivery Engine
3.1 Notification Delivery
python
# delivery/notification_delivery.py
from typing import Dict, List, Optional
from datetime import datetime
import asyncio

class NotificationDelivery:
    def __init__(self, providers: Dict):
        self.providers = providers
        self.queue = asyncio.Queue()
        self.workers = []
    
    async def deliver(self, notification: Dict) -> bool:
        """Deliver notification through appropriate channel"""
        
        try:
            # Get user preferences
            user_id = notification.get('user_id')
            preferences = await self._get_user_preferences(user_id)
            
            # Determine delivery channels
            channels = self._determine_channels(preferences)
            
            # Format message for each channel
            formatted_messages = await self._format_messages(
                notification,
                channels
            )
            
            # Deliver through each channel
            results = []
            for channel, message in formatted_messages.items():
                if channel in self.providers:
                    result = await self._deliver_channel(
                        channel,
                        message,
                        user_id
                    )
                    results.append(result)
            
            # Track delivery
            await self._track_delivery(notification, results)
            
            return all(results)
            
        except Exception as e:
            # Log error
            print(f"Delivery failed: {e}")
            return False
    
    def _determine_channels(self, preferences: Dict) -> List[str]:
        """Determine delivery channels based on preferences"""
        
        channels = preferences.get('notification_channels', ['email'])
        
        # Check if real-time or scheduled
        if preferences.get('real_time_alerts'):
            return channels
        
        # For scheduled, use only email and push
        return [c for c in channels if c in ['email', 'push']]
    
    async def _format_messages(self, notification: Dict, channels: List[str]) -> Dict:
        """Format message for different channels"""
        
        messages = {}
        
        for channel in channels:
            if channel == 'email':
                messages[channel] = self._format_email(notification)
            elif channel == 'whatsapp':
                messages[channel] = self._format_whatsapp(notification)
            elif channel == 'web':
                messages[channel] = self._format_web(notification)
            elif channel == 'push':
                messages[channel] = self._format_push(notification)
        
        return messages
    
    def _format_email(self, notification: Dict) -> Dict:
        """Format for email channel"""
        
        return {
            'to': notification.get('user_email'),
            'subject': notification.get('title', 'New Opportunity Alert'),
            'body': notification.get('message', ''),
            'template': 'opportunity_alert',
            'context': {
                'opportunity': notification.get('opportunity'),
                'match_score': notification.get('match_score')
            }
        }
    
    def _format_whatsapp(self, notification: Dict) -> Dict:
        """Format for WhatsApp channel"""
        
        return {
            'to': notification.get('user_phone'),
            'message': notification.get('message', ''),
            'buttons': [
                {
                    'label': 'View Details',
                    'action': 'view_opportunity',
                    'data': {'opportunity_id': notification.get('opportunity_id')}
                }
            ]
        }
    
    def _format_web(self, notification: Dict) -> Dict:
        """Format for web channel"""
        
        return {
            'user_id': notification.get('user_id'),
            'title': notification.get('title', 'New Alert'),
            'message': notification.get('message', ''),
            'url': f"/opportunities/{notification.get('opportunity_id')}",
            'icon': '🔔'
        }
    
    def _format_push(self, notification: Dict) -> Dict:
        """Format for push notification"""
        
        return {
            'title': notification.get('title', 'New Opportunity Alert'),
            'body': notification.get('message', ''),
            'data': {
                'opportunity_id': notification.get('opportunity_id'),
                'type': 'opportunity_alert'
            }
        }
    
    async def _deliver_channel(self, channel: str, message: Dict, user_id: str) -> bool:
        """Deliver message through specific channel"""
        
        provider = self.providers.get(channel)
        if not provider:
            return False
        
        try:
            result = await provider.send(message)
            return result.get('success', False)
        except Exception as e:
            print(f"Channel {channel} delivery failed: {e}")
            return False
3.2 Templates
python
# delivery/templates.py
from typing import Dict, Optional

class NotificationTemplates:
    def __init__(self):
        self.templates = {
            'email': {
                'opportunity_alert': """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            body { font-family: Arial, sans-serif; }
                            .container { max-width: 600px; margin: 0 auto; }
                            .header { background: #1a237e; color: white; padding: 20px; }
                            .content { padding: 20px; }
                            .opportunity { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
                            .match-score { background: #4caf50; color: white; padding: 2px 10px; border-radius: 3px; }
                            .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>🔔 New Opportunity Alert</h1>
                            </div>
                            <div class="content">
                                <p>Hi {{ user_name }},</p>
                                <p>We found a new opportunity that matches your preferences!</p>
                                
                                <div class="opportunity">
                                    <h2>{{ opportunity.title }}</h2>
                                    <p><strong>Domain:</strong> {{ opportunity.domain }}</p>
                                    <p><strong>Location:</strong> {{ opportunity.location }}</p>
                                    <p><strong>Match Score:</strong> 
                                        <span class="match-score">{{ match_score }}%</span>
                                    </p>
                                    {{ #salary }}
                                    <p><strong>Salary:</strong> {{ salary }}</p>
                                    {{ /salary }}
                                    <p>{{ opportunity.description|truncate(200) }}</p>
                                    <a href="{{ opportunity.url }}">View Details</a>
                                </div>
                                
                                <p>Best regards,<br>WildAutomations Team</p>
                            </div>
                            <div class="footer">
                                <p>You're receiving this because you subscribed to notifications.</p>
                                <p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
                            </div>
                        </div>
                    </body>
                    </html>
                """,
                
                'daily_summary': """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            body { font-family: Arial, sans-serif; }
                            .container { max-width: 600px; margin: 0 auto; }
                            .header { background: #1a237e; color: white; padding: 20px; }
                            .content { padding: 20px; }
                            .opportunity { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
                            .match-score { background: #4caf50; color: white; padding: 2px 10px; border-radius: 3px; }
                            .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                            .summary-stats { background: #f5f5f5; padding: 15px; margin: 10px 0; }
                            .stat { display: inline-block; margin-right: 30px; }
                            .stat-number { font-size: 24px; font-weight: bold; color: #1a237e; }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>📊 Daily Summary</h1>
                            </div>
                            <div class="content">
                                <p>Hi {{ user_name }},</p>
                                <p>Here's your daily summary of opportunities!</p>
                                
                                <div class="summary-stats">
                                    <div class="stat">
                                        <div class="stat-number">{{ total_opportunities }}</div>
                                        <div>Total Opportunities</div>
                                    </div>
                                    <div class="stat">
                                        <div class="stat-number">{{ new_today }}</div>
                                        <div>New Today</div>
                                    </div>
                                    <div class="stat">
                                        <div class="stat-number">{{ match_rate }}%</div>
                                        <div>Match Rate</div>
                                    </div>
                                </div>
                                
                                <h3>Top Opportunities</h3>
                                {{ #top_opportunities }}
                                <div class="opportunity">
                                    <h4>{{ title }}</h4>
                                    <p>{{ description|truncate(100) }}</p>
                                    <a href="{{ url }}">View Details</a>
                                </div>
                                {{ /top_opportunities }}
                                
                                <p>Best regards,<br>WildAutomations Team</p>
                            </div>
                            <div class="footer">
                                <p>You're receiving this because you subscribed to daily summaries.</p>
                                <p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
                            </div>
                        </div>
                    </body>
                    </html>
                """
            },
            
            'whatsapp': {
                'opportunity_alert': """
                    🔔 New Opportunity Alert!
                    
                    {title}
                    Domain: {domain}
                    Location: {location}
                    Match Score: {match_score}%
                    {salary}
                    
                    {description}
                    
                    Reply with "view {id}" for details
                    Reply with "save {id}" to save this opportunity
                    Reply with "notify me" for similar opportunities
                """,
                
                'daily_summary': """
                    📊 Daily Summary for {date}
                    
                    Total Opportunities: {total}
                    New Today: {new}
                    Match Rate: {match_rate}%
                    
                    Top Matches:
                    {top_opportunities}
                    
                    Reply with "help" for options
                """
            }
        }
    
    def render(self, channel: str, template_name: str, context: Dict) -> str:
        """Render template with context"""
        
        channel_templates = self.templates.get(channel, {})
        template = channel_templates.get(template_name)
        
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Simple template rendering
        rendered = template
        for key, value in context.items():
            rendered = rendered.replace('{' + key + '}', str(value))
        
        return rendered
4. Scheduling Engine
python
# delivery/scheduler.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import croniter

class NotificationScheduler:
    def __init__(self, db_session, queue_manager):
        self.db = db_session
        self.queue = queue_manager
    
    async def schedule_notification(
        self,
        user_id: str,
        opportunity_id: str,
        schedule_type: str,
        schedule_time: Optional[datetime] = None
    ) -> Dict:
        """Schedule a notification"""
        
        # Validate schedule type
        valid_types = ['immediate', 'scheduled', 'daily_summary', 'weekly_summary']
        if schedule_type not in valid_types:
            raise ValueError(f"Invalid schedule type: {schedule_type}")
        
        # Create schedule
        schedule = {
            'user_id': user_id,
            'opportunity_id': opportunity_id,
            'type': schedule_type,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'scheduled_time': schedule_time,
            'executed_at': None
        }
        
        # If immediate, process right away
        if schedule_type == 'immediate':
            await self._process_immediate(schedule)
        else:
            # Store scheduled notification
            await self._store_schedule(schedule)
        
        return schedule
    
    async def process_scheduled_notifications(self):
        """Process all due scheduled notifications"""
        
        # Get pending notifications
        pending = await self._get_pending_notifications()
        
        for notification in pending:
            # Check if due
            if self._is_due(notification):
                await self._process_notification(notification)
    
    async def _process_immediate(self, schedule: Dict):
        """Process immediate notification"""
        
        # Add to queue
        await self.queue.enqueue({
            'type': 'notification',
            'user_id': schedule['user_id'],
            'opportunity_id': schedule['opportunity_id'],
            'priority': 'high'
        })
        
        # Update schedule
        schedule['status'] = 'queued'
        schedule['executed_at'] = datetime.utcnow()
        await self._update_schedule(schedule)
    
    async def _process_notification(self, notification: Dict):
        """Process a scheduled notification"""
        
        # Get user preferences
        preferences = await self._get_user_preferences(notification['user_id'])
        
        # Check if notification should be sent
        if not self._should_send(notification, preferences):
            notification['status'] = 'skipped'
            await self._update_schedule(notification)
            return
        
        # Add to queue
        await self.queue.enqueue({
            'type': 'notification',
            'user_id': notification['user_id'],
            'opportunity_id': notification['opportunity_id']
        })
        
        # Update schedule
        notification['status'] = 'queued'
        notification['executed_at'] = datetime.utcnow()
        await self._update_schedule(notification)
    
    def _is_due(self, notification: Dict) -> bool:
        """Check if notification is due"""
        
        scheduled_time = notification.get('scheduled_time')
        if not scheduled_time:
            return False
        
        return scheduled_time <= datetime.utcnow()
    
    def _should_send(self, notification: Dict, preferences: Dict) -> bool:
        """Check if notification should be sent based on preferences"""
        
        # Check if notifications are enabled
        if not preferences.get('notifications_enabled', True):
            return False
        
        # Check domain preferences
        domains = preferences.get('domains', [])
        opportunity = self._get_opportunity(notification['opportunity_id'])
        
        if opportunity and opportunity.get('domain') not in domains:
            return False
        
        return True