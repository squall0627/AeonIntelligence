from nicegui import ui
from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.state.user_state import user_state
import asyncio
from nice_gui.i18n import t, LANGUAGES, setup_i18n


class Sidebar(AIPageBase):

    def __init__(self, content_instance):
        super().__init__()
        self.content_instance = content_instance
        self.user_label = None
        self.dark_mode = False
        self.dark_mode_ui = ui.dark_mode()
        self.language_selector = None
        self.theme_icon = None
        self.is_collapsed = False
        self.sidebar_container = None
        self.setup_sidebar()
        self.async_ui_card = ui.card()
        self.async_ui_card.set_visibility(False)
        # Create a task to initialize user and theme
        asyncio.create_task(self.initialize())

    async def initialize(self):
        """Initialize user data and theme"""
        # Get user state for current context
        await self.load_user_data()
        # Ensure theme initialization is within UI context
        with self.async_ui_card:  # Create a proper UI context container
            await self.initialize_theme()
            await self.initialize_language_selector()

        # Get user information
        user = await user_state.get_user(self.api_client)
        # If user is administrator, display admin icon on the right of the user_label
        if user and user.is_admin:
            with self.user_label:
                ui.icon("admin_panel_settings").classes("text-3xl dark:text-gray-400")

    def setup_sidebar(self):
        """Setup the sidebar UI"""
        with ui.row().classes("h-screen w-full"):
            # Collapsible sidebar container with border
            self.sidebar_container = ui.column().classes(
                "h-full transition-all duration-300 ease-in-out flex flex-col "
                "border-r border-gray-200 dark:border-gray-700"
            )

            with self.sidebar_container:
                # Toggle button at top
                with ui.row().classes("w-full justify-end p-2"):
                    self.toggle_button = ui.button(
                        on_click=self.toggle_sidebar, icon="chevron_left"
                    ).classes("text-gray-700 dark:text-gray-300")

                # Main content wrapper (maintains structure when collapsed)
                self.sidebar_content = ui.column().classes(
                    "flex-grow flex flex-col justify-between w-64 p-4"
                )

                with self.sidebar_content:
                    # Top menu section
                    with ui.column().classes("gap-2"):
                        ui.label("Menu").classes("text-lg font-bold dark:text-gray-200")
                        # Menu items with icons
                        with ui.link(target="/ui/chat").classes(
                            "flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-blue-500"
                        ):
                            ui.icon("chat").classes("text-gray-500 dark:text-gray-400")
                            self.local_ui(
                                ui.label(t("sidebar.menu.chat")), "sidebar.menu.chat"
                            )

                        with ui.link(target="/ui/knowledge").classes(
                            "flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-blue-500"
                        ):
                            ui.icon("school").classes(
                                "text-gray-500 dark:text-gray-400"
                            )
                            self.local_ui(
                                ui.label(t("sidebar.menu.knowledge")),
                                "sidebar.menu.knowledge",
                            )

                        with ui.link(target="/ui/translation").classes(
                            "flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-blue-500"
                        ):
                            ui.icon("translate").classes(
                                "text-gray-500 dark:text-gray-400"
                            )
                            self.local_ui(
                                ui.label(t("sidebar.menu.translator")),
                                "sidebar.menu.translator",
                            )

                    # Bottom section
                    with ui.column().classes("mt-auto gap-4"):
                        # User email
                        self.user_label = ui.link(
                            "Loading...", target="/ui/profile"
                        ).classes(
                            "text-gray-700 dark:text-gray-300 hover:text-blue-500 text-sm"
                        )

                        # Icons row
                        with ui.row().classes("w-full items-center justify-between"):
                            # github link
                            with ui.link(
                                target="https://github.com/squall0627/AeonIntelligence",
                                new_tab=True,
                            ).classes("cursor-pointer"):
                                ui.html(
                                    """
                                    <img src="/static/github-logo.svg" style="width: 24px; height: 24px;" class="dark:invert" />
                                """
                                )

                            # language selector
                            self.language_selector = ui.select(
                                options=LANGUAGES,
                                # value="en",
                                on_change=self.handle_language_change,
                            ).classes("ml-2")

                            # theme selector
                            self.theme_icon = ui.icon("light_mode").classes(
                                "cursor-pointer"
                            )
                            self.theme_icon.on("click", self.toggle_theme)

            # Main content area with title
            with ui.column().classes("flex-1 p-4"):
                # Page title container
                with ui.row().classes(
                    "mb-4 border-b border-gray-200 dark:border-gray-700 pb-4"
                ):
                    ui.label(self.get_current_page().title).classes(
                        "text-2xl font-bold dark:text-gray-200"
                    )

                # Content area
                self.content = ui.column().classes("w-full")

    def toggle_sidebar(self):
        """Toggle sidebar collapse state"""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.sidebar_container.classes(
                replace="w-16 h-full transition-all duration-300 ease-in-out flex flex-col"
            )
            self.sidebar_content.classes(add="hidden")
            self.toggle_button.props("icon=menu")
        else:
            self.sidebar_container.classes(
                replace="w-64 h-full transition-all duration-300 ease-in-out flex flex-col border-r border-gray-200 dark:border-gray-700"
            )
            self.sidebar_content.classes(remove="hidden")
            self.toggle_button.props("icon=chevron_left")

    async def initialize_theme(self):
        """Initialize theme from user settings"""
        try:
            # Get user state and settings
            user_settings = await user_state.get_user_settings(self.api_client)

            self.dark_mode = user_settings.dark_mode

            # Apply the stored theme
            self.apply_theme_change()

        except Exception as e:
            print(f"Error loading theme settings: {e}")
            # Use local storage as fallback
            self.dark_mode = await user_state.get_user_settings().dark_mode
            # Apply theme change
            self.apply_theme_change()

    async def toggle_theme(self):
        """Toggles between light and dark themes, and updates the theme icon."""
        try:
            self.dark_mode = not self.dark_mode

            # Update user settings through user state
            await user_state.update_user_settings(
                self.api_client, dark_mode=self.dark_mode
            )

            # Apply theme change
            self.apply_theme_change()
        except Exception as e:
            print(f"Error saving theme settings: {e}")
            ui.notify("Failed to save theme preference", type="negative")

    def apply_theme_change(self):
        """Apply theme change to the current page"""
        if self.dark_mode:
            self.dark_mode_ui.enable()
            self.theme_icon.props("icon=dark_mode")
            ui.colors(primary="#34495E")
        else:
            self.dark_mode_ui.disable()
            self.theme_icon.props("icon=light_mode")
            ui.colors()

    async def load_user_data(self):
        """Load user data and update UI"""
        try:
            user = await user_state.get_user(self.api_client)
            if user:
                self.user_label.text = user.email
                self.user_label.tooltip = f"Logged in as {user.full_name}"
            else:
                self.user_label.text = "Not logged in"
        except Exception as e:
            print(f"Error loading user data: {e}")
            self.user_label.text = "Error loading user"

    async def set_content(self, content_fn):
        """Helper to set the content dynamically."""
        with self.content:
            await content_fn()

    async def initialize_language_selector(self):
        user_settings = await user_state.get_user_settings(self.api_client)
        setup_i18n(user_settings.language)  # Initialize i18n with user's language

        self.language_selector.value = user_settings.language

    async def handle_language_change(self, e):
        await user_state.update_user_settings(self.api_client, language=e.value)
        setup_i18n(e.value)  # Update current language
        self.localize()
        self.content_instance.localize()
