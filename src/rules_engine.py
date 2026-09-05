from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    rule_name: str
    triggered: bool
    matched_transaction_ids: List[str]
    baseline_stats: Dict
    severity: str

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "triggered": self.triggered,
            "matched_transaction_ids": self.matched_transaction_ids,
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


def rule_large_transfer(df: pd.DataFrame) -> RuleResult:
    matched = []
    baseline_medians = []

    for i, row in df.iterrows():
        window_start = row["timestamp"] - pd.Timedelta(days=90)
        trailing = df[(df["timestamp"] < row["timestamp"]) & (df["timestamp"] >= window_start)]
        if len(trailing) < 15:
            continue
        median_amount = float(trailing["amount"].median())
        threshold = max(median_amount * 3.0, 750.0)
        baseline_medians.append(median_amount)
        if float(row["amount"]) > threshold:
            matched.append(row["transaction_id"])

    return RuleResult(
        rule_id="R1",
        rule_name="Unusually large transfers",
        triggered=bool(matched),
        matched_transaction_ids=matched,
        baseline_stats={
            "lookback_days": 90,
            "threshold_formula": "max(3x trailing_90d_median, 750)",
            "observed_trailing_median_mean": round(sum(baseline_medians) / len(baseline_medians), 2) if baseline_medians else 0,
        },
        severity="high" if matched else "none",
    )


def rule_new_payee_burst(df: pd.DataFrame) -> RuleResult:
    matched = []
    burst_payees = []

    for payee, group in df.groupby("payee"):
        group = group.sort_values("timestamp")
        first_idx = group.index[0]
        first_time = group.iloc[0]["timestamp"]

        prior = df[(df.index < first_idx) & (df["payee"] == payee)]
        if not prior.empty:
            continue
        if first_idx < 30:
            continue

        window_end = first_time + pd.Timedelta(hours=72)
        burst = group[group["timestamp"] <= window_end]
        if len(burst) >= 3 and float(burst["amount"].sum()) >= 300:
            burst_payees.append(payee)
            matched.extend(burst["transaction_id"].tolist())

    return RuleResult(
        rule_id="R2",
        rule_name="Burst of payments to newly added payee",
        triggered=bool(matched),
        matched_transaction_ids=matched,
        baseline_stats={
            "window_hours": 72,
            "burst_threshold": 3,
            "new_payees_triggered": burst_payees,
        },
        severity="medium" if matched else "none",
    )


def rule_odd_hours(df: pd.DataFrame) -> RuleResult:
    hours = df["timestamp"].dt.hour
    q_low = int(hours.quantile(0.05, interpolation="lower"))
    q_high = int(hours.quantile(0.95, interpolation="higher"))
    typical_hours = list(range(q_low, q_high + 1))
    matched_df = df[(hours < q_low) | (hours > q_high)]
    matched = matched_df["transaction_id"].tolist()
    triggered = len(matched) >= 3

    return RuleResult(
        rule_id="R3",
        rule_name="Odd-hours activity",
        triggered=triggered,
        matched_transaction_ids=matched if triggered else [],
        baseline_stats={
            "typical_hours": typical_hours,
            "quantile_low": 0.05,
            "quantile_high": 0.95,
            "minimum_outlier_count": 3,
        },
        severity="medium" if triggered else "none",
    )


def rule_pattern_break(df: pd.DataFrame) -> RuleResult:
    matched = []
    min_history = 20

    for i, row in df.iterrows():
        if i < min_history:
            continue
        prior = df.iloc[:i]
        channel_unseen = row["channel"] not in set(prior["channel"])
        region_unseen = row["region"] not in set(prior["region"])

        if channel_unseen or region_unseen:
            matched.append(row["transaction_id"])

    return RuleResult(
        rule_id="R4",
        rule_name="Pattern-break transactions",
        triggered=bool(matched),
        matched_transaction_ids=matched,
        baseline_stats={
            "signals": ["unseen_channel", "unseen_region"],
            "min_history_required": min_history,
        },
        severity="medium" if matched else "none",
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
