import abc
import asyncio

from nicegui.element import Element

from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.pages.sidebar import Sidebar


class BaseLayout(AIPageBase):
    """A reusable layout to include the Sidebar on every page."""

    def __init__(self):
        super().__init__()
        self.local_contents = []
        sidebar = Sidebar(self)
        asyncio.create_task(sidebar.set_content(self.setup_content))

    @abc.abstractmethod
    async def setup_content(self):
        raise NotImplementedError

    def local_ui(self, ui_element: Element | AIPageBase, local_key: str):
        if isinstance(ui_element, AIPageBase):
            self.local_contents.append(ui_element)
        elif isinstance(ui_element, Element):
            super().local_ui(ui_element, local_key)
        return ui_element

    def localize(self):
        super().localize()
        for content in self.local_contents:
            content.localize()
