from nicegui import ui

from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.pages.layout_base import BaseLayout
from nice_gui.pages.translation.translation_file import FileTranslationPage
from nice_gui.pages.translation.translation_text import TextTranslationPage


class TranslationPage(AIPageBase, BaseLayout):

    def __init__(self):
        super().__init__()

    def setup_content(self):
        # Main layout
        with ui.tabs().classes("w-full") as tabs:
            ui.tab("Text")
            ui.tab("File")

        with ui.tab_panels(tabs, value="Text").classes("w-full"):
            with ui.tab_panel("Text"):
                TextTranslationPage()
            with ui.tab_panel("File"):
                FileTranslationPage()
