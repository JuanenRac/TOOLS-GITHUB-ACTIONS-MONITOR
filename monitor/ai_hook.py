# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The gate script of an AI tool: it tells the AI session what the monitor sees, without a skill or a plugin. Installed by `monitor_cli.py ai-hook install` (see docs/AI_ALERTS.md).

    python ai_hook.py EVENT [--format assistant|cursor|generic] [--config FILE]

The tool runs it at some moments and writes a JSON document to its standard input (`hook_event_name` among other things):
  * SessionStart / UserPromptSubmit: when real red alerts are open it writes the summary of ALERTS_BRIEF.md as extra context for the AI;
  * Stop: only with `ai_alerts.client_hook.block_on_stop` (OFF by default) and not more than once every `cooldown_minutes`, it asks the AI to look at the open real alerts before it ends
    its turn (never when the tool is already retrying because of this script).
Read only: the script reads the brief and the configuration file, notes in `ai_heartbeat.json` (next to the brief) that an AI read it, and keeps its own small state file for the cooldown.
It needs nothing but Python, writes only ASCII (JSON escapes, so no accented letter is garbled by a Windows console) and never raises an error towards the tool: on any failure it writes
nothing and ends with 0. Every figure is a setting of `ai_alerts.client_hook` in the configuration file of the monitor.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULTS = {"enabled": True, "block_on_stop": False, "cooldown_minutes": 20, "stale_hours": 3, "max_lines": 12, "max_chars": 2400}
TEXTS = {
    "en": {"head": "[MONITOR] {n} real red alert(s) open (brief updated {age} ago):", "stale": "(Warning: the brief is {age} old; the monitor may be stopped.)",
           "act": "Diagnose them with the log of the failing run and act without waiting to be told.", "block": "The monitor reports {n} real red alert(s): look at them and act."},
    "es": {"head": "[MONITOR] {n} alerta(s) roja(s) real(es) abierta(s) (resumen actualizado hace {age}):", "stale": "(Aviso: el resumen tiene {age}; puede que el monitor este parado.)",
           "act": "Diagnostica con el log de la ejecucion fallida y actua sin esperar a que te lo digan.", "block": "El monitor indica {n} alerta(s) roja(s) real(es): revisalas y actua."},
    "de": {"head": "[MONITOR] {n} echte rote Warnung(en) offen (Zusammenfassung vor {age} aktualisiert):", "stale": "(Hinweis: die Zusammenfassung ist {age} alt; der Monitor ist vielleicht angehalten.)",
           "act": "Diagnostiziere sie mit dem Log des fehlgeschlagenen Laufs und handle, ohne darauf zu warten.", "block": "Der Monitor meldet {n} echte rote Warnung(en): pruefe sie und handle."},
    "fr": {"head": "[MONITOR] {n} alerte(s) rouge(s) reelle(s) ouverte(s) (resume mis a jour il y a {age}) :", "stale": "(Attention : le resume date de {age} ; le moniteur est peut-etre arrete.)",
           "act": "Diagnostique-les avec le journal de l'execution en echec et agis sans attendre qu'on te le dise.", "block": "Le moniteur signale {n} alerte(s) rouge(s) reelle(s) : examine-les et agis."},
    "it": {"head": "[MONITOR] {n} avviso/i rosso/i reale/i aperto/i (riepilogo aggiornato {age} fa):", "stale": "(Attenzione: il riepilogo ha {age}; il monitor potrebbe essere fermo.)",
           "act": "Diagnosticali con il log dell'esecuzione fallita e agisci senza aspettare che te lo dicano.", "block": "Il monitor segnala {n} avviso/i rosso/i reale/i: esaminali e agisci."},
    "ja": {"head": "[MONITOR] 実際の赤いアラートが {n} 件あります (ブリーフの更新は {age} 前):", "stale": "(注意: ブリーフは {age} 前のものです。モニターが停止しているかもしれません。)",
           "act": "失敗した実行のログで原因を調べ、言われる前に対応してください。", "block": "モニターが実際の赤いアラート {n} 件を報告しています。確認して対応してください。"},
    "zh": {"head": "[MONITOR] 有 {n} 个真实的红色告警未处理 (摘要更新于 {age} 前):", "stale": "(注意: 摘要已有 {age}; 监控器可能已停止。)",
           "act": "用失败运行的日志诊断它们, 不必等待提示就采取行动。", "block": "监控器报告了 {n} 个真实的红色告警: 请查看并处理。"},
    "pt": {"head": "[MONITOR] {n} alerta(s) vermelho(s) real/reais aberto(s) (resumo atualizado ha {age}):", "stale": "(Aviso: o resumo tem {age}; o monitor pode estar parado.)",
           "act": "Diagnostica-os com o registo da execucao falhada e age sem esperar que to digam.", "block": "O monitor indica {n} alerta(s) vermelho(s) real/reais: analisa-os e age."},
}
KNOWN = {"sessionstart": "start", "userpromptsubmit": "prompt", "beforesubmitprompt": "prompt", "stop": "stop"}


def language(env=None):
    env = os.environ if env is None else env
    for name in ("MONITOR_LANG", "LC_ALL", "LANG", "LANGUAGE"):
        code = (env.get(name) or "").lower().replace("-", "_")
        for lang in TEXTS:
            if code.startswith(lang):
                return lang
    return "en"


def load_config(path=None):
    """The `ai_alerts` block of the configuration file of the monitor (next to this script, or MONITOR_CONFIG, or --config), or {}."""
    candidate = Path(path or os.environ.get("MONITOR_CONFIG") or HERE / "actions_monitor.json")
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        return data.get("ai_alerts") if isinstance(data.get("ai_alerts"), dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def settings(block):
    client = block.get("client_hook") if isinstance(block.get("client_hook"), dict) else {}
    out = dict(DEFAULTS)
    for key, (low, high) in {"cooldown_minutes": (1, 1440), "stale_hours": (1, 168), "max_lines": (1, 40), "max_chars": (400, 8000)}.items():
        value = client.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            out[key] = value
    for key in ("enabled", "block_on_stop"):
        if isinstance(client.get(key), bool):
            out[key] = client[key]
    return out


def feed_folder(block):
    text = block.get("folder") if isinstance(block.get("folder"), str) else ""
    ok = bool(text.strip()) and len(text) <= 260 and not any(ord(c) < 32 for c in text) and not text.startswith(("\\\\", "//")) and not re.match(r"^(?:[Dd]:|/mnt/[dD](?:/|$))", text.strip())
    return Path(text.strip()) if ok else HERE


def read_brief(folder, now):
    """(number of real alerts open, the lines worth showing, age in seconds) or None when there is no brief."""
    path = folder / "ALERTS_BRIEF.md"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        stamp = path.stat().st_mtime
    except OSError:
        return None
    match = re.search(r"^updated_epoch: (\d+)$", text, re.M)
    if match:
        stamp = int(match.group(1))
    count = re.search(r"(\d+)\s+real alert", text)
    lines = [line.rstrip() for line in text.splitlines() if line.startswith("- ") or (line.startswith("  ") and line.strip())]
    return (int(count.group(1)) if count else 0), lines, max(0, now - stamp)


def human_age(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600} h" if seconds >= 3600 else (f"{seconds // 60} min" if seconds >= 60 else f"{seconds} s")


def summary(count, lines, age, cfg, lang):
    text = TEXTS[lang]
    shown = [re.sub(r"\s+", " ", line)[:230] for line in lines[:cfg["max_lines"]]]
    out = text["head"].format(n=count, age=human_age(age)) + "\n" + "\n".join(shown)
    if age > cfg["stale_hours"] * 3600:
        out += "\n" + text["stale"].format(age=human_age(age))
    return (out[:cfg["max_chars"]] + "\n" + text["act"]).strip()


def private_write(path, text):
    """The state files of this script are created readable by their owner only (mode 0600; on Windows the folder permissions rule)."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(text.encode("utf-8"))


def touch(folder, now):
    try:
        path = folder / "ai_heartbeat.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        reads = data.get("reads") if isinstance(data.get("reads"), dict) else {}
        reads["hook"] = {"at": int(now), "client": "ai_hook"}
        tmp = Path(str(path) + ".tmp")
        private_write(tmp, json.dumps({"reads": reads}, ensure_ascii=True) + "\n")
        os.replace(tmp, path)
    except OSError:
        pass


def cooldown_ok(folder, minutes, now):
    """True (and the moment is kept) when the last block was more than `minutes` ago."""
    path = folder / "ai_hook_state.json"
    try:
        last = float(json.loads(path.read_text(encoding="utf-8")).get("last_block", 0))
    except (OSError, ValueError, AttributeError, TypeError):
        last = 0.0
    if now - last < minutes * 60:
        return False
    try:
        private_write(path, json.dumps({"last_block": now}))
    except OSError:
        pass
    return True


def answer(kind, event_kind, text, fmt):
    """The document the tool expects, as a dict, or None (nothing to say)."""
    if fmt == "generic":
        return {"text": text}
    if fmt == "cursor":
        return {"additional_context": text} if kind == "start" else ({"followup_message": text} if kind == "stop" else None)
    if kind == "stop":
        return {"decision": "block", "reason": text}
    return {"hookSpecificOutput": {"hookEventName": event_kind, "additionalContext": text}}


def run(argv, stdin_text, now=None, env=None):
    """The text to write to standard output (empty = nothing). Raises nothing the caller must handle: main() wraps it."""
    now = time.time() if now is None else now
    args = list(argv)
    fmt = "assistant"
    config_path = None
    if "--format" in args:
        index = args.index("--format")
        fmt = args[index + 1] if index + 1 < len(args) and args[index + 1] in ("assistant", "cursor", "generic") else "assistant"
        del args[index:index + 2]
    if "--config" in args:
        index = args.index("--config")
        config_path = args[index + 1] if index + 1 < len(args) else None
        del args[index:index + 2]
    try:
        payload = json.loads(stdin_text or "{}")
    except ValueError:
        payload = {}
    payload = payload if isinstance(payload, dict) else {}
    event = str(payload.get("hook_event_name") or (args[0] if args else ""))
    kind = KNOWN.get(event.lower())
    block = load_config(config_path)
    cfg = settings(block)
    if kind is None or not cfg["enabled"]:
        return ""
    folder = feed_folder(block)
    brief = read_brief(folder, now)
    if not brief:
        return ""
    touch(folder, now)
    count, lines, age = brief
    if count <= 0:
        return ""
    lang = language(env)
    if kind == "stop":
        if not cfg["block_on_stop"] or payload.get("stop_hook_active") or not cooldown_ok(folder, cfg["cooldown_minutes"], now):
            return ""
        text = TEXTS[lang]["block"].format(n=count) + "\n" + summary(count, lines, age, cfg, lang)
    else:
        text = summary(count, lines, age, cfg, lang)
    reply = answer(kind, event, text, fmt)
    return json.dumps(reply, ensure_ascii=True) if reply else ""


def main(argv=None):
    try:
        stdin_text = "" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
        out = run(sys.argv[1:] if argv is None else argv, stdin_text)
        if out:
            sys.stdout.write(out + "\n")
            sys.stdout.flush()
    except Exception:      # noqa: BLE001 - a gate script must never break the session of the AI
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
