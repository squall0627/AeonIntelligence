import abc
import asyncio

from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.pages.sidebar import Sidebar


class BaseLayout(AIPageBase):
    """A reusable layout to include the Sidebar on every page."""

    def __init__(self):
        super().__init__()
        sidebar = Sidebar()
        asyncio.create_task(sidebar.set_content(self.setup_content))

    @abc.abstractmethod
    async def setup_content(self):
        raise NotImplementedError
