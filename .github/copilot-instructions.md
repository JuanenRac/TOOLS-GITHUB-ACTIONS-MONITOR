<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Instructions for coding assistants in this repository

Read PRODUCT.md first: purpose, users and the rules that do not change.

- The core uses the Python standard library only; an optional package is imported where it is used and its absence is said, not hidden.
- Every visible text goes through the catalogue and exists in the eight languages with the same keys.
- Anything that writes to GitHub or to the system is off by default.
- Add a test for every change and an entry under "Unreleased" in monitor/CHANGELOG.md and its seven translations.
- Generated files (the root CHANGELOG.md, monitor/docs/SETTINGS.md, monitor/docs/help_index.json, the numbers of the README files) are made by the scripts in tools/; do not edit them by hand.
- Never write a token, a key or a path of a person into a file of the repository.
