"""MES-signal keywords (DE/FR/IT/EN) and a scanner that reports which labels a text matches.

Labels:
- mes: MES/MOM/eBR terms
- vendor:<name>: an MES vendor or product is mentioned
- digital: shop-floor digitalisation
- expansion: new or larger production capacity
Acronyms are matched case-sensitively ("MES", not French "mes").
"""

import re
from dataclasses import dataclass

_I = re.IGNORECASE

MES = [
    re.compile(r"\bMES\b|\bMOM\b|\be?BR\b(?=.{0,40}(batch|charge|lot))|\bEBR\b"),
    re.compile(
        r"manufacturing execution|manufacturing operations management|electronic batch record"
        r"|elektronische[snr]? chargen(protokoll|dokumentation)|dossier de lot [ée]lectronique"
        r"|paperless (manufacturing|production)|papierlose (produktion|fertigung)"
        r"|review by exception|batch record review",
        _I,
    ),
]
VENDORS = {
    "PharmaSuite": re.compile(r"pharma ?suite|factorytalk", _I),
    "Tulip": re.compile(r"\bTulip\b(?! ?(bulb|flower|zwiebel|garden))|tulip interfaces"),
    "Körber PAS-X": re.compile(r"\bPAS-X\b|\bwerum\b|k[öo]rber pharma software", _I),
    "Emerson Syncade": re.compile(r"\bsyncade\b", _I),
    "Siemens Opcenter": re.compile(r"\bopcenter\b|simatic it\b", _I),
    "MasterControl": re.compile(r"\bmastercontrol\b", _I),
    "AVEVA": re.compile(r"aveva (mes|manufacturing)|wonderware mes", _I),
    "Critical Manufacturing": re.compile(r"critical manufacturing mes|\bcmf mes\b", _I),
    "Apprentice": re.compile(r"apprentice\.io|tempo (mes|platform)", _I),
}
DIGITAL = re.compile(
    r"pharma 4\.0|industr(ie|y) 4\.0|smart factory|digital (plant|factory|shop ?floor)"
    r"|shop ?floor digitali[sz]|digitali[sz](ierung|ation) (der|de la|of) (produktion|production"
    r"|fertigung|manufacturing)|usine (du futur|num[ée]rique)|fabbrica digitale",
    _I,
)
EXPANSION = re.compile(
    r"new (production|manufacturing) (facility|plant|site|building|line)"
    r"|(expan(d|sion)|increas(e|ing)) (of |our )?(production|manufacturing) capacit"
    r"|neue[sn]? (produktions|fertigungs)(gebäude|anlage|linie|stätte|standort)"
    r"|(produktions|kapazitäts)erweiterung|ausbau der produktion"
    r"|nouvelle (usine|unit[ée] de production|ligne de production)"
    r"|nuov[oa] (stabilimento|linea di produzione|impianto produttivo)",
    _I,
)


@dataclass(frozen=True)
class Match:
    labels: frozenset[str]
    snippet: str


def scan(text: str, snippet_length: int = 160) -> Match | None:
    """Labels found in `text` plus a short snippet around the first match; None if nothing."""
    found: dict[str, int] = {}
    for pattern in MES:
        if m := pattern.search(text):
            found.setdefault("mes", m.start())
    for vendor, pattern in VENDORS.items():
        if m := pattern.search(text):
            found[f"vendor:{vendor}"] = m.start()
    for label, pattern in (("digital", DIGITAL), ("expansion", EXPANSION)):
        if m := pattern.search(text):
            found[label] = m.start()
    if not found:
        return None
    first = min(found.values())
    start = max(0, first - snippet_length // 2)
    snippet = re.sub(r"\s+", " ", text[start : start + snippet_length]).strip()
    return Match(frozenset(found), ("…" if start else "") + snippet + "…")
