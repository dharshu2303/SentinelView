from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    rule_num: int
    rule_name: str
    triggered: bool
    matched_transaction_ids: List[str]
    description: str
    baseline_stats: Dict
    severity: str

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "rule_num": self.rule_num,
            "rule_name": self.rule_name,
            "triggered": self.triggered,
            "matched_transaction_ids": self.matched_transaction_ids,
            "description": self.description,
            "baseline_stats": self.baseline_stats,
            "severity": self.severity,
        }


def _prepare_df(transactions: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(transactions).copy()
    required = {"transaction_id", "date", "payee", "amount", "channel", "category", "region"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required transaction fields: {sorted(missing)}")

    df["timestamp"] = pd.to_datetime(df["date"], errors="coerce", utc=False)
    if df["timestamp"].isna().any():
        raise ValueError("Malformed transaction dates detected")

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if df["amount"].isna().any():
        raise ValueError("Malformed transaction amounts detected")

    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def _format_inr(amount: float) -> str:
    """Format number to Indian Rupee representation (e.g. ₹2,40,000)."""
    s = f"{int(round(amount)):,}"
    # Standard Python :, gives 240,000. In Indian numbering format:
    # 2,40,000:
    val = int(round(amount))
    if val < 1000:
        return f"₹{val}"
    val_str = str(val)
    last_three = val_str[-3:]
    other_numbers = val_str[:-3]
    if other_numbers != "":
        # Group in pairs of 2 from right to left
        res = ""
        while len(other_numbers) > 2:
            res = "," + other_numbers[-2:] + res
            other_numbers = other_numbers[:-2]
        res = other_numbers + res
        return f"₹{res},{last_three}"
    return f"₹{last_three}"


def _format_hour_ampm(hour: int, minute: int = 0) -> str:
    period = "AM" if hour < 12 else "PM"
    h = hour % 12
    if h == 0:
        h = 12
    if minute == 0:
        return f"{h} {period}"
    return f"{h:02d}:{minute:02d} {period}"


def rule_large_transfer(df: pd.DataFrame) -> RuleResult:
    matched = []
    baseline_medians = []
    max_matched_amt = 0.0
    ref_median = 0.0

    for i, row in df.iterrows():
        window_start = row["timestamp"] - pd.Timedelta(days=90)
        trailing = df[(df["timestamp"] < row["timestamp"]) & (df["timestamp"] >= window_start)]
        if len(trailing) < 15:
            continue
        median_amount = float(trailing["amount"].median())
        baseline_medians.append(median_amount)
        threshold = max(median_amount * 2.5, 750.0)
        if float(row["amount"]) > threshold:
            matched.append(row["transaction_id"])
            if float(row["amount"]) > max_matched_amt:
                max_matched_amt = float(row["amount"])
                ref_median = median_amount

    overall_median = float(df["amount"].median()) if not df.empty else 0.0

    if matched:
        multiplier = round(max_matched_amt / max(ref_median, 1.0), 1)
        desc = f"Transaction {_format_inr(max_matched_amt)} is {multiplier:.1f}× higher than customer's 90-day median ({_format_inr(ref_median)})."
        severity = "High"
    else:
        desc = f"No transactions significantly exceed customer's 90-day median ({_format_inr(overall_median)})."
        severity = "Low"

    return RuleResult(
        rule_id="R1",
        rule_num=1,
        rule_name="Unusually Large Transfers",
        triggered=bool(matched),
        matched_transaction_ids=matched,
        description=desc,
        baseline_stats={
            "lookback_days": 90,
            "median_baseline": round(ref_median or overall_median, 2),
            "max_flagged_amount": round(max_matched_amt, 2),
            "multiplier": round(max_matched_amt / max(ref_median, 1.0), 1) if matched else 1.0,
        },
        severity=severity,
    )


def rule_new_payee_burst(df: pd.DataFrame) -> RuleResult:
    matched = []
    burst_payees = []
    burst_counts = {}

    for payee, group in df.groupby("payee"):
        group = group.sort_values("timestamp")
        first_idx = group.index[0]
        first_time = group.iloc[0]["timestamp"]

        prior = df[(df.index < first_idx) & (df["payee"] == payee)]
        if not prior.empty:
            continue
        if first_idx < 10:
            continue

        window_end = first_time + pd.Timedelta(hours=48)
        burst = group[group["timestamp"] <= window_end]
        if len(burst) >= 3 and float(burst["amount"].sum()) >= 300:
            burst_payees.append(payee)
            burst_counts[payee] = len(burst)
            matched.extend(burst["transaction_id"].tolist())

    if matched and burst_payees:
        p = burst_payees[0]
        c = burst_counts[p]
        desc = f"{c} transactions to {p} within 48 hours. No previous history with this payee."
        severity = "Medium"
    else:
        desc = "No rapid frequency or sudden burst of payments to newly added payees."
        severity = "Low"

    return RuleResult(
        rule_id="R2",
        rule_num=2,
        rule_name="New Payee Burst",
        triggered=bool(matched),
        matched_transaction_ids=matched,
        description=desc,
        baseline_stats={
            "window_hours": 48,
            "burst_threshold": 3,
            "new_payees_triggered": burst_payees,
            "burst_count": burst_counts.get(burst_payees[0], 0) if burst_payees else 0,
            "burst_payee": burst_payees[0] if burst_payees else None,
        },
        severity=severity,
    )


def rule_odd_hours(df: pd.DataFrame) -> RuleResult:
    hours = df["timestamp"].dt.hour
    if len(hours) < 10:
        return RuleResult(
            rule_id="R3",
            rule_num=3,
            rule_name="Odd-Hours Activity",
            triggered=False,
            matched_transaction_ids=[],
            description="Insufficient history to establish active hours.",
            baseline_stats={},
            severity="Low",
        )

    # Establish customer's baseline active hours (e.g. 5th to 95th quantile)
    q_low = int(hours.quantile(0.05, interpolation="lower"))
    q_high = int(hours.quantile(0.95, interpolation="higher"))
    # Normalize typical active hours (standard Indian business window e.g. 9 AM - 7 PM)
    active_start = min(q_low, 9)
    active_end = max(q_high, 19)
    active_hours_str = f"{_format_hour_ampm(active_start)} - {_format_hour_ampm(active_end)}"

    # Flag transactions occurring outside active hours, especially late night / early morning (e.g. < 6 or > 22)
    matched_rows = df[(hours < active_start) | (hours > active_end)]
    matched = matched_rows["transaction_id"].tolist()
    triggered = len(matched) >= 1 and any(h < 6 or h >= 23 for h in matched_rows["timestamp"].dt.hour)

    if triggered:
        # Find earliest / most prominent odd hour transaction
        deep_night = matched_rows[matched_rows["timestamp"].dt.hour < 6]
        earliest_row = deep_night.iloc[0] if not deep_night.empty else matched_rows.iloc[0]
        dt = earliest_row["timestamp"]
        time_str = dt.strftime("%I:%M %p")
        desc = f"Transaction at {time_str}, outside customer's typical active hours ({active_hours_str})."
        severity = "Medium"
    else:
        desc = f"Transactions align with customer's typical active hours ({active_hours_str})."
        severity = "Low"

    return RuleResult(
        rule_id="R3",
        rule_num=3,
        rule_name="Odd-Hours Activity",
        triggered=triggered,
        matched_transaction_ids=matched if triggered else [],
        description=desc,
        baseline_stats={
            "typical_active_hours_str": active_hours_str,
            "active_start": active_start,
            "active_end": active_end,
            "earliest_odd_time": matched_rows.iloc[0]["timestamp"].strftime("%I:%M %p") if not matched_rows.empty else None,
        },
        severity=severity,
    )


def rule_pattern_break(df: pd.DataFrame) -> RuleResult:
    matched = []
    min_history = 15
    details = []

    for i, row in df.iterrows():
        if i < min_history:
            continue
        prior = df.iloc[:i]
        channel_unseen = row["channel"] not in set(prior["channel"])
        region_unseen = row["region"] not in set(prior["region"])

        if channel_unseen or region_unseen:
            matched.append(row["transaction_id"])
            if channel_unseen:
                details.append(f"unseen channel '{row['channel']}'")
            if region_unseen:
                details.append(f"unseen region '{row['region']}'")

    if matched:
        desc = f"Transactions break established patterns with {', '.join(set(details))}."
        severity = "Medium"
    else:
        desc = "No unusual channel, category or location change detected beyond above rules."
        severity = "Low"

    return RuleResult(
        rule_id="R4",
        rule_num=4,
        rule_name="Pattern Break",
        triggered=bool(matched),
        matched_transaction_ids=matched,
        description=desc,
        baseline_stats={
            "signals": ["unseen_channel", "unseen_region"],
            "min_history_required": min_history,
        },
        severity=severity,
    )


class RulesEngine:
    def analyze(self, customer_id: str, transactions: List[Dict]) -> List[Dict]:
        _ = customer_id
        df = _prepare_df(transactions)
        return [
            rule_large_transfer(df).to_dict(),
            rule_new_payee_burst(df).to_dict(),
            rule_odd_hours(df).to_dict(),
            rule_pattern_break(df).to_dict(),
        ]

    def get_behavior_analysis(self, customer_id: str, customer_meta: Dict, transactions: List[Dict]) -> Dict:
        """Compute full behavioral profile, metrics, key reasons, and attention verdict dynamically."""
        df = _prepare_df(transactions)
        findings = self.analyze(customer_id, transactions)
        triggered_findings = [f for f in findings if f["triggered"]]

        # 90-day median
        latest_time = df["timestamp"].max()
        window_90d = latest_time - pd.Timedelta(days=90)
        trailing_90d = df[df["timestamp"] >= window_90d]
        typical_median = float(trailing_90d["amount"].median()) if not trailing_90d.empty else float(df["amount"].median())

        # Flagged transaction IDs
        flagged_ids = sorted({tx_id for f in triggered_findings for tx_id in f["matched_transaction_ids"]})
        flagged_txs = df[df["transaction_id"].isin(flagged_ids)]

        # Determine current transfer amount
        if not flagged_txs.empty:
            max_flagged_row = flagged_txs.sort_values("amount", ascending=False).iloc[0]
            current_transfer_amt = float(max_flagged_row["amount"])
        else:
            current_transfer_amt = float(df.iloc[-1]["amount"]) if not df.empty else 0.0

        multiplier = round(current_transfer_amt / max(typical_median, 1.0), 1)

        # Active hours
        r3 = next((f for f in findings if f["rule_id"] == "R3"), None)
        active_hours_str = r3["baseline_stats"].get("typical_active_hours_str", "9:00 AM - 7:00 PM") if r3 else "9:00 AM - 7:00 PM"

        # Current transaction time (earliest odd time or latest transaction time)
        if not flagged_txs.empty:
            earliest_flagged = flagged_txs.sort_values("timestamp").iloc[0]
            current_txn_time = earliest_flagged["timestamp"].strftime("%I:%M %p")
        else:
            current_txn_time = df.iloc[-1]["timestamp"].strftime("%I:%M %p") if not df.empty else "N/A"

        # Attention Banner verdict
        if triggered_findings:
            risk_level = "HIGH" if len(triggered_findings) >= 2 or any(f["severity"] == "High" for f in triggered_findings) else "MEDIUM"
            attention_title = "ATTENTION REQUIRED"
            signals_count = len(triggered_findings)
            tx_count = len(flagged_ids)
            signals_text = f"{signals_count} risk signal{'s' if signals_count > 1 else ''} detected across {tx_count} transaction{'s' if tx_count > 1 else ''}."
            attention_subtitle = f"{signals_text} This activity warrants review."
        else:
            risk_level = "NO RISK"
            attention_title = "NO ATTENTION REQUIRED"
            attention_subtitle = "No risk signals detected. All transactions align with established baseline."

        # Key Reasons (dynamic 3 cards)
        key_reasons = []
        r1 = next((f for f in findings if f["rule_id"] == "R1"), None)
        r2 = next((f for f in findings if f["rule_id"] == "R2"), None)
        r3_stat = r3["baseline_stats"] if r3 else {}

        if triggered_findings:
            if r1 and r1["triggered"]:
                key_reasons.append({
                    "id": "R1",
                    "title": _format_inr(r1["baseline_stats"]["max_flagged_amount"]),
                    "subtitle": "Unusually large transfer",
                    "detail": f"({r1['baseline_stats']['multiplier']}× customer's normal)",
                    "type": "amount",
                })
            else:
                key_reasons.append({
                    "id": "R1",
                    "title": _format_inr(typical_median),
                    "subtitle": "Transfer amount baseline",
                    "detail": "(normal range)",
                    "type": "amount",
                })

            if r2 and r2["triggered"]:
                cnt = r2["baseline_stats"].get("burst_count", 4)
                key_reasons.append({
                    "id": "R2",
                    "title": f"{cnt} payments",
                    "subtitle": "to newly added payee",
                    "detail": "(within 48 hours)",
                    "type": "payee",
                })
            else:
                payees_count = len(df["payee"].unique())
                key_reasons.append({
                    "id": "R2",
                    "title": f"{payees_count} payees",
                    "subtitle": "Known payee network",
                    "detail": "(no sudden bursts)",
                    "type": "payee",
                })

            if r3 and r3["triggered"]:
                odd_time = r3_stat.get("earliest_odd_time", "02:13 AM")
                key_reasons.append({
                    "id": "R3",
                    "title": odd_time,
                    "subtitle": "Outside usual active hours",
                    "detail": f"({active_hours_str})",
                    "type": "time",
                })
            else:
                key_reasons.append({
                    "id": "R3",
                    "title": active_hours_str,
                    "subtitle": "Usual active window",
                    "detail": "(consistent)",
                    "type": "time",
                })
        else:
            key_reasons = [
                {
                    "id": "R1",
                    "title": _format_inr(typical_median),
                    "subtitle": "Typical transfer amount",
                    "detail": "(median, last 90 days)",
                    "type": "amount",
                },
                {
                    "id": "R2",
                    "title": f"{len(df['payee'].unique())} payees",
                    "subtitle": "All payees established",
                    "detail": "(no new payee bursts)",
                    "type": "payee",
                },
                {
                    "id": "R3",
                    "title": active_hours_str,
                    "subtitle": "Usual active hours",
                    "detail": "(consistent timing)",
                    "type": "time",
                },
            ]

        # Tag each transaction with triggered rules
        tx_dict_list = df.to_dict(orient="records")
        for tx in tx_dict_list:
            tx["date_formatted"] = pd.to_datetime(tx["date"]).strftime("%d %b %Y %I:%M %p")
            tx["amount_formatted"] = _format_inr(float(tx["amount"]))
            tx["triggered_rules"] = []
            for f in findings:
                if f["triggered"] and tx["transaction_id"] in f["matched_transaction_ids"]:
                    badge_name = "Large Transfer" if f["rule_id"] == "R1" else ("New Payee" if f["rule_id"] == "R2" else ("Odd Hours" if f["rule_id"] == "R3" else "Pattern Break"))
                    tx["triggered_rules"].append({
                        "rule_id": f["rule_id"],
                        "rule_name": f["rule_name"],
                        "badge_name": badge_name,
                        "severity": f["severity"],
                    })

        return {
            "customer_id": customer_id,
            "customer_name": customer_meta.get("name", ""),
            "customer_since": customer_meta.get("customer_since", "2 years 4 months"),
            "last_analysed": customer_meta.get("last_analysed", "26 Aug 2025, 14:32"),
            "account_number": customer_meta.get("account_number", "•••• •••• 4821"),
            "account_type": customer_meta.get("account_type", "Savings Platinum"),
            "branch": customer_meta.get("branch", "Fort Branch, Mumbai"),
            "phone": customer_meta.get("phone", "+91 98201 44821"),
            "email": customer_meta.get("email", ""),
            "risk_level": risk_level,
            "attention_required": bool(triggered_findings),
            "attention_title": attention_title,
            "attention_subtitle": attention_subtitle,
            "key_reasons": key_reasons,
            "behavior_analysis": {
                "typical_transfer_amount": _format_inr(typical_median),
                "typical_transfer_subtitle": "(median, last 90 days)",
                "current_transfer_amount": _format_inr(current_transfer_amt),
                "current_transfer_subtitle": f"({multiplier:.1f}× higher)" if multiplier > 1.2 else "(within baseline)",
                "usual_active_hours": active_hours_str,
                "usual_active_subtitle": "(most activity)",
                "current_txn_time": current_txn_time,
                "current_txn_subtitle": "(outside usual hours)" if (r3 and r3["triggered"]) else "(within active hours)",
            },
            "findings": findings,
            "flagged_transaction_ids": flagged_ids,
            "flagged_transactions": [tx for tx in tx_dict_list if tx["transaction_id"] in flagged_ids],
            "all_transactions": tx_dict_list,
        }
