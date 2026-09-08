TRACK_ID=PS06

# SentinelView - Transaction Risk Investigation Assistant 🛡️

**SentinelView** is an intelligent, AI-powered investigation assistant built for a bank's fraud desk. It analyzes customer transaction histories (covering several months of activity) against deterministic risk rules, detects behavioral anomalies, and generates structured compliance investigation dossiers using Google Gemini AI.

---

## 🌐 Live Deployment
* **Live Demo:** [https://sentinelview-ai.vercel.app](https://sentinelview-ai.vercel.app)
* **Alternative Domain:** [https://sentinelview-app.vercel.app](https://sentinelview-app.vercel.app)

---

## ✨ Key Features & Capabilities

* **Deterministic Risk Engine:** Scores customer activity on the fly against 4 core banking surveillance rules:
  1. **Unusually Large Transfers (R1):** Detects single transfers breaking 90-day customer baseline medians(2.5x times).
  2. **New Payee Bursts (R2):** Identifies rapid-fire consecutive payments to newly added accounts within short time windows.
  3. **Odd-Hours Activity (R3):** Flags transfers occurring outside the customer's established active hours (e.g. 02:13 AM).
  4. **Pattern Break Behavior (R4):** Catches anomalous channels, rapid velocity shifts, or regional breaks.
* **Google Gemini AI Narrator:** Uses Gemini (`gemini-2.0-flash` / `gemini-embedding-001`) to generate grounded executive summaries and actionable investigator checklists directly tied to transaction row IDs. Fallbacks gracefully if offline or unconfigured.
* **24-Hour Behavioral Timeline:** Plots transaction activity across a 24-hour cycle with green business hour bands and pulsing red anomaly markers.
* **Interactive Transaction Modal:** "View All Transactions" modal dialog allowing analysts to toggle between **All** and **Flagged** transactions with instant filtering and search.
* **Full Multi-Page PDF & Word Export:** Generates complete, multi-page compliance dossiers with unclipped transaction ledgers ready for audit review.
* **Light / Dark Mode:** Toggleable visual themes (White/Light mode default).
* **Instant Customer Switching:** Pre-warmed server and browser caching for 0ms transition between customer dossiers.
* **Investigating Officer:** Preset to **Dharshini (Fraud Desk Analyst #4029)**.

---

## 📁 Repository Structure

```
.
├── app.py                      # Flask API server & static asset handler
├── requirements.txt            # Python dependencies (Flask, pandas, google-genai, etc.)
├── vercel.json                 # Vercel deployment configuration
├── api/
│   └── index.py                # Serverless entrypoint for Vercel Python runtime
├── src/
│   ├── rules_engine.py         # Deterministic risk rule evaluation engine
│   ├── gemini_narrator.py      # Gemini AI narrative generator & fallback logic
│   └── data_loader.py          # Data ingestion parser for JSON and CSV records
├── data/
│   ├── customers.json          # Customer metadata, accounts & profiles
│   └── transactions.csv        # 741+ raw transaction records
├── frontend/
│   └── dist/
│       ├── index.html          # Main application single-page interface
│       ├── style.css           # Modern CSS design system & print styles
│       └── app.js              # Client application state & UI interactions
└── tests/
    └── test_api.py             # Automated PyTest test suite
```

---

## 🚀 Local Quickstart

### Prerequisites
* Python 3.10+
* Git

### Installation & Running

```bash
# 1. Clone the repository
git clone https://github.com/dharshu2303/SentinelView.git
cd SentinelView

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Configure Gemini API Key
copy .env.example .env
# Open .env and add: GEMINI_API_KEY=your_api_key_here

# 4. Start the application server
python app.py
```

Once running, open your browser and navigate to:
`http://localhost:8000`

---

## 🧪 Testing

Run the automated PyTest suite to verify risk calculations and API endpoints:

```bash
pytest tests/test_api.py
```

---

## 📡 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/customers` | GET | List all customer profiles |
| `GET /api/customers/{id}/transactions` | GET | Get raw transactions for a customer |
| `POST /api/customers/{id}/investigate` | POST | Trigger full risk analysis & Gemini AI report |
| `GET /api/dashboard/stats` | GET | Fetch dashboard summary metrics & alert queue |
| `GET /api/alerts` | GET | List active risk alerts |
| `GET /api/reports` | GET | Fetch investigation dossier archive |

---

## ⚖️ Regulatory Notice
This project is an investigation assistant designed to flag deviations against customer baselines. It provides grounded evidence and behavioral narratives to assist human analysts. It never automatically declares fraud—final adjudication rests with designated compliance authorities.
