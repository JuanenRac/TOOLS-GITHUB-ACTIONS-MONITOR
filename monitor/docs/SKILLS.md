<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SKILLS_spa.md) | [🇫🇷 Français](SKILLS_fra.md) | [🇮🇹 Italiano](SKILLS_ita.md) | [🇩🇪 Deutsch](SKILLS_deu.md) | [🇨🇳 简体中文](SKILLS_zho.md) | [🇯🇵 日本語](SKILLS_jpn.md) | [🇵🇹 Português](SKILLS_por.md)

# Skills for AIs

The monitor carries two skills: short guides, in English, that tell an AI how to work with it. They are in the folder `skills/` of the package, in the page (Settings, AI tab) and one command installs them.

## The two skills

- `skills/internal`: for the AI built into the monitor, local (Ollama, a llama.cpp server, LM Studio) or external (the API of a provider). It says what the monitor is and what it sees, what it may read, what it must never do, how to diagnose a red run, when to stay silent and how to use and propose lessons. Its core (`SKILL.md`) is added to every prompt of that AI, cut to `ai.skill_max_chars`, when `ai.skill` is on.
- `skills/external`: for the AIs that talk to the monitor from outside, in every direction: reading (`/api/ai/*`, the files of `ai/`), being told (the stream or the brief every few minutes), writing (acknowledge, lessons, failures, notification preferences) with the permissions that belong, the link between the monitor and a session, the brief before a push and the whole self-learning cycle. It covers an AI with a command line, an AI with only HTTP or files, an AI with MCP and an AI on the stream.

## What is inside

Each skill is a short `SKILL.md` (the core) and a folder `references/` that is read only when needed, so a model with a small context can take just the core: scenarios step by step (a real red, a transient red, low quota, a degraded monitor, a repeated failure, a new lesson, no network, several screens), the self-learning cycle, the providers and their limits, security (prompt injection from logs, secrets, minimum permissions, audit of what an AI writes) and the references generated from the code.

## Nothing is left out

The references (`api.md`, `cli.md`, `settings.md`, `files.md`, `roles.md`, `tabs.md`) and `skills/COVERAGE.md` are GENERATED from the code by `python tools/make_skill_refs.py`: every endpoint with the least role that may call it, every command and flag, every setting with its default, every file the monitor writes, every role and every tab. A test reads the same lists from the code and fails when something is not named in the skills, so a new endpoint, command, setting or file cannot appear without being described to the AIs (and the generator stops until its note is written).

## Install

Copy the skill to the folder your AI tool reads its skills from:

```
python bin/monitor_cli.py install-skill internal --dest /path/to/the/skills/folder
python bin/monitor_cli.py install-skill external --dest /path/to/the/skills/folder
```

## Safety of the installer

It writes `github-actions-monitor-internal` or `github-actions-monitor-external` inside the folder you give and nothing else. It never overwrites a file that differs from the one in the package (it keeps yours and says which), and it refuses the D: drive and network paths. A second run changes nothing.

## In the page and over HTTP

In the Settings, AI tab, the block **Skills for AIs** has Copy (the core of the skill) and Download (the whole skill with its references in one file) for each one. `GET /api/skills` lists them and `GET /api/skills?name=internal|external[&file=references/api.md][&all=1]` returns the text; it is read only.

## Settings

`ai.skill` (on) and `ai.skill_max_chars` (3000; 1500 for a small local model). Registering failures from outside is `POST /api/ai/failures` and needs `lessons.allow_write` and an administrator, like writing a lesson.
