"""A4 (operator-ruled): the seed-unit law — full chapter + locked beats,
enforced by tooling at card load, never by convention."""
import sys
from pathlib import Path

import pytest
import yaml

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from sovereign_agent.press import adversary as adv  # noqa: E402

LAWFUL = {
    "chapter": "ch01",
    "seed_unit": "full_chapter",
    "beats_locked": True,
    "beats": ["receipts are append-only", "the operator speaks the word"],
    "promise": "the chapter explains the receipt law",
    "runs_today": ["append-only receipt bundles"],
    "prose": ("Receipts are append-only in this design. Every run writes its own "
              "bundle and no bundle is ever reused. The operator speaks the word "
              "before anything promotes, and the record shows it."),
}


def _write(tmp_path, card, name="ch01.yaml"):
    d = tmp_path / "seeds"
    d.mkdir(exist_ok=True)
    (d / name).write_text(yaml.safe_dump(card))
    return d


def test_lawful_card_loads(tmp_path):
    d = _write(tmp_path, LAWFUL)
    cards = adv.load_cards(d)
    assert len(cards) == 1 and cards[0]["chapter"] == "ch01"


@pytest.mark.parametrize("mutation,needle", [
    ({"seed_unit": None}, "seed_unit: full_chapter"),
    ({"seed_unit": "excerpt"}, "seed_unit: full_chapter"),
    ({"beats_locked": False}, "beats_locked"),
    ({"beats": []}, "no beats"),
    ({"beats": ["receipts are append-only", "TBD tighten this beat"]}, "placeholder"),
    ({"prose": "One sentence only."}, "too short"),
    ({"prose": "A start. A middle. And then the chapter simply"}, "mid-sentence"),
])
def test_unlawful_cards_refused_loud(tmp_path, mutation, needle):
    card = dict(LAWFUL)
    card.update(mutation)
    if card.get("seed_unit") is None:
        card.pop("seed_unit")
    d = _write(tmp_path, card)
    with pytest.raises(SystemExit) as e:
        adv.load_cards(d)
    assert needle in str(e.value), str(e.value)


def test_validate_returns_none_for_lawful():
    assert adv.validate_seed_unit(dict(LAWFUL)) is None


# The furniture refinement: a full chapter may lawfully END with typesetting
# furniture (\newpage, rules, headings, bold-only lines). Found by whole-pipeline
# verification — a genuine chapter ending `…sentence.` + `\newpage` was refused.
@pytest.mark.parametrize("furniture_tail", [
    "\n\n\\newpage",
    "\n\n---",
    "\n\n## What Comes Next",
    "\n\n**End of chapter**",
    "\n\n---\n\\newpage\n",
])
def test_furniture_final_full_chapter_is_lawful(tmp_path, furniture_tail):
    card = dict(LAWFUL)
    card["prose"] = LAWFUL["prose"] + furniture_tail
    d = _write(tmp_path, card)
    cards = adv.load_cards(d)
    assert len(cards) == 1


@pytest.mark.parametrize("prose", [
    # the check reads the last PROSE line beneath the furniture — an excerpt
    # hiding under \newpage is still an excerpt
    "A start. A middle. And then the chapter simply\n\n\\newpage",
    # pure furniture holds no chapter at all
    "## Heading\n\n---\n\n\\newpage",
])
def test_furniture_never_launders_an_excerpt(tmp_path, prose):
    card = dict(LAWFUL)
    card["prose"] = prose
    d = _write(tmp_path, card)
    with pytest.raises(SystemExit) as e:
        adv.load_cards(d)
    assert "seed-unit law (A4)" in str(e.value), str(e.value)


# ── A6: the width lexicon, single-sourced and exported ─────────────────────────
from sovereign_agent.press.adversary import chapter_end_lawful


def _base_prose(tail):
    return "First sentence here. Second one follows. A third completes the chapter.\n" + tail


WIDTH_LAWFUL_TAILS = [
    "\\newpage",                                     # typesetting directive
    "3. **Set a calendar reminder in 30 days.**",    # list item closing in bold
    "> *Visibility guaranteed; one renderer draws every surface.*",  # blockquote italic
    "![Stage 3 Divider](divider_stage_3.png)",       # image/divider furniture
    "---\n\\newpage\n![Card](card.png)",             # stacked furniture
    "| receipts | append-only |",                    # table row tail
    "> ```",                                         # blockquoted fence tail
]


def test_a6_width_tails_are_lawful():
    for tail in WIDTH_LAWFUL_TAILS:
        assert chapter_end_lawful(_base_prose(tail)) is None, f"lawful tail refused: {tail!r}"


FURNITURE_ONLY_TAILS = ["\\newpage", "![Stage 3 Divider](divider_stage_3.png)",
                        "---\n\\newpage\n![Card](card.png)", "| receipts | append-only |", "> ```"]


def test_a6_truncation_still_refused_under_pure_furniture():
    """An end-check sees THROUGH furniture to the last prose line. Beneath a PROSE
    tail (list item, blockquote sentence) that lawful line IS the ending — an earlier
    truncation is a completeness question, not an ending question. Beneath pure
    furniture, the truncated line is the last prose and must refuse."""
    for tail in FURNITURE_ONLY_TAILS:
        prose = "First sentence. Second. This one cuts of\n" + tail
        assert chapter_end_lawful(prose) is not None, f"truncation admitted under: {tail!r}"


def test_a6_lexicon_is_the_single_source():
    """Generation tooling imports these names; their existence IS the contract."""
    from sovereign_agent.press import adversary
    for name in ("FURNITURE", "SENTENCE_END", "chapter_end_lawful"):
        assert hasattr(adversary, name)


SIGIL_TAILS = [
    "∞Δ∞",                                   # book back-matter sigil (real S2 tail, n=2 in the field)
    "* * *",                                 # classic dinkus
    "···",                                   # dot dinkus
    "— — —",                                 # dash rule
    "---\n∞Δ∞",                              # rule then sigil (stacked, the observed real shape)
]


def test_sigil_and_dinkus_tails_are_lawful():
    """Short symbol-only lines are typesetting furniture. Field origin: every volume in
    one series ends its back-matter with a sigil line; before this rule the final
    chapter of each refused as mid-sentence (two distinct volumes reproduced it)."""
    for tail in SIGIL_TAILS:
        assert chapter_end_lawful(_base_prose(tail)) is None, f"sigil tail refused: {tail!r}"


def test_truncation_still_refused_under_sigil():
    """Fail-direction preserved: the sigil is furniture, not an ending — a truncated
    last prose line beneath it still refuses."""
    for tail in SIGIL_TAILS:
        prose = "First sentence. Second. This one cuts of\n" + tail
        assert chapter_end_lawful(prose) is not None, f"truncation admitted under: {tail!r}"


def test_symbol_run_length_is_bounded():
    """A LONG symbol line is not a sigil — boundedness keeps the furniture class from
    swallowing content-bearing lines."""
    assert chapter_end_lawful(_base_prose("∞Δ∞" * 12)) is not None


CONTACT_BLOCK_TAILS = [
    "**Email:** contact@[example.com](https://example.com)",
    "**Publisher:** Example Press",
    "**Publisher:** Example Press — examplepress.com",
    "**Email:** contact@[example.com](https://example.com)\n\n**Publisher:** Example Press",
]


def test_contact_block_tails_are_lawful():
    """Back-matter contact blocks are typesetting metadata, not chapter prose. Field
    origin, eight uniform reproductions: one series ends every volume on its contact
    block (no epigraph, no sigil) and every final chapter refused as mid-sentence."""
    for tail in CONTACT_BLOCK_TAILS:
        assert chapter_end_lawful(_base_prose(tail)) is None, f"contact tail refused: {tail!r}"


def test_truncation_still_refused_under_contact_block():
    """Fail-direction preserved: a truncated last prose line beneath the contact
    block still refuses — the block is furniture, never an ending."""
    for tail in CONTACT_BLOCK_TAILS:
        prose = "First sentence. Second. This one cuts of\n" + tail
        assert chapter_end_lawful(prose) is not None, f"truncation admitted under: {tail!r}"


def test_long_label_led_line_is_prose_not_furniture():
    """Boundedness: a label-led CONTENT line ('**How it works:** <long sentence>') is
    prose — if it trails off unfinished it must refuse, not hide behind the label."""
    long_tail = ("**How it works:** the optimization agent scans every data source the "
                 "other agents use and identifies savings projects, each project getting")
    assert chapter_end_lawful(_base_prose(long_tail)) is not None


def test_full_contact_block_field_shape_is_lawful():
    """The field-faithful five-line block that exposed the 24-char label bound:
    'Sovereign Inference Exchange' is 28 chars. Fixture is the real shape, not a
    convenient abbreviation — the first landing's fixtures were too polite."""
    block = ("## Connect\n\n"
             "**Website:** [example.com](https://example.com)\n\n"
             "**Sovereign Inference Exchange:** example-exchange.com\n\n"
             "**X:** @example\n\n"
             "**LinkedIn:** linkedin.com/in/example\n\n"
             "**Email:** contact@[example.com](https://example.com)\n\n"
             "**Publisher:** Example Press")
    assert chapter_end_lawful(_base_prose(block)) is None
    truncated = "First sentence. Second. This one cuts of\n" + block
    assert chapter_end_lawful(truncated) is not None


def test_sigil_after_terminal_punctuation_is_lawful():
    """One house style closes chapters with a sigil-wrapped paragraph — the final line
    ends '<sentence>. <sigil>' on the SAME line. Terminal punctuation followed by
    trailing sigil glyphs is a lawful ending (eight uniform field reproductions,
    swept before landing)."""
    assert chapter_end_lawful(
        "First sentence. A history that cannot change. ∞Δ∞") is None
    assert chapter_end_lawful(
        "First sentence. Second one. This one trails off ∞Δ∞") is not None  # no punct → refuse


def test_whole_line_italic_span_and_nbsp_are_furniture():
    """'*Published by Example Press*' and '&nbsp;' spacer lines are typesetting
    back-matter; truncation beneath them still refuses."""
    for tail in ("*Published by Example Press*", "&nbsp;", "&nbsp; &nbsp;"):
        assert chapter_end_lawful(_base_prose(tail)) is None, f"refused: {tail!r}"
        assert chapter_end_lawful(
            "First. Second. This one cuts of\n" + tail) is not None
