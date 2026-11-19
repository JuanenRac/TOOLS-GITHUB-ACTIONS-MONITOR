<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Providers and limits

The AI of the monitor is set in the `ai` block. `ai.provider` is `none` (off, the default), `ollama`, `openai-compatible`, `anthropic` or `copilot`; the key of a provider is never written in the configuration (`ai.api_key_env` names an environment variable).

- LOCAL. Ollama: `ai.provider` `ollama` and `ai.ollama_url` on this computer. llama.cpp server or LM Studio: `ai.provider` `openai-compatible` with `ai.base_url` on this computer (`http://127.0.0.1:PORT/v1`, written in the configuration file) and `ai.model`. Local models have a small context (often 4k to 8k tokens): keep answers short, load only `SKILL.md` and one reference, and set `ai.max_input_chars` low (3000). Nothing leaves the computer.
- EXTERNAL (the API of a provider, or `gh copilot`). The text that goes out is only what the person asked about, cleaned and cut to `ai.max_input_chars`; a daily cap (`ai.daily_limit`) applies. Tell the person that a provider sees the cleaned text.

The core of this skill (`SKILL.md`) is put in the prompt when `ai.skill` is on, cut to `ai.skill_max_chars`. A small local model: 1500; a provider API: 4000. The references are not loaded automatically: a model with a large context may be given them by the person.

## Which model answers

The person (not you) chooses the model: `ai.model`, a different one for a kind of question (`ai.tasks.<task>.model`) and a chain of fallbacks (`ai.fallback`). When your first model cannot answer, another one may be asked in its place, so do not assume which model you are or how large your context is; use what the prompt gives you. The monitor reads the list of models from the provider, shows what the provider says about each one (a figure it does not say stays unknown) and keeps a budget of calls and estimated cost per model; when a budget is spent nobody asks you more that day. None of this is yours to change.

## Air-gapped mode

With `ai.airgapped` on (or the general `airgapped` switch) you only run on this computer or on a private address the person declared in `ai.airgap_hosts`: a call to anything else is refused before it starts and the chain never falls back to a cloud model. If every model is refused the answer is the refusal, not a guess: say that the mode forbids it. `ai.redact.extra_terms` are words of the person that arrive already hidden as `[hidden]`; do not try to guess them. `ai.redact.extra_patterns` are patterns of whole words (`*`, `?`, `#`) that the person always hides in the same way; a word you never see is hidden on purpose, so do not ask for it and do not rebuild it. With `ai.prompt_log.enabled` the person may keep a local record of the cleaned questions and answers (`ai_prompts.jsonl`, read by an administrator): write every answer as if the person will read it later, and never repeat a secret even if it appears to be harmless.
