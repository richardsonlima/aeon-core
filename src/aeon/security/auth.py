"""Authentication module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import secrets
import logging

logger = logging.getLogger(__name__)


class AuthType(Enum):
    """Authentication types."""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    HMAC = "hmac"
    BASIC = "basic"


@dataclass
class Credentials:
    """User credentials."""
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Token:
    """Authentication token."""
    token_id: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    auth_type: AuthType = AuthType.BEARER_TOKEN
    subject: str = ""
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=1))
    scopes: set = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def has_scope(self, scope: str) -> bool:
        """Check if token has scope."""
        return scope in self.scopes


class AuthProvider(ABC):
    """Abstract authentication provider."""
    
    @abstractmethod
    async def authenticate(self, credentials: Credentials) -> Optional[Token]:
        """Authenticate credentials and return token."""
        pass
    
    @abstractmethod
    async def validate_token(self, token: Token) -> bool:
        """Validate token."""
        pass
    
    @abstractmethod
    async def refresh_token(self, token: Token) -> Optional[Token]:
        """Refresh token."""
        pass
    
    @abstractmethod
    async def revoke_token(self, token: Token) -> None:
        """Revoke token."""
        pass


class APIKeyAuthProvider(AuthProvider):
    """API Key authentication."""
    
    def __init__(self):
        self.valid_keys: Dict[str, Dict[str, Any]] = {}
    
    def register_key(self, api_key: str, scopes: set, metadata: Optional[Dict] = None) -> None:
        """Register valid API key."""
        self.valid_keys[api_key] = {
            "scopes": scopes,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        logger.info(f"API key registered")
    
    async def authenticate(self, credentials: Credentials) -> Optional[Token]:
        """Authenticate with API key."""
        if not credentials.api_key:
            return None
        
        if credentials.api_key not in self.valid_keys:
            logger.warning("Invalid API key")
            return None
        
        key_info = self.valid_keys[credentials.api_key]
        token = Token(
            auth_type=AuthType.API_KEY,
            subject=credentials.metadata.get("username", "api_user"),
            scopes=key_info["scopes"],
            metadata=key_info["metadata"]
        )
        
        logger.info(f"API key authentication successful for {token.subject}")
        return token
    
    async def validate_token(self, token: Token) -> bool:
        """Validate token."""
        return not token.is_expired()
    
    async def refresh_token(self, token: Token) -> Optional[Token]:
        """Refresh token."""
        if token.is_expired():
            return None
        
        new_token = Token(
            auth_type=token.auth_type,
            subject=token.subject,
            scopes=token.scopes,
            metadata=token.metadata
        )
        return new_token
    
    async def revoke_token(self, token: Token) -> None:
        """Revoke token."""
        logger.info(f"Token revoked: {token.token_id}")


class TokenManager:
    """Manages tokens lifecycle."""
    
    def __init__(self, providers: Optional[Dict[str, AuthProvider]] = None):
        self.providers = providers or {}
        self.tokens: Dict[str, Token] = {}
        self.stats = {
            "total_issued": 0,
            "total_validated": 0,
            "total_revoked": 0,
            "total_refreshed": 0
        }
    
    def register_provider(self, name: str, provider: AuthProvider) -> None:
        """Register authentication provider."""
        self.providers[name] = provider
        logger.info(f"Auth provider registered: {name}")
    
    async def authenticate(
        self,
        credentials: Credentials,
        provider_name: str = "default"
    ) -> Optional[Token]:
        """Authenticate using provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            logger.error(f"Unknown auth provider: {provider_name}")
            return None
        
        token = await provider.authenticate(credentials)
        if token:
            self.tokens[token.token_id] = token
            self.stats["total_issued"] += 1
            logger.info(f"Token issued for {token.subject}")
        
        return token
    
    async def validate_token(self, token_id: str, provider_name: str = "default") -> bool:
        """Validate token."""
        token = self.tokens.get(token_id)
        if not token:
            return False
        
        provider = self.providers.get(provider_name)
        if not provider:
            return False
        
        valid = await provider.validate_token(token)
        if valid:
            self.stats["total_validated"] += 1
        
        return valid
    
    async def refresh_token(self, token_id: str, provider_name: str = "default") -> Optional[Token]:
        """Refresh token."""
        token = self.tokens.get(token_id)
        if not token:
            return None
        
        provider = self.providers.get(provider_name)
        if not provider:
            return None
        
        new_token = await provider.refresh_token(token)
        if new_token:
            del self.tokens[token_id]
            self.tokens[new_token.token_id] = new_token
            self.stats["total_refreshed"] += 1
            logger.info(f"Token refreshed for {new_token.subject}")
        
        return new_token
    
    async def revoke_token(self, token_id: str, provider_name: str = "default") -> None:
        """Revoke token."""
        token = self.tokens.get(token_id)
        if not token:
            return
        
        provider = self.providers.get(provider_name)
        if provider:
            await provider.revoke_token(token)
        
        del self.tokens[token_id]
        self.stats["total_revoked"] += 1
    
    def get_token(self, token_id: str) -> Optional[Token]:
        """Get token by ID."""
        return self.tokens.get(token_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token statistics."""
        return {
            **self.stats,
            "active_tokens": len(self.tokens)
        }
