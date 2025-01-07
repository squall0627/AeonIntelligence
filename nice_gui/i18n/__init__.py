import threading

import i18n
import os

# Configure i18n
i18n.load_path.append(os.path.join(os.path.dirname(__file__), "locales"))
# i18n.set("locale", "en")
i18n.set("filename_format", "{locale}.json")
# i18n.set("file_format", "json")
i18n.set("skip_locale_root_data", True)
i18n.set("fallback", "en")

# Available languages
LANGUAGES = {"en": "English", "ja": "日本語", "zh": "中文"}

# Thread-local storage for the locale
_thread_locale = threading.local()


def setup_i18n(locale="en"):
    # """Set up i18n with the specified locale"""
    # i18n.set("locale", locale)
    """Set up i18n for the current thread"""
    _thread_locale.locale = locale


def get_locale():
    """Retrieve the current thread's locale (falling back to 'en')"""
    return getattr(_thread_locale, "locale", "en")


def t(key):
    """Shorthand for thread-local translation"""

    current_locale = get_locale()
    i18n.set("locale", current_locale)  # Temporarily set locale for this thread
    return i18n.t(key)
