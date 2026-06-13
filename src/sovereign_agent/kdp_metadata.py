"""
kdp_metadata.py — parse a book's `metadata_v1.0.md` into KDP-ready fields.

The metadata files in the books vault are authored KDP-paste-ready (Title/Subtitle, Amazon Description
HTML + plain-text, 7 keyword slots, 2 categories, pricing, print options, ISBN). This parser turns that
markdown into a structured dict the Atrium KDP Dispatch surface renders + copies field-by-field.

Tolerant by design — two authored formats exist in the vault and both must parse:
  · S1 canonical: `### Section` headers with the value in the section body (e.g. `### Series` / body).
  · S2 early:     `## Section` headers + inline `- **Label:** value` bullets (Series is a bullet, not a
                  section; "BISAC" stands in for "Categories"; pricing is a table; lowercase headers).
Missing/TBD fields return '' or [] rather than raising — a half-authored file still yields a usable
(partial) dispatch card, honestly showing what's present.

∞Δ∞ Book defines the listing; the surface just stages it for the one manual KDP click. SEAL: complete ∞Δ∞
"""
from __future__ import annotations
import re


def _sections(text: str) -> dict:
    """Split a metadata markdown doc into {header: body} by '## ' or '### ' headers (h2 + h3)."""
    parts = re.split(r"^#{2,3}\s+(.+?)\s*$", text, flags=re.M)
    secs = {}
    for i in range(1, len(parts), 2):
        secs[parts[i].strip()] = (parts[i + 1] if i + 1 < len(parts) else "").strip()
    return secs


def _by_prefix(secs: dict, prefix: str) -> str:
    """Body of the first section whose header starts with `prefix` (case-insensitive)."""
    pl = prefix.lower()
    for h, b in secs.items():
        if h.lower().startswith(pl):
            return b
    return ""


def _field(text: str, label: str) -> str:
    """Value after an inline `**Label:**` marker (used when the value is a bullet, not a section)."""
    m = re.search(r"\*\*" + re.escape(label) + r":\*\*\s*(.+)", text)
    return m.group(1).strip() if m else ""


def _clean(s: str) -> str:
    """Strip markdown emphasis + a trailing parenthetical note; cut a chained `· **Other:**` segment."""
    s = re.split(r"\s+·\s+\*\*", s)[0]      # `Kenneth Mangum · **Publisher:** …` → `Kenneth Mangum`
    s = re.split(r"\s+\(", s)[0]            # drop a trailing `(parenthetical note)`
    s = s.replace("*", "").replace(" — ", ", ").strip()
    return s


def _value(secs: dict, text: str, section: str, label: str, clean: bool = False) -> str:
    """Section body if that header exists (S1 canonical), else the inline `**Label:**` bullet (S2 early)."""
    v = _by_prefix(secs, section) or _field(text, label)
    return _clean(v) if clean else v


def _series(secs: dict, text: str) -> str:
    """The series name + volume. Prefer the title-block inline bullet (S2 early), else the exact `Series`
    section (S1 canonical) — never a `Series Cross-Reference` section, which would shadow the real value."""
    inline = _field(text, "Series")
    if inline:
        return _clean(inline)
    for h, b in secs.items():
        if h.strip().lower() == "series":
            return _clean(b)
    return ""


def _price(text: str, fmt: str) -> str:
    """First dollar amount associated with a format label — matches `**Ebook:** $6.99` and a
    `| **Ebook (Kindle)** | **$6.99** |` table cell alike."""
    m = re.search(fmt + r"[^$\n]*\$\s*([0-9][0-9.]*)", text, re.I)
    return m.group(1) if m else ""


def parse_kdp_metadata(text: str) -> dict:
    """metadata_v1.0.md text → structured KDP fields (tolerant of both authored formats)."""
    secs = _sections(text)

    title = _clean(_field(text, "Title"))
    subtitle = _clean(_field(text, "Subtitle"))

    pricing = {k: v for k, v in
               ((f.lower(), _price(text, f)) for f in ("Ebook", "Paperback", "Hardcover")) if v}

    print_options = {}
    for k in ("Trim", "Paper", "Bleed", "Cover finish"):
        v = _field(text, k)
        if v:
            print_options[k.lower().replace(" ", "_")] = v

    # Amazon description — HTML (fenced ```html block) + plain-text fallback section (case-insensitive).
    mh = re.search(r"Amazon Description \(HTML.*?\n```html\s*\n(.*?)\n```", text, re.S | re.I)
    description_html = mh.group(1).strip() if mh else ""
    description_text = _by_prefix(secs, "Amazon Description (Plain Text")

    # Keywords: numbered list, values may be wrapped in backticks. Stop before "Keyword strategy notes".
    kw_body = _by_prefix(secs, "KDP Keywords") or _by_prefix(secs, "KDP keywords")
    kw_body = re.split(r"\*\*Keyword strategy", kw_body)[0]
    keywords = [re.sub(r"`", "", k).strip()
                for k in re.findall(r"^\s*\d+\.\s*(.+?)\s*$", kw_body, re.M)]

    # Categories — S1 uses "Categories"; S2 early uses "BISAC" for the same KDP picker field.
    cat_body = _by_prefix(secs, "Categories") or _by_prefix(secs, "BISAC")
    categories = [c.strip() for c in re.findall(r"^\s*\d+\.\s*(.+?)\s*$", cat_body, re.M)]

    isbn_body = _by_prefix(secs, "ISBN")
    isbn = {}
    for k in ("Paperback", "Hardcover"):
        m = re.search(r"\*\*" + k + r":\*\*\s*(.+)", isbn_body)
        if m:
            isbn[k.lower()] = m.group(1).strip()

    return {
        "title": title,
        "subtitle": subtitle,
        "author": _value(secs, text, "Author", "Author", clean=True),
        "publisher": _value(secs, text, "Publisher", "Publisher", clean=True),
        "series": _series(secs, text),
        "pricing": pricing,
        "print_options": print_options,
        "ai_disclosure": _by_prefix(secs, "AI Disclosure"),
        "publication_date": _by_prefix(secs, "Publication Date"),
        "description_html": description_html,
        "description_text": description_text,
        "keywords": keywords,
        "categories": categories,
        "isbn": isbn,
        "present": {
            "title": bool(title),
            "subtitle": bool(subtitle),
            "series": bool(_series(secs, text)),
            "description_html": bool(description_html),
            "keywords": len(keywords),
            "categories": len(categories),
        },
    }
