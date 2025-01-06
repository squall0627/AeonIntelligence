from nicegui import ui, app
from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.state.user_state import get_user_state
import asyncio


class Sidebar(AIPageBase):

    def __init__(self):
        super().__init__()
        self.user_label = None
        self.dark_mode = False
        self.dark_mode_ui = ui.dark_mode()
        self.theme_icon = None
        self.setup_sidebar()
        # Create a task to initialize user and theme
        asyncio.create_task(self.initialize())

    async def initialize(self):
        """Initialize user data and theme"""
        # Get user state for current context
        self.user_state = await get_user_state()
        await self.load_user_data()
        await self.initialize_theme()

    def setup_sidebar(self):
        """Setup the sidebar UI"""
        with ui.row().classes("h-screen w-full"):
            # Sidebar
            with ui.column().classes("h-full w-64 p-4 flex flex-col justify-between"):
                # Top section with menu
                with ui.column().classes("gap-2"):
                    ui.label("Menu").classes("text-lg font-bold")
                    # Menu links instead of buttons
                    ui.link("Chat", target="/ui/chat").classes(
                        "text-gray-700 dark:text-gray-300 hover:text-blue-500"
                    )
                    ui.link("My Knowledge", target="/ui/knowledge").classes(
                        "text-gray-700 dark:text-gray-300 hover:text-blue-500"
                    )
                    ui.link("Translator", target="/ui/translation").classes(
                        "text-gray-700 dark:text-gray-300 hover:text-blue-500"
                    )

                # Bottom section with user info and icons
                with ui.column().classes("gap-4"):
                    # User email link
                    self.user_label = ui.link(
                        "Loading...", target="/ui/profile"
                    ).classes(
                        "text-gray-700 dark:text-gray-300 hover:text-blue-500 text-sm"
                    )

                    # Icons row with right-aligned theme selector
                    with ui.row().classes("w-full items-center justify-between"):
                        # GitHub icon
                        with ui.link(
                            target="https://github.com/squall0627/AeonIntelligence",
                            new_tab=True,
                        ).classes("cursor-pointer"):
                            ui.html(
                                """
                                <img src="/static/github-logo.svg" style="width: 24px; height: 24px;" class="dark:invert" />
                            """
                            )

                        # Theme selector (right-aligned)
                        self.theme_icon = ui.icon("light_mode").classes(
                            "cursor-pointer"
                        )
                        self.theme_icon.on("click", self.toggle_theme)

            # Main content area (full width)
            with ui.column().classes("flex-1 p-4"):
                self.content = ui.column().classes("w-full")

    async def initialize_theme(self):
        """Initialize theme from user settings"""
        try:
            # Get user state and settings
            user_settings = await self.user_state.get_user_settings(self.api_client)
            self.dark_mode = user_settings.dark_mode

            # Apply the stored theme
            if self.dark_mode:
                self.dark_mode_ui.enable()
                self.theme_icon.props("icon=dark_mode")
            else:
                self.dark_mode_ui.disable()
                self.theme_icon.props("icon=light_mode")
        except Exception as e:
            print(f"Error loading theme settings: {e}")
            # Use local storage as fallback
            self.dark_mode = app.storage.user.get("dark_mode", False)
            if self.dark_mode:
                self.dark_mode_ui.enable()
                self.theme_icon.props("icon=dark_mode")
            else:
                self.dark_mode_ui.disable()
                self.theme_icon.props("icon=light_mode")

    async def toggle_theme(self):
        """Toggles between light and dark themes, and updates the theme icon."""
        try:
            self.dark_mode = not self.dark_mode

            # Update user settings through user state
            await self.user_state.update_user_settings(
                self.api_client, dark_mode=self.dark_mode
            )

            # Update local storage as backup
            app.storage.user.update({"dark_mode": self.dark_mode})

            # Apply theme change
            if self.dark_mode:
                self.dark_mode_ui.enable()
                self.theme_icon.props("icon=dark_mode")
            else:
                self.dark_mode_ui.disable()
                self.theme_icon.props("icon=light_mode")
        except Exception as e:
            print(f"Error saving theme settings: {e}")
            ui.notify("Failed to save theme preference", type="negative")

    async def load_user_data(self):
        """Load user data and update UI"""
        try:
            user = await self.user_state.fetch_user(self.api_client)
            if user:
                self.user_label.text = user.email
                self.user_label.tooltip = f"Logged in as {user.full_name}"
            else:
                self.user_label.text = "Not logged in"
        except Exception as e:
            print(f"Error loading user data: {e}")
            self.user_label.text = "Error loading user"

    def set_content(self, content_fn):
        """Helper to set the content dynamically."""
        with self.content:
            content_fn()
