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
