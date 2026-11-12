# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Translations for every text the user can read: web page, command line tools, report, events and error messages. Standard library only.

  t("key", name=value)       the text of `key` in the current language, with {name} placeholders filled in; falls back to English, then to the key
  language()                 the current language code; set_language("de") pins it; use_language("fr") is a context manager for one request/thread
  detect()                   configured language ("language" in actions_monitor.json, or the MONITOR_LANG environment variable), else the language of the
                             system, else English

The catalogues are locales/<lang>.json (flat {"key": "text"}; keys that start with "_" are metadata). The eight languages are en, es, de, fr, it, ja, zh
and pt (European Portuguese). Technical names (workflow, CI, build, release, gh, file names, commands, paths) are never translated: they are not in
the catalogues, they are passed in as values.

Per-request language: the web server wraps a request in use_language(), which is a ContextVar, so a thread that does not set it (the sentinel loop,
the event feed) keeps the configured language. The events written to events_monitor.jsonl also carry a stable `code`, so nobody has to parse text.
"""
import contextlib
import contextvars
import json
import locale
import os
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCALES = HERE / "locales"
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
NATIVE_NAMES = {"en": "English", "es": "Español", "de": "Deutsch", "fr": "Français", "it": "Italiano", "ja": "日本語", "zh": "中文", "pt": "Português"}
ENGLISH_NAMES = {"en": "English", "es": "Spanish", "de": "German", "fr": "French", "it": "Italian", "ja": "Japanese", "zh": "Chinese", "pt": "European Portuguese"}
HTML_LANG = {"en": "en", "es": "es", "de": "de", "fr": "fr", "it": "it", "ja": "ja", "zh": "zh-CN", "pt": "pt-PT"}
BROWSER_LOCALE = {"en": "en-GB", "es": "es-ES", "de": "de-DE", "fr": "fr-FR", "it": "it-IT", "ja": "ja-JP", "zh": "zh-CN", "pt": "pt-PT"}
DEFAULT = "en"

_lock = threading.Lock()
_catalogues = {}
_global = {"lang": None}
_request = contextvars.ContextVar("i18n_request_language", default=None)


def normalize(code):
    """'es_ES.UTF-8' / 'pt-BR' / 'zh_CN' / 'DE' -> a supported code, or None."""
    text = str(code or "").strip().lower().replace("_", "-").split(".")[0].split("@")[0]
    if not text or text in ("c", "posix"):
        return None
    head = text.split("-")[0]
    if head in LANGS:
        return head
    names = {"english": "en", "spanish": "es", "german": "de", "french": "fr", "italian": "it", "japanese": "ja", "chinese": "zh", "portuguese": "pt"}
    return names.get(head)


def system_language():
    """The language of the system if it is one of the eight, else None."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        found = normalize(str(os.environ.get(var, "")).split(":")[0])
        if found:
            return found
    if os.name == "nt":
        try:
            import ctypes
            buffer = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, 85):   # e.g. "es-ES", "pt-PT", "zh-CN"
                found = normalize(buffer.value)
                if found:
                    return found
        except (OSError, AttributeError, ValueError):
            pass
    try:
        return normalize(locale.getlocale()[0])
    except (ValueError, TypeError, AttributeError):
        return None


def detect(config_value=None):
    """Environment override > configured value > English. The language of the system does NOT decide: the tools start in English until you choose another one."""
    return normalize(os.environ.get("MONITOR_LANG")) or normalize(os.environ.get("JUANENRAC_LANG")) or normalize(config_value) or DEFAULT


def _load(lang):
    with _lock:
        if lang not in _catalogues:
            try:
                data = json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            _catalogues[lang] = {k: v for k, v in data.items() if isinstance(k, str) and not k.startswith("_") and isinstance(v, str)}
        return _catalogues[lang]


def catalogue(lang):
    return dict(_load(lang if lang in LANGS else DEFAULT))


def language():
    current = _request.get()
    if current:
        return current
    if _global["lang"] is None:
        import toolconfig
        _global["lang"] = detect(toolconfig.language())
    return _global["lang"]


def set_language(code):
    """Pins the language for the whole process (None = detect again). Returns the language now in force."""
    found = normalize(code)
    _global["lang"] = found
    return language()


@contextlib.contextmanager
def use_language(code):
    """The language for the code inside the `with` (this thread/request only); an unsupported code leaves the current one."""
    found = normalize(code)
    token = _request.set(found) if found else None
    try:
        yield language()
    finally:
        if token is not None:
            _request.reset(token)


def cli_language(argv=None):
    """For the command line tools: `--lang CODE` (or --lang=CODE) beats the environment (MONITOR_LANG / JUANENRAC_LANG), which beats the configuration.
    Pins the language and returns it; call it first thing in main(), before the help texts are built."""
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    for i, item in enumerate(args):
        if item.startswith("--lang="):
            found = normalize(item.partition("=")[2])
        elif item == "--lang" and i + 1 < len(args):
            found = normalize(args[i + 1])
        else:
            continue
        if found:
            return set_language(found)
    return set_language(detect(__import__("toolconfig").language()))


def tl(lang, key, /, **values):
    """Text of `key` in an explicit language."""
    lang = lang if lang in LANGS else DEFAULT
    text = _load(lang).get(key)
    if text is None:
        text = _load(DEFAULT).get(key)
    if text is None:
        return key
    if values:
        values = {k: (_tz().localize(v) if isinstance(v, str) and "Z" in v else v) for k, v in values.items()}   # an ISO UTC time in a text for people is shown in the zone of display.timezone
    try:
        return text.format(**values) if values else text
    except (KeyError, IndexError, ValueError):
        return text


def _tz():
    import tzdisplay
    return tzdisplay


def t(key, /, **values):
    return tl(language(), key, **values)


def about_line():
    """One line with the author and the licence in the current language (command line start-up and --version; the web page shows the same text)."""
    from tool_version import AUTHOR, LICENSE_ID
    return t("ui.about", author=AUTHOR, license=LICENSE_ID)


def ui_catalogues():
    """{lang: {key: text}} of the keys that start with 'ui.' or 'cfg.' (what the web page needs: the texts and the labels of the settings), for the page to embed."""
    return {lang: {k: v for k, v in _load(lang).items() if k.startswith(("ui.", "cfg.", "surf.t.", "lint.rule."))} for lang in LANGS}
