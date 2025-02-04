import json as json_lib
import os

from nicegui import ui, background_tasks
from nicegui.events import UploadEventArguments, UiEventArguments
from typing import Dict

from api.cache.file_translation_status_cache import FileTranslationStatusCache
from api.cache.redis_handler import get_redis
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
                        self.local_ui(
                            ui.button(
                                on_click=self.submit_handler(
                                    lambda tt=task_id: self.submit_translate_files(tt)
                                ),
                            ),
                            f"translator.button.{task_id}",
                        ).classes("flex-grow-0")
                    )

            # Active translations container
            self.active_translations = ui.column().classes("w-full gap-4")

    def setup_file_history(self):
        with ui.column().classes("w-full gap-4 p-4"):
            # History section header with refresh button
            with ui.row().classes("w-full items-center justify-between"):
                self.local_ui(
                    ui.label(),
                    "translator.file_tab.label.translation_history",
                ).classes("text-xl font-bold")
                self.wrap_ui(
                    ui.button("", on_click=self.load_translation_history).props(
                        "icon=refresh"
                    )
                )

            # History table
            self.file_history_table = ui.table(
                columns=[
                    {"name": "datetime", "label": "Date Time", "field": "datetime"},
                    {"name": "task", "label": "Task", "field": "task"},
                    {"name": "duration", "label": "Duration", "field": "duration"},
                    {"name": "source", "label": "Source File", "field": "source"},
                    {
                        "name": "translated",
                        "label": "Translated File",
                        "field": "translated",
                    },
                    {"name": "status", "label": "Status", "field": "status"},
                ],
                rows=[],
                row_key="datetime",
            ).classes("w-full")

            # Load history
            background_tasks.create(self.load_translation_history())

    async def submit_translate_files(self, task_id: str):
        """Handle file translation"""
        if not self.uploaded_files:
            ui.notify("Please upload files to translate", type="warning")
            return

        # Clear active translations
        self.active_translations.clear()

        # Start translation tasks without waiting
        for file in self.uploaded_files:
            background_tasks.create(self.start_file_translation(file, task_id))

        # Create explicit container for notifications and UI updates
        # notification_container = ui.column()  # Always reuse this container

        # Start polling for translation status
        # TODO
        # background_tasks.create(self.poll_translation_status(notification_container))

        # Clear uploaded files after translation starts
        self.uploaded_files = []
        self.upload.reset()
        ui.notify("All translations started!", type="positive")

    async def start_file_translation(self, file: Dict, task_id: str):
        """Start translation process for a single file"""
        with self.active_translations:
            # Create a container for this file's translation
            with ui.card().classes("w-full"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(f'File: {file["name"]}').classes("font-bold")
                    status_label = ui.label("Translating...").classes("text-blue-500")

                # Progress bar
                progress_bar = ui.linear_progress(
                    value=0, size="20px", show_value=False
                ).classes("w-full")
                with progress_bar:
                    ui.label().classes(
                        "absolute-center text-sm text-white"
                    ).bind_text_from(
                        progress_bar, "value", lambda x: f"{int(x * 100)}%"
                    )

                # Download link
                download_link = ui.link("Download translation").classes("text-blue-500")
                download_link.set_visibility(False)

                try:
                    # Call translation API and update progress
                    result = await self.call_file_translation_api(
                        task_id=task_id,
                        file=file,
                        callback=lambda status: self.update_processbar(
                            progress_bar, status
                        ),
                    )

                    status_label.text = "Completed"
                    status_label.classes("text-green-500")

                    # Extract filename from the output path
                    output_filename = os.path.basename(result["output_file_path"])

                    # create download handler
                    async def download_handler():
                        try:
                            # Download the file using api_client
                            file_content = await self.api_client.get_file(
                                f"/api/translation/download",
                                params={"task_id": result["task_id"]},
                            )
                            # Use ui.download to trigger browser download
                            ui.download(file_content, output_filename)
                        except Exception as e:
                            ui.notify(f"Download failed: {str(e)}", type="negative")

                    # Download Button
                    ui.button(text=output_filename, on_click=download_handler).classes(
                        "text-blue-500"
                    )

                    # Save translation to history
                    await self.create_translation_history(result)

                except Exception as e:
                    status_label.text = f"Translation failed: {str(e)}"
                    status_label.classes("text-red-500")

        # Load translation history
        background_tasks.create(self.load_translation_history())

    async def call_file_translation_api(
        self,
        task_id: str,
        file: Dict,
        callback,
    ):
        """Call the file translation API with authentication"""
        try:
            # Prepare file data
            files = {"file": (file["name"], file["content"])}
            # TODO
            json = {
                "kwargs": {"run_parallely": False, "target_pages": [1]},
            }
            final_status = None
            async for status in self.api_client.post_streaming(
                f"/api/translation/file/{task_id}", json=json, files=files
            ):
                final_status = json_lib.loads(status)
                callback(final_status)

            return final_status

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

    def update_processbar(self, processbar, status):
        """Update process bar with percentage display"""
        progress = status.get("progress", 0.0)
        processbar.set_value(progress)

    async def create_translation_history(self, status: dict):
        """Create translation history"""
        try:
            params = {"task_id": status["task_id"]}
            history = await self.api_client.post(
                "/api/translation/file/history/create", params=params
            )

            # Clear the status cache
            status_cache = FileTranslationStatusCache(get_redis())
            await status_cache.delete_status(status["task_id"])

            return history

        except Exception as e:
            raise Exception(f"Create file translation history API error: {str(e)}")

    async def load_translation_history(self):
        """Load translation history"""
        try:
            history_list = await self.api_client.get("/api/translation/file/history")

            # Convert history data to table rows
            rows = []
            for history in history_list:
                rows.append(
                    {
                        "datetime": history["date_time"],
                        "task": history["task_name"],
                        "duration": f"{history['duration']:.1f}s",
                        "source": history["source_file_name"],
                        "translated": history["translated_file_name"] or "-",
                        "status": history["status"],
                    }
                )

            # Update the table with new rows
            self.file_history_table.rows = rows
            self.file_history_table.update()

        except Exception as e:
            ui.notify(f"Failed to load history: {str(e)}", type="negative")
            raise Exception(f"Get file translation history API error: {str(e)}")
