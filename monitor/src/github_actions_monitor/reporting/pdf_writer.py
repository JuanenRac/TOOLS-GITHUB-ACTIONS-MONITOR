# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A small PDF writer for the report of a tab: standard library only, no font file and no library.

The text is set in the two standard fonts every PDF reader has (Helvetica and Helvetica-Bold, WinAnsi encoding), so the file needs no embedded font. That encoding covers the Latin languages of
the monitor (English, Spanish, German, French, Italian and Portuguese) and nothing else: a text with a character outside it (Japanese, Chinese...) is REFUSED with `UnsupportedText`, because a
PDF with broken characters is worse than none; the page then uses the print of the browser, which has the fonts. Nothing is written to disk here: `render_pdf` returns the bytes.

  render_pdf(report, paper)   the bytes of the PDF of a report (the structure of tab_report.build)
  encodable(report)           True when every character of the report can be set in the standard fonts
  text_width(text, bold, size)  width in points of a text, used to wrap lines
  PAPERS                      the sizes in points: a4 and letter
"""
import unicodedata

PAPERS = {"a4": (595.28, 841.89), "letter": (612.0, 792.0)}
MARGIN = 48.0
BODY = 9.0
LEAD = 12.0

_REGULAR = (278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722,
            667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222,
            500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584)
_BOLD = (278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722,
         667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278,
         556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584)
_PUNCTUATION = {"–": 556, "—": 1000, "•": 350, "‘": 222, "’": 222, "“": 333, "”": 333, "…": 1000, "€": 556, " ": 278, "×": 584, "·": 278}
_PLAIN = {"→": "->", "←": "<-", "✓": "ok", "✔": "ok", "✗": "x", "✘": "x", " ": " ", " ": " ", " ": " ", " ": " ", "​": "", "−": "-",
          "‐": "-", "‑": "-", "‒": "-", "′": "'", "″": '"', "●": "*", "→️": "->", "­": ""}


class UnsupportedText(ValueError):
    """The report holds a character that the standard fonts cannot set (the script of Japanese or Chinese, for example)."""


def clean(text):
    """The text as the fonts can set it: control characters out, a few typographic symbols made plain; anything else must be WinAnsi (cp1252) or `UnsupportedText` is raised."""
    out = []
    for ch in str(text):
        if ch in "\r\n\t":
            out.append(" ")
        elif ch in _PLAIN:
            out.append(_PLAIN[ch])
        elif unicodedata.category(ch) in ("Cc", "Cf"):
            continue
        else:
            try:
                ch.encode("cp1252")
            except UnicodeEncodeError as error:
                raise UnsupportedText(ch) from error
            out.append(ch)
    return "".join(out)


def _char_width(ch, bold):
    table = _BOLD if bold else _REGULAR
    code = ord(ch)
    if 32 <= code <= 126:
        return table[code - 32]
    if ch in _PUNCTUATION:
        return _PUNCTUATION[ch]
    base = unicodedata.normalize("NFD", ch)[:1]
    if base and 32 <= ord(base) <= 126:
        return table[ord(base) - 32]
    return 556


def text_width(text, bold=False, size=BODY):
    """Width in points of a text in Helvetica (Helvetica-Bold when `bold`), with a small safety margin so a wrapped line never touches the next column."""
    return sum(_char_width(ch, bold) for ch in str(text)) * size / 1000.0 * 1.02


def wrap(text, width, bold=False, size=BODY):
    """The lines of a text no wider than `width` points; a word wider than the width is cut where it must."""
    lines, line = [], ""
    for word in str(text).split(" "):
        pieces = [word]
        if text_width(word, bold, size) > width:
            pieces, piece = [], ""
            for ch in word:
                if piece and text_width(piece + ch, bold, size) > width:
                    pieces.append(piece)
                    piece = ""
                piece += ch
            pieces.append(piece)
        for piece in pieces:
            trial = piece if not line else line + " " + piece
            if line and text_width(trial, bold, size) > width:
                lines.append(line)
                line = piece
            else:
                line = trial
    lines.append(line)
    return lines


def _walk(report):
    """Every text of the report, in the order it is set."""
    yield report.get("title", "")
    yield report.get("subtitle", "")
    for item in report.get("meta", []):
        yield item.get("label", "")
        yield item.get("value", "")
    for group in ("figures", "alerts"):
        yield report.get(group + "_title", "")
        yield report.get(group + "_empty", "")
        for item in report.get(group, []):
            yield from (str(v) for v in item.values() if isinstance(v, (str, int, float)))
    for section in report.get("sections", []):
        yield section.get("title", "")
        yield section.get("empty", "")
        yield from section.get("columns", [])
        for row in section.get("rows", []):
            yield from (str(c) for c in row)
    yield report.get("footer", "")
    yield report.get("page_label", "")


def encodable(report):
    """True when the PDF writer can set every text of the report."""
    try:
        for text in _walk(report):
            clean(text)
        return True
    except UnsupportedText:
        return False


def _escape(text):
    """A PDF literal string: ASCII stays, backslash and brackets are escaped, anything else is an octal escape of its WinAnsi byte (the file stays plain ASCII)."""
    out = []
    for byte in clean(text).encode("cp1252", "replace"):
        ch = chr(byte)
        if ch in "\\()":
            out.append("\\" + ch)
        elif 32 <= byte < 127:
            out.append(ch)
        else:
            out.append("\\%03o" % byte)
    return "".join(out)


class _Pages:
    """The pages being laid out: a cursor going down, a new page when the next line does not fit."""

    def __init__(self, paper):
        self.width, self.height = PAPERS.get(paper, PAPERS["a4"])
        self.pages = []
        self.ops = None
        self.y = 0.0
        self.new_page()

    def new_page(self):
        self.ops = []
        self.pages.append(self.ops)
        self.y = self.height - MARGIN

    def room(self, needed):
        if self.y - needed < MARGIN + 18:
            self.new_page()

    def text(self, x, text, size=BODY, bold=False, gray=0.0):
        self.ops.append("%.2f g BT /%s %.1f Tf %.2f %.2f Td (%s) Tj ET" % (gray, "F2" if bold else "F1", size, x, self.y - size, _escape(text)))

    def line(self, x1, x2, gray=0.75, width=0.5):
        self.ops.append("%.2f G %.2f w %.2f %.2f m %.2f %.2f l S" % (gray, width, x1, self.y, x2, self.y))

    def fill(self, x, y, w, h, gray):
        self.ops.append("%.2f g %.2f %.2f %.2f %.2f re f" % (gray, x, y, w, h))


def _columns(section, usable):
    """Widths of the columns: each gets what its longest text asks for (with a floor and a ceiling), then all are scaled to the usable width."""
    columns = section.get("columns", [])
    asks = []
    for index, name in enumerate(columns):
        longest = max([text_width(name, True)] + [text_width(clean(row[index]), False) for row in section.get("rows", []) if index < len(row)] or [30])
        asks.append(min(max(longest + 8, 40.0), usable * 0.6))
    total = sum(asks) or 1.0
    scale = usable / total
    return [a * scale for a in asks]


def render_pdf(report, paper="a4"):
    """The bytes of a PDF with the report: title, meta lines, figures, alerts and one table per section, a footer with the page number on every page."""
    page = _Pages(paper)
    left, right = MARGIN, page.width - MARGIN
    usable = right - left
    for text in _walk(report):      # refuse before laying anything out
        clean(text)

    def paragraph(text, size=BODY, bold=False, gray=0.0, indent=0.0, after=2.0):
        for piece in wrap(clean(text), usable - indent, bold, size):
            page.room(size + 4)
            page.text(left + indent, piece, size, bold, gray)
            page.y -= size + 3
        page.y -= after

    paragraph(report.get("title", ""), 18, True, 0.0, after=0)
    if report.get("subtitle"):
        paragraph(report["subtitle"], 10, False, 0.35)
    page.y -= 2
    for item in report.get("meta", []):
        paragraph("%s: %s" % (item.get("label", ""), item.get("value", "")), BODY, False, 0.25, after=0)
    page.y -= 6
    page.line(left, right, 0.5, 1.0)
    page.y -= 10
    if report.get("figures"):
        paragraph(report.get("figures_title", ""), 12, True)
        for item in report["figures"]:
            mark = {"act": "[!] ", "watch": "[~] "}.get(item.get("level"), "")
            paragraph("%s%s: %s" % (mark, item.get("label", ""), item.get("value", "")), BODY, False, 0.0, 6, 0)
        page.y -= 4
    if report.get("alerts_title"):
        paragraph(report.get("alerts_title", ""), 12, True)
        if not report.get("alerts"):
            paragraph(report.get("alerts_empty", ""), BODY, False, 0.4, 6)
        for item in report.get("alerts", []):
            mark = {"act": "[!] ", "watch": "[~] "}.get(item.get("level"), "- ")
            where = (item.get("repo") + ": ") if item.get("repo") else ""
            paragraph(mark + where + item.get("text", ""), BODY, False, 0.0, 6, 1)
        page.y -= 4
    for section in report.get("sections", []):
        page.room(60)
        paragraph(section.get("title", ""), 12, True)
        rows = section.get("rows", [])
        if not rows:
            paragraph(section.get("empty", ""), BODY, False, 0.4, 6)
            continue
        widths = _columns(section, usable)
        offsets = [left]
        for w in widths[:-1]:
            offsets.append(offsets[-1] + w)
        head = [wrap(clean(name), w - 6, True) for name, w in zip(section.get("columns", []), widths)]

        def draw(cells, bold):
            lines = max(len(c) for c in cells) if cells else 0
            for i in range(lines):
                page.room(LEAD)
                if bold and i == 0:
                    page.fill(left, page.y - LEAD + 2, usable, LEAD, 0.92)
                for x, cell in zip(offsets, cells):
                    if i < len(cell):
                        page.text(x + 3, cell[i], BODY, bold)
                page.y -= LEAD
            page.line(left, right, 0.8, 0.4)
        draw(head, True)
        for row in rows:
            draw([wrap(clean(c), w - 6) for c, w in zip(list(row) + [""] * (len(widths) - len(row)), widths)], False)
        page.y -= 10
    total = len(page.pages)
    footer = report.get("footer", "")
    label = report.get("page_label", "")
    for number, ops in enumerate(page.pages, 1):
        page.ops = ops
        page.y = MARGIN - 4
        tail = "%s %d / %d" % (label, number, total) if label else "%d / %d" % (number, total)
        page.text(left, footer, 8, False, 0.4)
        page.text(right - text_width(tail, False, 8), tail, 8, False, 0.4)
    return _assemble(page, report.get("title", ""))


def _assemble(page, title):
    objects = [None] * (4 + 2 * len(page.pages))
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join("%d 0 R" % (5 + 2 * i) for i in range(len(page.pages)))
    objects[1] = ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page.pages))).encode("ascii")
    objects[2] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
    for i, ops in enumerate(page.pages):
        content = ("\n".join(ops)).encode("ascii")
        number = 5 + 2 * i
        objects[number - 1] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>" % (page.width, page.height, number + 1)).encode("ascii")
        objects[number] = b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"
    info_number = len(objects) + 1
    objects.append(("<< /Title (%s) /Producer (GitHub Actions Monitor) >>" % _escape(title)).encode("ascii"))
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, info_number, xref)
    return bytes(out)
