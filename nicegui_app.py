from nicegui import ui, app
from contextlib import suppress
from pathlib import Path

from nice_gui.pages.chat.chat import Chat

# Import page components
from nice_gui.pages.login import LoginPage
from nice_gui.pages.knowledge_warehouse.knowledge import KnowledgePage
from nice_gui.pages.profile.register import UserRegister
from nice_gui.pages.profile.user_profile import UserProfile
from nice_gui.pages.translation.translation import TranslationPage
from nice_gui.state.user_state import user_state

# Define storage secret as a constant
STORAGE_SECRET = "c336912d82d41aae33905f51acc0f63294ec77b71ab1915cd91409d6916d55b8"

# Get the absolute path to your static directory
STATIC_PATH = Path(__file__).parent / "nice_gui" / "static"
print(f"Static path: {STATIC_PATH}")  # Debug print to verify path

# Add static files directory
app.add_static_files("/static", STATIC_PATH)


# Authentication middleware
def auth_required():
    if not user_state.get_auth() or not user_state.get_auth().authenticated:
        # Store the current path as string for redirect after login
        current_path = ui.context.client.page.path  # Convert to string
        with suppress(Exception):  # Safely update storage
            if current_path is not None:
                user_state.update_redirect_path(current_path)
        # Redirect to login page
        ui.navigate.to("/ui/login")
        return True
    return False


# Main application class
class Application:
    def __init__(self):
        self.setup_routes()

    def setup_routes(self):
        @ui.page("/ui", title="Login")
        @ui.page("/ui/", title="Login")
        @ui.page("/ui/login", title="Login")
        def login_page():
            # Clear any existing auth if accessing login page
            user_state.clear_all()
            LoginPage()

        @ui.page("/ui/chat", title="Chat")
        @ui.page("/ui/chat/", title="Chat")
        @ui.page("/ui/chat/{tab}", title="Chat")
        def chat_page(tab: str = "chat"):
            if not auth_required():  # Only render if authenticated
                Chat()

        @ui.page("/ui/knowledge", title="Knowledge Warehouse")
        @ui.page("/ui/knowledge/", title="Knowledge Warehouse")
        @ui.page("/ui/knowledge/{tab}", title="Knowledge Warehouse")
        def knowledge_page(tab: str = "chat"):
            if not auth_required():  # Only render if authenticated
                KnowledgePage(tab)

        @ui.page("/ui/translation", title="Translator")
        @ui.page("/ui/translation/", title="Translator")
        def translation_page():
            if not auth_required():  # Only render if authenticated
                TranslationPage()

        @ui.page("/ui/profile", title="Profile")
        @ui.page("/ui/profile/", title="Profile")
        def profile_page():
            if not auth_required():  # Only render if authenticated
                UserProfile()

        @ui.page("/ui/register", title="User Register")
        @ui.page("/ui/register/", title="User Register")
        def user_register_page():
            UserRegister()


def startup():
    ai_ui = Application()

    @app.on_connect
    def handle_connect():
        with suppress(Exception):
            print("Client connected")

    @app.on_disconnect
    def handle_disconnect():
        with suppress(Exception):
            print("Client disconnected")

# Run startup code
startup()

# Only run startup() if running directly
if __name__ in {"__main__", "__mp_main__"}:
    # Run the app locally
    ui.run(
        storage_secret=STORAGE_SECRET,  # Use the same secret
        port=5005,
    )
else:
    # Run the app in a production environment
    ui.run(storage_secret=STORAGE_SECRET)

# Expose the app object for uvicorn
nicegui_app = app
