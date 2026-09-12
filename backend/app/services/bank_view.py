"""Consent-gated bank view with attribute masking.

The bank only ever receives the farmer attributes explicitly listed in an
active consent grant. Masked attributes are transformed deterministically.
"""
from typing import Dict, List, Optional

from app.models.consent_log import ConsentLog
from app.models.farmer import Farmer
from app.models.trust_passport import TrustPassport


def _mask_value(key: str, value: Optional[str]) -> str:
    if value is None:
        return ""
    text = str(value)
    if key == "mobile" and len(text) == 10:
        return "xxxxxx" + text[-4:]
    if key in ("name", "fpo_membership"):
        return " ".join(f"{w[0]}." for w in text.split() if w)
    return "••••••"


def _farmer_field(farmer: Farmer, attribute: str) -> str:
    mapping = {
        "name": farmer.name,
        "mobile": farmer.mobile,
        "village": farmer.village,
        "district": farmer.district,
        "state": farmer.state,
        "acreage": f"{farmer.acreage} acres",
        "crop": farmer.primary_crop or "",
        "fpo_membership": farmer.fpo_membership or "",
    }
    return mapping.get(attribute, "")


def build_bank_view(
    farmer: Farmer,
    consent: ConsentLog,
    passport: Optional[TrustPassport],
) -> Dict:
    allowed = set(consent.attributes or [])
    masked = set(consent.masked_attributes or [])

    fields: List[Dict] = []
    for attribute in sorted(allowed):
        raw = _farmer_field(farmer, attribute)
        is_masked = attribute in masked
        value = _mask_value(attribute, raw) if is_masked else raw
        fields.append({"attribute": attribute, "value": value, "masked": is_masked})

    view: Dict = {
        "farmer_id": farmer.farmer_id,
        "bank_name": consent.bank_name,
        "consent_id": consent.id,
        "consent_expires_at": consent.expires_at,
        "fields": fields,
    }

    if "passport" in allowed and passport is not None:
        view["safe_credit_limit"] = (
            None if passport.safe_credit_limit is None else round(passport.safe_credit_limit, 2)
        )
        view["credit_tier"] = passport.credit_tier
        view["component_scores"] = passport.component_scores
    else:
        view["safe_credit_limit"] = None
        view["credit_tier"] = None
        view["component_scores"] = None

    return view