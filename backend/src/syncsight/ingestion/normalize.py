"""Normalisation shared by all sources: UIDs and company-name match keys."""

import re
import unicodedata

_UID_DIGITS = re.compile(r"^CHE-?(\d{3})\.?(\d{3})\.?(\d{3})$")
# typographic quotes and accents used as apostrophes -> ASCII quotes
_QUOTES = str.maketrans(
    dict.fromkeys("\u2018\u2019\u0060\u00b4", "'")
    | dict.fromkeys("\u00ab\u00bb\u201c\u201d\u201e", '"')
)


def normalize_uid(value: str | None) -> str | None:
    """'CHE242294601' or 'CHE-242.294.601' -> 'CHE-242.294.601'; None if not a UID."""
    if not value:
        return None
    match = _UID_DIGITS.match(value.strip().upper())
    return "CHE-{}.{}.{}".format(*match.groups()) if match else None


def clean_street(street: str | None) -> str | None:
    """Collapse whitespace and drop the literal "null" LINDAS uses for missing parts."""
    words = [w for w in (street or "").split() if w.lower() != "null"]
    return " ".join(words) or None


def name_key(name: str) -> str:
    """Case-, quote- and whitespace-insensitive key for matching company names across sources."""
    text = unicodedata.normalize("NFKC", name).translate(_QUOTES).casefold()
    text = re.sub(r"[\"'.,]", "", text)
    text = re.sub(r"\s*-\s*", "-", text)  # "Hoffmann - La Roche" = "Hoffmann-La Roche"
    return re.sub(r"\s+", " ", text).strip()
