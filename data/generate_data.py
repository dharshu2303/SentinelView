import csv
import json
import random
from datetime import datetime, timedelta

random.seed(42)

CUSTOMERS = [
    {
        "id": "CUST001",
        "name": "Priya Sharma",
        "profile": "multi_rule",
        "customer_since": "2 years 4 months",
        "last_analysed": "26 Aug 2025, 14:32",
        "account_number": "•••• •••• 4821",
        "account_type": "Savings Platinum",
        "branch": "Fort Branch, Mumbai",
        "phone": "+91 98201 44821",
        "email": "priya.sharma@example.com",
    },
    {
        "id": "CUST002",
        "name": "Rahul Mehta",
        "profile": "clean_routine_1",
        "customer_since": "3 years 1 month",
        "last_analysed": "26 Aug 2025, 12:15",
        "account_number": "•••• •••• 3912",
        "account_type": "Salary Account",
        "branch": "BKC, Mumbai",
        "phone": "+91 98334 13912",
        "email": "rahul.mehta@example.com",
    },
    {
        "id": "CUST003",
        "name": "Ananya Iyer",
        "profile": "new_payee_burst_only",
        "customer_since": "1 year 8 months",
        "last_analysed": "26 Aug 2025, 11:45",
        "account_number": "•••• •••• 7741",
        "account_type": "Current Business",
        "branch": "Koramangala, Bengaluru",
        "phone": "+91 97412 87741",
        "email": "ananya.iyer@example.com",
    },
    {
        "id": "CUST004",
        "name": "Karthik R",
        "profile": "clean_routine_2",
        "customer_since": "4 years 2 months",
        "last_analysed": "26 Aug 2025, 10:20",
        "account_number": "•••• •••• 8219",
        "account_type": "Savings Classic",
        "branch": "T. Nagar, Chennai",
        "phone": "+91 94440 28219",
        "email": "karthik.r@example.com",
    },
    {
        "id": "CUST005",
        "name": "Sneha Verma",
        "profile": "clean_routine_3",
        "customer_since": "11 months",
        "last_analysed": "26 Aug 2025, 09:50",
        "account_number": "•••• •••• 6104",
        "account_type": "Savings Gold",
        "branch": "Connaught Place, Delhi",
        "phone": "+91 98112 56104",
        "email": "sneha.verma@example.com",
    },
    {
        "id": "CUST006",
        "name": "Vikram Malhotra",
        "profile": "pattern_break_only",
        "customer_since": "5 years",
        "last_analysed": "25 Aug 2025, 18:10",
        "account_number": "•••• •••• 9032",
        "account_type": "NRI Premier",
        "branch": "Sector 17, Chandigarh",
        "phone": "+91 98765 19032",
        "email": "vikram.m@example.com",
    },
    {
        "id": "CUST007",
        "name": "Neha Gupta",
        "profile": "odd_hours_only",
        "customer_since": "2 years",
        "last_analysed": "25 Aug 2025, 16:30",
        "account_number": "•••• •••• 5519",
        "account_type": "Savings Platinum",
        "branch": "MG Road, Pune",
        "phone": "+91 98220 35519",
        "email": "neha.gupta@example.com",
    },
    {
        "id": "CUST008",
        "name": "Arjun Singhania",
        "profile": "large_and_odd",
        "customer_since": "3 years 6 months",
        "last_analysed": "26 Aug 2025, 15:10",
        "account_number": "•••• •••• 1184",
        "account_type": "Current Business",
        "branch": "Cyber City, Gurugram",
        "phone": "+91 99100 81184",
        "email": "arjun.singhania@example.com",
    },
    {
        "id": "CUST009",
        "name": "Pooja Nair",
        "profile": "clean_routine_4",
        "customer_since": "2 years 9 months",
        "last_analysed": "26 Aug 2025, 08:30",
        "account_number": "•••• •••• 2490",
        "account_type": "Salary Account",
        "branch": "Whitefield, Bengaluru",
        "phone": "+91 96111 92490",
        "email": "pooja.nair@example.com",
    },
    {
        "id": "CUST010",
        "name": "Aditya Joshi",
        "profile": "new_payee_burst_only",
        "customer_since": "1 year 2 months",
        "last_analysed": "25 Aug 2025, 14:15",
        "account_number": "•••• •••• 6723",
        "account_type": "Savings Classic",
        "branch": "Deccan, Pune",
        "phone": "+91 98900 16723",
        "email": "aditya.joshi@example.com",
    },
    {
        "id": "CUST011",
        "name": "Ritu Deshmukh",
        "profile": "clean_routine_5",
        "customer_since": "4 years",
        "last_analysed": "26 Aug 2025, 09:10",
        "account_number": "•••• •••• 4157",
        "account_type": "Savings Classic",
        "branch": "Dharampeth, Nagpur",
        "phone": "+91 97640 24157",
        "email": "ritu.deshmukh@example.com",
    },
    {
        "id": "CUST012",
        "name": "Manish Choudhury",
        "profile": "multi_rule_2",
        "customer_since": "3 years",
        "last_analysed": "26 Aug 2025, 16:40",
        "account_number": "•••• •••• 8831",
        "account_type": "Current Business",
        "branch": "Park Street, Kolkata",
        "phone": "+91 98300 48831",
        "email": "manish.c@example.com",
    },
]

INDIAN_PAYEES = [
    "Kirana Supermarket",
    "Swiggy Foods",
    "Reliance Digital",
    "Tata Power",
    "Apollo Pharmacy",
    "Indian Oil Bunk",
    "Flipkart Online",
    "Sharma Contractors",
    "Zomato Orders",
    "BookMyShow",
    "D-Mart Retail",
    "Airtel Broadband",
]

BASE_CHANNELS = ["UPI", "IMPS", "Net Banking", "Debit Card"]
CATEGORIES = ["groceries", "food_dining", "electronics", "utilities", "healthcare", "fuel", "shopping", "services"]
REGIONS = ["Mumbai_Metro", "Mumbai_Metro", "Mumbai_Metro", "Pune_Suburban"]


def random_business_time(start_hour=9, end_hour=19):
    h = random.randint(start_hour, end_hour - 1)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return h, m, s


def generate_baseline_transactions(customer_id, start_date, end_date, count=60, median_target=58000):
    txs = []
    total_days = (end_date - start_date).days

    for i in range(count):
        day_offset = random.randint(0, max(1, total_days - 3))
        dt = start_date + timedelta(days=day_offset)
        h, m, s = random_business_time(9, 19)
        dt = dt.replace(hour=h, minute=m, second=s)

        idx = random.randint(0, len(INDIAN_PAYEES) - 1)
        amount = round(random.gauss(median_target, 10000), 2)
        amount = max(500.0, min(amount, median_target * 1.6))

        channel = BASE_CHANNELS[i % len(BASE_CHANNELS)]
        cat = CATEGORIES[idx % len(CATEGORIES)]
        payee = INDIAN_PAYEES[idx]
        region = REGIONS[i % len(REGIONS)] if i < 10 else random.choice(REGIONS)

        txs.append({
            "transaction_id": f"TXN{1000 + len(txs):04d}",
            "customer_id": customer_id,
            "date": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": f"{cat.replace('_', ' ').title()} at {payee}",
            "payee": payee,
            "amount": amount,
            "channel": channel,
            "category": cat,
            "region": region,
        })

    amounts = [t["amount"] for t in txs]
    amounts.sort()
    mid_idx = len(amounts) // 2
    txs[mid_idx]["amount"] = float(median_target)

    txs.sort(key=lambda x: x["date"])
    for idx, tx in enumerate(txs):
        tx["transaction_id"] = f"{customer_id}-T{idx+1:03d}"
    return txs


def apply_customer_profile(profile, txs, customer_id):
    if profile == "multi_rule":
        # Priya Sharma (CUST001) - matches screenshot exactly
        flagged_txs = [
            {
                "transaction_id": "TXN1042",
                "customer_id": customer_id,
                "date": "2025-08-26T02:13:00",
                "description": "NEFT Transfer",
                "payee": "ABC Traders",
                "amount": 240000.00,
                "channel": "IMPS",
                "category": "services",
                "region": "Mumbai_Metro",
            },
            {
                "transaction_id": "TXN1043",
                "customer_id": customer_id,
                "date": "2025-08-26T02:21:00",
                "description": "UPI Payment",
                "payee": "ABC Traders",
                "amount": 35000.00,
                "channel": "UPI",
                "category": "services",
                "region": "Mumbai_Metro",
            },
            {
                "transaction_id": "TXN1044",
                "customer_id": customer_id,
                "date": "2025-08-26T03:02:00",
                "description": "UPI Payment",
                "payee": "ABC Traders",
                "amount": 40000.00,
                "channel": "UPI",
                "category": "services",
                "region": "Mumbai_Metro",
            },
            {
                "transaction_id": "TXN1045",
                "customer_id": customer_id,
                "date": "2025-08-26T09:14:00",
                "description": "NEFT Transfer",
                "payee": "ABC Traders",
                "amount": 25000.00,
                "channel": "Net Banking",
                "category": "services",
                "region": "Mumbai_Metro",
            },
            {
                "transaction_id": "TXN1046",
                "customer_id": customer_id,
                "date": "2025-08-26T11:32:00",
                "description": "UPI Payment",
                "payee": "ABC Traders",
                "amount": 15000.00,
                "channel": "UPI",
                "category": "services",
                "region": "Mumbai_Metro",
            },
        ]
        txs.extend(flagged_txs)

    elif profile == "new_payee_burst_only":
        # Ananya Iyer (CUST003) & Aditya Joshi (CUST010)
        last_date = datetime.fromisoformat(txs[-1]["date"])
        burst_base = (last_date + timedelta(days=1)).replace(hour=11, minute=15, second=0)
        payee_name = "Zenith Logistics" if customer_id == "CUST003" else "Maharashtra Electricals"
        burst_txs = [
            {
                "transaction_id": f"{customer_id}-B01",
                "customer_id": customer_id,
                "date": burst_base.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "Vendor Advance Payment",
                "payee": payee_name,
                "amount": 42000.00,
                "channel": "UPI",
                "category": "services",
                "region": "Mumbai_Metro",
            },
            {
                "transaction_id": f"{customer_id}-B02",
                "customer_id": customer_id,
                "date": (burst_base + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "Freight Clearance",
                "payee": payee_name,
                "amount": 38000.00,
                "channel": "UPI",
                "category": "services",
                "region": "Mumbai_Metro",
            },
            {
                "transaction_id": f"{customer_id}-B03",
                "customer_id": customer_id,
                "date": (burst_base + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "Warehouse Deposit",
                "payee": payee_name,
                "amount": 45000.00,
                "channel": "IMPS",
                "category": "services",
                "region": "Mumbai_Metro",
            },
        ]
        txs.extend(burst_txs)

    elif profile == "odd_hours_only":
        # Neha Gupta (CUST007) - odd-hours activity
        last_date = datetime.fromisoformat(txs[-1]["date"])
        for i in range(3):
            dt = (last_date + timedelta(days=i+1)).replace(hour=2, minute=15 + i * 10, second=0)
            txs.append({
                "transaction_id": f"{customer_id}-OH{i+1:02d}",
                "customer_id": customer_id,
                "date": dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "Late Night Online Payment",
                "payee": "Kirana Supermarket",
                "amount": round(4500.00 + i * 800, 2),
                "channel": "UPI",
                "category": "groceries",
                "region": "Mumbai_Metro",
            })

    elif profile == "pattern_break_only":
        # Vikram Malhotra (CUST006) - pattern break
        last_date = datetime.fromisoformat(txs[-1]["date"])
        dt = (last_date + timedelta(days=1)).replace(hour=14, minute=30, second=0)
        txs.append({
            "transaction_id": f"{customer_id}-PB01",
            "customer_id": customer_id,
            "date": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": "Foreign Exchange Remittance",
            "payee": "Reliance Digital",
            "amount": 48000.00,
            "channel": "International Wire",
            "category": "electronics",
            "region": "Overseas_Europe",
        })

    elif profile == "large_and_odd":
        # Arjun Singhania (CUST008) - High Risk
        last_date = datetime.fromisoformat(txs[-1]["date"])
        dt = (last_date + timedelta(days=1)).replace(hour=1, minute=45, second=0)
        txs.append({
            "transaction_id": f"{customer_id}-LO01",
            "customer_id": customer_id,
            "date": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": "Off-Hour Bulk Vendor Clearing",
            "payee": "Apex Steel Works",
            "amount": 380000.00,
            "channel": "IMPS",
            "category": "commercial",
            "region": "Mumbai_Metro",
        })
        dt2 = (last_date + timedelta(days=1)).replace(hour=2, minute=10, second=0)
        txs.append({
            "transaction_id": f"{customer_id}-LO02",
            "customer_id": customer_id,
            "date": dt2.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": "Urgent Material Surcharge",
            "payee": "Apex Steel Works",
            "amount": 75000.00,
            "channel": "IMPS",
            "category": "commercial",
            "region": "Mumbai_Metro",
        })

    elif profile == "multi_rule_2":
        # Manish Choudhury (CUST012) - High Risk
        last_date = datetime.fromisoformat(txs[-1]["date"])
        dt = (last_date + timedelta(days=1)).replace(hour=2, minute=30, second=0)
        txs.append({
            "transaction_id": f"{customer_id}-MR01",
            "customer_id": customer_id,
            "date": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": "High Value Equipment Liquidation",
            "payee": "Eastern Industrial Ltd",
            "amount": 410000.00,
            "channel": "IMPS",
            "category": "commercial",
            "region": "Mumbai_Metro",
        })
        for i in range(3):
            txs.append({
                "transaction_id": f"{customer_id}-MR{i+2:02d}",
                "customer_id": customer_id,
                "date": (dt + timedelta(hours=3 * (i + 1))).strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "Expedited Delivery Fee",
                "payee": "Eastern Industrial Ltd",
                "amount": 32000.00 + i * 5000,
                "channel": "UPI",
                "category": "commercial",
                "region": "Mumbai_Metro",
            })

    txs.sort(key=lambda x: x["date"])
    return txs


def main():
    start_date = datetime(2025, 5, 20, 0, 0, 0)
    end_date = datetime(2025, 8, 25, 0, 0, 0)

    all_txs = []
    summary = []

    for cust in CUSTOMERS:
        median_val = 58000 if cust["id"] == "CUST001" else random.choice([28000, 35000, 42000, 52000])
        txs = generate_baseline_transactions(cust["id"], start_date, end_date, count=60, median_target=median_val)
        txs = apply_customer_profile(cust["profile"], txs, cust["id"])
        all_txs.extend(txs)

        summary.append({
            "id": cust["id"],
            "name": cust["name"],
            "profile": cust["profile"],
            "customer_since": cust["customer_since"],
            "last_analysed": cust["last_analysed"],
            "account_number": cust.get("account_number", "•••• •••• 0000"),
            "account_type": cust.get("account_type", "Savings Classic"),
            "branch": cust.get("branch", "Main Branch"),
            "phone": cust.get("phone", "+91 98000 00000"),
            "email": cust.get("email", ""),
            "transaction_count": len(txs),
            "date_start": txs[0]["date"],
            "date_end": txs[-1]["date"],
        })

    with open("data/customers.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    fieldnames = [
        "transaction_id",
        "customer_id",
        "date",
        "description",
        "payee",
        "amount",
        "channel",
        "category",
        "region",
    ]
    with open("data/transactions.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tx in sorted(all_txs, key=lambda x: (x["customer_id"], x["date"])):
            writer.writerow(tx)

    print(f"Generated {len(all_txs)} transactions across {len(summary)} customers.")


if __name__ == "__main__":
    main()
