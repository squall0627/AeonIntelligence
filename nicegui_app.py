from nicegui import ui, app
from contextlib import suppress

# Import page components
from nice_gui.pages.login import LoginPage
from nice_gui.pages.knowledge import KnowledgePage
from nice_gui.pages.translation import TranslationPage


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
        @ui.page("/ui")
        def login_page():
            # Clear any existing auth if accessing login page
            with suppress(Exception):  # Safely clear storage
                app.storage.user.clear()
            LoginPage()

        @ui.page("/ui/knowledge")
        @ui.page("/ui/knowledge/{tab}")
        def knowledge_page(tab: str = "chat"):
            if not auth_required():  # Only render if authenticated
                KnowledgePage(tab)

        @ui.page("/ui/translation")
        def translation_page():
            if not auth_required():  # Only render if authenticated
                TranslationPage()


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

    ui.run(
        storage_secret="your-secret-key",
        port=5005,
        # before_startup=lambda: ui.get_backend().fastapi.mount("/api", api_main.app),
    )
