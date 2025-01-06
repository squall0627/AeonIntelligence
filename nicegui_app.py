from nicegui import ui, app
from contextlib import suppress
from pathlib import Path

from nice_gui.pages.chat.chat import Chat

# Import page components
from nice_gui.pages.login import LoginPage
from nice_gui.pages.knowledge_warehouse.knowledge import KnowledgePage
from nice_gui.pages.profile.user_profile import UserProfile
from nice_gui.pages.translation.translation import TranslationPage

# Get the absolute path to your static directory
STATIC_PATH = Path(__file__).parent / "nice_gui" / "static"
print(f"Static path: {STATIC_PATH}")  # Debug print to verify path

# Add static files directory
app.add_static_files("/static", STATIC_PATH)


# Authentication middleware
def auth_required():
    if not app.storage.user.get("authenticated", False):
        # Store the current path as string for redirect after login
        # current_path = str(ui.page.path)  # Convert to string
        # with suppress(Exception):  # Safely update storage
        #     if ui.page.path is not None:
        #         app.storage.user.update({'redirect': ui.page.path})
        # Redirect to login page
        ui.navigate.to("/ui")
        return True
    return False


# Main application class
class Application:
    def __init__(self):
        self.setup_routes()

    def setup_routes(self):
        @ui.page("/ui", title="Login")
        @ui.page("/ui/login", title="Login")
        def login_page():
            # Clear any existing auth if accessing login page
            with suppress(Exception):  # Safely clear storage
                app.storage.user.clear()
            LoginPage()

        @ui.page("/ui/chat", title="Chat")
        @ui.page("/ui/chat/{tab}", title="Chat")
        def chat_page(tab: str = "chat"):
            if not auth_required():  # Only render if authenticated
                Chat()

        @ui.page("/ui/knowledge", title="Knowledge Warehouse")
        @ui.page("/ui/knowledge/{tab}", title="Knowledge Warehouse")
        def knowledge_page(tab: str = "chat"):
            if not auth_required():  # Only render if authenticated
                KnowledgePage(tab)

        @ui.page("/ui/translation", title="Translator")
        def translation_page():
            if not auth_required():  # Only render if authenticated
                TranslationPage()

        @ui.page("/ui/profile", title="Profile")
        def profile_page():
            if not auth_required():  # Only render if authenticated
                UserProfile()


if __name__ in {"__main__", "__mp_main__"}:
    ai_ui = Application()

    @app.on_connect
    def handle_connect():
        with suppress(Exception):
            print("Client connected")

    @app.on_disconnect
    def handle_disconnect():
        with suppress(Exception):
            print("Client disconnected")

    # Run the app
    ui.run(
        storage_secret="your-secret-key",
        port=5005,
        # before_startup=lambda: ui.get_backend().fastapi.mount("/api", api_main.app),
    )
