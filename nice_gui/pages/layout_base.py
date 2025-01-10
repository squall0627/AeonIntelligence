import abc

from nicegui import ui

from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.pages.sidebar import Sidebar


class BaseLayout(AIPageBase):
    """A reusable layout to include the Sidebar on every page."""

    def __init__(self):
        super().__init__()
        self.local_contents = []
        with ui.header().classes(replace="row items-center"):
            ui.button(on_click=lambda: self.sidebar.toggle(), icon="menu").props(
                "flat color=white"
            )
        self.sidebar = Sidebar(self)

        ui.timer(0.01, self.setup_content, once=True)

    @abc.abstractmethod
    async def setup_content(self):
        raise NotImplementedError
