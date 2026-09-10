
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