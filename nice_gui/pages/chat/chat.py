from nicegui import ui

from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.pages.layout_base import BaseLayout


class Chat(AIPageBase, BaseLayout):
    """Chat page."""

    def __init__(self):
        super().__init__()

    def setup_content(self):
        # TODO
        ui.label("Chat page")
