"""KDP metadata parser — tolerance conformance.

Two authored metadata formats live in the books vault and the KDP Dispatch card must render BOTH honestly:
  · S1 canonical — `### Section` headers, value in the section body.
  · S2 early     — `## Section` headers + inline `- **Label:** value` bullets; "BISAC" for Categories;
                   pricing as a table; a `Series Cross-Reference` section that must NOT shadow `Series`.

TRUTH: the card shows what the book declares. A blank series field on a card whose file declares a series
is a parser lie — this test bars its return (regression that KM caught on the Vol 1 dispatch card).
"""
from sovereign_agent.kdp_metadata import parse_kdp_metadata

S1 = """# Book Metadata: Scaling AI Agents
## Agentic AI Series — Book 10

### Title & Subtitle
**Title:** Scaling AI Agents
**Subtitle:** Enterprise-Wide Deployment

### Author
Kenneth Mangum

### Publisher
Breathline Books

### Series
Agentic AI Series, Book 10

### Format & Pricing
- **Ebook:** $6.99
- **Paperback:** $14.99
- **Hardcover:** $24.99

### Amazon Description (HTML — copy-paste into KDP Source view)

```html
<b>Scale without breaking what works.</b>
```

### KDP Keywords (7 slots — keyword-optimized)
1. `scaling AI agents`
2. `enterprise AI platform`

### Categories (2)
1. Business & Money > Management & Leadership
2. Computers & Technology > AI & Machine Learning
"""

S2 = """# Metadata — *The Primacy Cockpit* (v1.0)

## Title block
- **Title:** *The Primacy Cockpit*
- **Subtitle:** *Build the Atrium That Keeps Humans Sovereign*
- **Author:** Kenneth Mangum · **Publisher:** Breathline Books
- **Series:** *Building the Agentic Harness* — Volume 2 (cockpit surface)
- **Series number:** 2 of 5

## Format + pricing
| Format | Price |
|---|---|
| **Ebook (Kindle)** | **$6.99** KU funnel tier |
| Paperback | $14.99 |
| Hardcover | $24.99 (optional) |

## Amazon description (HTML)

```html
<p>The cockpit that keeps you in command.</p>
```

## KDP keywords (7)
1. sovereign cockpit
2. human in the loop AI

## BISAC
1. **COM004000** — Computers / Intelligence (AI) & Semantics *(primary)*
2. **COM044000** — Computers / Security / Cryptography *(secondary)*

## Series cross-reference
| Volume | Title | Status |
|---|---|---|
| Vol 1 | Sovereign Inference & Memory | sealed |
| Vol 2 | The Primacy Cockpit | this volume |
"""


def test_s1_canonical_parses():
    m = parse_kdp_metadata(S1)
    assert m["title"] == "Scaling AI Agents"
    assert m["series"] == "Agentic AI Series, Book 10"
    assert m["author"] == "Kenneth Mangum"
    assert m["pricing"] == {"ebook": "6.99", "paperback": "14.99", "hardcover": "24.99"}
    assert len(m["keywords"]) == 2 and len(m["categories"]) == 2
    assert m["description_html"] and m["present"]["series"]


def test_s2_early_parses_and_series_not_shadowed():
    m = parse_kdp_metadata(S2)
    # the title-block bullet wins — NOT the "Series cross-reference" table (the bug KM caught)
    assert m["series"] == "Building the Agentic Harness, Volume 2"
    assert m["author"] == "Kenneth Mangum"          # `· **Publisher:**` chain stripped
    assert m["publisher"] == "Breathline Books"
    assert m["pricing"]["ebook"] == "6.99"          # table cell parsed despite `|` columns
    assert len(m["keywords"]) == 2
    assert len(m["categories"]) == 2                # BISAC stands in for Categories
    assert m["description_html"] and m["present"]["series"]


def test_partial_file_is_tolerant_not_raising():
    m = parse_kdp_metadata("# Metadata\n## Title block\n- **Title:** Half Authored\n")
    assert m["title"] == "Half Authored"
    assert m["series"] == "" and m["keywords"] == [] and not m["present"]["series"]
