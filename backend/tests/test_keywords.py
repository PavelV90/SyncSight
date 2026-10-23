import pytest

from syncsight.ingestion.keywords import scan


@pytest.mark.parametrize(
    ("text", "labels"),
    [
        ("We are introducing a new MES at our Visp site.", {"mes"}),
        ("Einführung des elektronischen Chargenprotokolls (eBR) in der Abfüllung", {"mes"}),
        ("Rollout of PharmaSuite and Tulip apps", {"vendor:PharmaSuite", "vendor:Tulip"}),
        ("Projektleiter Werum PAS-X (m/w/d)", {"vendor:Körber PAS-X"}),
        ("Unser Weg zu Pharma 4.0", {"digital"}),
        ("Kapazitätserweiterung: neues Produktionsgebäude in Stein", {"expansion"}),
        ("Nous construisons une nouvelle usine à Monthey", {"expansion"}),
        ("Découvrez mes conseils et mes recettes", set()),
        ("Tulip bulbs for your garden", set()),
    ],
)
def test_scan_labels(text: str, labels: set[str]) -> None:
    match = scan(text)
    assert (match.labels if match else set()) == labels


def test_snippet_is_short_and_around_first_match() -> None:
    text = "x " * 200 + "Implementation of a Manufacturing Execution System" + " y" * 200

    match = scan(text)

    assert match is not None
    assert "Manufacturing Execution System" in match.snippet
    assert len(match.snippet) <= 162
