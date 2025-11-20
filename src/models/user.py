from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class User:
    id: int
    username: str
    first_name: str
    last_name: str
    store_code: Optional[str] = None
    last_activity: Optional[datetime] = None
    is_active: bool = True

    def get_full_name(self) -> str:
        """Get user's full name"""
        names = [self.first_name, self.last_name]
        return ' '.join(filter(None, names))

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()


@dataclass
class UserSession:
    user_id: int
    store_code: str
    start_time: datetime
    last_action: datetime
    actions: List[str]

    def add_action(self, action: str):
        """Add action to session history"""
        self.actions.append(action)
        self.last_action = datetime.now()

    def get_session_duration(self) -> float:
        """Get session duration in seconds"""
        return (datetime.now() - self.start_time).total_seconds()