"""API response models."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from syncsight.db import mes as mes_scoring
from syncsight.db.models import Company, SogcNotice, SwissmedicSite
from syncsight.ingestion.shab import PUBLIC_URL
from syncsight.ingestion.swissmedic import ACTIVITIES
from syncsight.legal_forms import LEGAL_FORMS


class CompanySummary(BaseModel):
    uid: str
    name: str
    legal_form: str | None
    seat: str | None
    canton: str | None
    status: str | None

    @classmethod
    def of(cls, company: Company) -> "CompanySummary":
        return cls(
            uid=company.uid,
            name=company.name,
            legal_form=LEGAL_FORMS.get(company.legal_form or "", company.legal_form),
            seat=company.seat,
            canton=company.canton,
            status=company.status,
        )


class Notice(BaseModel):
    id: str
    publication_date: date
    sub_rubric: str
    changes: list[str]
    capital: float | None
    previous_capital: float | None
    text: str | None
    url: str

    @classmethod
    def of(cls, notice: SogcNotice, previous_capital: float | None = None) -> "Notice":
        return cls(
            id=notice.id,
            publication_date=notice.publication_date,
            sub_rubric=notice.sub_rubric,
            changes=notice.changes,
            capital=as_float(notice.capital_nominal),
            previous_capital=previous_capital,
            text=notice.publication_text,
            url=PUBLIC_URL.format(id=notice.id),
        )


class Site(BaseModel):
    licence_number: str
    site_name: str | None
    site_locality: str | None
    site_canton: str | None
    activities: list[str]
    last_inspection: date | None
    compliance_status: str | None

    @classmethod
    def of(cls, site: SwissmedicSite) -> "Site":
        return cls(
            licence_number=site.licence_number,
            site_name=site.site_name,
            site_locality=site.site_locality,
            site_canton=site.site_canton,
            activities=[ACTIVITIES[code] for code in site.activity_codes if code in ACTIVITIES],
            last_inspection=site.last_inspection,
            compliance_status=site.compliance_status,
        )


class EvidenceItem(BaseModel):
    kind: str
    on: date | None
    title: str
    detail: str | None
    url: str | None
    points: int


class KindScore(BaseModel):
    kind: str
    items: int
    counted: int
    points_each: int
    points: int


class MesLead(BaseModel):
    company: CompanySummary
    score: int
    breakdown: list[KindScore]
    site_cantons: list[str]
    activities: list[str]
    vendors: list[str]
    evidence: list[EvidenceItem]

    @classmethod
    def of(cls, lead: mes_scoring.MesLead) -> "MesLead":
        return cls(
            company=CompanySummary.of(lead.company),
            score=lead.score,
            breakdown=[KindScore(**vars(k), points=k.points) for k in lead.breakdown],
            site_cantons=lead.site_cantons,
            activities=[ACTIVITIES[c] for c in lead.activity_codes if c in ACTIVITIES],
            vendors=sorted(lead.vendors),
            evidence=[EvidenceItem(**vars(e)) for e in lead.evidence],
        )


class ScoringRule(BaseModel):
    kind: str
    points: int
    max_items: int


class CompanyProfile(CompanySummary):
    purpose: str | None
    address: str | None
    website: str | None
    history_fetched_at: datetime | None
    notice_count: int
    earliest_notice: date | None
    sites: list[Site]
    timeline: list[Notice]
    mes: MesLead | None


class SourceStatus(BaseModel):
    key: str
    label: str
    rows: int
    last_loaded_at: datetime | None
    newest_record: date | None
    stale: bool
    command: str


class Lead(BaseModel):
    company: CompanySummary
    site_cantons: list[str]
    activities: list[str]
    last_change: date
    notices: list[Notice]


class Target(BaseModel):
    company: CompanySummary
    founded_on: date
    raised_on: date
    capital_before: float
    capital_after: float
    notice_url: str
    purpose_excerpt: str | None  # matched words wrapped in ⟦ ⟧


def as_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None
