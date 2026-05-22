"""Compliance Engine

Minimal compliance enforcement for development startup.
Replace with Mastercard-approved governance controls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import re


@dataclass
class ComplianceResult:
    allowed: bool
    reason: str = ""
    flags: List[str] = None


class ComplianceEngine:
    def __init__(self, security_config: Dict[str, Any], compliance_config: Dict[str, Any]):
        self.security_config = security_config
        self.compliance_config = compliance_config

    async def validate_query(self, parsed_query: Dict[str, Any], user_role: str, region: str) -> ComplianceResult:
        return ComplianceResult(allowed=True, flags=[])

    async def validate_response(self, response: Dict[str, Any], user_role: str, region: str) -> Dict[str, Any]:
        answer = response.get("answer", "")
        masked_answer = self._mask_pans(answer)
        masked = masked_answer != answer

        out = dict(response)
        if masked:
            out["masked_answer"] = masked_answer
            out["masked_data"] = True
            out["flags"] = list(set((out.get("compliance_flags") or []) + ["COMPLIANCE_MASKED"]))
        else:
            out["flags"] = out.get("compliance_flags") or []
        return out

    def _mask_pans(self, text: str) -> str:
        # Mask 13-19 digit sequences conservatively.
        def repl(m: re.Match) -> str:
            pan = m.group(0)
            if len(pan) < 10:
                return "*" * len(pan)
            return pan[:6] + "*" * (len(pan) - 10) + pan[-4:]

        return re.sub(r"\b\d{13,19}\b", repl, text)
