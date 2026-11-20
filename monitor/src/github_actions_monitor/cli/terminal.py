# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What the command line knows about the place it writes to: colour, width and a pipe that closes early. Standard library only.

  --color auto    colour only on a terminal, never with NO_COLOR set (not empty) or TERM=dumb; the default
  --color always  colour whatever the destination (a pager that understands it)
  --color never   no escape sequence at all

With no terminal (a redirect, `tee`, a pipe, cron) the width is COLUMNS when it is a number and 80 otherwise, no escape sequence is written (text that came from GitHub is cleaned of the ones it carries) and a
reader that closes early (`| head`) ends the command quietly instead of with a traceback.
"""
import errno
import os
import re
import sys

MODES = ("auto", "always", "never")
DEFAULT_WIDTH = 80
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?|\x1b[@-_]")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1a\x1c-\x1f\x7f]")      # no tab, no line break, no escape (the escape is handled apart)


def is_tty(stream):
    try:
        return bool(stream and stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def use_color(mode, stream=None, env=None):
    """Whether to write colour: the mode, then NO_COLOR and TERM=dumb, then whether the stream is a terminal."""
    env = os.environ if env is None else env
    mode = mode if mode in MODES else "auto"
    if mode == "never":
        return False
    if mode == "always":
        return True
    if (env.get("NO_COLOR") or "") != "" or (env.get("TERM") or "") == "dumb":
        return False
    return is_tty(sys.stdout if stream is None else stream)


def width(stream=None, env=None, default=DEFAULT_WIDTH):
    """Columns to write to: the terminal when there is one, else COLUMNS when it is a sensible number, else 80."""
    env = os.environ if env is None else env
    stream = sys.stdout if stream is None else stream
    if is_tty(stream):
        try:
            return max(40, os.get_terminal_size(stream.fileno()).columns)
        except (AttributeError, ValueError, OSError):
            pass
    raw = (env.get("COLUMNS") or "").strip()
    if raw.isdigit() and 20 <= int(raw) <= 1000:
        return int(raw)
    return default


def clean(text):
    """The text without the escape sequences and control characters it may carry (names and titles come from GitHub)."""
    text = ANSI.sub("", text).replace(chr(27), "")
    return CONTROL.sub("", text)


def bold(text, on):
    return "\x1b[1m" + text + "\x1b[0m" if on else text


def emit(text, stream=None, end="\n"):
    """Write one answer; a reader that went away (`| head`) ends it without an error. Returns False when the reader is gone."""
    stream = sys.stdout if stream is None else stream
    try:
        stream.write(text + end)
        stream.flush()
        return True
    except (BrokenPipeError, OSError) as error:
        if not isinstance(error, BrokenPipeError) and getattr(error, "errno", None) not in (errno.EPIPE, errno.EINVAL) and getattr(error, "winerror", None) not in (109, 232):
            raise
        try:      # the interpreter would flush again at exit and raise the same error: point the stream at nothing
            os.dup2(os.open(os.devnull, os.O_WRONLY), stream.fileno())
        except (OSError, ValueError, AttributeError):
            pass
        return False
