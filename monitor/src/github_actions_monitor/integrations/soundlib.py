# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The library of sounds of the monitor: more than fifty short patterns, each one made of a few notes that the browser synthesizes with the Web Audio API (no audio file, nothing downloaded, nothing sent).

This module is the ONE source of the library. The page (actions_monitor.html) and the wall screens (screens.html) carry the same generated copy between `/*SND-LIBRARY-BEGIN*/` and `/*SND-LIBRARY-END*/`
(tools/make_sound_library.py writes it and `--check` fails when a copy is out of date; a test runs the check), and the sound of this computer (soundalert.py) takes its tones from here as well.

A sound is `(wave, notes)`; a note is `(Hz, start in seconds, length in seconds)` or, for a slide, `(Hz, start, length, Hz at the end)`. The first eleven are the sounds of the eleven kinds of event
(the ones every installation always had); the others are free to assign: `sound.voices` gives a kind of event another sound of the library for the page and for this computer, and `screens.sound_voices`
does it for the wall screens only. Both are a text of `kind=sound` pairs separated by commas (for instance `new_red=coin,warning=drop`); a name that is not in the library is ignored.
Standard library only."""
import re

WAVES = ("sine", "triangle", "square", "sawtooth")
#: the eleven kinds of event of the settings and the key of the page for each one (the page calls them red, score, conn and live)
PAGE_KEY = {"new_red": "red", "sentinel": "sentinel", "stuck": "stuck", "score_drop": "score", "connection_lost": "conn", "warning": "warning", "resolved": "resolved", "report": "report", "lesson": "lesson",
            "info": "info", "live_recovered": "live"}
KINDS = tuple(PAGE_KEY)
PAIR_RE = re.compile(r"^[a-z_]{3,20}=[a-z0-9_]{2,24}\Z")
MAX_VOICES_TEXT = 400


def _run(wave, freqs, step, length, to=None):
    """Notes one after the other: the same length, `step` seconds apart."""
    return (wave, tuple((hz, round(i * step, 3), length) + ((to[i],) if to else ()) for i, hz in enumerate(freqs)))


def _slide(wave, start, stop, length):
    return (wave, ((start, 0, length, stop),))


LIBRARY = {
    # the eleven kinds of event (unchanged)
    "red": ("sine", ((880, 0, .15), (1175, .22, .15))),
    "sentinel": ("triangle", ((330, 0, .14), (330, .2, .14), (330, .4, .14))),
    "stuck": ("sine", ((740, 0, .7, 370),)),
    "score": ("triangle", ((784, 0, .16), (622, .2, .16), (466, .4, .28))),
    "conn": ("sine", ((392, 0, .3), (262, .38, .4))),
    "warning": ("triangle", ((660, 0, .16), (660, .26, .16))),
    "resolved": ("sine", ((523, 0, .12), (659, .14, .12), (784, .28, .25))),
    "report": ("triangle", ((1047, 0, .12), (784, .16, .3))),
    "lesson": ("sine", ((1319, 0, .08), (1568, .1, .08), (1976, .2, .16))),
    "info": ("sine", ((988, 0, .22),)),
    "live": ("sine", ((392, 0, .12), (523, .14, .12), (659, .28, .12), (880, .42, .22))),
    # clear single notes and pairs
    "bell": ("sine", ((1319, 0, .5),)),
    "chime": ("sine", ((1047, 0, .12), (1319, .15, .3))),
    "ding_dong": ("sine", ((880, 0, .3), (659, .38, .45))),
    "doorbell": ("sine", ((659, 0, .25), (523, .3, .4))),
    "ding": ("triangle", ((1568, 0, .3),)),
    "ping_high": ("sine", ((2093, 0, .1),)),
    "ping_low": ("sine", ((440, 0, .25),)),
    "tick_soft": ("triangle", ((1760, 0, .03),)),
    "tock_soft": ("triangle", ((1175, 0, .04),)),
    "double_tick": ("triangle", ((1760, 0, .03), (1760, .12, .03))),
    "tick_tock": ("triangle", ((1760, 0, .04), (1175, .3, .06))),
    "knock": ("triangle", ((196, 0, .06), (196, .14, .06))),
    "knock_three": ("triangle", ((196, 0, .06), (196, .14, .06), (196, .28, .06))),
    "blip": ("square", ((1500, 0, .06),)),
    "bloop": ("sine", ((320, 0, .1, 700),)),
    "bubble": ("sine", ((500, 0, .12, 900), (700, .16, .1, 1100))),
    "drop": ("sine", ((1200, 0, .18, 500),)),
    "droplet": ("sine", ((1500, 0, .07, 900), (1100, .14, .1, 600))),
    # melodies and arpeggios
    "arpeggio_up": _run("sine", (523, 659, 784, 1047), .1, .12),
    "arpeggio_down": _run("sine", (1047, 784, 659, 523), .1, .12),
    "minor_up": _run("triangle", (440, 523, 659), .12, .14),
    "minor_down": _run("triangle", (659, 523, 440), .12, .14),
    "fanfare": ("square", ((523, 0, .1), (523, .12, .1), (523, .24, .1), (784, .38, .4))),
    "level_up": _run("square", (392, 523, 659, 784, 1047), .08, .08),
    "coin": ("square", ((988, 0, .07), (1319, .08, .35))),
    "harp_up": _run("sine", (392, 494, 587, 784, 988, 1175), .07, .2),
    "harp_down": _run("sine", (1175, 988, 784, 587, 494, 392), .07, .2),
    "marimba": _run("triangle", (523, 659, 523, 784), .13, .1),
    "xylophone": _run("sine", (1047, 1319, 1568, 2093), .09, .07),
    "pluck": ("triangle", ((330, 0, .1), (247, .12, .2))),
    "cascade": _run("sine", (1568, 1319, 1047, 880, 659, 523), .06, .08),
    "sparkle": _run("sine", (1568, 2093, 1760, 2349, 2093), .05, .05),
    "ascend": _run("triangle", (330, 392, 440, 494, 587), .1, .1),
    "descend": _run("triangle", (587, 494, 440, 392, 330), .1, .1),
    "notify_a": ("sine", ((880, 0, .1), (1175, .12, .1), (1568, .24, .18))),
    "notify_b": ("triangle", ((1568, 0, .1), (1175, .12, .1), (880, .24, .18))),
    "notify_c": ("sine", ((784, 0, .08), (988, .1, .08), (784, .2, .08), (988, .3, .16))),
    # slides and electronic sounds
    "sweep_up": _slide("sine", 300, 1400, .45),
    "sweep_down": _slide("sine", 1400, 300, .45),
    "whistle_up": _slide("sine", 800, 1800, .3),
    "whistle_down": _slide("sine", 1750, 800, .3),
    "zap": _slide("sawtooth", 1800, 200, .18),
    "laser": _slide("square", 2200, 300, .22),
    "radar": ("sine", ((1000, 0, .08), (1000, .33, .08), (1000, .66, .08))),
    "sonar": ("sine", ((700, 0, .9, 650),)),
    "beacon": ("sine", ((880, 0, .06), (880, .25, .06), (880, .5, .06), (880, .75, .06))),
    "heartbeat": ("sine", ((110, 0, .12), (90, .18, .16))),
    # urgent sounds
    "alarm_fast": ("square", ((880, 0, .1), (660, .14, .1), (880, .28, .1), (660, .42, .1))),
    "siren": ("sawtooth", ((600, 0, .45, 1000), (1000, .45, .45, 600))),
    "klaxon": ("sawtooth", ((220, 0, .4), (220, .5, .4))),
    "buzzer": ("square", ((150, 0, .4),)),
    "gong": ("sine", ((196, 0, .9),)),
    "phone": ("square", ((1000, 0, .08), (800, .1, .08), (1000, .2, .08), (800, .3, .08))),
    "cuckoo": ("sine", ((784, 0, .2), (622, .28, .3))),
}
DEFAULT_COUNT = len(PAGE_KEY)
assert len(LIBRARY) >= 50 and all(wave in WAVES for wave, _ in LIBRARY.values())


def names():
    """The names of the sounds of the library, the eleven of the kinds first."""
    return tuple(LIBRARY)


def free_names():
    """The sounds that are not the default of a kind (the ones a person may assign)."""
    return tuple(n for n in LIBRARY if n not in PAGE_KEY.values())


def parse_voices(value):
    """The kinds that a text (or a dict) gives another sound: {kind: sound} with only the pairs that name a kind of event and a sound of the library; anything else is left out."""
    pairs = []
    if isinstance(value, dict):
        pairs = [(str(k), str(v)) for k, v in value.items()]
    elif isinstance(value, str):
        pairs = [tuple(part.strip().split("=", 1)) for part in value[:MAX_VOICES_TEXT].split(",") if "=" in part]
    out = {}
    for kind, sound in pairs:
        kind, sound = kind.strip().lower(), sound.strip().lower()
        page = kind if kind in LIBRARY and kind in PAGE_KEY.values() else PAGE_KEY.get(kind)
        if page and sound in LIBRARY:
            out[next(k for k, v in PAGE_KEY.items() if v == page)] = sound
    return out


def valid_text(value):
    """True for a text of `kind=sound` pairs that is entirely valid (empty is valid: no change)."""
    text = str(value or "").strip()
    if not text:
        return True
    if len(text) > MAX_VOICES_TEXT:
        return False
    for part in text.split(","):
        part = part.strip()
        if not PAIR_RE.match(part):
            return False
        kind, sound = part.split("=", 1)
        if kind not in PAGE_KEY or sound not in LIBRARY:
            return False
    return True


def merged(*layers):
    """Voices from several layers (the last one wins): each layer a text or a dict."""
    out = {}
    for layer in layers:
        out.update(parse_voices(layer))
    return out


def server_tones(name):
    """The sound as a list of (Hz, milliseconds) one after the other (the computer's beep has no rests or slides): the start of a slide is used."""
    wave_notes = LIBRARY.get(name)
    if not wave_notes:
        return ()
    return tuple((int(max(37, min(32767, note[0]))), int(max(20, min(1200, round(note[2] * 1000))))) for note in wave_notes[1])


def js_block():
    """The text of the library between its markers, exactly as the page and the wall screens carry it (one sound per line, JSON values, so a test can read it back)."""
    import json
    lines = []
    for name, (wave, notes) in LIBRARY.items():
        lines.append(' %s:{"w":%s,"n":%s}' % (json.dumps(name), json.dumps(wave), json.dumps([list(n) for n in notes], separators=(",", ":"))))
    return "/*SND-LIBRARY-BEGIN*/\nconst SND_LIBRARY={\n" + ",\n".join(lines) + "\n};\n/*SND-LIBRARY-END*/"
