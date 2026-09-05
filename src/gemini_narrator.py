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
]

NARRATIVE_MODEL = os.getenv("GEMINI_NARRATIVE_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


class GeminiNarrator:
    def __init__(self, api_key: str | None, timeout: int = 45):
        self.api_key = api_key
        self.timeout = timeout

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def _embedding_ranked_context_ids(self, findings: List[Dict], all_transactions: List[Dict], flagged_transactions: List[Dict]) -> List[str]:
        if not self.api_key or not all_transactions:
            return [t["transaction_id"] for t in flagged_transactions]

        client = genai.Client(api_key=self.api_key)
        descriptions = [f"{t['description']} | {t['payee']} | {t['channel']} | {t['category']} | {t['region']}" for t in all_transactions]
        emb_response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=descriptions,
        )
        tx_embeddings = np.array([e.values for e in emb_response.embeddings], dtype=float)

        rule_text = " ".join(f["rule_name"] for f in findings)
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
            "You are a bank transaction risk investigation assistant. "
            "Only reference transactions provided in the context. "
            "Do not speculate beyond the data. "
            "Never state fraud has occurred. "
            "Use language like 'warrants review' and 'flagged for investigator attention'."
        )

        user_payload = {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "triggered_findings": findings,
            "context_transactions": context_rows,
            "required_output": {
                "first_finding": "string beginning with either 'Needs attention:' or 'No attention needed:'",
                "summary": "2-4 concise sentences",
                "claims": [
                    {
                        "title": "short heading",
                        "explanation": "specific grounded explanation",
                        "transaction_ids": ["ids from context only"],
                        "rule_id": "R1/R2/R3/R4",
                        "investigator_next_step": "what to check first",
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
        try:
            parsed = json.loads(raw_text)
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

        first_finding = self._sanitize(str(parsed.get("first_finding", "Needs attention: risk rules were triggered and warrant review.")))
        summary = self._sanitize(str(parsed.get("summary", "Flagged activity warrants investigator attention.")))

        return {
            "first_finding": first_finding,
            "summary": summary,
            "claims": claims,
            "context_transaction_ids": context_ids,
        }


def deterministic_fallback(findings: List[Dict], flagged_transactions: List[Dict]) -> Dict:
    claims = []
    tx_map = {t["transaction_id"]: t for t in flagged_transactions}

    for finding in findings:
        ids = finding.get("matched_transaction_ids", [])
        if not ids:
            continue
        claims.append(
            {
                "title": finding["rule_name"],
                "explanation": f"Rule {finding['rule_id']} triggered with {len(ids)} matched transaction(s).",
                "transaction_ids": [txid for txid in ids if txid in tx_map],
                "rule_id": finding["rule_id"],
                "investigator_next_step": "Review linked transactions first, then confirm customer intent.",
            }
        )

    return {
        "first_finding": f"Needs attention: {len(claims)} rule(s) were triggered and warrant review.",
        "summary": "AI narrative unavailable — showing rule-engine findings directly.",
        "claims": claims,
        "context_transaction_ids": sorted(tx_map.keys()),
    }
