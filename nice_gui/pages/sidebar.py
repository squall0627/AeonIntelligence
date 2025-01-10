from nicegui import ui
from nice_gui.pages.ai_page_base import AIPageBase
from nice_gui.state.user_state import user_state
from nice_gui.i18n import LANGUAGES, setup_i18n


class Sidebar(AIPageBase):

    def __init__(self, content_instance):
        super().__init__()
        self.content_instance = content_instance

        # Get user theme setting
        self.dark_mode = user_state.get_user_settings().dark_mode
        # Apply the stored theme
        self.apply_theme_change()
        # Change theme according to the value of self.dark_mode
        ui.dark_mode().bind_value_from(self, "dark_mode")

        # Initialize the sidebar
        self.left_drawer = ui.left_drawer().classes(
            "h-full transition-all duration-300 ease-in-out flex flex-col"
        )
        with self.left_drawer:
            self.setup_sidebar()

    def setup_sidebar(self):
        """Setup the sidebar UI"""

        # Top menu section
        with ui.column().classes("gap-2"):
            ui.label("Menu").classes("text-lg font-bold dark:text-gray-200")
            # Menu items with icons

            # Chat Link
            with ui.link(target="/ui/chat").classes(
                "flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-blue-500"
            ):
                ui.icon("chat").classes("text-gray-500 dark:text-gray-400")
                self.local_ui(ui.label(), "sidebar.menu.chat")

            # Knowledge link
            with ui.link(target="/ui/knowledge").classes(
                "flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-blue-500"
            ):
                ui.icon("school").classes("text-gray-500 dark:text-gray-400")
                self.local_ui(
                    ui.label(),
                    "sidebar.menu.knowledge",
                )

            # Translation link
            with ui.link(target="/ui/translation").classes(
                "flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-blue-500"
            ):
                ui.icon("translate").classes("text-gray-500 dark:text-gray-400")
                self.local_ui(
                    ui.label(),
                    "sidebar.menu.translator",
                )

        # Bottom section
        with ui.column().classes("mt-auto gap-2"):
            # User email link
            user_label = ui.link("Loading...", target="/ui/profile").classes(
                "text-gray-700 dark:text-gray-300 hover:text-blue-500 text-sm"
            )

            # Initialize user data
            self.load_user_data(user_label)

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

                # Language selector
                language_selector = ui.select(
                    options=LANGUAGES,
                    on_change=self.handle_language_change,
                ).classes("ml-2")

                # Initialize language selector
                self.initialize_language_selector(language_selector)

                # Theme selector
                ui.icon("").bind_name_from(
                    self,
                    "dark_mode",
                    lambda x: "light_mode" if self.dark_mode else "dark_mode",
                ).classes("cursor-pointer").on("click", self.toggle_theme)

    def load_user_data(self, user_label):
        """Load user data and update UI"""

        user = user_state.get_user()
        if user:
            user_label.text = user.email
            user_label.tooltip = f"Logged in as {user.full_name}"

            # If user is administrator, display admin icon on the right of the user_label
            if user and user.is_admin:
                with user_label:
                    ui.icon("admin_panel_settings").classes(
                        "text-3xl dark:text-gray-400"
                    )
        else:
            ui.navigate.to("/ui/login")

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
            ui.colors(primary="#34495E")
        else:
            ui.colors()

    def initialize_language_selector(self, language_selector):
        """Initialize language selector with user's language"""

        user_settings = user_state.get_user_settings()
        setup_i18n(user_settings.language)  # Initialize i18n with user's language

        language_selector.value = user_settings.language

    async def handle_language_change(self, e):
        """Handle language change event"""

        # Update user settings
        await user_state.update_user_settings(self.api_client, language=e.value)
        # Update current language
        setup_i18n(e.value)

    def toggle(self):
        """Toggle the left drawer"""

        self.left_drawer.toggle()
