from contextlib import suppress
from dataclasses import dataclass
from typing import Optional

from nicegui import app


@dataclass
class Auth:
    authenticated: bool
    username: str
    access_token: str
    token_type: str


@dataclass
class User:
    email: str
    username: str
    full_name: str
    is_admin: bool


@dataclass
class UserSettings:
    dark_mode: bool = False


class UserState:
    def __init__(self):
        pass

    async def fetch_user(self, api_client) -> Optional[User]:
        """Fetch current user data from API"""
        try:
            user_data = await api_client.get("/api/auth/users/me")
            app.storage.user.update(
                {
                    "user": {
                        "email": user_data.get("email", ""),
                        "username": user_data.get("username", ""),
                        "full_name": user_data.get("full_name", ""),
                        "is_admin": user_data.get("is_admin", False),
                    }
                }
            )

            return User(
                email=user_data.get("email", ""),
                username=user_data.get("username", ""),
                full_name=user_data.get("full_name", ""),
                is_admin=user_data.get("is_admin", False),
            )
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None

    def get_auth(self) -> Optional[Auth]:
        if app.storage.user.get("auth"):
            return Auth(
                authenticated=app.storage.user.get("auth").get("authenticated", False),
                username=app.storage.user.get("auth").get("username", ""),
                access_token=app.storage.user.get("auth").get("access_token", ""),
                token_type=app.storage.user.get("auth").get("token_type", ""),
            )
        else:
            return None

    def update_auth(self, **auth):
        app.storage.user.update(
            {
                "auth": {
                    "authenticated": auth.get("authenticated", False),
                    "username": auth.get("username", ""),
                    "access_token": auth.get("access_token", ""),
                    "token_type": auth.get("token_type", ""),
                }
            }
        )

    def clear_auth(self):
        with suppress(Exception):
            app.storage.user.pop("auth")

    async def get_user(self, api_client) -> Optional[User]:
        # return self.current_user
        if app.storage.user.get("user"):
            return User(
                email=app.storage.user.get("user").get("email", ""),
                username=app.storage.user.get("user").get("username", ""),
                full_name=app.storage.user.get("user").get("full_name", ""),
                is_admin=app.storage.user.get("user").get("is_admin", False),
            )
        else:
            return await self.fetch_user(api_client)

    def clear_user(self):
        with suppress(Exception):
            app.storage.user.pop("user")

    async def get_user_settings(self, api_client) -> UserSettings:
        """Get user settings for current user"""

        if not app.storage.user.get("user"):
            return UserSettings()

        if not app.storage.user.get("user_settings"):
            try:
                settings_data = await api_client.get("/api/user/settings/theme")

                app.storage.user.update(
                    {
                        "user_settings": {
                            "dark_mode": settings_data.get("dark_mode", False),
                        }
                    }
                )
            except Exception as e:
                print(f"Error fetching user settings: {e}")
                return UserSettings()

        return UserSettings(
            dark_mode=app.storage.user.get("user_settings").get("dark_mode", False),
        )

    async def update_user_settings(self, api_client, **settings):
        """Update settings for current user"""

        if not app.storage.user.get("user"):
            return None

        try:
            await api_client.post("/api/user/settings/theme", json=settings)

            current_settings = await self.get_user_settings(api_client)
            for key, value in settings.items():
                setattr(current_settings, key, value)
            app.storage.user.update({"user_settings": current_settings.__dict__})

            return current_settings
        except Exception as e:
            print(f"Error updating user settings: {e}")
            raise

    def clear_user_settings(self):
        with suppress(Exception):
            app.storage.user.pop("user_settings")

    def update_redirect_path(self, redirect_path: str):
        app.storage.user.update("redirect", redirect_path)

    def get_redirect_path(self, default="/ui/chat"):
        return app.storage.user.get("redirect", default)

    def clear_all(self):
        self.clear_auth()
        self.clear_user()
        self.clear_user_settings()
        # app.storage.user.clear()


# # Create a context variable for user state
# user_state_var: ContextVar[UserState] = ContextVar("user_state")
#
#
# def get_user_state() -> UserState:
#     """Get or create user state for current context"""
#     try:
#         return user_state_var.get()
#     except LookupError:
#         state = UserState()
#         user_state_var.set(state)
#         return state


# Initialize global instance (for backward compatibility)
user_state = UserState()
