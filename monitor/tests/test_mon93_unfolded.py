# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The one unfolded panel of a Sentinel tab takes the rest of the height of its box, and no process the monitor starts is detached from its console.

The source of the page is read as text (runs everywhere); the geometry is measured in a headless browser in the eight languages, wide and narrow (tools/check_unfolded.py), and is skipped
when there is no Edge, Chrome or Chromium on this computer, or no tools folder. The flags of the processes are read from the source of every file that starts one."""
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(TOOLS))
try:
    import check_overflow  # noqa: E402
    import check_unfolded  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_unfolded = check_overflow = None

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
BROWSER_ONLY = unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
DETACHED = 0x00000008


class TheSource(unittest.TestCase):
    def test_the_three_sentinel_tabs_let_the_single_unfolded_panel_grow(self):
        for part in ("#t-sci section>.body", "#t-scol section>.body", "#t-ssec section>.body", "#t-sdel section>.body", "#t-ssup section>.body", "flex-direction:column", "flex:1 1 auto", "max-height:none", "::details-content"):
            self.assertIn(part, PAGE)

    def test_the_limit_of_the_unfolded_body_stays_everywhere_else(self):
        self.assertRegex(PAGE, r"details>\.dbody\{[^}]*overflow:auto;max-height:46vh\}")


class NoProcessIsDetached(unittest.TestCase):
    """DETACHED_PROCESS leaves a process without a console, and then every git or gh it starts opens a console window of its own."""

    def test_no_creation_flag_in_the_source_has_the_detached_bit(self):
        offenders = []
        for folder in (HERE / "src", HERE / "tools", HERE / "bin"):
            for path in folder.rglob("*.py"):
                text = path.read_text(encoding="utf-8", errors="replace")
                if re.search(r"\bDETACHED_PROCESS\b", text):
                    offenders.append(f"{path.name}: DETACHED_PROCESS")
                for match in re.finditer(r"creationflags\"?\s*[:=]\s*([0-9xXa-fA-F |]+)", text):
                    value = 0
                    for piece in match.group(1).split("|"):
                        piece = piece.strip()
                        if re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", piece):
                            value |= int(piece, 0)
                    if value & DETACHED:
                        offenders.append(f"{path.name}: creationflags {match.group(1).strip()}")
        self.assertEqual(offenders, [])

    def test_the_updater_starts_the_monitor_with_a_hidden_console_and_a_group_of_its_own(self):
        text = (HERE / "tools" / "monitor_updater.py").read_text(encoding="utf-8")
        line = next(l for l in text.splitlines() if "module, \"--no-browser\"" in l or "kwargs = {\"creationflags\"" in l)
        self.assertIn("0x00000200 | 0x08000000", text)
        self.assertNotIn("0x00000008 |", text)
        self.assertTrue(line)

    def test_the_account_supervisor_gives_its_children_a_hidden_console_on_windows(self):
        text = (HERE / "src" / "github_actions_monitor" / "accounts" / "accounts_supervisor.py").read_text(encoding="utf-8")
        self.assertIn("0x08000000", text)


@unittest.skipUnless(check_unfolded is not None and check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
class TheGeometry(unittest.TestCase):
    @BROWSER_ONLY
    def test_the_unfolded_panel_reaches_the_bottom_in_the_three_tabs_in_the_eight_languages_wide_and_narrow(self):
        results = check_unfolded.run(quiet=True)
        self.assertIsNotNone(results)
        self.assertEqual(len(results), len(check_unfolded.LANGS) * 2)
        lines = [f"[{lang}/{size}] {item['kind']} {item['at']}: {item['detail']}" for (lang, size), items in sorted(results.items()) for item in items]
        self.assertEqual(lines, [], "an unfolded panel stops short of the bottom:\n" + "\n".join(lines[:40]))


if __name__ == "__main__":
    unittest.main()
