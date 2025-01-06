from nicegui import ui

from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.pages.layout_base import BaseLayout


class UserProfile(AIPageBase, BaseLayout):
    """User profile page."""

    def __init__(self):
        super().__init__()

    def setup_content(self):
        # TODO
        ui.label("User profile page")
