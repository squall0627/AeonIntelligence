from contextlib import suppress

from nicegui import ui
from nicegui import app

from nice_gui.pages.layout_base import BaseLayout
from nice_gui.state.user_state import get_user_state


class UserProfile(BaseLayout):
    """User profile page."""

    def __init__(self):
        super().__init__()

    async def setup_content(self):
        await self.setup_register_page()

    async def setup_register_page(self):
        user = await get_user_state().fetch_user(self.api_client)
        if user:
            with ui.card().classes("w-96 mx-auto mt-8 p-4"):
                ui.label("Edit Profile").classes("text-2xl text-center mb-4")

                self.email = (
                    ui.input(
                        label="Email",
                        value=user.email,
                        validation={
                            "Input too long": lambda value: 50 >= len(value),
                            "This field is required": lambda value: len(value) > 0,
                        },
                    )
                    .props("readonly")
                    .classes("w-full mb-4")
                )

                self.username = ui.input(
                    label="Username",
                    value=user.username,
                    placeholder="Choose a username",
                    validation={
                        "Input too long": lambda value: 30 >= len(value),
                        "This field is required": lambda value: len(value) > 0,
                    },
                ).classes("w-full mb-4")

                self.full_name = ui.input(
                    label="Full Name",
                    value=user.full_name,
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

                with ui.row().classes("w-full gap-2 flex-wrap justify-center"):
                    self.wrap_ui(
                        ui.button(
                            "Edit",
                            on_click=self.submit_handler(self.handle_edit),
                            icon="edit",
                        ).classes("w-full mb-2")
                    )

                    ui.button(
                        "Logout",
                        on_click=self.submit_handler(self.logout),
                        icon="logout",
                    ).classes("w-full mb-2")

    async def handle_edit(self):
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

            ui.notify("Edit successful!", type="positive")

        except Exception as e:
            ui.notify(f"Edit failed: {str(e)}", type="negative")

    def logout(self):
        with suppress(Exception):
            app.storage.user.clear()
        ui.navigate.to("/ui/login")
