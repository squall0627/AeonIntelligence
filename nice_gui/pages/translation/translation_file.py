import os

from nicegui import ui, background_tasks, events
from nicegui.events import UploadEventArguments, UiEventArguments
from typing import Dict

from api.cache.file_translation_status_cache import FileTranslationStatusCache
from api.cache.redis_handler import get_redis
from core.ai_core.translation.file_translator.models.file_translation_status import (
    Status,
)
from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.state.user_state import user_state


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

            # Recover translating tasks
            background_tasks.create(self.recover_translating_tasks())

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
                    {
                        "name": "source",
                        "label": "Source File",
                        "field": "source",
                        "classes": "cursor-pointer",
                    },
                    {
                        "name": "translated",
                        "label": "Translated File",
                        "field": "translated",
                        "classes": "cursor-pointer",
                    },
                    {"name": "status", "label": "Status", "field": "status"},
                ],
                rows=[],
                row_key="datetime",
            ).classes("w-full")

            # Download handler
            async def download_handler(e: events.GenericEventArguments) -> None:
                task_id = e.args["source"]["task_id"]
                filename = e.args["source"]["filename"]
                await self.download_handler(task_id, filename)

            # Add custom slot for the table body
            self.file_history_table.add_slot(
                "body",
                r"""
                <q-tr :props="props">
                    <q-td key="datetime" :props="props">
                        {{ props.row.datetime }}
                    </q-td>
                    <q-td key="task" :props="props">
                        {{ props.row.task }}
                    </q-td>
                    <q-td key="duration" :props="props">
                        {{ props.row.duration }}
                    </q-td>
                    <q-td key="source" :props="props">
                        <a class="text-blue-500 hover:underline cursor-pointer"
                           @click="() => $parent.$emit('download_handler', props.row)">
                            {{ props.row.source.text }}
                        </a>
                    </q-td>
                    <q-td key="translated" :props="props">
                        <a v-if="props.row.translated.text !== '-'"
                           class="text-blue-500 hover:underline cursor-pointer"
                           @click="() => $parent.$emit('download_handler', props.row)">
                            {{ props.row.translated.text }}
                        </a>
                        <span v-else>-</span>
                    </q-td>
                    <q-td key="status" :props="props">
                        {{ props.row.status }}
                    </q-td>
                </q-tr>
                """,
            )

            self.file_history_table.on("download_handler", download_handler)

            # Load history
            background_tasks.create(self.load_translation_history())

    async def submit_translate_files(self, task_name: str):
        """Handle file translation"""
        if not self.uploaded_files:
            ui.notify("Please upload files to translate", type="warning")
            return

        # Clear active translations
        self.active_translations.clear()

        # Start translation tasks without waiting
        for file in self.uploaded_files:
            # background_tasks.create(self.start_file_translation_stream(file, task_id))
            background_tasks.create(
                self.start_file_translation_task(file["name"], task_name, file=file)
            )

        # Clear uploaded files after translation starts
        self.uploaded_files = []
        self.upload.reset()
        ui.notify("All translations started!", type="positive")

    async def start_file_translation_task(
        self,
        filename: Dict,
        task_name: str,
        is_call_translation_api=True,
        task_id=None,
        file: Dict = None,
    ):
        """Start translation process for a single file"""
        with self.active_translations:
            # Create a container for this file's translation
            with ui.card().classes("w-full"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(f"File: {filename}").classes("font-bold")
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
                    if is_call_translation_api:
                        # Call translation API
                        task_id = await self.call_file_translation_api(
                            task_name=task_name,
                            file=file,
                        )

                    # Call get task status API and update progress bar every 5 seconds
                    t = ui.timer(
                        5,
                        lambda: self.get_task_status_and_update_progress_bar(
                            task_id, progress_bar, status_label, t
                        ),
                    )

                    return task_id
                except Exception as e:
                    status_label.text = f"Translation failed: {str(e)}"
                    status_label.classes("text-red-500")

    async def get_task_status_and_update_progress_bar(
        self, task_id: str, progress_bar, status_label, timer
    ):
        """Get translation task status and update progress bar"""

        # Get translation status
        status = await self.api_client.get(
            f"/api/translation/status", params={"task_id": task_id}
        )

        # Update the progress bar
        self.update_processbar(status, progress_bar, status_label)

        # When translation is completed
        if status.get("status") == Status.COMPLETED:
            timer.deactivate()
            # Save translation to history
            await self.create_translation_history(status)
            # Load translation history
            background_tasks.create(self.load_translation_history())

    async def call_file_translation_api(
        self,
        task_name: str,
        file: Dict,
    ):
        """Call the file translation API with authentication"""
        try:
            # Prepare file data
            files = {"file": (file["name"], file["content"])}
            # TODO
            json = {
                "kwargs": {"run_parallely": False, "target_pages": [1]},
            }
            result = await self.api_client.post(
                f"/api/translation/file/{task_name}", json=json, files=files
            )

            return result["task_id"]

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

    def update_processbar(self, status, processbar, status_label):
        """Update process bar with percentage display"""
        progress = status.get("progress", 0.0)
        processbar.set_value(progress)

        # When translation is completed
        if status.get("status") == Status.COMPLETED:

            status_label.text = "Completed"
            status_label.classes("text-green-500")

            # Extract filename from the output path
            output_filename = os.path.basename(status["output_file_path"])

            # create download handler
            async def download_handler():
                await self.download_handler(status["task_id"], output_filename)

            # Download Button
            ui.button(text=output_filename, on_click=download_handler).classes(
                "text-blue-500"
            )

    async def create_translation_history(self, status: dict):
        """Create translation history"""
        try:
            params = {"task_id": status["task_id"]}
            history = await self.api_client.post(
                "/api/translation/file/history/create", params=params
            )

            # Clear the status cache
            status_cache = FileTranslationStatusCache(get_redis())
            await status_cache.delete_status(
                user_state.get_user().email, status["task_id"]
            )

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
                        "source": {
                            "text": history["source_file_name"],
                            "task_id": history["task_id"],
                            "filename": history["source_file_name"],
                        },
                        "translated": {
                            "text": history["translated_file_name"] or "-",
                            "task_id": history["task_id"],
                            "filename": history["translated_file_name"] or "",
                        },
                        "status": history["status"],
                    }
                )

            # Update the table with new rows
            self.file_history_table.rows = rows
            self.file_history_table.update()

        except Exception as e:
            ui.notify(f"Failed to load history: {str(e)}", type="negative")
            raise Exception(f"Get file translation history API error: {str(e)}")

    async def download_handler(self, task_id: str, filename: str) -> None:
        """Download file handler"""
        try:
            # Download the file using api_client
            file_content = await self.api_client.get_file(
                f"/api/translation/download", params={"task_id": task_id}
            )
            # Use ui.download to trigger browser download
            ui.download(file_content, filename)
            ui.notify(f"{filename} Downloaded successfully!", type="positive")
        except Exception as e:
            ui.notify(f"Download failed: {str(e)}", type="negative")

    async def recover_translating_tasks(self):
        """Get translating tasks and recover the progress bar"""

        try:
            # Get translating tasks
            tasks = await self.api_client.get("/api/translation/status/all")

            # Recover the progress bar
            for task_id, task in tasks.items():
                await self.start_file_translation_task(
                    os.path.basename(task["input_file_path"]),
                    task["task_name"],
                    is_call_translation_api=False,
                    task_id=task_id,
                )
        except Exception as e:
            raise Exception(f"Recover translating tasks API error: {str(e)}")
