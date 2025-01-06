import abc
from abc import ABC

from nice_gui.pages.sidebar import Sidebar


class BaseLayout(ABC):
    """A reusable layout to include the Sidebar on every page."""

    def __init__(self):
        super().__init__()
        sidebar = Sidebar()
        sidebar.set_content(self.setup_content)

    @abc.abstractmethod
    def setup_content(self):
        raise NotImplementedError
