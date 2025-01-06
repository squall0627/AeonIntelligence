import asyncio

from nicegui import ui
from nicegui.events import UploadEventArguments, UiEventArguments
from datetime import datetime
from typing import Dict

from core.ai_core.translation.file_translator.models.file_translation_status import (
    Status,
)
from nice_gui.pages.ai_page_base import AIPageBase


class FileTranslationPage(AIPageBase):

    def __init__(self):
        super().__init__()

        # ui component
        self.upload = None
        self.active_translations = None
        self.file_history_table = None

        # Translation task types
        self.TRANSLATION_TASKS = {
            "ja_to_zh": "日➡︎中",
            "ja_to_en": "日➡︎英",
            "zh_to_ja": "中➡︎日",
            "zh_to_en": "中➡︎英",
            "en_to_ja": "英➡︎日",
            "en_to_zh": "英➡︎中",
        }

        # Store uploaded files
        self.uploaded_files = []
        self.processing_task_ids = {}
        self.file_status_bars = {}

        self.setup_file_translation()
        self.setup_file_history()

    def setup_file_translation(self):
        with ui.column().classes("w-full gap-4 p-4"):
            # File upload area
            self.upload = self.wrap_ui(
                ui.upload(
                    multiple=True,
                    on_upload=lambda e: self.handle_file_upload(e),
                    on_rejected=lambda e: self.handle_file_reject(e),
                )
                .props("accept=.pdf,.txt,.docx,.pptx,.xlsx")
                .classes("w-full")
            )

            # Translation buttons
            with ui.row().classes("w-full gap-2 flex-wrap justify-center"):
                for task_id, task_name in self.TRANSLATION_TASKS.items():
                    self.wrap_ui(
                        ui.button(
                            task_name,
                            on_click=self.submit_handler(
                                lambda t=task_id: self.submit_translate_files(t)
                            ),
                        ).classes("flex-grow-0")
                    )

            # Active translations container
            self.active_translations = ui.column().classes("w-full gap-4")

    def setup_file_history(self):
        with ui.column().classes("w-full gap-4 p-4"):
            # History section header with refresh button
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Translation History").classes("text-xl font-bold")
                self.wrap_ui(
                    ui.button("", on_click=self.load_file_history).props("icon=refresh")
                )

            # History table
            self.file_history_table = ui.table(
                columns=[
                    {"name": "datetime", "label": "Date Time", "field": "datetime"},
                    {"name": "task", "label": "Task", "field": "task"},
                    {"name": "source", "label": "Source File", "field": "source"},
                    {"name": "status", "label": "Status", "field": "status"},
                    {
                        "name": "translated",
                        "label": "Translated File",
                        "field": "translated",
                    },
                ],
                rows=[],
                row_key="datetime",
            ).classes("w-full")

    async def submit_translate_files(self, task_id: str):
        """Handle file translation"""
        if not self.uploaded_files:
            ui.notify("Please upload files to translate", type="warning")
            return

        # Start translation tasks without waiting
        for file in self.uploaded_files:
            task_id = await self.start_file_translation(file, task_id)
            self.processing_task_ids.update({task_id: Status.PROCESSING})

        # Create explicit container for notifications and UI updates
        notification_container = ui.column()  # Always reuse this container

        # Start polling for translation status
        asyncio.create_task(self.poll_translation_status(notification_container))

        # Clear uploaded files after translation starts
        self.uploaded_files = []
        self.upload.reset()
        ui.notify("All translations started!", type="positive")

    async def start_file_translation(self, file: Dict, task_id: str) -> str:
        """Start translation process for a single file"""
        with self.active_translations:
            # Create a container for this file's translation
            with ui.card().classes("w-full"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(f'File: {file["name"]}').classes("font-bold")
                    status_label = ui.label("Translating...").classes("text-blue-500")

                progress_bar = ui.linear_progress(value=0).classes("w-full")
                download_link = ui.link("Download translation").classes("text-blue-500")
                download_link.set_visibility(False)

                try:
                    # Call translation API and update progress
                    result = await self.call_file_translation_api(
                        task_id=task_id,
                        file=file,
                    )

                    if result:
                        # status_label.text = "Completed"
                        # status_label.classes("text-green-500")

                        # ui.link("Download translation", result["download_url"]).classes(
                        #     "text-blue-500"
                        # )

                        self.file_status_bars.update(
                            {
                                result["task_id"]: {
                                    "status_label": status_label,
                                    "progress_bar": progress_bar,
                                    "download_link": download_link,
                                }
                            }
                        )
                        # Save to history with correct argument names
                        # TODO
                        return result["task_id"]
                        # await self.save_file_history(
                        #     task_id=task_id,
                        #     source_file=file["name"],
                        #     result_file=result["filename"],
                        # )

                except Exception as e:
                    status_label.text = f"Translation failed: {str(e)}"
                    status_label.classes("text-red-500")

    async def poll_translation_status(self, notification_container):
        """Poll the translation status every 5 seconds"""
        try:
            while True:
                await asyncio.sleep(5)  # Wait for 5 seconds
                for task_id in self.processing_task_ids.keys():
                    # Call the API to get the translation status
                    try:
                        # Prepare params
                        params = {"task_id": task_id}
                        result = await self.api_client.get(
                            f"/api/translation/status", params=params
                        )
                        self.processing_task_ids[task_id] = result["status"]
                        status_bar = self.file_status_bars[task_id]

                        # Ensure updates to the UI occur in the context of the container
                        with notification_container:
                            self.update_translation_status(
                                result,
                                status_bar["status_label"],
                                status_bar["progress_bar"],
                                status_bar["download_link"],
                            )

                    except Exception as e:
                        # Use shared notification container for error messages
                        with notification_container:
                            ui.notify(
                                f"Get Translation Status API error: {str(e)}",
                                type="negative",
                            )
                        raise  # Optionally re-raise exception

                # Stop polling if all tasks are complete
                if all(
                    status != Status.PROCESSING
                    for status in self.processing_task_ids.values()
                ):
                    break
        except Exception as e:
            # Final error notification in the shared container
            with notification_container:
                ui.notify(f"Translation failed: {str(e)}", type="negative")

        # Notify completion in the shared container
        with notification_container:
            ui.notify("All translations completed!", type="positive")

        # Reset internal variables and load file history
        self.processing_task_ids = {}
        self.file_status_bars = {}
        self.active_translations.clear()
        self.upload.reset()
        await self.load_file_history()

        # Notify history loaded
        with notification_container:
            ui.notify("History loaded", type="positive")

    def update_translation_status(
        self, status: dict, status_label, progress_bar, download_link
    ):
        """Update translation status"""
        if status["status"] == Status.COMPLETED:
            status_label.text = "Completed"
            status_label.classes("text-green-500")
            download_link.set_visibility(True)
            download_link.props(f'href="{status["output_file_path"]}"')
            download_link.classes("text-blue-500")
            progress_bar.set_value(1)
        else:
            status_label.text = "Translating..."
            status_label.classes("text-blue-500")
            progress_bar.set_value(status["progress"])
            download_link.set_visibility(False)
            download_link.props('href=""')
            download_link.classes("")

    async def load_file_history(self):
        """Load file translation history"""
        # Call API to get history
        pass

    async def save_file_history(self, task_id: str, source_file: str, result_file: str):
        """Save file translation to history"""
        try:
            # Call API to save history
            json = {
                "task_id": task_id,
                "source_file": source_file,
                "result_file": result_file,
                "datetime": datetime.now().isoformat(),
                "status": "completed",
            }
            await self.api_client.post("/api/translation/history/file", json=json)

        except Exception as e:
            ui.notify(f"Failed to save history: {str(e)}", type="warning")

    async def call_file_translation_api(
        self,
        task_id: str,
        file: Dict,
    ):
        """Call the file translation API with authentication"""
        try:
            # Prepare file data
            files = {"file": (file["name"], file["content"])}
            # TODO
            json = {"kwargs": {"run_parallely": True, "target_pages": [1]}}
            result = await self.api_client.post(
                f"/api/translation/file/{task_id}", json=json, files=files
            )
            return result

        except Exception as e:
            raise Exception(f"Translation API error: {str(e)}")

    def handle_file_upload(self, event: UploadEventArguments) -> None:
        """Handle file upload event"""
        try:
            file_info = {
                "name": event.name,
                "content": event.content,  # The actual file content
                "file": event,  # Store the entire event for later use
            }
            self.uploaded_files.append(file_info)
            ui.notify(f"File uploaded: {event.name}", type="positive")

        except Exception as e:
            ui.notify(f"Upload failed: {str(e)}", type="negative")

    def handle_file_reject(self, event: UiEventArguments) -> None:
        """Handle rejected files"""
        try:
            # Access the rejected files directly from the event
            if isinstance(event, dict):
                rejected_files = event.get("files", [])
                for file in rejected_files:
                    ui.notify(f"File rejected: {file}", type="negative")
            else:
                ui.notify(f"File rejected", type="negative")
        except Exception as e:
            ui.notify("File rejection error", type="negative")
