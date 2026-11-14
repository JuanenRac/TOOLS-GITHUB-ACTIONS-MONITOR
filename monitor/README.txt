Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

GITHUB ACTIONS MONITOR + SENTINEL - 1.8.0
==========================================
Choose your language / Elige tu idioma / Sprache wählen / Choisissez votre langue / Scegli la lingua / 言語を選択 / 选择语言 / Escolha o idioma:

  English ........ docs/README_en.txt   docs/QUICKSTART_en.txt
  Español ........ docs/README_es.txt   docs/QUICKSTART_es.txt
  Deutsch ........ docs/README_de.txt   docs/QUICKSTART_de.txt
  Français ....... docs/README_fr.txt   docs/QUICKSTART_fr.txt
  Italiano ....... docs/README_it.txt   docs/QUICKSTART_it.txt
  日本語 ......... docs/README_ja.txt   docs/QUICKSTART_ja.txt
  中文 ........... docs/README_zh.txt   docs/QUICKSTART_zh.txt
  Português (PT) . docs/README_pt.txt   docs/QUICKSTART_pt.txt

QUICK START (English)
  1. Install Python 3.10+ and the GitHub CLI (gh); then run once:  gh auth login
  2. Start:  Windows: MONITOR_GITHUB_ACTIONS.bat | Linux: ./MONITOR_GITHUB_ACTIONS.sh | macOS: MONITOR_GITHUB_ACTIONS.command
  3. A page opens at http://127.0.0.1:8765 (only on your computer). Pick your language in the header.
  It does NOT sign or publish anything by itself, writes nothing to GitHub on its own (only `dispatch --go`, `dispatch --real` and `finalize --execute`, which you run, do) and keeps no token unless you switch on the optional one (Settings > Advanced). Everything that reaches beyond this computer or acts on GitHub is OFF by default.

Licence: GPL-3.0-or-later (see LICENSE, NOTICE, AUTHORS). Copyright (C) 2026 JuanenRac (Electro Hobby 3D).
