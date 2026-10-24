import pytest

from syncsight.ingestion.normalize import clean_street, name_key, normalize_uid


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CHE242294601", "CHE-242.294.601"),
        ("CHE-242.294.601", "CHE-242.294.601"),
        (" che-242.294.601 ", "CHE-242.294.601"),
        ("CHE-24.294.601", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_uid(raw: str | None, expected: str | None) -> None:
    assert normalize_uid(raw) == expected


def test_name_key_ignores_case_quotes_and_spacing() -> None:
    assert name_key("«Alpen» Pharma  AG") == name_key('"alpen" pharma ag') == "alpen pharma ag"
    assert name_key("F. Hoffmann - La Roche AG") == name_key("F. Hoffmann-La Roche AG")
    assert name_key("L’Atelier Sàrl") == name_key("L'Atelier SÀRL")  # noqa: RUF001


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Chemin de la Pensée null", "Chemin de la Pensée"),
        ("null", None),
        (" Haupt  strasse 1 ", "Haupt strasse 1"),
        (None, None),
    ],
)
def test_clean_street_drops_null_tokens(raw: str | None, expected: str | None) -> None:
    assert clean_street(raw) == expected
