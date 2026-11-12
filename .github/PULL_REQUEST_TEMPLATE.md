<!--
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
-->

## Summary

Describe the observable change.

## Validation

- [ ] `python -m unittest discover -s monitor/tests` passes.
- [ ] New texts exist in the eight languages.
- [ ] Help checklist: `cfg.h.<key>` for every new setting, the help of the tab that changed, the guides, the help index (`python tools/make_help_index.py`).
- [ ] `CHANGELOG.md` has a line for this change.
- [ ] The README and its translations are updated if behaviour changed.
- [ ] No token, private path or personal data is included.

## Safety

- [ ] Anything that writes to GitHub or opens a port is off by default and local only.
