<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Providers and limits

The AI of the monitor is set in the `ai` block. `ai.provider` is `none` (off, the default), `ollama`, `openai-compatible`, `anthropic` or `copilot`; the key of a provider is never written in the configuration (`ai.api_key_env` names an environment variable).

- LOCAL. Ollama: `ai.provider` `ollama` and `ai.ollama_url` on this computer. llama.cpp server or LM Studio: `ai.provider` `openai-compatible` with `ai.base_url` on this computer (`http://127.0.0.1:PORT/v1`, written in the configuration file) and `ai.model`. Local models have a small context (often 4k to 8k tokens): keep answers short, load only `SKILL.md` and one reference, and set `ai.max_input_chars` low (3000). Nothing leaves the computer.
- EXTERNAL (the API of a provider, or `gh copilot`). The text that goes out is only what the person asked about, cleaned and cut to `ai.max_input_chars`; a daily cap (`ai.daily_limit`) applies. Tell the person that a provider sees the cleaned text.

The core of this skill (`SKILL.md`) is put in the prompt when `ai.skill` is on, cut to `ai.skill_max_chars`. A small local model: 1500; a provider API: 4000. The references are not loaded automatically: a model with a large context may be given them by the person.
