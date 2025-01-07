from nicegui import ui

from nice_gui.pages.layout_base import BaseLayout


class Chat(BaseLayout):
    """Chat page."""

    def __init__(self):
        super().__init__()

    async def setup_content(self):
        # TODO
        ui.label("Chat page")
