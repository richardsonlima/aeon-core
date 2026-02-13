"""Permissions and authorization."""

from enum import Enum
from typing import Set, Dict, List, Optional
from abc import ABC, abstractmethod


class Permission(Enum):
    """Standard permissions."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"
    CONFIGURE = "configure"


class PermissionSet:
    """Collection of permissions."""
    
    def __init__(self, permissions: Optional[Set[Permission]] = None):
        self.permissions = permissions or set()
    
    def grant(self, permission: Permission) -> None:
        """Grant permission."""
        self.permissions.add(permission)
    
    def revoke(self, permission: Permission) -> None:
        """Revoke permission."""
        self.permissions.discard(permission)
    
    def has(self, permission: Permission) -> bool:
        """Check if permission is granted."""
        if Permission.ADMIN in self.permissions:
            return True
        return permission in self.permissions
    
    def has_all(self, permissions: Set[Permission]) -> bool:
        """Check if all permissions are granted."""
        if Permission.ADMIN in self.permissions:
            return True
        return permissions.issubset(self.permissions)
    
    def has_any(self, permissions: Set[Permission]) -> bool:
        """Check if any permission is granted."""
        if Permission.ADMIN in self.permissions:
            return True
        return bool(permissions & self.permissions)


class PolicyRule(ABC):
    """Abstract policy rule."""
    
    @abstractmethod
    def evaluate(self, context: Dict) -> bool:
        """Evaluate rule in context."""
        pass


class SimpleRule(PolicyRule):
    """Simple permission rule."""
    
    def __init__(self, permission: Permission):
        self.permission = permission
    
    def evaluate(self, context: Dict) -> bool:
        """Check if permission granted."""
        permissions = context.get("permissions", PermissionSet())
        return permissions.has(self.permission)


class RoleBasedRule(PolicyRule):
    """Role-based access control."""
    
    def __init__(self, allowed_roles: Set[str]):
        self.allowed_roles = allowed_roles
    
    def evaluate(self, context: Dict) -> bool:
        """Check if role allowed."""
        user_role = context.get("role")
        return user_role in self.allowed_roles


class PolicyEvaluator:
    """Evaluates authorization policies."""
    
    def __init__(self):
        self.policies: Dict[str, List[PolicyRule]] = {}
    
    def register_policy(self, policy_name: str, rules: List[PolicyRule]) -> None:
        """Register policy."""
        self.policies[policy_name] = rules
    
    def evaluate(self, policy_name: str, context: Dict) -> bool:
        """Evaluate policy."""
        rules = self.policies.get(policy_name, [])
        if not rules:
            return False
        
        # All rules must pass (AND logic)
        return all(rule.evaluate(context) for rule in rules)
    
    def evaluate_any(self, policy_names: List[str], context: Dict) -> bool:
        """Evaluate any of the policies."""
        # At least one policy must pass (OR logic)
        return any(self.evaluate(name, context) for name in policy_names)
