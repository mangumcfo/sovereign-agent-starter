"""
kdp_metadata.py — parse a book's `metadata_v1.0.md` into KDP-ready fields.

The metadata files in the books vault are authored KDP-paste-ready (Title/Subtitle, Amazon Description
HTML + plain-text, 7 keyword slots, 2 categories, pricing, print options, ISBN). This parser turns that
markdown into a structured dict the Atrium KDP Dispatch surface renders + copies field-by-field.

Tolerant by design: missing/TBD sections return '' or [] rather than raising — a half-authored metadata
file still yields a usable (partial) dispatch card, honestly showing what's present.

∞Δ∞ Book defines the listing; the surface just stages it for the one manual KDP click. ∞Δ∞
"""
from __future__ import annotations
import re


def _sections(text: str) -> dict:
    """Split a metadata markdown doc into {h3_header: body} by '### ' headers."""
    parts = re.split(r"^###\s+(.+?)\s*$", text, flags=re.M)
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
    """Value after a `**Label:**` marker."""
    m = re.search(r"\*\*" + re.escape(label) + r":\*\*\s*(.+)", text)
    return m.group(1).strip() if m else ""


def parse_kdp_metadata(text: str) -> dict:
    """metadata_v1.0.md text → structured KDP fields."""
    secs = _sections(text)

    title = _field(text, "Title")
    subtitle = _field(text, "Subtitle")

    pricing = {}
    for k in ("Ebook", "Paperback", "Hardcover"):
        m = re.search(r"\*\*" + k + r":\*\*\s*\$?\s*([0-9][0-9.]*)", text)
        if m:
            pricing[k.lower()] = m.group(1)

    print_options = {}
    for k in ("Trim", "Paper", "Bleed", "Cover finish"):
        v = _field(text, k)
        if v:
            print_options[k.lower().replace(" ", "_")] = v

    # Amazon description — HTML (fenced ```html block) + plain-text fallback section.
    mh = re.search(r"Amazon Description \(HTML.*?\n```html\s*\n(.*?)\n```", text, re.S)
    description_html = mh.group(1).strip() if mh else ""
    description_text = _by_prefix(secs, "Amazon Description (Plain Text")

    # Keywords: numbered list, values may be wrapped in backticks. Stop before "Keyword strategy notes".
    kw_body = _by_prefix(secs, "KDP Keywords")
    kw_body = re.split(r"\*\*Keyword strategy", kw_body)[0]
    keywords = [re.sub(r"`", "", k).strip()
                for k in re.findall(r"^\s*\d+\.\s*(.+?)\s*$", kw_body, re.M)]

    categories = [c.strip() for c in
                  re.findall(r"^\s*\d+\.\s*(.+?)\s*$", _by_prefix(secs, "Categories"), re.M)]

    isbn_body = _by_prefix(secs, "ISBN")
    isbn = {}
    for k in ("Paperback", "Hardcover"):
        m = re.search(r"\*\*" + k + r":\*\*\s*(.+)", isbn_body)
        if m:
            isbn[k.lower()] = m.group(1).strip()

    return {
        "title": title,
        "subtitle": subtitle,
        "author": _by_prefix(secs, "Author"),
        "publisher": _by_prefix(secs, "Publisher"),
        "series": _by_prefix(secs, "Series"),
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
            "description_html": bool(description_html),
            "keywords": len(keywords),
            "categories": len(categories),
        },
    }
