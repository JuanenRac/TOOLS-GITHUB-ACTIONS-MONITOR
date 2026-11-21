<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Coverage of the two skills

Generated from the code. Each row is a kind of thing that a person or an AI can touch; `internal` is the skill of the AI of the monitor, `external` the skill of the AIs that talk to the monitor.
A test fails when something in the code is not named in these skills, so this table cannot fall behind.

| kind | how many | internal skill | external skill |
| --- | --- | --- | --- |
| endpoints | 149 | references/api.md | references/api.md |
| commands | 26 | out of scope: the AI of the monitor does not run commands | references/cli.md |
| settings | 891 | references/settings.md (the ai, lessons and alert ones matter) | references/settings.md |
| files | 14 | references/files.md | references/files.md |
| roles | 3 | references/roles.md | references/roles.md |
| tabs | 21 | references/tabs.md | references/tabs.md |
| classes | 6 | SKILL.md (Alert classes) | SKILL.md (Alert classes) |
| signals | 40 | references/signals.md | references/signals.md |
| panels | 14 | references/signals.md | references/signals.md |

Out of scope on purpose: the keys, tokens and passwords themselves (the AIs never ask for or print them), the content of the repositories, and writing to GitHub (the monitor never does it; actions go through a plan and a person's confirmation).
