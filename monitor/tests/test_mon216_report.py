# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Save and print the report of a tab. ONE function builds the report (reporting/tab_report.py) and the text file, the data file, the PDF written by the monitor and the printed page are all drawn from it.
Here: the builder for every tab, the PDF writer (a real PDF: header, cross-reference table, the text, accents, lines and pages that break), the routes (the PDF only for this computer), the settings, the
words in the eight languages, and a headless browser that opens the saving window, marks and unmarks the formats and opens the report view. Nothing here reaches GitHub."""
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(TOOLS))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import briefs, signals  # noqa: E402
from github_actions_monitor.reporting import pdf_writer, tab_report  # noqa: E402

try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
KEYS = ["generated", "version", "tab", "figures", "alerts", "none", "none_alerts", "col_repo", "col_what", "col_age", "col_next", "col_workflow", "col_status", "col_minutes", "col_number", "col_title",
        "col_category", "col_lesson", "col_do", "fig_active", "fig_queued", "fig_fail24", "fig_ok24", "fig_red", "running", "red", "issues", "lessons", "page", "unavailable", "dlg_title", "fmt_txt",
        "fmt_pdf", "fmt_json", "fmt_short_txt", "fmt_short_pdf", "fmt_short_json", "pdf_path", "path_auto", "path_own", "path_browser", "note_script", "note_browser", "save", "save_next", "cancel",
        "none_chosen", "saved", "cancelled", "downloaded", "printed", "pdf_remote", "pdf_script", "print", "close"]
SETTINGS = ("txt", "pdf", "json", "name", "paper", "pdf_path")


def a_state(edition="complete"):
    rows = [{"repo": "owner/repo-one", "text": "Build: failure (años, über, façade, già, ação)", "url": "https://github.com/owner/repo-one/actions/runs/1", "age_seconds": 4000, "next": "open the log"}]
    data = {"updated": None, "figures": {"active": 1, "queued": 0, "fail24": 2, "ok24": 5}, "failing": [{"repo": "owner/repo-one", "name": "Build", "conclusion": "failure", "started": None}],
            "active": [{"repo": "owner/repo-two", "name": "Tests", "status": "in_progress", "seconds": 600}], "issues": [{"repo": "owner/repo-one", "number": 7, "title": "Build is red", "created": None}]}
    state = signals.state(data, [{"id": "a3", "title": "Trend", "summary": "trend is up", "level": "warn", "rows": rows}], edition, {"age_seconds": 3}, version="9.9.9")
    return state, data


def build(tab, lang="en", edition="complete", **extra):
    state, data = a_state(edition)
    return tab_report.build(tab, state, lang, i18n.tl, data=data, **extra)


def pdf_text(pdf):
    """The texts the PDF sets, decoded from their literal strings and WinAnsi bytes (the file is plain ASCII, accents are octal escapes)."""
    found = []
    for raw in re.findall(rb"\(((?:[^()\\]|\\.)*)\) Tj", pdf):
        out = bytearray()
        i = 0
        while i < len(raw):
            if raw[i:i + 1] == b"\\":
                nxt = raw[i + 1:i + 2]
                if nxt.isdigit():
                    out.append(int(raw[i + 1:i + 4], 8))
                    i += 4
                    continue
                out += nxt
                i += 2
                continue
            out.append(raw[i])
            i += 1
        found.append(bytes(out).decode("cp1252"))
    return found


def check_structure(test, pdf):
    """A well formed PDF: header, trailer, a cross-reference table whose offsets point at their objects, and a start address that points at the table."""
    test.assertTrue(pdf.startswith(b"%PDF-1."))
    test.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
    start = int(re.search(rb"startxref\n(\d+)\n%%EOF", pdf).group(1))
    test.assertEqual(pdf[start:start + 4], b"xref")
    count = int(re.match(rb"xref\n0 (\d+)\n", pdf[start:]).group(1))
    entries = re.findall(rb"(\d{10}) (\d{5}) ([nf]) \n", pdf[start:])
    test.assertEqual(len(entries), count)
    for number, (offset, _generation, kind) in enumerate(entries):
        if kind == b"n":
            test.assertEqual(pdf[int(offset):].split(b"\n", 1)[0], b"%d 0 obj" % number, number)
    test.assertIn(b"/Size %d" % count, pdf)
    return count


class TheBuilder(unittest.TestCase):
    def test_every_tab_has_a_report_with_the_same_shape(self):
        for tab in briefs.tabs():
            doc = build(tab)
            with self.subTest(tab=tab):
                self.assertEqual((doc["kind"], doc["tab"], doc["schema"]), ("tab-report", tab, tab_report.SCHEMA))
                for key in ("title", "meta", "figures", "alerts", "sections", "footer", "figures_title", "alerts_title", "alerts_empty", "page_label", "date"):
                    self.assertIn(key, doc)
                self.assertTrue(doc["title"].startswith(tab_report.PRODUCT))
                self.assertEqual([m["label"] for m in doc["meta"]], ["Generated", "Version", "Tab"])
                self.assertEqual(doc["meta"][1]["value"], "9.9.9")
                for section in doc["sections"]:
                    self.assertTrue(all(len(row) == len(section["columns"]) for row in section["rows"]), section["title"])
                json.dumps(doc)
                self.assertTrue(tab_report.render_text(doc).startswith(doc["title"]))

    def test_a_tab_that_does_not_exist_has_no_report(self):
        self.assertIsNone(build("nope"))

    def test_the_now_tab_lists_what_runs_and_what_is_red(self):
        doc = build("now")
        titles = [s["title"] for s in doc["sections"]]
        self.assertEqual(titles[:2], ["Running now", "Red on the default branch"])
        self.assertEqual(doc["sections"][0]["rows"], [["owner/repo-two", "Tests", "in_progress", 10]])
        self.assertEqual(doc["figures"][0]["value"], 1)
        self.assertEqual({f["label"] for f in doc["figures"]} >= {"Running", "Queued", "Failures, 24 h"}, True)

    def test_the_alerts_tab_lists_red_workflows_and_issues(self):
        doc = build("al")
        self.assertEqual(doc["sections"][0]["rows"], [["owner/repo-one", "Build", "failure"]])
        self.assertEqual(doc["sections"][1]["rows"], [["owner/repo-one", "#7", "Build is red"]])

    def test_the_lessons_tab_lists_the_library(self):
        doc = build("les", library=[{"category": "lint", "what": "ruff failed", "do": "run ruff first"}])
        self.assertEqual(doc["sections"][0]["rows"], [["lint", "ruff failed", "run ruff first"]])
        self.assertEqual(build("les", library=[])["sections"][0]["rows"], [])

    def test_a_tab_without_a_specific_builder_still_reports_its_signals(self):
        doc = build("sent")
        self.assertTrue(doc["figures"])
        self.assertTrue(any("trend is up" in s["title"] for s in doc["sections"]))
        self.assertTrue(any(a["level"] == "watch" for a in doc["alerts"]))
        self.assertIn("age", " ".join(doc["sections"][0]["columns"]).lower())
        self.assertEqual(tab_report._age(4000), "1 h")
        self.assertEqual((tab_report._age(120), tab_report._age(90000), tab_report._age(None), tab_report._age("x")), ("2 min", "1 d", "", ""))

    def test_a_tab_the_edition_does_not_have_says_so_and_is_empty(self):
        doc = build("team", edition="lite")
        self.assertEqual((doc["sections"], doc["figures"], doc["alerts"]), ([], [], []))
        self.assertIn("does not exist", doc["subtitle"])

    def test_the_words_come_in_the_language_asked_for(self):
        self.assertEqual(build("now", "es")["meta"][0]["label"], "Generado")
        self.assertEqual(build("now", "de")["figures_title"], "Wichtigste Zahlen")
        self.assertEqual(build("now", "ja")["alerts_title"], "アラート")

    def test_the_text_and_the_data_say_the_same_thing(self):
        doc = build("al", "fr")
        text = tab_report.render_text(doc)
        for section in doc["sections"]:
            self.assertIn(section["title"], text)
            for row in section["rows"]:
                self.assertIn(" | ".join(str(c) for c in row), text)
        for alert in doc["alerts"]:
            self.assertIn(alert["text"], text)

    def test_the_settings_fall_back_to_the_safe_default(self):
        self.assertEqual(tab_report.settings({}), {"txt": True, "pdf": True, "json": False, "name": "monitor-{tab}-{date}", "paper": "a4", "pdf_path": "auto", "limits": True})
        bad = {"report_export": {"txt": "yes", "pdf": 1, "json": None, "name": "../x y", "paper": "a3", "pdf_path": "cloud"}}
        self.assertEqual(tab_report.settings(bad), tab_report.settings({}))
        good = {"report_export": {"txt": False, "json": True, "name": "informe_{tab}", "paper": "letter", "pdf_path": "browser"}}
        self.assertEqual(tab_report.settings(good), {"txt": False, "pdf": True, "json": True, "name": "informe_{tab}", "paper": "letter", "pdf_path": "browser"})

    def test_the_file_name_is_safe(self):
        self.assertEqual(tab_report.file_name("monitor-{tab}-{date}", "now", "2030-01-02"), "monitor-now-2030-01-02")
        self.assertEqual(tab_report.file_name("../../etc/{tab}", "al", "d"), "monitor-al-d")
        self.assertEqual(tab_report.file_name("", "al", "d"), "monitor-al-d")

    def test_japanese_and_chinese_always_use_the_browser_for_the_pdf(self):
        for lang in ("ja", "zh"):
            for preference in tab_report.PDF_PATH:
                self.assertEqual(tab_report.pdf_route(lang, preference), "browser", (lang, preference))
        for lang in ("en", "es", "de", "fr", "it", "pt"):
            self.assertEqual(tab_report.pdf_route(lang, "auto"), "own")
            self.assertEqual(tab_report.pdf_route(lang, "own"), "own")
            self.assertEqual(tab_report.pdf_route(lang, "browser"), "browser")


class ThePdfWriter(unittest.TestCase):
    def test_it_is_a_well_formed_pdf_with_the_text_in_it(self):
        pdf = pdf_writer.render_pdf(build("al"))
        count = check_structure(self, pdf)
        self.assertEqual(count, 1 + 4 + 2 + 1)      # the free entry, catalog, pages, two fonts, one page and its content, and the information
        texts = pdf_text(pdf)
        self.assertIn("GitHub Actions Monitor - Alerts", texts)
        self.assertIn("Red on the default branch", texts)
        self.assertTrue(any(t.startswith("Page 1 / 1") for t in texts))
        self.assertIn(b"/BaseFont /Helvetica", pdf)
        self.assertIn(b"/WinAnsiEncoding", pdf)
        self.assertIn(b"/MediaBox [0 0 595.28 841.89]", pdf)

    def test_accents_of_the_latin_languages_come_out_right(self):
        doc = build("sent", "es")
        doc["sections"][0]["rows"][0][1] = "Informe de actualización: años, über, façade, già, ação, œuvre «x» – “y”"
        pdf = pdf_writer.render_pdf(doc)
        joined = " ".join(pdf_text(pdf))
        for piece in ("actualización", "años", "über", "façade", "già", "ação", "œuvre", "«x»", "–", "“y”"):
            self.assertIn(piece, joined)
        self.assertTrue(all(b < 128 for b in pdf.split(b"\n", 2)[2]), "the file is plain ASCII: accents are octal escapes")
        self.assertNotIn("\xe2\x80".encode("latin-1"), pdf.split(b"stream", 1)[1])      # no UTF-8 bytes of a quote reached the page

    def test_every_latin_language_can_be_set(self):
        for lang in ("en", "es", "de", "fr", "it", "pt"):
            for tab in ("now", "al", "les", "sent"):
                doc = build(tab, lang, library=[])
                self.assertTrue(pdf_writer.encodable(doc), (lang, tab))
                check_structure(self, pdf_writer.render_pdf(doc))

    def test_japanese_and_chinese_are_refused_not_drawn_broken(self):
        for lang in ("ja", "zh"):
            doc = build("now", lang)
            self.assertFalse(pdf_writer.encodable(doc), lang)
            with self.assertRaises(pdf_writer.UnsupportedText):
                pdf_writer.render_pdf(doc)
        english = build("sent")
        english["sections"][0]["rows"][0][1] = "日本語"
        self.assertFalse(pdf_writer.encodable(english))

    def test_a_long_text_breaks_into_lines_that_fit_and_a_long_table_into_pages(self):
        doc = build("sent")
        long_word = "x" * 400
        doc["sections"][0]["rows"] = [["owner/repo-%d" % n, ("long text %d " % n) * 40 + long_word, "5 min", "next " * 30] for n in range(60)]
        pdf = pdf_writer.render_pdf(doc)
        count = check_structure(self, pdf)
        pages = (count - 1 - 4 - 1) // 2
        self.assertGreater(pages, 2)
        self.assertEqual(len(re.findall(rb"/Type /Page /", pdf)), pages)
        texts = pdf_text(pdf)
        self.assertTrue(any(t.startswith("Page %d / %d" % (pages, pages)) for t in texts))
        width = pdf_writer.PAPERS["a4"][0]
        for match in re.finditer(rb"/(F[12]) ([\d.]+) Tf ([\d.]+) ([\d.]+) Td \(((?:[^()\\]|\\.)*)\) Tj", pdf):
            font, size, x = match.group(1), float(match.group(2)), float(match.group(3))
            text = pdf_text(b"(" + match.group(5) + b") Tj")[0]
            self.assertLessEqual(x + pdf_writer.text_width(text, font == b"F2", size), width - pdf_writer.MARGIN + 1.0, text[:40])
        self.assertGreater(len(pdf_text(pdf)), 100)

    def test_the_paper_is_a4_or_letter(self):
        self.assertIn(b"/MediaBox [0 0 612.00 792.00]", pdf_writer.render_pdf(build("now"), "letter"))
        self.assertIn(b"/MediaBox [0 0 595.28 841.89]", pdf_writer.render_pdf(build("now"), "other"))

    def test_brackets_and_backslashes_do_not_break_the_strings(self):
        doc = build("sent")
        doc["sections"][0]["rows"][0][1] = "a (b) \\ c ) ("
        texts = pdf_text(pdf_writer.render_pdf(doc))
        self.assertTrue(any("a (b) \\ c ) (" in t for t in texts))

    def test_the_same_report_gives_the_same_bytes(self):
        doc = build("now")
        self.assertEqual(pdf_writer.render_pdf(doc), pdf_writer.render_pdf(doc))


class Served:
    def __init__(self, case, peer_ip=None, config=None):
        _testenv.guard(case)
        self.server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        case.addCleanup(self.server.server_close)
        case.addCleanup(self.server.shutdown)
        for patcher in (mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=config or {}), mock.patch.object(actions_monitor, "LITE", {"on": False})):
            patcher.start()
            case.addCleanup(patcher.stop)
        self.port = self.server.server_address[1]

    def get(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            connection.request("GET", path, headers={"Host": f"127.0.0.1:{self.port}"})
            answer = connection.getresponse()
            return answer.status, answer.read(), answer
        finally:
            connection.close()


class TheRoutes(unittest.TestCase):
    def test_the_data_the_text_and_the_options(self):
        served = Served(self)
        status, body, answer = served.get("/api/report/tab?tab=al&lang=es")
        self.assertEqual(status, 200)
        doc = json.loads(body)
        self.assertEqual((doc["kind"], doc["tab"], doc["meta"][0]["label"]), ("tab-report", "al", "Generado"))
        status, body, answer = served.get("/api/report/tab?tab=al&lang=es&fmt=txt")
        self.assertEqual(status, 200)
        self.assertTrue(answer.getheader("Content-Type").startswith("text/plain"))
        self.assertTrue(body.decode("utf-8").startswith(doc["title"]))
        status, body, _ = served.get("/api/report/tab?tab=al&lang=ja&fmt=options")
        options = json.loads(body)
        self.assertEqual((status, options["browser_only"], options["pdf_route"], options["options"]["pdf"], options["options"]["json"]), (200, True, "browser", True, False))
        self.assertFalse(json.loads(served.get("/api/report/tab?fmt=options&lang=de")[1])["browser_only"])

    def test_a_tab_that_does_not_exist_answers_404(self):
        status, body, _ = Served(self).get("/api/report/tab?tab=nope")
        self.assertEqual((status, json.loads(body)["error"]), (404, "tab"))

    def test_the_pdf_for_this_computer(self):
        served = Served(self)
        status, body, answer = served.get("/api/report/tab.pdf?tab=now&lang=fr&paper=letter")
        self.assertEqual(status, 200)
        self.assertEqual(answer.getheader("Content-Type"), "application/pdf")
        check_structure(self, body)
        self.assertIn(b"/MediaBox [0 0 612.00 792.00]", body)
        self.assertIn("GitHub Actions Monitor - Maintenant", pdf_text(body))

    def test_japanese_has_no_pdf_of_the_monitor_but_says_the_browser_does(self):
        status, body, _ = Served(self).get("/api/report/tab.pdf?tab=now&lang=ja")
        self.assertEqual((status, json.loads(body)["error"], json.loads(body)["route"]), (422, "pdf_script", "browser"))

    def test_the_settings_choose_the_paper_and_the_defaults(self):
        served = Served(self, config={"report_export": {"paper": "letter", "json": True, "name": "r_{tab}"}})
        self.assertIn(b"/MediaBox [0 0 612.00 792.00]", served.get("/api/report/tab.pdf?tab=now")[1])
        options = json.loads(served.get("/api/report/tab?fmt=options")[1])["options"]
        self.assertEqual((options["json"], options["name"]), (True, "r_{tab}"))

    def test_the_pdf_is_only_for_this_computer_and_left_a_line_in_the_log_of_actions(self):
        source = Path(actions_monitor.__file__).read_text(encoding="utf-8")
        self.assertRegex(source, r'path == "/api/report/tab\.pdf":[^\n]*\n\s+if not self\.guard\(\) or not self\.this_computer\(\)')
        self.assertIn('audit_action(self, "report_export"', source)


class TheWords(unittest.TestCase):
    def test_every_word_exists_in_the_eight_languages(self):
        for lang in LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in KEYS:
                self.assertTrue(catalogue.get("ui.rx_" + key), (lang, key))
            for key in SETTINGS:
                self.assertTrue(catalogue.get("cfg.f.report_export." + key), (lang, key))
                self.assertTrue(catalogue.get("cfg.h.report_export." + key), (lang, key))
            self.assertTrue(catalogue.get("ui.cfg_b_report_export"), lang)

    def test_the_words_differ_from_english_and_keep_their_placeholders(self):
        english = json.loads((HERE / "assets" / "locales" / "en.json").read_text(encoding="utf-8"))
        for lang in LANGS[1:]:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("rx_dlg_title", "rx_none_chosen", "rx_note_browser", "rx_printed", "rx_pdf_script"):
                self.assertNotEqual(catalogue["ui." + key], english["ui." + key], (lang, key))
            for key in KEYS:
                self.assertEqual(sorted(re.findall(r"\{\w+\}", catalogue["ui.rx_" + key])), sorted(re.findall(r"\{\w+\}", english["ui.rx_" + key])), (lang, key))
            for key in SETTINGS:
                self.assertEqual(sorted(re.findall(r"\{\w+\}", catalogue["cfg.h.report_export." + key])), sorted(re.findall(r"\{\w+\}", english["cfg.h.report_export." + key])), (lang, key))

    def test_the_latin_languages_use_only_what_the_standard_pdf_fonts_can_set(self):
        for lang in ("en", "es", "de", "fr", "it", "pt"):
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in KEYS:
                pdf_writer.clean(catalogue["ui.rx_" + key])

    def test_portuguese_is_the_one_of_portugal(self):
        catalogue = json.loads((HERE / "assets" / "locales" / "pt.json").read_text(encoding="utf-8"))
        self.assertIn("Guardar", catalogue["ui.rx_save"])
        self.assertIn("ficheiro", catalogue["cfg.f.report_export.name"].lower())
        self.assertNotIn("arquivo", " ".join(catalogue[k] for k in catalogue if k.startswith(("ui.rx_", "cfg.h.report_export"))).lower())


class TheSettings(unittest.TestCase):
    def test_every_setting_is_in_the_schema_with_a_safe_default_and_in_the_example(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["report_export"], tab_report.DEFAULTS)
        for key in SETTINGS:
            self.assertIn("report_export." + key, settings_api.FIELDS)
        self.assertEqual(tab_report.DEFAULTS["json"], False)
        self.assertTrue(tab_report.DEFAULTS["txt"] and tab_report.DEFAULTS["pdf"])

    def test_the_schema_refuses_a_bad_value(self):
        for key, value in (("report_export.paper", "a3"), ("report_export.pdf_path", "cloud"), ("report_export.name", "../x"), ("report_export.txt", "yes")):
            clean, errors = settings_api.validate({key: value})
            self.assertEqual((clean, list(errors)), ({}, [key]))
        clean, errors = settings_api.validate({"report_export.paper": "letter", "report_export.json": True, "report_export.name": "r_{tab}-{date}"})
        self.assertEqual((errors, clean["report_export.paper"], clean["report_export.json"]), ({}, "letter", True))


class ThePage(unittest.TestCase):
    def test_the_bar_opens_the_window_and_the_print_view(self):
        self.assertIn('$("bar-save").addEventListener("click",repOpen)', PAGE)
        self.assertIn('$("bar-print").addEventListener("click",()=>repView(true))', PAGE)
        self.assertNotIn('$("bar-print").addEventListener("click",()=>window.print())', PAGE)
        for ident in ("rep-dlg", "rep-txt", "rep-pdf", "rep-json", "rep-path", "rep-go", "rep-view", "rep-doc"):
            self.assertIn(f'id="{ident}"', PAGE)

    def test_the_native_save_as_window_is_used_with_a_suggested_name_and_file_types(self):
        self.assertIn("window.showSaveFilePicker", PAGE)
        self.assertIn("suggestedName:name", PAGE)
        self.assertIn("accept:{[types[0]]:[types[1]]}", PAGE)
        self.assertIn("ui.rx_downloaded", PAGE)      # a browser without that window downloads and says where it went

    def test_json_starts_unmarked_and_the_defaults_come_from_the_settings(self):
        self.assertIn('$("rep-json").checked=!!o.json', PAGE)
        self.assertNotRegex(PAGE, r'id="rep-(txt|pdf|json)"[^>]*checked')

    def test_the_print_style_shows_only_the_report(self):
        rule = re.search(r"@media print\{body\.rep-on>\*:not\(#rep-view\)\{display:none!important\}([^@]*)\}", PAGE)
        self.assertIsNotNone(rule)
        self.assertIn("#rep-view{position:static", rule.group(1))

    def test_the_screen_buttons_sit_left_of_save_and_print_in_the_bar(self):
        bar = PAGE.split('id="sb-bar"', 1)[1].split('id="bar-ai-int"', 1)[0]
        order = [bar.index(f'id="{i}"') for i in ("scrm-open", "fs", "hotonly", "bar-save", "bar-print")]
        self.assertEqual(order, sorted(order))
        for ident in ("scrm-open", "fs", "hotonly"):
            self.assertEqual(PAGE.count(f'id="{ident}"'), 1)
        self.assertNotIn('id="fs"', PAGE.split('class="hcorner"', 1)[1].split('class="vh"', 1)[0])

    def test_no_native_confirm_is_used(self):
        self.assertNotRegex(PAGE, r"(?<![\w.])confirm\(")


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  const $=id=>document.getElementById(id);
  try{
    await wait(1500);
    const r={printed:0};window.print=()=>{r.printed++};
    $("bar-save").click();await wait(700);
    r.open=!$("rep-dlg").hidden;
    r.defaults=[$("rep-txt").checked,$("rep-pdf").checked,$("rep-json").checked];
    $("rep-json").click();r.json_on=$("rep-json").checked;$("rep-json").click();r.json_off=!$("rep-json").checked;
    $("rep-pdf").click();r.pdf_off=!$("rep-pdf").checked;$("rep-pdf").click();r.pdf_on=$("rep-pdf").checked;
    r.path_disabled=$("rep-path").disabled;r.note=$("rep-note").textContent;
    $("rep-txt").click();$("rep-pdf").click();$("rep-go").click();await wait(300);r.none_chosen=$("rep-out").textContent;
    $("rep-close").click();await wait(150);r.closed=$("rep-dlg").hidden;
    const boxes=["scrm-open","fs","hotonly","bar-save","bar-print"].map(id=>$(id)).filter(e=>e&&e.getClientRects().length).map(e=>{const b=e.getBoundingClientRect();return {id:e.id,l:b.left,r:b.right,t:b.top+scrollY,b:b.bottom+scrollY}});
    r.rects=boxes.map(b=>[b.id,Math.round(b.l),Math.round(b.r),Math.round(b.t),Math.round(b.b),innerWidth,innerHeight]);r.boxes=boxes.map(b=>b.id);r.inside=boxes.every(b=>b.l>=0&&b.r<=innerWidth);
    r.overlap=boxes.some((a,i)=>boxes.some((c,j)=>j>i&&a.l<c.r-0.5&&c.l<a.r-0.5&&a.t<c.b-0.5&&c.t<a.b-0.5));
    r.left_of_save=boxes.filter(b=>b.id!=="bar-save"&&b.id!=="bar-print").every(b=>b.r<=boxes.find(x=>x.id==="bar-save").l+1||b.t+1<boxes.find(x=>x.id==="bar-save").t);
    $("bar-print").click();await wait(900);
    r.view=!$("rep-view").hidden;r.printed_after=r.printed;r.h1=($("rep-doc").querySelector("h1")||{}).textContent;r.tables=$("rep-doc").querySelectorAll("table").length;
    r.visible_others=[...document.body.children].filter(e=>e.id!=="rep-view"&&e.id!=="overflow-report"&&e.tagName!=="SCRIPT"&&getComputedStyle(e).display!=="none"&&e.id==="statusbar").length;
    $("rep-vclose").click();await wait(100);r.view_closed=$("rep-view").hidden&&!document.body.classList.contains("rep-on");
    out.textContent=JSON.stringify({ok:true,found:r});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:{}})}
})();
</script>
"""


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class TheSavingWindowInABrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(cls.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        cls.relay = check_overflow.relay(cls.port, probe=PROBE)
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        cls.relay.shutdown()
        cls.demo.terminate()

    def run_probe(self, lang):
        return check_overflow.measure(check_overflow.edge(), f"{self.base}?lang={lang}&nowizard=1", check_overflow.SIZES["desktop"], report="overflow-report")

    def test_the_window_opens_the_formats_are_marked_and_unmarked_and_the_view_opens(self):
        found = self.run_probe("en")
        self.assertTrue(found["open"])
        self.assertEqual(found["defaults"], [True, True, False])
        self.assertTrue(found["json_on"] and found["json_off"] and found["pdf_off"] and found["pdf_on"])
        self.assertFalse(found["path_disabled"])
        self.assertEqual(found["none_chosen"], "Choose at least one format.")
        self.assertTrue(found["closed"])
        self.assertTrue(found["view"])
        self.assertEqual(found["printed"], 1)
        self.assertTrue(found["h1"].startswith("GitHub Actions Monitor"))
        self.assertTrue(found["view_closed"])

    def test_the_buttons_of_the_bar_do_not_overlap_or_leave_the_frame_in_any_width(self):
        for lang in ("en", "de", "ja", "pt"):
            for size in ("desktop", "mobile"):
                found = check_overflow.measure(check_overflow.edge(), f"{self.base}?lang={lang}&nowizard=1", check_overflow.SIZES[size], report="overflow-report")
                self.assertIn("bar-save", found["boxes"])
                self.assertIn("fs", found["boxes"])
                self.assertTrue(found["inside"], (lang, size, found["rects"]))
                self.assertFalse(found["overlap"], (lang, size))
                if size == "desktop":
                    self.assertTrue(found["left_of_save"], (lang, size))

    def test_in_japanese_the_pdf_goes_through_the_browser_and_says_so(self):
        found = self.run_probe("ja")
        self.assertTrue(found["path_disabled"])
        self.assertIn("PDF", found["note"])


if __name__ == "__main__":
    unittest.main()
