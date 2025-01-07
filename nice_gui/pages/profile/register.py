from nicegui import ui
from nice_gui.pages.ai_page_base import AIPageBase


class UserRegister(AIPageBase):
    def __init__(self):
        super().__init__()

        self.setup_register_page()

    def setup_register_page(self):
        with ui.card().classes("w-96 mx-auto mt-8 p-4"):
            ui.label("Register").classes("text-2xl text-center mb-4")

            self.email = ui.input(
                label="Email",
                placeholder="Enter your email",
                validation={
                    "Input too long": lambda value: 50 >= len(value),
                    "This field is required": lambda value: len(value) > 0,
                },
            ).classes("w-full mb-4")

            self.username = ui.input(
                label="Nickname",
                placeholder="Choose a nickname",
                validation={
                    "Input too long": lambda value: 30 >= len(value),
                    "This field is required": lambda value: len(value) > 0,
                },
            ).classes("w-full mb-4")

            self.full_name = ui.input(
                label="Full Name",
                placeholder="Enter your full name (optional)",
                validation={"Input too long": lambda value: 100 >= len(value)},
            ).classes("w-full mb-4")

            self.password = ui.input(
                label="Password",
                placeholder="Enter your password",
                password=True,
                validation={
                    "Password too short": lambda value: len(value) >= 6,
                },
            ).classes("w-full mb-4")

            self.confirm_password = ui.input(
                label="Confirm Password",
                placeholder="Confirm your password",
                password=True,
                validation={
                    "Password too short": lambda value: len(value) >= 6,
                },
            ).classes("w-full mb-4")

            self.wrap_ui(
                ui.button(
                    "Register", on_click=self.submit_handler(self.handle_register)
                ).classes("w-full mb-2")
            )

            with ui.row().classes("w-full justify-center"):
                ui.link("Already have an account? Login", "/ui/login").classes(
                    "text-blue-500"
                )

    async def handle_register(self):
        try:
            # Trigger validation for all fields
            for field in [
                self.email,
                self.username,
                self.full_name,
                self.password,
                self.confirm_password,
            ]:
                field.validate()

            # Check if any field has validation errors
            if any(
                [
                    self.email.error,
                    self.username.error,
                    self.full_name.error,
                    self.password.error,
                    self.confirm_password.error,
                ]
            ):
                ui.notify(
                    "Please fix validation errors before submitting", type="negative"
                )
                return

            if self.password.value != self.confirm_password.value:
                ui.notify("Passwords do not match!", type="negative")
                return

            json = {
                "email": self.email.value,
                "password": self.password.value,
                "username": self.username.value,
                "full_name": self.full_name.value,
            }
            await self.api_client.post("/api/auth/register", False, json=json)

            ui.navigate.to("/ui/login")
            ui.notify("Registration successful!", type="positive")

        except Exception as e:
            ui.notify(f"Registration failed: {str(e)}", type="negative")
