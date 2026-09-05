from __future__ import annotations

import os
import json
import re
from typing import Dict, List

import numpy as np
from google import genai


BANNED_PHRASES = [
    "fraud confirmed",
    "this is fraud",
    "fraud has occurred",
    "confirmed fraud",
    "fraudulent activity",
]

NARRATIVE_MODEL = os.getenv("GEMINI_NARRATIVE_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

def _format_amount(amt: float) -> str:
    val = int(round(amt))
    if val >= 100000:
        return f"₹{val / 100000:.1f}L"
    return f"₹{val:,}"


class GeminiNarrator:
    def __init__(self, api_key: str | None, timeout: int = 45):
        self.api_key = api_key
        self.timeout = timeout

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def _embedding_ranked_context_ids(
        self, findings: List[Dict], all_transactions: List[Dict], flagged_transactions: List[Dict]
    ) -> List[str]:
        if not self.api_key or not all_transactions:
            return [t["transaction_id"] for t in flagged_transactions]

        try:
            client = genai.Client(api_key=self.api_key)
            descriptions = [
                f"{t.get('description', '')} | {t.get('payee', '')} | {t.get('channel', '')} | {t.get('category', '')} | {t.get('region', '')}"
                for t in all_transactions
            ]
            emb_response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=descriptions,
            )
            tx_embeddings = np.array([e.values for e in emb_response.embeddings], dtype=float)

            rule_text = " ".join(f.get("rule_name", "") for f in findings)
            query = f"Risk evidence context for: {rule_text}"
            q_emb_response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[query],
            )
            query_vec = np.array(q_emb_response.embeddings[0].values, dtype=float)

            sims = [self._cosine_sim(query_vec, tx_embeddings[i]) for i in range(len(all_transactions))]
            top_idx = np.argsort(sims)[::-1][:10]

            selected = {t["transaction_id"] for t in flagged_transactions}
            selected.update(all_transactions[i]["transaction_id"] for i in top_idx)
            return sorted(selected)
        except Exception:
            return [t["transaction_id"] for t in flagged_transactions]

    def _sanitize(self, text: str) -> str:
        safe = text
        for phrase in BANNED_PHRASES:
            safe = re.sub(re.escape(phrase), "warrants review", safe, flags=re.IGNORECASE)
        return safe

    def generate_narrative(
        self,
        customer_id: str,
        customer_name: str,
        findings: List[Dict],
        flagged_transactions: List[Dict],
        all_transactions: List[Dict],
    ) -> Dict:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        context_ids = self._embedding_ranked_context_ids(findings, all_transactions, flagged_transactions)
        context_rows = [t for t in all_transactions if t["transaction_id"] in set(context_ids)]
        allowed_ids = {t["transaction_id"] for t in context_rows}

        client = genai.Client(api_key=self.api_key)

        system_prompt = (
            "You are an expert fraud desk investigation assistant for a premier bank. "
            "Your role is to produce an objective investigation brief evaluating flagged transactions against baseline customer behavior. "
            "RULES: "
            "1. Ground every statement strictly in the provided transactions and findings. "
            "2. Never state or imply that fraud has occurred; use objective phrasing like 'warrants review', 'deviates from baseline', and 'flagged for investigator attention'. "
            "3. Output valid JSON only."
        )

        user_payload = {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "triggered_findings": findings,
            "context_transactions": context_rows,
            "required_output_schema": {
                "first_finding": "String starting with 'Needs attention:' or 'No attention needed:'",
                "summary": "2-3 clear, professional sentences explaining how the signals connect and how activity deviates from normal baseline.",
                "recommended_checks": [
                    "Check 1: specific verification action",
                    "Check 2: specific transaction or relationship check",
                    "Check 3: authentication/session verification"
                ],
                "claims": [
                    {
                        "title": "Short title for rule finding",
                        "explanation": "Factually grounded explanation citing specific amounts, payees, or times",
                        "transaction_ids": ["TXN IDs from context only"],
                        "rule_id": "R1/R2/R3/R4",
                        "investigator_next_step": "Actionable verification step",
                    }
                ],
            },
        }

        response = client.models.generate_content(
            model=NARRATIVE_MODEL,
            contents=[
                {"role": "user", "parts": [{"text": system_prompt}]},
                {"role": "user", "parts": [{"text": json.dumps(user_payload)}]},
            ],
        )

        raw_text = response.text or ""
        # Strip markdown JSON wrappers if present
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("```")[1]
            if clean_text.startswith("json"):
                clean_text = clean_text[4:]
            clean_text = clean_text.strip()

        try:
            parsed = json.loads(clean_text)
        except Exception as exc:
            raise RuntimeError(f"Malformed Gemini response: {exc}")

        claims = []
        for claim in parsed.get("claims", []):
            ids = [txid for txid in claim.get("transaction_ids", []) if txid in allowed_ids]
            if not ids:
                continue
            claims.append(
                {
                    "title": self._sanitize(str(claim.get("title", ""))),
                    "explanation": self._sanitize(str(claim.get("explanation", ""))),
                    "transaction_ids": ids,
                    "rule_id": claim.get("rule_id", ""),
                    "investigator_next_step": self._sanitize(str(claim.get("investigator_next_step", ""))),
                }
            )

        first_finding = self._sanitize(
            str(parsed.get("first_finding", "Needs attention: risk signals detected across transactions warrant review."))
        )
        summary = self._sanitize(str(parsed.get("summary", "Flagged activity warrants investigator attention.")))
        recommended_checks = [self._sanitize(str(c)) for c in parsed.get("recommended_checks", [])]

        if not recommended_checks:
            recommended_checks = _build_default_checks(findings, flagged_transactions)

        return {
            "first_finding": first_finding,
            "summary": summary,
            "recommended_checks": recommended_checks,
            "claims": claims,
            "context_transaction_ids": context_ids,
        }


def _build_default_checks(findings: List[Dict], flagged_transactions: List[Dict]) -> List[str]:
    checks = []
    r_ids = {f.get("rule_id") for f in findings if f.get("triggered")}

    # Check 1: New Payee / relationship
    if "R2" in r_ids:
        r2 = next((f for f in findings if f.get("rule_id") == "R2"), {})
        payee = r2.get("baseline_stats", {}).get("burst_payee", "the new payee")
        checks.append(f"Verify whether the customer initiated the new payee relationship with {payee}.")
    else:
        checks.append("Verify customer transaction initiation and authorization details.")

    # Check 2: Large transfer
    if "R1" in r_ids:
        r1 = next((f for f in findings if f.get("rule_id") == "R1"), {})
        max_amt = r1.get("baseline_stats", {}).get("max_flagged_amount", 0)
        checks.append(f"Review the purpose/source of the {_format_amount(max_amt)} transfer.")
    else:
        checks.append("Review whether recent transaction volumes deviate from scheduled commitments.")

    # Check 3: Odd hours / known customer event
    if "R3" in r_ids:
        checks.append("Check whether the activity corresponds to a known customer event or travel schedule.")
    else:
        checks.append("Confirm payee account details against internal watchlists and beneficiary history.")

    # Check 4: Channel & authentication
    checks.append("Review authentication/channel information and IP/device telemetry for the flagged transactions.")
    return checks


def deterministic_fallback(findings: List[Dict], flagged_transactions: List[Dict]) -> Dict:
    claims = []
    tx_map = {t["transaction_id"]: t for t in flagged_transactions}
    triggered_findings = [f for f in findings if f.get("triggered")]

    for finding in triggered_findings:
        ids = finding.get("matched_transaction_ids", [])
        if not ids:
            continue
        claims.append(
            {
                "title": finding["rule_name"],
                "explanation": finding.get("description", f"Rule {finding['rule_id']} triggered with {len(ids)} matched transaction(s)."),
                "transaction_ids": [txid for txid in ids if txid in tx_map],
                "rule_id": finding["rule_id"],
                "investigator_next_step": (
                    "Verify payee addition authorization." if finding["rule_id"] == "R2"
                    else ("Check funding source and customer confirmation." if finding["rule_id"] == "R1"
                    else ("Inspect session login timestamps and device telemetry." if finding["rule_id"] == "R3"
                    else "Check channel credentials and origin destination."))
                ),
            }
        )

    # Build dynamic synthesized narrative matching the reference UI tone
    signals_count = len(triggered_findings)
    if signals_count >= 3:
        summary = (
            "The activity warrants review because three independent behavioural signals occur within a short period. "
            "The largest transfer is substantially above the customer's historical baseline, while multiple payments were made "
            "to a previously unseen payee. One transaction also occurred outside the customer's established activity window."
        )
    elif signals_count == 2:
        names = [f["rule_name"].lower() for f in triggered_findings]
        summary = (
            f"The activity warrants review due to two concurring behavioral signals: {names[0]} and {names[1]}. "
            "These transactions deviate notably from established customer patterns and warrant investigator verification."
        )
    elif signals_count == 1:
        f0 = triggered_findings[0]
        summary = (
            f"A single risk signal ({f0['rule_name'].lower()}) was triggered. While other behavioral metrics remain within baseline, "
            f"{f0.get('description', 'the flagged transaction warrants review')}."
        )
    else:
        summary = "All reviewed activity stays within this customer's established behavior. No risk rules were triggered."

    first_finding = (
        f"Needs attention: {signals_count} risk signal{'s' if signals_count > 1 else ''} detected across {len(flagged_transactions)} transaction{'s' if len(flagged_transactions) > 1 else ''}. This activity warrants review."
        if signals_count > 0
        else "No attention needed: all transactions stay within this customer's established baseline."
    )

    recommended_checks = _build_default_checks(triggered_findings, flagged_transactions)

    return {
        "first_finding": first_finding,
        "summary": summary,
        "recommended_checks": recommended_checks,
        "claims": claims,
        "context_transaction_ids": sorted(tx_map.keys()),
    }
