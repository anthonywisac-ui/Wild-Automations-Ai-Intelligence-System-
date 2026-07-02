1. Security Overview
1.1 Security Layers
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SECURITY ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    NETWORK SECURITY                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Firewall   │  │  WAF        │  │  DDoS       │  │  VPN      │  │  │
│  │  │  Rules      │  │  (AWS WAF)  │  │  Protection │  │  Access   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    APPLICATION SECURITY                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  AuthN/AuthZ│  │  Input      │  │  Output     │  │  Rate     │  │  │
│  │  │  (JWT/RBAC) │  │  Validation │  │  Encoding   │  │  Limiting │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    DATA SECURITY                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Encryption │  │  PII        │  │  Data       │  │  Backup   │  │  │
│  │  │  (At Rest)  │  │  Protection │  │  Masking    │  │  Security │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    COMPLIANCE & AUDIT                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Audit Logs │  │  GDPR       │  │  SOC2       │  │  ISO27001 │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

1.2 Security Requirements
Security Requirements:
  Authentication:
    - Multi-factor authentication (MFA)
    - Password policies (minimum 12 characters)
    - Session management with timeout
    - JWT with short-lived tokens
    - Refresh token rotation
    
  Authorization:
    - Role-based access control (RBAC)
    - Least privilege principle
    - API scope restrictions
    - Resource-level permissions
    
  Data Protection:
    - Encryption at rest (AES-256)
    - Encryption in transit (TLS 1.3)
    - PII data masking
    - Secure key management (AWS KMS)
    
  Network Security:
    - VPC isolation
    - Security groups and NACLs
    - WAF protection
    - DDoS protection (AWS Shield)
    
  Application Security:
    - Input validation (Pydantic)
    - SQL injection prevention (ORM)
    - XSS protection
    - CSRF protection
    - Rate limiting (1000 req/min)
    
  Compliance:
    - GDPR compliance
    - CCPA compliance
    - Data residency requirements
    - Breach notification procedures
    - Privacy policy enforcement
	
2. Authentication & Authorization
2.1 JWT Implementation

# security/jwt.py
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
import secrets

class JWTManager:
    def __init__(self, config: Dict):
        self.secret_key = config.get('secret_key')
        self.algorithm = config.get('algorithm', 'HS256')
        self.access_token_expiry = config.get('access_token_expiry', 3600)
        self.refresh_token_expiry = config.get('refresh_token_expiry', 86400 * 7)
        self.refresh_token_store = {}
    
    def create_access_token(self, user_id: str, scopes: List[str] = None) -> str:
        """Create access token"""
        payload = {
            'user_id': user_id,
            'type': 'access',
            'scopes': scopes or [],
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=self.access_token_expiry)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token"""
        token = secrets.token_urlsafe(32)
        self.refresh_token_store[token] = {
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(seconds=self.refresh_token_expiry)
        }
        return token
    
    def verify_token(self, token: str, required_scopes: List[str] = None) -> Dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get('type') != 'access':
                raise InvalidTokenError("Invalid token type")
            
            # Check scopes
            if required_scopes:
                token_scopes = payload.get('scopes', [])
                for scope in required_scopes:
                    if scope not in token_scopes:
                        raise InsufficientScopeError(f"Missing scope: {scope}")
            
            return payload
            
        except JWTError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
    
    def verify_refresh_token(self, token: str) -> Optional[str]:
        """Verify refresh token"""
        token_data = self.refresh_token_store.get(token)
        if not token_data:
            return None
        
        if token_data['expires_at'] < datetime.utcnow():
            del self.refresh_token_store[token]
            return None
        
        return token_data['user_id']
    
    def revoke_refresh_token(self, token: str) -> bool:
        """Revoke refresh token"""
        if token in self.refresh_token_store:
            del self.refresh_token_store[token]
            return True
        return False
		
2.2 RBAC Implementation
# security/rbac.py
from enum import Enum
from typing import List, Dict, Optional

class Role(Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"
    API = "api"

class Permission(Enum):
    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Opportunity permissions
    OPPORTUNITY_READ = "opportunity:read"
    OPPORTUNITY_WRITE = "opportunity:write"
    OPPORTUNITY_DELETE = "opportunity:delete"
    
    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_DELETE = "admin:delete"
    
    # System permissions
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_DELETE = "system:delete"

class RBACManager:
    def __init__(self):
        self.role_permissions = self._initialize_permissions()
    
    def _initialize_permissions(self) -> Dict[Role, List[Permission]]:
        """Initialize role-permission mappings"""
        return {
            Role.ADMIN: [
                Permission.USER_READ,
                Permission.USER_WRITE,
                Permission.USER_DELETE,
                Permission.OPPORTUNITY_READ,
                Permission.OPPORTUNITY_WRITE,
                Permission.OPPORTUNITY_DELETE,
                Permission.ADMIN_READ,
                Permission.ADMIN_WRITE,
                Permission.ADMIN_DELETE,
                Permission.SYSTEM_READ,
                Permission.SYSTEM_WRITE,
                Permission.SYSTEM_DELETE
            ],
            Role.MANAGER: [
                Permission.USER_READ,
                Permission.USER_WRITE,
                Permission.OPPORTUNITY_READ,
                Permission.OPPORTUNITY_WRITE,
                Permission.OPPORTUNITY_DELETE,
                Permission.ADMIN_READ
            ],
            Role.USER: [
                Permission.USER_READ,
                Permission.USER_WRITE,
                Permission.OPPORTUNITY_READ,
                Permission.OPPORTUNITY_WRITE
            ],
            Role.GUEST: [
                Permission.OPPORTUNITY_READ
            ],
            Role.API: [
                Permission.OPPORTUNITY_READ,
                Permission.OPPORTUNITY_WRITE
            ]
        }
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check if role has permission"""
        permissions = self.role_permissions.get(role, [])
        return permission in permissions
    
    def get_permissions(self, role: Role) -> List[Permission]:
        """Get all permissions for role"""
        return self.role_permissions.get(role, [])
    
    def check_resource_access(self, role: Role, resource: str, action: str) -> bool:
        """Check if role can access resource with specific action"""
        permission = Permission(f"{resource}:{action}")
        return self.has_permission(role, permission)

# Dependency for FastAPI
async def require_permission(permission: Permission):
    """Dependency to check permission"""
    async def permission_dependency(current_user: User = Depends(get_current_user)):
        if not RBACManager().has_permission(current_user.role, permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return True
    return permission_dependency

# Usage in routes
@router.get("/admin/users")
async def get_users(
    has_permission: bool = Depends(require_permission(Permission.ADMIN_READ))
):
    """Get users (admin only)"""
    # Implementation
    pass
	
3. Data Protection
3.1 Encryption Service
# security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class EncryptionService:
    def __init__(self, config: Dict):
        self.key = self._derive_key(config.get('encryption_password'))
        self.fernet = Fernet(self.key)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        salt = b'salt_'  # In production, use a secure random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt data"""
        encrypted_data = self.fernet.encrypt(data.encode())
        return encrypted_data.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data"""
        decrypted_data = self.fernet.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    
    def encrypt_field(self, data: Dict, field: str) -> Dict:
        """Encrypt a specific field in dict"""
        if field in data and data[field]:
            data[field] = self.encrypt(data[field])
        return data
    
    def decrypt_field(self, data: Dict, field: str) -> Dict:
        """Decrypt a specific field in dict"""
        if field in data and data[field]:
            data[field] = self.decrypt(data[field])
        return data
		
3.2 PII Protection
# security/pii_protection.py
import re
from typing import Dict, Optional

class PIIProtection:
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\+?[\d\s\-\(\)]{7,15}\b',
            'credit_card': r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
            'ssn': r'\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b',
            'address': r'\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)',
            'name': r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        }
    
    def mask_data(self, data: str) -> str:
        """Mask sensitive data in text"""
        masked = data
        
        for pattern_name, pattern in self.patterns.items():
            masked = re.sub(pattern, self._mask_pattern, masked)
        
        return masked
    
    def _mask_pattern(self, match: re.Match) -> str:
        """Mask matched pattern"""
        matched_text = match.group(0)
        if '@' in matched_text:  # Email
            parts = matched_text.split('@')
            return f"{parts[0][:2]}***@{parts[1]}"
        elif re.match(self.patterns['phone'], matched_text):
            # Phone number
            return f"{matched_text[:3]}****{matched_text[-2:]}"
        else:
            # General masking
            return f"{matched_text[:2]}{'*' * (len(matched_text) - 4)}{matched_text[-2:]}"
    
    def sanitize_request_data(self, data: Dict) -> Dict:
        """Sanitize request data by masking PII"""
        sanitized = data.copy()
        
        for key, value in sanitized.items():
            if isinstance(value, str):
                sanitized[key] = self.mask_data(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_request_data(value)
        
        return sanitized
    
    def validate_no_pii(self, text: str) -> bool:
        """Check if text contains PII"""
        for pattern in self.patterns.values():
            if re.search(pattern, text):
                return False
        return True
4. Compliance
4.1 GDPR Compliance
# compliance/gdpr.py
from datetime import datetime
from typing import Dict, List, Optional
import json

class GDPRCompliance:
    def __init__(self, user_repo: UserRepository, log_service: LogService):
        self.user_repo = user_repo
        self.log_service = log_service
    
    async def get_user_data(self, user_id: str) -> Dict:
        """Get all user data for GDPR data portability"""
        user = await self.user_repo.get_by_id(user_id)
        
        # Get all user data
        data = {
            'user': user.to_dict(),
            'profile': await self.user_repo.get_profile(user_id),
            'preferences': await self.user_repo.get_preferences(user_id),
            'search_history': await self.user_repo.get_search_history(user_id),
            'notifications': await self.user_repo.get_notifications(user_id),
            'saved_opportunities': await self.user_repo.get_saved_opportunities(user_id)
        }
        
        # Add metadata
        data['metadata'] = {
            'export_date': datetime.utcnow().isoformat(),
            'format': 'json',
            'version': '1.0'
        }
        
        return data
    
    async def delete_user_data(self, user_id: str) -> bool:
        """Delete all user data (GDPR right to be forgotten)"""
        
        # Log the deletion
        await self.log_service.log_event(
            user_id=user_id,
            event_type='gdpr_deletion',
            details={'deleted_at': datetime.utcnow().isoformat()}
        )
        
        # Delete user data
        await self.user_repo.delete_user(user_id)
        await self.user_repo.delete_profile(user_id)
        await self.user_repo.delete_preferences(user_id)
        await self.user_repo.delete_search_history(user_id)
        await self.user_repo.delete_notifications(user_id)
        await self.user_repo.delete_saved_opportunities(user_id)
        
        return True
    
    async def anonymize_user_data(self, user_id: str) -> bool:
        """Anonymize user data"""
        
        # Remove PII
        await self.user_repo.anonymize_user(user_id)
        
        # Log anonymization
        await self.log_service.log_event(
            user_id=user_id,
            event_type='gdpr_anonymization',
            details={'anonymized_at': datetime.utcnow().isoformat()}
        )
        
        return True
    
    async def consent_management(self, user_id: str, consent_data: Dict) -> bool:
        """Manage user consent"""
        
        # Validate consent data
        if not self._validate_consent(consent_data):
            raise ValueError("Invalid consent data")
        
        # Store consent
        await self.user_repo.update_consent(user_id, consent_data)
        
        # Log consent
        await self.log_service.log_event(
            user_id=user_id,
            event_type='gdpr_consent',
            details={'consent': consent_data}
        )
        
        return True
    
    def _validate_consent(self, consent_data: Dict) -> bool:
        """Validate consent data"""
        required_fields = ['data_collection', 'marketing', 'analytics']
        
        for field in required_fields:
            if field not in consent_data:
                return False
            if not isinstance(consent_data[field], bool):
                return False
        
        return True
		
