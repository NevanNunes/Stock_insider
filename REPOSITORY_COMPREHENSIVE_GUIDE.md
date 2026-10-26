# Cloud-Based Market Surveillance & Insider-Trading Anomaly Detection System
## Complete System Context, Architecture, Dataset, Local Execution, and AWS Deployment Guide

---

## 1. Executive Summary & Purpose

The **Stock Insider / Market Surveillance System** is an end-to-end, full-stack cloud computing prototype that simulates how modern financial regulators (such as SEBI, SEC, or FINRA) and stock exchange compliance divisions monitor real-time equity trading for abnormal patterns and potential insider trading.

### Key Mission & Philosophy
- **Statistical Surveillance, Not Legal Proof**: The system explicitly detects **statistical anomalies and behavioral outliers** against established trader baselines. Alerts state: *"Unusual trading activity detected. Further human review recommended."* It flags suspicious behavior for compliance officers to inspect rather than asserting legal guilt.
- **100% Synthetic Data**: The system operates purely on generated synthetic data (50 trader accounts, 20 fictional symbols, 92 trading days, 20,500 total trades, 150 market events). No real individuals, real corporate entities, proprietary market feeds, or real funds are involved.
- **Dual-Role Live Viva / Demonstration Concept**: Designed for real-world academic presentations across two physical devices:
  1. **Trader Portal (Laptop 1)**: Allows submitting normal trades, custom manual trades (with real-time parameter tweaking), or 1-click synthetic suspicious trades.
  2. **Surveillance Admin Dashboard (Laptop 2)**: Receives instantaneous on-screen red toast alerts via WebSockets without page reload, concurrently triggers an AWS SNS alert (email/SMS), enables drill-down mathematical explanations, and generates downloadable compliance PDF reports stored to Amazon S3.
- **Zero-Cloud-Cost Local Mode vs. Full AWS Production**: The codebase features automatic cloud fallbacks. Running locally uses SQLite, in-process queues, console notifications, and local filesystem reports. When environment variables point to AWS services, it seamlessly activates Amazon SQS, SNS, S3, and RDS PostgreSQL without code modifications.

---

## 2. System Architecture & High-Level Data Flow

```
                               ┌────────────────────────────────────────────────────────┐
                               │                    AWS Cloud (Production)              │
                               │                                                        │
 ┌──────────────────────┐      │   ┌───────────────┐        ┌───────────────────────┐   │
 │   Laptop 1: Trader   │──────┼──▶│   ALB / Port  │───────▶│    FastAPI Backend    │   │
 │   (Terminal UI)      │      │   │  8000 (Proxy) │        │   (EC2 / Auto Scaling)│   │
 └──────────────────────┘      │   └───────────────┘        └───────────┬───────────┘   │
                               │                                        │               │
 ┌──────────────────────┐      │   ┌───────────────┐                    ▼               │
 │   Laptop 2: Admin    │◀─────┼───│   WebSocket   │         ┌──────────────────────┐   │
 │   (Surveillance UI)  │      │   │  /ws/alerts   │         │  Async Message Queue │   │
 └──────────────────────┘      │   └───────────────┘         │  (In-Memory / SQS)   │   │
                               │                                        │               │
                               │                                        ▼               │
                               │                             ┌──────────────────────┐   │
                               │                             │ Background Worker &  │   │
                               │                             │   Anomaly Engine     │   │
                               │                             │  - Z-Score (Stat)    │   │
                               │                             │  - Isolation Forest  │   │
                               │                             │  - Contextual Rules  │   │
                               │                             └──────────┬───────────┘   │
                               │                                        │               │
                               │              ┌─────────────────────────┼────────────────────────┐
                               │              ▼                         ▼                        ▼
                               │   ┌─────────────────────┐   ┌─────────────────────┐  ┌─────────────────────┐
                               │   │   Database Layer    │   │  Alert Notification │  │   Report Storage    │
                               │   │ SQLite (Local) /    │   │ Console (Local) /   │  │ Local Disk /        │
                               │   │ RDS PostgreSQL      │   │ Amazon SNS (Email)  │  │ Amazon S3 Bucket    │
                               │   └─────────────────────┘   └─────────────────────┘  └─────────────────────┘
                               └────────────────────────────────────────────────────────┘
```

### End-to-End Processing Flow
1. **Trade Ingestion**: A trader places an order through the Trader Terminal (`POST /api/trades` or 1-click generators).
2. **Immediate Acknowledgment & Enqueueing**: The trade is validated, assigned a unique code (e.g., `TRD-20261026-ABC12345`), saved to the database with `is_processed = False`, and published as an event payload to the queue (Amazon SQS in production, `asyncio.Queue` locally).
3. **Asynchronous Detection**: A continuously running background worker dequeues trade messages every 500ms and feeds them into the 3-tier Anomaly Engine.
4. **Scoring & Alert Creation**:
   - The engine computes Z-Scores against historical baselines, Isolation Forest behavior score, and Contextual proximity to market events.
   - It synthesizes a composite risk score (0.00 to 1.00) and assigns a classification: `LOW`, `MEDIUM`, or `HIGH`.
   - The trade is updated to `is_processed = True`, and an `AnomalyAlert` record is persisted with mathematical human-readable explanations.
5. **Real-Time Notification Dispatch**:
   - **WebSocket**: If risk is `MEDIUM` or `HIGH`, the WebSocket manager pushes the alert JSON immediately to all connected Admin dashboards.
   - **Amazon SNS**: If risk is `HIGH`, an email alert is published to the configured Amazon SNS topic.
6. **Investigation & PDF Generation**: The compliance admin reviews the alert, initiates an official investigation, and triggers `report_service.py` to compile an audit-ready compliance PDF stored in Amazon S3 or `./storage/reports/`.

---

## 3. Technology Stack Breakdown

| Layer | Technology | Purpose & Capabilities |
|---|---|---|
| **Frontend UI** | React 18, Vite 6, React Router DOM 6 | Modern Single-Page Application (SPA) with dual dashboards, dark trading terminal styling, live tables, risk badges, and SVG charts. |
| **Data Visualization** | Recharts 2, Lucide React | Time-series volume/pricing charts, risk score distribution, real-time toast alert banners. |
| **Backend Framework**| FastAPI 0.115, Uvicorn 0.30 | High-performance asynchronous REST API and WebSocket server with automatic OpenAPI/Swagger documentation (`/docs`). |
| **Language & Runtime**| Python 3.12, Node.js 18+ | Strict type annotations, pydantic v2 data validation, and modern ES module support. |
| **Database & ORM** | SQLAlchemy 2.0, SQLite / PostgreSQL | Database abstraction supporting SQLite locally and Amazon RDS PostgreSQL in production. Schema includes automated seeders. |
| **Authentication** | JWT (python-jose), Passlib (Bcrypt) | Secure token-based authentication with role-based access control (`admin` vs `trader`). |
| **Machine Learning** | Scikit-Learn 1.5, NumPy, Pandas, Joblib | Isolation Forest unsupervised model trained on 11 behavioral features; serialized to `if_model.joblib`. |
| **Report Generation** | ReportLab 4.2 | Server-side PDF generation detailing trade diagnostics, trader history, and event timestamps. |
| **Cloud Services** | AWS SQS, SNS, S3, RDS, EC2, ALB, IAM, CloudWatch | Comprehensive enterprise cloud deployment spanning compute, networking, database, messaging, and storage. |

---

## 4. Anomaly Detection Engine Deep Dive

The anomaly detection engine (`backend/app/anomaly_engine/`) implements a tripartite pipeline combining statistical hypothesis testing, multi-dimensional machine learning, and contextual market intelligence.

```
Incoming Trade ──▶ [ 1. Z-Score Engine ]      (Weight: 40%) ──┐
               ──▶ [ 2. Isolation Forest ]    (Weight: 40%) ──┼──▶ [ Composite Score ] ──▶ [ Risk Classifier ]
               ──▶ [ 3. Contextual Engine ]   (Weight: 20%) ──┘
```

### 1. Statistical Z-Score Engine (`zscore.py`)
- Evaluates the current trade's `notional_value` ($Q \times P$) and `quantity` against the specific trader's frozen historical baseline ($\mu, \sigma$).
- Formula:
  $$Z = \frac{x - \mu_{\text{historical}}}{\sigma_{\text{historical}}}$$
- If $\sigma < 10^{-6}$, $Z = 0$ (avoids division by zero).
- **Rule of Thumb**:
  - $|Z| \ge 3.0$: Extreme statistical deviation $\rightarrow$ Flags `HIGH` risk immediately.
  - $2.0 \le |Z| < 3.0$: Moderate deviation $\rightarrow$ Flags `MEDIUM` risk.
  - $|Z| < 2.0$: Expected variation $\rightarrow$ `LOW` risk.

### 2. Machine Learning Isolation Forest (`isolation_forest.py`)
- Uses unsupervised tree partitioning to isolate points that are sparse or unusual in high-dimensional behavioral space.
- Fitted on historical baseline trades with `contamination=0.05` and `random_state=42`.
- Operates on an **11-feature behavioral vector**:
  1. `quantity`: Trade share size.
  2. `notional_value`: Total trade money value.
  3. `trade_frequency_1h`: Number of trades by this trader in the past hour.
  4. `trade_frequency_1d`: Number of trades by this trader in the past day.
  5. `buy_sell_ratio`: Rolling 10-trade direction bias: $(B + 1) / (S + 1)$.
  6. `time_deviation`: Minutes trade occurred outside the trader's preferred window (0 inside).
  7. `volume_ratio`: Current day volume relative to 20-day moving average.
  8. `volume_deviation`: `volume_ratio - 1`.
  9. `price_return_before_trade`: Price movement percentage in preceding 60 minutes.
  10. `event_distance`: Minutes to nearest corporate disclosure/earnings for this symbol.
  11. `trader_symbol_frequency`: Smoothed historical preference for trading this specific stock.
- Outputs an anomaly score normalized between `0.0` and `1.0`.

### 3. Contextual Rules Engine (`contextual.py`)
- Examines real-time market circumstances surrounding the trade:
  - **Pre-Event Proximity**: Trade executed within 24 hours prior to a major corporate disclosure or earnings shock ($+0.40$ context penalty).
  - **Uncharacteristic Stock**: Trader is dealing in a ticker with $<1\%$ historical personal activity ($+0.25$ context penalty).
  - **Off-Hours Execution**: Trade executed outside the trader's preferred operating hours ($+0.20$ context penalty).
  - **Market-Wide Volume Spike**: Symbol trading volume $\ge 2.0\times$ the 20-day moving average ($+0.15$ context penalty).

### 4. Composite Scoring & Risk Classification
The composite risk score is calculated as:
$$\text{Score}_{\text{composite}} = (0.40 \times \text{Score}_{\text{statistical}}) + (0.40 \times \text{Score}_{\text{ML}}) + (0.20 \times \text{Score}_{\text{contextual}})$$

- $\text{Score}_{\text{composite}} \ge 0.65 \implies$ **HIGH RISK** (Triggers WebSocket Alert + AWS SNS Email Notification).
- $\text{Score}_{\text{composite}} \ge 0.35 \implies$ **MEDIUM RISK** (Triggers WebSocket Alert).
- $\text{Score}_{\text{composite}} < 0.35 \implies$ **LOW RISK** (Normal Activity).
- *Override*: If $|Z| \ge 3.0$, the final classification is automatically forced to **HIGH** regardless of the other scores.

### 5. Automated Explainability Engine
The system generates human-readable audit text saved alongside the alert, detailing why the trade was flagged:
```
Unusual trading activity detected. Further human review recommended.

Trade flagged because:
- Notional value ₹1,250,000 is 4.3σ above this trader's historical average (₹180,000).
- Multi-feature machine learning (Isolation Forest) score: 0.82/1.00 (≥0.6 is flagged as behaviorally unusual).
- Trade executed 45 minutes prior to scheduled EARNINGS announcement for ALPHATECH.
```

---

## 5. Dataset Architecture & Synthetic Realism

The dataset (`data/`) contains 20,500 total trades generated via deterministic pseudorandom simulation (`generate_dataset_corrected.py`):

1. **50 Trader Profiles (`traders.csv`)**:
   - Spanning 6 distinct archetypes: *Conservative, Active, Swing Trader, Momentum Trader, Sector-Focused, Diversified*.
   - Each trader has strict baseline parameters: historical mean/std for quantity and notional, trading time window, preferred symbols, and buy probability.
2. **20 Fictional Stock Symbols (`symbols.csv`)**:
   - Symbols across 12 sectors with realistic baseline prices (₹100 to ₹4,000), typical spreads, average daily volumes, and daily volatilities (0.7% to 3.0%).
3. **150 Market Events (`market_events.csv`)**:
   - Calendar disclosures: `EARNINGS`, `MERGER`, `REGULATORY_APPROVAL`, `PRODUCT_LAUNCH`, `MANAGEMENT_CHANGE`, `DIVIDEND`.
   - Each event carries LOW/MEDIUM/HIGH severity, driving price jumps and volume spikes.
4. **20,000 Historical Baseline Trades (`historical_trades.csv`)**:
   - Distributed over 90 business days used to establish trader baseline statistics and train the Isolation Forest model.
5. **500 Test Trades with 100 Ground-Truth Injected Anomalies (`test_trades.csv`, `expected_anomalies.csv`)**:
   - 400 normal trades + 100 injected anomalies across 8 explicit surveillance patterns:
     - `LARGE_TRADE` (20 trades): Extreme notional spike ($Z \ge 3$).
     - `LARGE_QUANTITY` (15 trades): Extreme share count on low-cost stocks ($Z \ge 3$).
     - `FREQUENCY_SPIKE` (15 trades): Unusual burst of 7–8 trades in under 30 minutes by normally low-frequency traders.
     - `UNUSUAL_SYMBOL` (10 trades): Trading heavily in a stock the trader has never previously touched.
     - `UNUSUAL_TIME` (10 trades): Orders submitted 60–180 minutes outside the trader's operating window.
     - `PRE_EVENT_ACTIVITY` (10 trades): Aggressive buy orders placed 5–90 minutes before a high-impact corporate disclosure.
     - `BEHAVIOR_CHANGE` (10 trades): Traders with a 90% BUY bias abruptly flipping to heavy SELL orders with 2x size.
     - `MULTI_FEATURE_ANOMALY` (10 trades): Multi-variable combinations (large volume + rare stock + off-hours + pre-event).

---

## 6. Repository Directory Structure

```
Stock_insider/
├── DATASET_README.md                     # Dataset documentation & statistical methodology
├── market-surveillance-project-plan.md   # Original project roadmap & AWS deployment specs
├── generate_dataset_corrected.py         # Deterministic synthetic data generator script
├── REPOSITORY_COMPREHENSIVE_GUIDE.md     # This comprehensive guide
│
├── data/                                 # Seed data CSV files & trained ML models
│   ├── symbols.csv                       # 20 fictional stock tickers
│   ├── traders.csv                       # 50 trader accounts with baseline statistics
│   ├── market_events.csv                 # 150 corporate events/shocks
│   ├── historical_trades.csv             # 20,000 baseline historical trades
│   ├── test_trades.csv                   # 500 test trades (400 normal + 100 anomalies)
│   ├── expected_anomalies.csv            # Ground truth anomaly metadata
│   ├── feature_dataset.csv               # 20,500 rows with 11 extracted ML features
│   ├── reference_detection_results.csv   # Validation benchmark results
│   └── reference_evaluation.csv          # Evaluation metrics (precision, recall, F1)
│
├── backend/                              # FastAPI Backend application
│   ├── .env                              # Local runtime environment variables
│   ├── .env.example                      # Template for production / cloud variables
│   ├── requirements.txt                  # Python dependencies
│   ├── test_flow.py                      # Full integration test suite
│   ├── storage/                          # Local fallback directory for PDF reports
│   └── app/
│       ├── main.py                       # FastAPI application factory, CORS, and lifecycles
│       ├── core/
│       │   ├── config.py                 # Pydantic BaseSettings & AWS feature toggles
│       │   ├── dependencies.py           # Dependency injection (get_db, get_current_user)
│       │   └── security.py               # Password hashing (bcrypt) and JWT encode/decode
│       ├── db/
│       │   ├── base.py                   # SQLAlchemy Base declarative class
│       │   ├── session.py                # Database engine & sessionmaker factory
│       │   └── seeder.py                 # Auto-seeder for CSV reference data & default users
│       ├── models/                       # SQLAlchemy Database Entities
│       │   ├── user.py                   # User authentication model (admin / trader)
│       │   ├── symbol.py                 # Stock reference model
│       │   ├── trader_account.py         # Trader baseline profiles model
│       │   ├── trade.py                  # Trades model
│       │   ├── market_event.py           # Corporate market events model
│       │   ├── anomaly_alert.py          # Generated surveillance alerts model
│       │   └── investigation.py          # Admin investigation case tracker model
│       ├── schemas/                      # Pydantic Request/Response validation schemas
│       ├── anomaly_engine/               # Core surveillance algorithms
│       │   ├── detector.py               # Main pipeline coordinator
│       │   ├── zscore.py                 # Statistical Z-score calculator
│       │   ├── isolation_forest.py       # ML embedding predictor & model loader
│       │   ├── contextual.py             # Event proximity & timing rule evaluator
│       │   └── if_model.joblib           # Pre-fitted Isolation Forest weights
│       ├── services/                     # Business logic and external service adapters
│       │   ├── queue_service.py          # Abstraction for SQS or in-process queue
│       │   ├── notification_service.py   # Abstraction for SNS or console alerts
│       │   ├── report_service.py         # ReportLab PDF generator & S3 uploader
│       │   └── websocket_manager.py      # Thread-safe WebSocket broadcast manager
│       ├── workers/
│       │   └── sqs_worker.py             # Background polling worker loop
│       └── api/                          # REST API Endpoints
│           ├── auth.py                   # Login (`/api/auth/login`), me (`/api/auth/me`)
│           ├── trades.py                 # Submit, list, generate normal/suspicious trades
│           ├── alerts.py                 # Alerts list, detail, and WebSocket handler
│           └── investigations.py         # Case management & report generation endpoints
│
└── frontend/                             # React 18 + Vite frontend application
    ├── index.html                        # Application entry point
    ├── vite.config.js                    # Vite configuration with proxy for `/api` and `/ws`
    ├── package.json                      # Dependencies and scripts
    └── src/
        ├── main.jsx                      # React DOM rendering
        ├── App.jsx                       # Root routing, Auth/Toast providers, ProtectedRoute
        ├── api/
        │   └── client.js                 # Axios HTTP client with JWT interceptor & API methods
        ├── context/
        │   ├── AuthContext.jsx           # User state, token persistence, login/logout
        │   └── ToastContext.jsx          # Live alert toast notification state
        ├── hooks/
        │   └── useWebSocket.js           # Reconnecting WebSocket client hook
        ├── components/
        │   ├── Sidebar.jsx               # Navigation bar with connection status indicators
        │   ├── RiskBadge.jsx             # Color-coded LOW / MEDIUM / HIGH badges
        │   ├── ToastAlert.jsx            # Animated popup alerts on incoming suspicious trades
        │   ├── AlertDetailModal.jsx      # Modal showing statistical breakdown & math explanation
        │   └── InvestigationTracker.jsx  # Interactive investigation management modal
        ├── pages/
        │   ├── Login.jsx                 # User login page
        │   ├── Register.jsx              # User registration page
        │   ├── TraderTerminal.jsx        # Trader Portal: 1-click generation & manual trading
        │   ├── AdminDashboard.jsx        # Surveillance Center: Live alert feed & statistics
        │   ├── Alerts.jsx                # Full paginated table of flagged alerts with filters
        │   ├── Trades.jsx                # Searchable audit log of all executed trades
        │   └── Investigations.jsx        # Case files, notes, and PDF compliance report downloads
        └── styles/
            └── main.css                  # Dark-themed trading terminal styling and responsive UI
```

---

## 7. Database Entity Relationships

```mermaid
erDiagram
    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string role
        boolean is_active
        datetime created_at
    }

    SYMBOLS {
        string symbol PK
        string company_name
        string sector
        float baseline_price
        float volatility
        float average_daily_volume
        float typical_spread
    }

    TRADER_ACCOUNTS {
        string trader_id PK
        string trader_type
        string preferred_symbols
        string preferred_sectors
        string preferred_start_time
        string preferred_end_time
        float buy_probability
        float hist_mean_quantity
        float hist_std_quantity
        float hist_mean_notional
        float hist_std_notional
        int hist_trade_count
    }

    TRADES {
        int id PK
        string trade_code UK
        string trader_id FK
        string symbol FK
        string side
        float quantity
        float price
        float notional_value
        string sector
        string market_session
        datetime timestamp
        boolean is_processed
    }

    MARKET_EVENTS {
        int id PK
        string symbol FK
        string event_type
        string severity
        string description
        datetime event_time
    }

    ANOMALY_ALERTS {
        int id PK
        int trade_id FK
        float notional_zscore
        float quantity_zscore
        float statistical_score
        float ml_score
        float context_score
        float combined_score
        string risk_level
        string reason
        datetime detected_at
        string status
        boolean sns_notified
        int investigation_id FK
    }

    INVESTIGATIONS {
        int id PK
        int opened_by FK
        string status
        string notes
        string report_s3_key
        string report_url
        datetime opened_at
        datetime closed_at
    }

    TRADER_ACCOUNTS ||--o{ TRADES : places
    SYMBOLS ||--o{ TRADES : traded_in
    SYMBOLS ||--o{ MARKET_EVENTS : affects
    TRADES ||--o| ANOMALY_ALERTS : evaluated_into
    INVESTIGATIONS ||--o{ ANOMALY_ALERTS : groups
    USERS ||--o{ INVESTIGATIONS : manages
```

---

## 8. REST API & WebSocket Reference

### Authentication
- `POST /api/auth/login`: Accepts `username` and `password`. Returns JWT `access_token` and user profile (`id`, `username`, `role`).
- `POST /api/auth/register`: Create a new user (`trader` or `admin`).
- `GET /api/auth/me`: Validates current Bearer token and returns logged-in user details.

### Reference Data
- `GET /api/symbols`: Returns list of 20 fictional stock tickers with baseline prices and sector info.
- `GET /api/traders`: Returns list of 50 trader accounts with their historical baselines.

### Trades
- `POST /api/trades`: Submit a manual trade (`trader_id`, `symbol`, `side`, `quantity`, `price`). Returns trade object.
- `POST /api/trades/generate-suspicious`: 1-click test tool. Generates a statistically abnormal trade.
- `POST /api/trades/generate-normal`: 1-click test tool. Generates a normal trade matching profile expectations.
- `GET /api/trades`: Paginated list of trades with query filters (`trader_id`, `symbol`, `side`).
- `GET /api/trades/{id}`: Detailed trade record by ID.

### Surveillance Alerts
- `GET /api/alerts`: Paginated list of flagged alerts with filtering (`risk_level`, `status`).
- `GET /api/alerts/latest`: Retrieves recent alerts for initial dashboard rendering.
- `GET /api/alerts/{id}`: Full breakdown of a single alert (Z-scores, ML score, contextual flags).
- `PATCH /api/alerts/{id}/status`: Update alert review status (`OPEN`, `INVESTIGATING`, `CLOSED`).

### WebSocket Feed
- `WS /api/ws/alerts` (or `WS /ws/alerts`): Real-time persistent connection. Emits `NEW_ALERT` JSON events when the worker detects `MEDIUM` or `HIGH` risk trades.

### Investigations & Compliance Reports
- `POST /api/investigations`: Open an investigation case file linking one or more `alert_ids` and analyst `notes`.
- `GET /api/investigations`: List all open/closed investigation cases.
- `GET /api/investigations/{id}`: Fetch specific investigation case details.
- `PATCH /api/investigations/{id}`: Update case status or append analyst notes.
- `POST /api/investigations/{id}/report`: Generates compliance PDF via ReportLab, stores it in S3 (or `./storage/reports/`), and returns the download link.
- `GET /api/reports/{id}/pdf`: Serves the generated PDF report directly.

### System Health
- `GET /api/health`: Health-check endpoint used by AWS ALB Target Groups. Returns status and active cloud modes.

---

## 9. Local Execution Guide (Step-by-Step)

The environment has already been set up with a Python virtual environment and installed frontend packages. Follow these simple steps to run the application locally on your machine.

### Prerequisites Verified on System
- **Python**: 3.12 (`/opt/homebrew/bin/python3.12`)
- **Node.js**: v23.11.0 / npm 11.3.0
- **Virtualenv**: Created at `backend/venv/` with all packages installed.
- **Frontend Dependencies**: Installed via `npm install` in `frontend/`.

---

### Step 1: Start the FastAPI Backend
Open a terminal window and execute:
```bash
cd "/Users/ashmanraut/Ashman/Fr. CRCE/CCL/Miniproject/Stock_insider/backend"

# Activate the Python 3.12 virtual environment
source venv/bin/activate

# Launch the server with hot reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**What happens on backend startup**:
1. Creates the SQLite database (`market_surveillance.db`) if not present.
2. Runs `seeder.py` automatically: seeds symbols, traders, market events, and default credentials from the CSVs.
3. Starts the background SQS/asyncio worker task.
4. Mounts the REST routes and WebSocket handlers at `http://localhost:8000`.
5. API documentation is interactively accessible at `http://localhost:8000/docs`.

---

### Step 2: Start the React Frontend
Open a second terminal window and execute:
```bash
cd "/Users/ashmanraut/Ashman/Fr. CRCE/CCL/Miniproject/Stock_insider/frontend"

# Launch the Vite development server
npm run dev
```
The frontend will start at **`http://localhost:5173`**.

---

### Step 3: Default Credentials for Demo Testing

The database seeder automatically initializes two standard user accounts:

| Role | Username | Password | Default Redirect | Purpose |
|---|---|---|---|---|
| **Compliance Officer / Admin** | `admin` | `admin123` | `/dashboard` | Surveillance command center, alerts feed, investigation tracker, PDF reports. |
| **Trader** | `trader1` | `trader123` | `/terminal` | Trading terminal, 1-click generators, manual trade order submission. |

*(You can also use the `/register` page to create any additional accounts.)*

---

### Step 4: Conducting the Live Dual-Role Simulation

To simulate the two-laptop faculty demonstration on a single machine:
1. **Window A (Compliance Officer)**: Open an incognito browser window, navigate to `http://localhost:5173`, and log in as `admin` / `admin123`.
   - Observe the live summary cards (total trades, open alerts, risk distribution).
   - Check the green "Connected" WebSocket badge in the sidebar.
2. **Window B (Trader Terminal)**: Open a standard browser window, navigate to `http://localhost:5173`, and log in as `trader1` / `trader123`.
   - Click the blue **"Generate Normal Trade"** preset.
   - Switch back to Window A: The trade appears in the audit log as `LOW` risk without triggering intrusive alarms.
3. **Trigger Suspicious Activity**:
   - In Window B, click the red **"Generate Random Suspicious Trade"** button (or use the Manual form to buy 10,000 shares of a ₹2,000 stock).
   - In Window A: Within 1–2 seconds, a red **High-Risk Anomaly Toast Alert** pops up with audio/visual emphasis.
   - Click on the alert to open the **Alert Investigation Modal**. Review the exact mathematical Z-score and Isolation Forest reasoning.
   - Click **"Open Investigation"**, enter compliance notes, and click **"Generate Compliance Report"** to view and download the official PDF.

---

### Step 5: Running Integration Verification Tests
To verify all backend components without touching the browser, run:
```bash
cd "/Users/ashmanraut/Ashman/Fr. CRCE/CCL/Miniproject/Stock_insider/backend"
source venv/bin/activate
PYTHONPATH=. python test_flow.py
```
This tests authentication, reference endpoints, trade submissions, worker dequeueing, alert generation, investigation tracking, and PDF creation.

---

## 10. Production AWS Cloud Deployment Guide

When deploying this project to Amazon Web Services for the mini-project evaluation, configure the architecture according to the following step-by-step instructions.

```
                           Internet Gateway
                                  │
                   ┌──────────────┴──────────────┐
                   │   Public Subnet (ALB)       │
                   │   Port 80/443 (Internet)    │
                   └──────────────┬──────────────┘
                                  │ Forward to Port 8000
                   ┌──────────────┴──────────────┐
                   │   Public Subnet (EC2)       │
                   │   Backend API + SQS Worker  │
                   └──────────────┬──────────────┘
                                  │ Private Connection
                   ┌──────────────┴──────────────┐
                   │   Private Subnet (RDS PG)   │
                   │   Port 5432 (Internal only) │
                   └─────────────────────────────┘
```

### 1. Networking (Custom VPC)
1. **Create Custom VPC**:
   - Name: `market-surveillance-vpc`
   - CIDR block: `10.0.0.0/16`
2. **Subnets**:
   - `public-subnet-1a` (`10.0.1.0/24`) in `ap-south-1a` (for ALB & EC2)
   - `public-subnet-1b` (`10.0.2.0/24`) in `ap-south-1b` (for ALB multi-AZ requirement)
   - `private-subnet-1a` (`10.0.11.0/24`) in `ap-south-1a` (for RDS PostgreSQL)
   - `private-subnet-1b` (`10.0.12.0/24`) in `ap-south-1b` (for RDS DB Subnet Group)
3. **Internet Gateway & Route Tables**:
   - Create and attach an Internet Gateway (`igw-surveillance`) to the VPC.
   - Add route `0.0.0.0/0` $\rightarrow$ `igw-surveillance` on the Public Route Table and associate public subnets.
   - Private subnets remain isolated without direct internet access.

### 2. Security Groups
- **`alb-sg`**:
  - Inbound: HTTP (80) and HTTPS (443) from `0.0.0.0/0`.
  - Outbound: All traffic to `ec2-sg`.
- **`ec2-sg`**:
  - Inbound: Port 8000 only from `alb-sg`. SSH (22) from your administrator IP.
  - Outbound: All traffic.
- **`rds-sg`**:
  - Inbound: Port 5432 only from `ec2-sg` (strictly private; never open to `0.0.0.0/0`).
  - Outbound: None required.

### 3. Managed Database (Amazon RDS PostgreSQL)
1. Create a DB Subnet Group spanning `private-subnet-1a` and `private-subnet-1b`.
2. Provision an RDS PostgreSQL instance:
   - Engine: PostgreSQL 16.
   - Template: Free Tier (db.t4g.micro or db.t3.micro).
   - Storage: 20 GB gp3.
   - Multi-AZ: Disabled (Single-AZ keeps costs at zero within free tier).
   - Public Access: **No**.
   - Security Group: Attach `rds-sg`.
   - Database name: `market_surveillance`.

### 4. Messaging & Notifications (Amazon SQS & SNS)
1. **Amazon SQS**:
   - Create standard queue: `market-surveillance-trades-queue`.
   - Copy Queue URL for configuration.
2. **Amazon SNS**:
   - Create standard topic: `market-surveillance-high-risk-alerts`.
   - Create an **Email Subscription** using your team's email addresses. Confirm the subscription email.

### 5. Object Storage (Amazon S3)
1. Create S3 Bucket: `market-surveillance-reports-<unique-id>`.
2. Enable default server-side encryption (SSE-S3). Block all public access (reports will be signed or accessed through the backend).

### 6. IAM Least-Privilege Role for EC2
Create an IAM Role `MarketSurveillanceEC2Role` attached to EC2 with an inline policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:ap-south-1:ACCOUNT_ID:market-surveillance-trades-queue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:ap-south-1:ACCOUNT_ID:market-surveillance-high-risk-alerts"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::market-surveillance-reports-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:ap-south-1:ACCOUNT_ID:parameter/market_surveillance/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### 7. Configuration in AWS Systems Manager Parameter Store
Store sensitive credentials securely:
- `/market_surveillance/DATABASE_URL`: `postgresql://postgres:DB_PASS@rds-endpoint.rds.amazonaws.com:5432/market_surveillance`
- `/market_surveillance/SECRET_KEY`: `long-random-production-string`
- `/market_surveillance/SQS_QUEUE_URL`: `https://sqs.ap-south-1.amazonaws.com/...`
- `/market_surveillance/SNS_TOPIC_ARN`: `arn:aws:sns:ap-south-1:...`
- `/market_surveillance/S3_BUCKET_NAME`: `market-surveillance-reports-<unique-id>`

### 8. Compute Deployment (EC2 & ALB)
1. **EC2 Instance**:
   - AMI: Ubuntu Server 24.04 LTS (HVM) or Amazon Linux 2023.
   - Instance Type: `t3.small` or `t2.micro` (free-tier eligible).
   - IAM Role: Attach `MarketSurveillanceEC2Role`.
   - Security Group: Attach `ec2-sg`.
2. **Application Setup on EC2**:
   ```bash
   git clone <repo-url> Stock_insider
   cd Stock_insider/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install psycopg2-binary
   ```
3. **Environment Setup (`.env`)**:
   Configure `.env` with production RDS, SQS, SNS, and S3 credentials (or write a quick wrapper to fetch them from Parameter Store).
4. **Process Manager (Systemd)**:
   Create `/etc/systemd/system/surveillance-backend.service`:
   ```ini
   [Unit]
   Description=Market Surveillance FastAPI Backend
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/Stock_insider/backend
   ExecStart=/home/ubuntu/Stock_insider/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now surveillance-backend
   ```
5. **Frontend Hosting**:
   - **Option A (Simplest)**: Build frontend (`npm run build`), copy `dist/` to EC2, and serve via Nginx on port 80/443 proxying `/api` and `/ws` to `localhost:8000`.
   - **Option B (S3 + CloudFront)**: Deploy frontend build to an S3 static website bucket fronted by Amazon CloudFront, routing `/api/*` and `/ws/*` back to the ALB DNS.
6. **Application Load Balancer (ALB)**:
   - Create internet-facing ALB in `public-subnet-1a` and `public-subnet-1b`.
   - Target Group: Target EC2 port 8000. Health check path: `/api/health`.

### 9. Monitoring & Cost Control
1. **CloudWatch Metrics & Alarms**:
   - Set up an alarm on SQS Metric `ApproximateNumberOfMessagesVisible >= 50` or EC2 `CPUUtilization >= 80%`.
   - Set the alarm action to trigger the SNS topic (sends email alert).
2. **AWS Budgets**:
   - Create a monthly cost budget of **$5.00** with an email alert at 80% threshold ($4.00) to guarantee zero surprise charges.

---

## 11. Production Deployment Readiness Audit (10-File Checklist)

Before provisioning cloud infrastructure, the repository underwent an in-depth code-level audit across the 10 critical deployment files to ensure zero runtime surprises on AWS:

| File | Audit Focus | Findings & Verified Fixes | Status |
|---|---|---|---|
| **1. `backend/app/core/config.py`** | Environment Variables & Parameter Store | **Audited & Enhanced**: Added `load_from_ssm()` support. When `USE_PARAMETER_STORE=true`, it automatically fetches secrets from AWS Systems Manager (`/market_surveillance/*`) via IAM instance role. Retains `.env` fallback. `CORS_ORIGINS` includes `*` wildcard support. | Verified |
| **2. `backend/app/db/session.py`** | SQLAlchemy Engine & DB Driver | **Audited & Enhanced**: Added `pool_pre_ping=True` to prevent connection drops from RDS idle timeouts. Added `psycopg2-binary` to `requirements.txt` so PostgreSQL connections initialize reliably. | Verified |
| **3. `backend/app/services/queue_service.py`** | SQS vs Local Queue | **Audited**: Verified branching logic. When `SQS_QUEUE_URL` is populated, it lazily creates the `boto3` SQS client using instance IAM roles. Handles graceful fallback to `asyncio.Queue` if SQS is offline. | Verified |
| **4. `backend/app/services/notification_service.py`** | SNS vs Console Alerts | **Audited**: Verified `SNS_TOPIC_ARN` detection. Capped email subjects to 100 characters to comply with AWS SNS hard limits. Correctly falls back to console logging & mock file storage locally. | Verified |
| **5. `backend/app/services/report_service.py`** | S3 Uploads & Presigned URLs | **Audited & Enhanced**: When `S3_BUCKET_NAME` is set, uploads PDF to `reports/` and generates 1-hour presigned URL. Updated `investigations.py` endpoint so requests to `/api/reports/{id}/pdf` redirect cleanly to S3 presigned URLs instead of expecting local files. | Verified |
| **6. `backend/app/workers/sqs_worker.py`** | Background Consumer Loop | **Audited**: Continuous async polling loop (`dequeue_trade`) with at-least-once message processing and automatic backoff on network failures. Dispatches WebSocket toast notifications to active compliance sessions. | Verified |
| **7. `backend/app/main.py`** | App Lifecycle & Seeders | **Audited**: Idempotent table creation (`Base.metadata.create_all`) and conditional seeders. SQS worker launched as a managed background task that shuts down gracefully on SIGTERM. | Verified |
| **8. `frontend/src/api/client.js`** | API Base URL & WebSocket Host | **Audited & Fixed (CRITICAL)**: Previously defaulted to hardcoded `http://localhost:8000`. Updated so that in production, it defaults to relative paths (`''`), and `getWebSocketURL` dynamically resolves `window.location.host` with `ws://` / `wss://`. Eliminates production `ERR_CONNECTION_REFUSED`. | Verified & Fixed |
| **9. `frontend/vite.config.js`** | Dev Proxy Configuration | **Audited**: Verified `/api` and `/ws` reverse proxying to `:8000` during local development. Documented that in production, proxying is handled by Nginx / ALB. | Verified |
| **10. `backend/.env.example`** | Production Env Variables | **Audited & Updated**: Documented `USE_PARAMETER_STORE`, `CORS_ORIGINS`, RDS PostgreSQL connection formats, and the `VITE_API_BASE_URL` build parameter. | Verified & Updated |

---

## 12. Frequently Asked Viva / Evaluation Questions

| Question | Recommended Answer |
|---|---|
| **Does this system confirm insider trading?** | No. Legally, insider trading requires proving access to Material Non-Public Information (MNPI). The system flags *statistically unusual behavioral deviations* ($Z \ge 3$, ML outliers, event proximity) for human compliance review. |
| **Why use SQS instead of processing trades immediately?** | In real financial exchanges, trade volume spikes dramatically around news events. Synchronous processing would block API responses and crash under peak load. SQS buffers incoming orders and allows the anomaly engine to process them reliably without losing messages. |
| **Why combine Z-score with Isolation Forest?** | Z-score measures univariate scale (e.g. was this single trade too big?). Isolation Forest captures complex multi-variate non-linear interactions (e.g. normal trade size, but on an unusual symbol, 30 minutes before earnings, outside trading hours). |
| **How does the system ensure zero data leakage?** | When computing historical baselines and rolling statistics, only prior trades are considered. The Isolation Forest is strictly fitted on historical data. Post-trade price movements (`price_return_after_trade`) are explicitly excluded from real-time evaluation. |
| **How is cloud security enforced?** | EC2 uses IAM instance roles (no AWS access keys in code or `.env`), RDS PostgreSQL is secluded in private subnets with no internet route, security groups restrict database access solely to backend instances, and Parameter Store keeps DB secrets secure. |

---
*Document generated for the Fr. CRCE Cloud Computing Mini-Project (Stock Insider).*
