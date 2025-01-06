from dataclasses import dataclass
from typing import Optional, Dict
from contextvars import ContextVar


@dataclass
class User:
    email: str
    username: str
    full_name: str


@dataclass
class UserSettings:
    dark_mode: bool = False


class UserState:
    def __init__(self):
        self.current_user: Optional[User] = None
        self._settings: Dict[str, UserSettings] = {}

    async def fetch_user(self, api_client):
        """Fetch current user data from API"""
        try:
            user_data = await api_client.get("/api/auth/users/me")
            self.current_user = User(
                email=user_data.get("email", ""),
                username=user_data.get("username", ""),
                full_name=user_data.get("full_name", ""),
            )
            return self.current_user
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None

    def get_user(self) -> Optional[User]:
        return self.current_user

    async def get_user_settings(self, api_client) -> UserSettings:
        """Get user settings for current user"""
        if not self.current_user:
            return UserSettings()

        if self.current_user.email not in self._settings:
            try:
                settings_data = await api_client.get("/api/user/settings/theme")
                self._settings[self.current_user.email] = UserSettings(
                    dark_mode=settings_data.get("dark_mode", False)
                )
            except Exception as e:
                print(f"Error fetching user settings: {e}")
                return UserSettings()

        return self._settings[self.current_user.email]

    async def update_user_settings(self, api_client, **settings):
        """Update settings for current user"""
        if not self.current_user:
            return None

        try:
            await api_client.post("/api/user/settings/theme", json=settings)
            current_settings = self._settings.get(
                self.current_user.email, UserSettings()
            )
            for key, value in settings.items():
                setattr(current_settings, key, value)
            self._settings[self.current_user.email] = current_settings
            return current_settings
        except Exception as e:
            print(f"Error updating user settings: {e}")
            raise


# Create a context variable for user state
user_state_var: ContextVar[UserState] = ContextVar("user_state")


async def get_user_state() -> UserState:
    """Get or create user state for current context"""
    try:
        return user_state_var.get()
    except LookupError:
        state = UserState()
        user_state_var.set(state)
        return state


# Initialize global instance (for backward compatibility)
user_state = UserState()
