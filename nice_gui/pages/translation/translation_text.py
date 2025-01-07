import pyperclip
from nicegui import ui

from nice_gui.i18n import t
from nice_gui.pages.ai_page_base import AIPageBase


class TextTranslationPage(AIPageBase):

    def __init__(self):
        super().__init__()

        # ui component
        self.source_text = None
        self.target_text = None
        self.text_history_table = None

        # Translation task types
        self.TRANSLATION_TASKS = {
            "ja_to_zh": "日➡︎中",
            "ja_to_en": "日➡︎英",
            "zh_to_ja": "中➡︎日",
            "zh_to_en": "中➡︎英",
            "en_to_ja": "英➡︎日",
            "en_to_zh": "英➡︎中",
        }

        self.setup_text_translation()
        self.setup_text_history()

    def setup_text_translation(self):
        with ui.column().classes("w-full gap-4 p-4"):
            # Text areas container
            with ui.row().classes("w-full gap-4 flex flex-col md:flex-row"):
                # Source text area
                with ui.column().classes("flex-1"):
                    self.local_ui(
                        ui.label(t("translator.text_tab.label.source_text")),
                        "translator.text_tab.label.source_text",
                    ).classes("text-lg font-bold")
                    self.source_text = self.wrap_ui(
                        ui.textarea().classes("w-full h-48")
                    )

                # Translated text area with copy button
                with ui.column().classes("flex-1"):
                    with ui.row().classes("items-center justify-between"):
                        self.local_ui(
                            ui.label(t("translator.text_tab.label.translation_result")),
                            "translator.text_tab.label.translation_result",
                        ).classes("text-lg font-bold")
                        self.wrap_ui(
                            ui.button(
                                "", on_click=self.copy_translation, icon="content_copy"
                            ).classes("text-blue-500")
                        )
                    self.target_text = self.wrap_ui(
                        ui.textarea().props("readonly").classes("w-full h-48")
                    )

            # Translation buttons
            with ui.row().classes("w-full gap-2 flex-wrap justify-center"):
                for task_id, task_name in self.TRANSLATION_TASKS.items():
                    self.wrap_ui(
                        self.local_ui(
                            ui.button(
                                t(f"translator.button.{task_id}"),
                                on_click=self.submit_handler(
                                    lambda tt=task_id: self.submit_translation_text(tt)
                                ),
                            ),
                            f"translator.button.{task_id}",
                        ).classes("flex-grow-0")
                    )

    def setup_text_history(self):
        with ui.column().classes("w-full gap-4 p-4"):
            # History section header with refresh button
            with ui.row().classes("w-full items-center justify-between"):
                self.local_ui(
                    ui.label(t("translator.text_tab.label.translation_history")),
                    "translator.text_tab.label.translation_history",
                ).classes("text-xl font-bold")
                self.wrap_ui(
                    ui.button("", on_click=self.load_text_history).props("icon=refresh")
                )

            # History table
            self.text_history_table = ui.table(
                columns=[
                    {"name": "datetime", "label": "Date Time", "field": "datetime"},
                    {"name": "task", "label": "Task", "field": "task"},
                    {"name": "source", "label": "Source Text", "field": "source"},
                    {
                        "name": "translated",
                        "label": "Translated Text",
                        "field": "translated",
                    },
                ],
                rows=[],
                row_key="datetime",
            ).classes("w-full")

    async def submit_translation_text(self, task_id: str):
        """Handle text translation submission"""

        if not self.source_text.value:
            ui.notify("Please enter text to translate", type="warning")
            return

        try:
            # Create loading spinner
            spinner = ui.spinner(size="lg")
            try:
                # Clear previous translation
                self.target_text.value = ""
                # Start streaming translation
                json = {"text": self.source_text.value}
                async for partial_translation in self.api_client.post_streaming(
                    f"/api/translation/text/{task_id}", json=json
                ):
                    # Update target text area with new content
                    self.target_text.value += partial_translation
                    # Force UI update
                    ui.update()

                await self.save_text_history(task_id)
                ui.notify("Translation completed", type="positive")
            finally:
                spinner.delete()

        except Exception as e:
            ui.notify(f"Translation failed: {str(e)}", type="negative")

    def copy_translation(self):
        """Copy translated text to clipboard"""
        if self.target_text.value:
            try:
                pyperclip.copy(self.target_text.value)
                ui.notify("Text copied to clipboard", type="positive")
            except Exception as e:
                ui.notify(f"Failed to copy: {str(e)}", type="negative")

    async def load_text_history(self):
        """Load text translation history"""
        try:
            # Call API to get history
            history_data = await self.api_client.post("/api/translation/history/text")
            # Update table rows with new data
            self.text_history_table.rows = history_data
            ui.notify("History loaded", type="positive")
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(
            #         f'{os.getenv("API_ENDPOINT")}/api/translation/history/text'
            #     )
            #
            #     if response.status_code == 200:
            #         history_data = response.json()
            #         # Update table rows with new data
            #         self.text_history_table.rows = history_data
            #         ui.notify('History loaded', type='positive')
            #     else:
            #         raise Exception(f"Failed to load history: {response.status_code}")

        except Exception as e:
            ui.notify(f"Failed to load history: {str(e)}", type="negative")

    async def save_text_history(self, task_id: str):
        """Save text translation to history"""
        # Call API to save history
        pass
