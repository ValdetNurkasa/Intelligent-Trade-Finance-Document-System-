import csv
from pathlib import Path
from app.schemas.common import RiskLevel
from app.schemas.context import ContextPacket
from app.schemas.sanctions import SanctionsHit, SanctionsScreen
from app.tools.fuzzy_match_tool import similarity

DATA_DIR = Path("app/data/sanctions")
LIST_FILES = ["ofac_sdn_sample.csv", "eu_consolidated_sample.csv", "un_consolidated_sample.csv"]


def _load_lists() -> list[dict]:
    rows = []
    for name in LIST_FILES:
        path = DATA_DIR / name
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    return rows


def _load_country_risk() -> dict:
    path = DATA_DIR / "country_risk_sample.csv"
    table = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                table[row["country_code"].strip().upper()] = {
                    "name": row["country_name"],
                    "tier": int(row["risk_tier"]),
                    "embargo": str(row["embargo"]).strip().lower() == "true",
                }
    return table


def _load_dual_use() -> list[dict]:
    path = DATA_DIR / "dual_use_keywords_sample.csv"
    rows = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    return rows


def _normalize(name: str) -> str:
    return name.replace("SAMPLE - ", "").strip()


def _collect_entities(context: ContextPacket) -> list[dict]:
    entities = [
        {"name": context.applicant.name, "type": "applicant", "country": context.applicant.country},
        {"name": context.beneficiary.name, "type": "beneficiary", "country": context.beneficiary.country},
        {"name": context.issuing_bank.name, "type": "bank", "country": context.issuing_bank.country},
        {"name": context.advising_bank.name, "type": "bank", "country": context.advising_bank.country},
        {"name": context.vessel.name, "type": "vessel", "country": None},
    ]
    return entities


def _screen_entity(entity: dict, lists: list[dict], threshold: float) -> list[SanctionsHit]:
    hits = []
    for listed in lists:
        listed_name = _normalize(listed["entity_name"])
        score = similarity(entity["name"], listed_name)
        if score >= threshold:
            exact = score >= 0.99
            false_positive = not exact and score < (threshold + 0.05)
            hits.append(
                SanctionsHit(
                    entity_name=entity["name"],
                    entity_type=entity["type"],
                    list_name=listed["list_name"],
                    match_score=round(score, 4),
                    match_type="exact" if exact else "fuzzy",
                    is_false_positive=false_positive,
                    false_positive_reason=(
                        "Borderline fuzzy match near threshold; manual verification advised."
                        if false_positive
                        else None
                    ),
                    recommended_action="MANUAL_REVIEW" if false_positive else "FREEZE",
                )
            )
    return hits


def screen(context: ContextPacket, policy: dict) -> SanctionsScreen:
    threshold = float(policy.get("name_match_threshold", 0.85))
    escalation_tier = int(policy.get("country_risk_escalation_tier", 3))

    lists = _load_lists()
    country_risk = _load_country_risk()
    dual_use = _load_dual_use()

    entities = _collect_entities(context)
    all_hits: list[SanctionsHit] = []
    for entity in entities:
        all_hits.extend(_screen_entity(entity, lists, threshold))

    countries_flagged = []
    embargo_hit = False
    countries_to_check = {
        context.applicant.country,
        context.beneficiary.country,
        context.issuing_bank.country,
        context.advising_bank.country,
    }
    flag_code = None
    for code, info in country_risk.items():
        if context.vessel.flag_state and info["name"].lower() == context.vessel.flag_state.lower():
            flag_code = code
    countries_to_check.add(flag_code)
    for code in countries_to_check:
        if not code:
            continue
        info = country_risk.get(str(code).strip().upper())
        if info and (info["tier"] >= escalation_tier or info["embargo"]):
            countries_flagged.append(info["name"])
            if info["embargo"]:
                embargo_hit = True

    dual_use_flags = []
    goods_text = " ".join(
        ev.value.lower() for ev in context.evidence_index.values() if ev.value
    )
    for row in dual_use:
        if row["keyword"].lower() in goods_text:
            dual_use_flags.append(f"{row['keyword']} ({row['category']})")

    actionable_hits = [h for h in all_hits if not h.is_false_positive]
    freeze = bool(actionable_hits) or embargo_hit

    if freeze:
        risk = RiskLevel.critical
        status = "FREEZE"
    elif all_hits or countries_flagged or dual_use_flags:
        risk = RiskLevel.high if countries_flagged else RiskLevel.medium
        status = "ESCALATE"
    else:
        risk = RiskLevel.low
        status = "CLEAR"

    return SanctionsScreen(
        bundle_id=context.bundle_id,
        overall_status=status,
        freeze_processing=freeze,
        risk_level=risk,
        entities_screened=len(entities),
        hits=sorted(all_hits, key=lambda h: (h.entity_name, h.list_name)),
        countries_flagged=sorted(set(countries_flagged)),
        dual_use_flags=sorted(set(dual_use_flags)),
    )
