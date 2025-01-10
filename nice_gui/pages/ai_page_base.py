import asyncio
from abc import ABC
from typing import Callable, Any, Awaitable

from nicegui import ui, page, app
from nicegui.awaitable_response import AwaitableResponse
from nicegui.element import Element
from nicegui.elements.mixins.disableable_element import DisableableElement
from nicegui.elements.mixins.text_element import TextElement

from nice_gui.i18n import t
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

    def localize_page_title(self):
        pass

    def lock_ui(self):
        self.disabled_ctl.disable()

    def unlock_ui(self):
        self.disabled_ctl.enable()

    @property
    def api_client(self) -> APIClient:
        return self._api_client

    def wrap_ui(self, ui_element: Element):
        return self.component_wrapper.wrap(ui_element)

    def local_ui(self, ui_element: Element, local_key: str):
        if isinstance(ui_element, TextElement):
            ui_element.bind_text_from(
                app.storage.user.get("user_settings"),
                "language",
                lambda x: t(local_key),
            )
        return ui_element

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

    def get_current_page(self) -> page:
        """Get the current page instance"""
        return ui.context.client.page


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
