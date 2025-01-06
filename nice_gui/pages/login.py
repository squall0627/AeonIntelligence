from dotenv import load_dotenv
from nicegui import ui, app
from nice_gui.utils.api_client import APIClient

load_dotenv()


class LoginPage:
    def __init__(self):
        self.api_client = APIClient()

        with ui.card().classes("flex flex-col items-center p-8 w-96 mx-auto mt-20"):
            ui.label("Login").classes("text-2xl mb-4")
            self.username = ui.input("Username").classes("w-full")
            self.password = ui.input("Password", password=True).classes("w-full")
            with ui.row().classes("w-full gap-2 mt-4"):
                ui.button("Login", on_click=self.handle_login).classes("flex-grow")
                ui.button(
                    "Register", on_click=lambda: ui.navigate.to("/register")
                ).classes("bg-green-500")

            # Setup enter key handler for password field
            self.password.on("keydown.enter", self.handle_login)

    async def handle_login(self):
        if not self.username.value or not self.password.value:
            ui.notify("Please enter both username and password", type="warning")
            return

        try:
            # Create loading spinner
            spinner = ui.spinner("dots")
            try:
                # Call login API
                result = await self.api_client.post(
                    "/api/auth/login_for_access_token",
                    False,
                    data={
                        "username": self.username.value,
                        "password": self.password.value,
                    },
                )

                if result:
                    # Update user storage with authentication info
                    app.storage.user.update(
                        {
                            "authenticated": True,
                            "username": self.username.value,
                            "access_token": result["access_token"],
                            "token_type": result["token_type"],
                            "is_admin": result.get("is_admin", False),
                        }
                    )

                    # Navigate to redirect path or default to knowledge page
                    redirect_path = app.storage.user.get("redirect", "/ui/chat")
                    ui.navigate.to(redirect_path)
                    ui.notify(f"Welcome back, {self.username.value}!", type="positive")
                else:
                    ui.notify("Invalid credentials", type="negative")
            finally:
                spinner.delete()

        except Exception as e:
            ui.notify(f"Login error: {str(e)}", type="negative")
