from contextlib import suppress

from nicegui import ui
from nicegui import app

from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.pages.layout_base import BaseLayout


class UserProfile(AIPageBase, BaseLayout):
    """User profile page."""

    def __init__(self):
        super().__init__()

    def setup_content(self):
        # TODO
        ui.label("User profile page")
        ui.button("Logout", on_click=self.submit_handler(self.logout), icon="logout")

    def logout(self):
        with suppress(Exception):
            app.storage.user.clear()
        ui.navigate.to("/ui/login")
