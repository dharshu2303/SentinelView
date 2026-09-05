import csv
import json
import random
from datetime import datetime, timedelta

random.seed(42)

CUSTOMERS = [
    {"id": "C001", "name": "Avery Coleman", "profile": "clean_routine_1"},
    {"id": "C002", "name": "Mina Farouk", "profile": "clean_routine_2"},
    {"id": "C003", "name": "Jonas Patel", "profile": "large_transfer_only"},
    {"id": "C004", "name": "Elena Rossi", "profile": "new_payee_burst_only"},
    {"id": "C005", "name": "Noah Whitaker", "profile": "odd_hours_only"},
    {"id": "C006", "name": "Priya Sen", "profile": "pattern_break_only"},
    {"id": "C007", "name": "Lucas Meyer", "profile": "multi_rule"},
]

PAYEES = ["Metro Grocery", "City Transit", "North Fuel", "River Pharmacy", "Cloud Bistro", "Orbit Telecom", "Luma Utilities", "Bright Fitness"]
CHANNELS = ["card", "ach", "online", "wire"]
CATEGORIES = ["groceries", "transport", "fuel", "health", "dining", "utilities", "fitness", "retail"]
REGIONS = ["home_region", "home_region", "home_region", "home_region", "nearby_region"]


def random_time(hour_low=8, hour_high=20):
    h = random.randint(hour_low, hour_high)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return h, m, s


def generate_base_transactions(customer_id, start_date, count=70, amount_low=8, amount_high=140):
    txs = []
    for i in range(count):
        day_offset = random.randint(0, 150)
        dt = start_date + timedelta(days=day_offset)
        h, m, s = random_time()
        dt = dt.replace(hour=h, minute=m, second=s)

        idx = random.randint(0, len(PAYEES) - 1)
        amount = round(random.uniform(amount_low, amount_high), 2)
        txs.append({
            "transaction_id": f"{customer_id}-T{i+1:03d}",
            "customer_id": customer_id,
            "date": dt.isoformat(),
            "description": f"{CATEGORIES[idx].title()} purchase at {PAYEES[idx]}",
            "payee": PAYEES[idx],
            "amount": amount,
            "channel": random.choice(["card", "ach", "online"]),
            "category": CATEGORIES[idx],
            "region": random.choice(REGIONS),
        })
    txs.sort(key=lambda x: x["date"])
    return txs


def insert_transaction(txs, tx):
    txs.append(tx)
    txs.sort(key=lambda x: x["date"])


def apply_profile(profile, txs, customer_id):
    max_n = len(txs) + 1

    if profile == "large_transfer_only":
        dt = datetime.fromisoformat(txs[-1]["date"]) - timedelta(days=1)
        tx = {
            "transaction_id": f"{customer_id}-T{max_n:03d}",
            "customer_id": customer_id,
            "date": dt.replace(hour=14, minute=15, second=0).isoformat(),
            "description": "One-time escrow transfer",
            "payee": "Summit Escrow Services",
            "amount": 2400.00,
            "channel": "ach",
            "category": "housing",
            "region": "home_region",
        }
        insert_transaction(txs, tx)

    elif profile == "new_payee_burst_only":
        burst_start = datetime.fromisoformat(txs[-1]["date"]) - timedelta(days=2)
        for i in range(3):
            dt = burst_start + timedelta(hours=22 * i)
            tx = {
                "transaction_id": f"{customer_id}-T{max_n+i:03d}",
                "customer_id": customer_id,
                "date": dt.replace(hour=11 + i, minute=5, second=0).isoformat(),
                "description": "Contractor payment installment",
                "payee": "Northline Contractors",
                "amount": round(165 + i * 11.5, 2),
                "channel": "ach",
                "category": "home_services",
                "region": "home_region",
            }
            insert_transaction(txs, tx)

    elif profile == "odd_hours_only":
        odd_base = datetime.fromisoformat(txs[-1]["date"]) - timedelta(days=4)
        for i in range(4):
            dt = odd_base + timedelta(days=i)
            tx = {
                "transaction_id": f"{customer_id}-T{max_n+i:03d}",
                "customer_id": customer_id,
                "date": dt.replace(hour=2, minute=10 + i, second=0).isoformat(),
                "description": "Late-night online subscription",
                "payee": "StreamGrid Media",
                "amount": round(48 + i * 2.5, 2),
                "channel": "online",
                "category": "entertainment",
                "region": "home_region",
            }
            insert_transaction(txs, tx)

    elif profile == "pattern_break_only":
        dt = datetime.fromisoformat(txs[-1]["date"]) - timedelta(days=3)
        tx = {
            "transaction_id": f"{customer_id}-T{max_n:03d}",
            "customer_id": customer_id,
            "date": dt.replace(hour=13, minute=40, second=0).isoformat(),
            "description": "International luxury retail purchase",
            "payee": "Velour Luxe Global",
            "amount": 310.00,
            "channel": "wire",
            "category": "luxury_retail",
            "region": "overseas_region",
        }
        insert_transaction(txs, tx)

    elif profile == "multi_rule":
        dt = datetime.fromisoformat(txs[-1]["date"]) - timedelta(days=1)
        tx_large = {
            "transaction_id": f"{customer_id}-T{max_n:03d}",
            "customer_id": customer_id,
            "date": dt.replace(hour=1, minute=15, second=0).isoformat(),
            "description": "Urgent treasury movement",
            "payee": "Helios Treasury Desk",
            "amount": 3200.00,
            "channel": "wire",
            "category": "treasury",
            "region": "overseas_region",
        }
        insert_transaction(txs, tx_large)

        burst_start = dt - timedelta(hours=40)
        for i in range(3):
            bdt = burst_start + timedelta(hours=20 * i)
            tx = {
                "transaction_id": f"{customer_id}-T{max_n+1+i:03d}",
                "customer_id": customer_id,
                "date": bdt.replace(hour=3, minute=20 + i, second=0).isoformat(),
                "description": "Rapid vendor settlement",
                "payee": "QuickSpan Logistics",
                "amount": round(190 + i * 15, 2),
                "channel": "wire",
                "category": "logistics",
                "region": "overseas_region",
            }
            insert_transaction(txs, tx)

    return txs


def main():
    start = datetime(2026, 1, 1, 0, 0, 0)
    all_txs = []
    summary = []

    for cust in CUSTOMERS:
        txs = generate_base_transactions(cust["id"], start)
        txs = apply_profile(cust["profile"], txs, cust["id"])
        all_txs.extend(txs)
        summary.append({
            "id": cust["id"],
            "name": cust["name"],
            "profile": cust["profile"],
            "transaction_count": len(txs),
            "date_start": txs[0]["date"],
            "date_end": txs[-1]["date"],
        })

    with open("data/customers.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    fieldnames = ["transaction_id", "customer_id", "date", "description", "payee", "amount", "channel", "category", "region"]
    with open("data/transactions.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tx in sorted(all_txs, key=lambda x: (x["customer_id"], x["date"])):
            writer.writerow(tx)


if __name__ == "__main__":
    main()
