import asyncio
from abc import ABC
from typing import Callable, Any, Awaitable

from nicegui import ui
from nicegui.awaitable_response import AwaitableResponse
from nicegui.element import Element
from nicegui.elements.mixins.disableable_element import DisableableElement

from nice_gui.utils.api_client import APIClient


class AIPageBase(ABC):

    def __init__(self) -> None:
        super().__init__()
        # API Client
        self._api_client = APIClient()
        # Button for Component Control
        self.disabled_ctl = ui.button()
        self.disabled_ctl.set_visibility(False)  # Hide the button
        self.disabled_ctl.enable()
        # Init component wrapper
        self.component_wrapper = ComponentWrapper(self)

    def lock_ui(self):
        self.disabled_ctl.disable()

    def unlock_ui(self):
        self.disabled_ctl.enable()

    @property
    def api_client(self) -> APIClient:
        return self._api_client

    def wrap_ui(self, ui_element: Element):
        return self.component_wrapper.wrap(ui_element)

    async def submit(self, func: Callable[[], Any], lock_ui: bool = True):
        try:
            if lock_ui:
                self.lock_ui()
            result = func()
            if isinstance(result, Awaitable) and not isinstance(
                result, AwaitableResponse
            ):
                result = await asyncio.wait_for(result, timeout=None)
        finally:
            if lock_ui:
                self.unlock_ui()

        return result

    def submit_handler(self, callback: Callable[[], Any], lock_ui: bool = True):
        return lambda func=callback: self.submit(func, lock_ui)


class ComponentWrapper:
    def __init__(self, page: AIPageBase):
        self.page = page

    @staticmethod
    def from_ui(page: AIPageBase, component: Element) -> Element:
        if isinstance(component, DisableableElement):
            # Add disabled control to the ui
            return component.bind_enabled_from(page.disabled_ctl)
        else:
            return component

    def wrap(self, component: Element):
        return self.from_ui(self.page, component)
