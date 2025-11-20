import hashlib
import hmac
import os
from typing import Optional


class SecurityUtils:
    @staticmethod
    def validate_user_access(user_id: int, allowed_users: list) -> bool:
        """Validate user access"""
        return user_id in allowed_users

    @staticmethod
    def generate_request_signature(data: dict, secret: str) -> str:
        """Generate HMAC signature for API requests"""
        message = ''.join(str(v) for v in data.values())
        return hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize user input"""
        if not input_str:
            return ""

        # Remove potentially dangerous characters
        sanitized = input_str.strip()
        sanitized = re.sub(r'[;\"\']', '', sanitized)

        return sanitized

    @staticmethod
    def validate_store_access(user_id: int, store_code: str) -> bool:
        """Validate if user has access to specific store"""
        # Implement store-based access control if needed
        return True