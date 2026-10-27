# Cloud-Based Market Surveillance & Insider-Trading Anomaly Detection System
### Project Management & Implementation Document — AWS Cloud Computing Mini-Project

---

## 1. Project Overview

This project is a cloud-hosted web application that simulates how a stock exchange or regulator might watch trading activity for **unusual patterns**. Synthetic (fake, generated) trades flow into the system continuously. The backend processes each trade, compares it against a trader's normal behaviour, and flags trades that look statistically unusual. Flagged trades are shown on a React dashboard with a risk level (Low/Medium/High), and high-risk alerts also trigger a notification.

The entire system is deployed on AWS using a custom network (VPC), a load-balanced compute layer (EC2 + ALB + Auto Scaling), a managed database (RDS PostgreSQL), a message queue (SQS), a notification service (SNS), object storage (S3), and monitoring (CloudWatch), all secured with IAM roles and Parameter Store — with an AWS Budget to keep costs in check.

**This is an academic prototype.** It uses synthetic data only, is not connected to any real exchange or brokerage, and does not prove insider trading — it only flags statistically unusual trading patterns for further (human) review.

### 1.1 Real-Time Dual-Role Architecture & Live Demo Concept (Trader vs. Admin)

To provide an engaging, real-world demonstration during the faculty viva, the web application supports **two interactive user roles/portals running in real time across two separate laptops**:

1. **Trader Portal (Laptop 1 — Student A)**:
   A dedicated stock trading terminal where a user simulates real-time trade execution. The trader is offered two distinct trade placement modes:
   - **Mode A: "Generate Random Suspicious Trade" (1-Click Simulation)**: With a single click, the backend automatically selects a trader profile and synthesizes one of the realistic anomaly types (e.g., massive notional spike $Z \ge 3$, off-hours trading, trading in an uncharacteristic symbol, or pre-event activity). Also provides a 1-click **"Generate Normal Trade"** preset.
   - **Mode B: "Manual Trade Entry" (Interactive Form)**: Allows the user (or visiting evaluators) to pick any trader profile (`TRD001`–`TRD050`), pick a stock from the 20 fictional symbols, select BUY/SELL, and manually enter custom quantity and execution price. This allows on-the-spot testing of how the model reacts to arbitrary trade sizes.
2. **Surveillance Admin Dashboard (Laptop 2 — Student B)**:
   A real-time market surveillance center used by exchange compliance officers.
   - **Instant On-Screen Alert**: As soon as a suspicious/high-risk trade is executed on Laptop 1, Laptop 2 immediately displays a real-time on-screen banner/toast notification (powered by WebSockets with a short-polling fallback) with zero manual page refreshes.
   - **Real-Time AWS SNS Email Alert**: Concurrently, Amazon SNS dispatches an alert email directly to the team's inbox/phone (e.g., *"CRITICAL ALERT: TRD001 executed an abnormal trade on ALPHATECH with Z-score +4.2"*).
   - **Investigation Workflow**: The admin inspects the flagged trade breakdown (Z-scores, rolling baselines, pre-event context), opens an investigation, and triggers an S3 surveillance report.

---

## 2. Problem Statement

Real financial markets generate enormous volumes of trades every second. Regulators and exchanges cannot manually review every trade, so they rely on automated systems that flag statistically unusual behaviour — sudden volume spikes, price moves ahead of news, trades clustered suspiciously around market events, etc. Building even a simplified version of such a system requires:

- A way to generate/ingest trade data continuously
- A way to process that data asynchronously at scale
- Statistical or ML-based anomaly detection
- A way to alert humans to high-risk activity
- A dashboard for investigation
- A cloud architecture that can scale, stay secure, and stay observable

This project builds a scaled-down, educational version of that pipeline, demonstrating core cloud computing concepts (compute, networking, storage, database, security, monitoring) end-to-end.

---

## 3. Project Objectives

1. Build a working full-stack application (React + Django/FastAPI + PostgreSQL).
2. Generate realistic **synthetic** trade data and process it through a message queue.
3. Detect statistically unusual trades using Z-score analysis (optionally enhanced with Isolation Forest).
4. Assign risk levels (Low/Medium/High) to flagged trades and generate alerts.
5. Deploy the entire system on AWS using a custom VPC, EC2/ALB/Auto Scaling, RDS, S3, SQS, SNS, IAM, Parameter Store, and CloudWatch.
6. Demonstrate all six core cloud pillars: **Compute, Networking, Database, Storage, Security/IAM, Monitoring**.
7. Keep the architecture secure (no hardcoded credentials, private RDS, least-privilege IAM) and cost-controlled (small instances, Single-AZ RDS, AWS Budgets, no NAT Gateway unless required).
8. Produce full documentation: architecture diagram, service justification, screenshots, cost estimate, and a rehearsed faculty demo.

---

## 4. Scope

### In Scope (What We WILL Build)
- React dashboard showing trades, alerts, risk levels, and basic charts
- Django/FastAPI REST API with authentication
- PostgreSQL schema for users, trades, market events, alerts, investigations
- Synthetic trade generator (randomized, seeded, repeatable)
- Z-score based anomaly detection; optional Isolation Forest as an enhancement
- SQS-based asynchronous processing of trades
- SNS notifications for high-risk alerts
- S3 storage for generated surveillance reports / model artifacts
- Full AWS deployment: custom VPC, subnets, route tables, IGW, security groups, EC2, RDS, ALB, Auto Scaling, IAM, Parameter Store, CloudWatch (with at least one alarm), AWS Budgets

### Out of Scope (What We WILL NOT Build)
- Any connection to real stock exchanges, brokers, or market-data providers
- Real financial transactions or real money movement
- Legal/regulatory-grade insider-trading determination — the system only flags *statistical anomalies*, never a verdict
- Multi-region or Multi-AZ high-availability setups (kept single-AZ / single-region for cost reasons)
- Enterprise-grade authentication (OAuth/SSO) — a simple JWT/session-based auth is sufficient
- Mobile app version
- NAT Gateway-based private internet access (avoided unless a specific requirement forces it)

---

## 5. Complete Architecture

### Data Flow Narrative
1. A user opens the **React Dashboard**, which talks to the backend only through the **Application Load Balancer (ALB)**.
2. The ALB forwards requests to one or more **EC2** instances (behind an **Auto Scaling Group**) running the Django/FastAPI backend.
3. The backend exposes REST APIs to log in, fetch trades, fetch alerts, and trigger the synthetic trade generator.
4. New trade events are pushed onto an **SQS** queue rather than processed synchronously.
5. A worker process (running on the same EC2 fleet or a separate small worker) consumes messages from SQS, runs the **anomaly detection engine** (Z-score, optional Isolation Forest), computes a risk level, and writes results to **RDS PostgreSQL**.
6. If a trade is scored **High risk**, the engine publishes a message to **SNS**, which notifies subscribers (email/console) of the alert.
7. Periodically (or per investigation), the backend generates a **surveillance report** and stores it in **S3**.
8. EC2, SQS, and the application all emit metrics/logs to **CloudWatch**; a CloudWatch **alarm** watches a meaningful condition (e.g., SQS queue depth or high-risk alert rate) and can itself notify via SNS.
9. The backend reads database credentials and other secrets from **Systems Manager Parameter Store** at startup — nothing is hardcoded.
10. **IAM roles** attached to EC2 grant only the specific permissions needed (SQS send/receive, S3 put/get, Parameter Store read, CloudWatch put-metric) — least privilege throughout.
11. All of this lives inside a **custom VPC** with public subnets (ALB, EC2) and private subnets (RDS), connected via an **Internet Gateway** and controlled with **Route Tables** and **Security Groups**.
12. **AWS Budgets** watches total spend and alerts the team before costs run away.

### ASCII Architecture Diagram

```
                                   ┌───────────────────────────┐
                                   │        AWS Budgets        │
                                   │   (cost alert to team)    │
                                   └────────────▲───────────────┘
                                                │ monitors spend
                                                │
 ┌──────────────┐        HTTPS         ┌───────┴────────┐
 │   End User   │ ───────────────────▶ │   Internet GW   │
 │ (React app   │                      └───────┬────────┘
 │  in browser) │                              │
 └──────────────┘                              ▼
                                    ┌────────────────────────┐
                                    │   Custom VPC (10.0.0.0/16)  │
                                    │                         │
                    PUBLIC SUBNETS  │  ┌───────────────────┐  │
                    (10.0.1.0/24,   │  │        ALB         │  │
                     10.0.2.0/24)   │  └─────────┬─────────┘  │
                                    │            │ HTTP        │
                                    │  ┌─────────▼─────────┐  │
                                    │  │  Auto Scaling Grp  │  │
                                    │  │  EC2 (Backend API  │  │
                                    │  │  + SQS Worker)     │  │
                                    │  └───┬────┬────┬──────┘  │
                                    │      │    │    │         │
                    PRIVATE SUBNETS│      │    │    │         │
                    (10.0.11.0/24, │  ┌───▼┐ ┌─▼──┐ ┌▼──────┐ │
                     10.0.12.0/24) │  │RDS │ │SQS │ │Param  │ │
                                    │  │PG  │ │    │ │Store  │ │
                                    │  └────┘ └─┬──┘ └───────┘ │
                                    │           │              │
                                    │     ┌─────▼─────┐        │
                                    │     │    SNS     │        │
                                    │     └─────┬─────┘        │
                                    └───────────┼──────────────┘
                                                │ email/console
                                                ▼
                                       Investigator / Team

  Supporting services (span the VPC, accessed via IAM roles):
  EC2 ──▶ S3 (surveillance reports / model artifacts)
  EC2/SQS/App ──▶ CloudWatch (logs, metrics, 1+ alarm) ──▶ SNS (alarm notification)
  IAM ──▶ grants least-privilege access to EC2 for SQS, S3, Parameter Store, CloudWatch
```

---

## 6. Complete Technology Stack

| Technology / Service | Category | Purpose | Owner |
|---|---|---|---|
| React.js | Frontend | Dashboard UI, trade/alert visualization | Member 2 |
| Python (Django or FastAPI) | Backend | REST API, business logic, auth | Member 1 |
| PostgreSQL | Database (local) | Local dev schema/testing | Member 1 |
| Z-score / Isolation Forest (scikit-learn) | AI/Anomaly Detection | Flag unusual trades | Member 1 |
| Amazon EC2 | Compute | Hosts backend + worker | Member 3 |
| Amazon RDS (PostgreSQL) | Database (cloud) | Managed production DB | Member 3 |
| Amazon S3 | Storage | Surveillance reports, model artifacts | Member 3 |
| Amazon SQS | Messaging | Async trade processing queue | Member 1 & 3 |
| Amazon SNS | Notification | High-risk alert delivery | Member 1 & 3 |
| Amazon CloudWatch | Monitoring | Logs, metrics, alarms | Member 3 |
| AWS IAM | Security | Least-privilege roles/policies | Member 3 |
| AWS Systems Manager Parameter Store | Security/Config | Secrets, DB credentials, config | Member 3 |
| Application Load Balancer (ALB) | Networking | Distributes traffic to EC2 fleet | Member 3 |
| Auto Scaling | Compute/Scaling | Scales EC2 fleet under load | Member 3 |
| Amazon VPC + Subnets + Route Tables + IGW | Networking | Custom network isolation | Member 3 |
| Security Groups | Security/Networking | Firewall rules per component | Member 3 |
| AWS Budgets | Cost Control | Alerts on spend thresholds | Member 3 |

---

## 7. AWS Service-by-Service Explanation

### Amazon EC2
- **Why:** Hosts the Django/FastAPI backend and the SQS worker process.
- **What it does:** Runs the application code on a virtual machine.
- **Used by:** Backend API layer, background trade processing.
- **Responsible:** Member 3 (provisions), Member 1 (provides deployable code).
- **Demonstrate to faculty:** Running instance, SSH/console access, backend responding to requests through the ALB.

### Amazon RDS (PostgreSQL)
- **Why:** Managed database removes the burden of manual DB administration and patching.
- **What it does:** Stores users, trades, market events, alerts, investigations.
- **Used by:** Backend for all persistent data.
- **Responsible:** Member 3 (provisions, Single-AZ, private subnet), Member 1 (schema/migrations).
- **Demonstrate:** RDS console showing instance running in a private subnet, table contents via a query tool (e.g., a private bastion or SSM Session Manager).

### Amazon S3
- **Why:** Cheap, durable object storage with a genuine application purpose (not just decoration).
- **What it does:** Stores generated surveillance reports (e.g., PDF/CSV summaries per investigation) and any saved anomaly-detection model artifacts.
- **Used by:** Backend, after generating a report or retraining the optional Isolation Forest model.
- **Responsible:** Member 3 (bucket, policy), Member 1 (upload/download logic).
- **Demonstrate:** Bucket contents, at least one uploaded report.

### Amazon SQS
- **Why:** Decouples trade ingestion from anomaly processing so the system can absorb bursts of trades without blocking API responses.
- **What it does:** Queues trade events for asynchronous processing.
- **Used by:** Backend API (producer) → worker (consumer).
- **Responsible:** Member 1 (message format/producer/consumer code), Member 3 (queue provisioning, IAM permissions).
- **Demonstrate:** Queue metrics (messages sent/received), a message in-flight during a live demo.

### Amazon SNS
- **Why:** Delivers real-time notifications when a high-risk trade is detected, and can also notify the team on a CloudWatch alarm.
- **What it does:** Publish/subscribe notification service (email in this project).
- **Used by:** Anomaly engine (high-risk alert), CloudWatch alarm (ops alert).
- **Responsible:** Member 3 (topic/subscription), Member 1 (publish call from anomaly engine).
- **Demonstrate:** Received email notification during the live demo.

### Amazon CloudWatch
- **Why:** Gives visibility into system health without needing custom tooling.
- **What it does:** Collects EC2/ALB/SQS metrics and application logs; evaluates alarms.
- **Used by:** All compute/queue components.
- **Responsible:** Member 3.
- **Demonstrate:** Metrics dashboard, log group with recent entries, the configured alarm and its history.

### AWS IAM
- **Why:** Enforces least-privilege access — the EC2 instance can only do exactly what the app needs (SQS, S3, Parameter Store, CloudWatch), nothing more.
- **What it does:** Defines roles/policies attached to EC2.
- **Used by:** Every AWS API call the backend makes.
- **Responsible:** Member 3.
- **Demonstrate:** IAM role attached to the instance, policy JSON showing scoped permissions (not `*:*`).

### AWS Systems Manager Parameter Store
- **Why:** Avoids hardcoding secrets (DB password, SECRET_KEY, SNS topic ARN) in code or environment files committed to Git.
- **What it does:** Securely stores configuration values, fetched by the backend at startup via the IAM role.
- **Used by:** Backend startup.
- **Responsible:** Member 3 (creates parameters), Member 1 (reads them in code).
- **Demonstrate:** Parameter Store console showing SecureString parameters (values hidden), and the backend successfully starting using them.

### Application Load Balancer (ALB)
- **Why:** Single stable entry point for the frontend, distributes traffic across EC2 instances, enables Auto Scaling.
- **What it does:** Routes HTTP(S) traffic to healthy EC2 targets.
- **Used by:** All frontend → backend traffic.
- **Responsible:** Member 3.
- **Demonstrate:** ALB DNS name serving live traffic, target group health checks passing.

### Auto Scaling
- **Why:** Demonstrates elasticity — a core cloud computing concept — without needing to always run a large instance.
- **What it does:** Automatically adjusts EC2 instance count based on load (or a scheduled/minimal demo policy).
- **Used by:** Backend EC2 fleet.
- **Responsible:** Member 3.
- **Demonstrate:** Launch template + Auto Scaling Group configuration (min/max/desired kept small, e.g. 1–2, for cost reasons).

### Amazon VPC, Subnets, Route Tables, Internet Gateway
- **Why:** Required custom networking — isolates the project's resources and controls exactly how traffic flows.
- **What it does:** Public subnets host the ALB/EC2 (internet-reachable via IGW); private subnets host RDS (not internet-reachable).
- **Used by:** Every AWS resource in the project.
- **Responsible:** Member 3.
- **Demonstrate:** VPC diagram matching the actual console configuration, route tables showing public subnet → IGW, private subnet with no direct internet route.

### Security Groups
- **Why:** Firewall rules at the resource level — e.g., only the ALB can reach EC2 on the app port, only EC2 can reach RDS on 5432.
- **What it does:** Stateful inbound/outbound traffic filtering.
- **Used by:** ALB, EC2, RDS.
- **Responsible:** Member 3.
- **Demonstrate:** Security group rules showing scoped source (SG-to-SG references, not `0.0.0.0/0` for RDS).

### AWS Budgets
- **Why:** Required cost-control mechanism — alerts the team before spend gets out of hand.
- **What it does:** Sends an alert (email) when spend crosses a threshold (e.g., $5).
- **Used by:** Whole project.
- **Responsible:** Member 3.
- **Demonstrate:** Budget configuration and threshold alert setup.

---

## 8. Complete Feature List

**Frontend**
- Dual-role login/auth screen (Admin / Surveillance Officer vs. Trader)
- **Trader Terminal**:
  - 1-click **"Generate Random Suspicious Trade"** simulation button
  - 1-click **"Generate Normal Trade"** preset button
  - **Manual Trade Entry Form** (custom trader profile, symbol, side, quantity, price) with live notional value preview
- **Surveillance Admin Dashboard**:
  - Real-time pop-up toast & visual banner for incoming High-Risk alerts (WebSocket / polling)
  - Trade list/table with live streaming updates & filters
  - Alert list with risk-level badges (Low/Medium/High)
  - Alert detail view/modal with feature contribution breakdown
  - Investigation status tracker
  - Basic charts (trade volume over time, risk distribution)
  - Loading and error states throughout
  - Responsive layout

**Backend**
- User authentication (JWT or session) with role-based routing (Admin vs. Trader)
- Manual trade execution API (`POST /api/trades`)
- 1-Click random suspicious trade generator endpoint (`POST /api/trades/generate-suspicious`)
- Bulk synthetic trade generator endpoint (`POST /api/trades/generate`)
- Real-time push notification service (WebSocket endpoint `/ws/alerts` + polling fallback `/api/alerts/latest`)
- Trade listing/filter API
- Alert listing/detail API
- Investigation status API
- SQS producer (on trade ingestion)
- SQS consumer/worker (anomaly processing)
- SNS publisher (high-risk alerts)
- S3 report upload
- Parameter Store integration for config

**AI/ML**
- Historical baseline computation per trader
- Z-score based anomaly scoring
- Risk-level classification (Low/Medium/High thresholds — project-defined)
- Optional Isolation Forest model as an enhancement
- Human-readable anomaly explanation (which feature(s) triggered the flag)

**Cloud**
- Custom VPC with public/private subnets
- Route tables + Internet Gateway
- Security Groups per component
- EC2 + ALB + Auto Scaling
- RDS PostgreSQL (private, single-AZ)
- S3 bucket for reports
- SQS queue
- SNS topic + subscription
- IAM roles/policies (least privilege)
- Parameter Store secrets
- CloudWatch logs/metrics + 1 alarm
- AWS Budget alert

---

## 9. Database Design

### User
- **Purpose:** Application login accounts (analysts/admins using the dashboard).
- **Key fields:** id, username, email, password_hash, role, created_at
- **Relationships:** One User can create many Investigations.

### TraderAccount
- **Purpose:** Represents a *simulated* market participant whose trades are being watched (not an application login).
- **Key fields:** id, trader_code, display_name, account_type, created_at
- **Relationships:** One TraderAccount has many Trades.

### Trade
- **Purpose:** A single synthetic trade event.
- **Key fields:** id, trader_id (FK), symbol, side (buy/sell), quantity, price, timestamp, notional_value
- **Relationships:** Belongs to a TraderAccount; may relate to zero or one AnomalyAlert.

### MarketEvent
- **Purpose:** Synthetic "news"/event used to make anomaly patterns realistic (e.g., simulated earnings announcement).
- **Key fields:** id, symbol, event_type, description, event_time
- **Relationships:** Referenced by Trades/Alerts for context (loosely coupled, informational).

### AnomalyAlert
- **Purpose:** Represents a trade flagged as statistically unusual.
- **Key fields:** id, trade_id (FK), z_score, risk_level, reason, detected_at, status (open/reviewed)
- **Relationships:** Belongs to one Trade; can belong to one Investigation.

### Investigation
- **Purpose:** Tracks human follow-up on one or more alerts.
- **Key fields:** id, opened_by (FK → User), status, notes, opened_at, closed_at
- **Relationships:** Has many AnomalyAlerts; belongs to one User (analyst).

---

## 10. Trade Data Structure

```json
{
  "trade_id": "TRD-000123",
  "trader_id": "TRD-ACC-045",
  "symbol": "SYNTH-ABC",
  "side": "BUY",
  "quantity": 500,
  "price": 102.35,
  "notional_value": 51175.00,
  "timestamp": "2026-09-21T10:15:32Z",
  "is_synthetic": true
}
```

---

## 11. SQS Message Structure

```json
{
  "message_type": "TRADE_EVENT",
  "trade": {
    "trade_id": "TRD-000123",
    "trader_id": "TRD-ACC-045",
    "symbol": "SYNTH-ABC",
    "side": "BUY",
    "quantity": 500,
    "price": 102.35,
    "notional_value": 51175.00,
    "timestamp": "2026-09-21T10:15:32Z"
  },
  "producer": "backend-api",
  "sent_at": "2026-09-21T10:15:32.500Z"
}
```

---

## 12. Anomaly Detection Logic

**Data collected:** all historical trades per trader (quantity, price, notional value, time-of-day, frequency).

**Historical baseline:** rolling mean and standard deviation of a trader's notional value (and/or quantity) computed over their trade history.

**Features used:** notional value, quantity, trade frequency in a time window, deviation from the trader's typical trading hours.

**Z-score calculation (concept):**
```
z = (current_value - trader_mean) / trader_std_dev
```
A large absolute Z-score means the trade is far from that trader's normal behaviour.

**Risk levels (project-defined, NOT a regulatory standard):**
- `|z| < 2` → Low
- `2 ≤ |z| < 3` → Medium
- `|z| ≥ 3` → High

**Alert creation:** any trade above the Low threshold creates an `AnomalyAlert` row; High-risk alerts also trigger an SNS notification.

**Optional Isolation Forest enhancement:** trained on the same feature set to catch multi-dimensional anomalies that a single-feature Z-score might miss; its anomaly score can be blended with or shown alongside the Z-score.

**Explaining an anomaly to a user:** the alert should state *which* feature(s) deviated and by how much, e.g., "This trade's notional value is 4.2 standard deviations above this trader's 30-day average." This is a statistical flag for review — **never** phrase it as proof of wrongdoing.

---

## 13. Frontend Requirements

- **Authentication & Role Selection**:
  - Login page with role-based dashboard view (Trader vs. Compliance Admin/Surveillance Officer)
- **Trader Terminal (for live trading simulation)**:
  - 1-Click **"Generate Random Suspicious Trade"** button (immediately dispatches a pre-crafted anomaly trade)
  - 1-Click **"Generate Normal Trade"** button (dispatches a standard baseline trade)
  - **Manual Trade Entry Form**:
    - Trader Profile dropdown (shows `TRD001`–`TRD050` with archetype and normal avg trade size)
    - Stock Symbol dropdown (20 fictional companies with live reference price)
    - Order Side selector (`BUY` / `SELL`)
    - Quantity & Execution Price inputs with dynamic Notional Value preview
    - "Execute Trade" button with instant submission feedback
- **Surveillance Admin Dashboard (for compliance monitoring)**:
  - Real-time pop-up toast alerts / audio-visual banner when a High-Risk anomaly is detected
  - WebSocket connection manager with automatic reconnection & 2-second polling fallback
  - Summary cards (Total Trades, Open Alerts, High-Risk Anomaly Count, Active Investigations)
  - Live Trades table (real-time stream with filters by trader, symbol, and side)
  - Alerts table (filter by risk level: LOW / MEDIUM / HIGH, and status)
  - Alert detail modal/page (shows trade attributes, Z-score, anomaly explanation, linked investigation)
  - Investigation status tracker (open, under review, closed)
  - Charts: trade volume over time, risk-level distribution (pie/bar)
  - Loading spinners and error banners on every data-fetching view
  - Responsive layout (desktop/laptop optimized)

---

## 14. Backend Requirements

- Project structure (FastAPI recommended for native async/WebSocket support, or Django REST framework)
- Authentication (JWT recommended for simplicity with React)
- Database models + migrations for all 6 entities in Section 9
- Synthetic trade generator service (seeded for repeatability)
- **Real-time Alert Broadcast**:
  - WebSocket manager (`/ws/alerts`) to broadcast newly detected anomalies to connected Admin clients instantly
  - Short-polling fallback endpoint (`/api/alerts/latest`) for environments where WebSockets are restricted
- SQS producer on trade creation
- SQS consumer/worker loop
- Anomaly detection module (Z-score + optional Isolation Forest)
- Alert + Investigation CRUD endpoints
- SNS publish on High-risk alert
- S3 report generation + upload
- Parameter Store client for config/secrets
- Centralized error handling and input validation
- API documentation (OpenAPI/Swagger if FastAPI; drf-spectacular or manual docs if Django)

### API Endpoint Table

| Method | Endpoint | Purpose | Request | Response | Owner |
|---|---|---|---|---|---|
| POST | /api/auth/login | Authenticate user | `{username, password}` | `{token, role}` | Member 1 |
| POST | /api/trades | Submit manual trade from Trader Terminal | `{trader_id, symbol, side, quantity, price}` | `Trade` (queued) | Member 1 |
| POST | /api/trades/generate-suspicious | 1-Click random suspicious trade generator | `{}` | `Trade` (queued) | Member 1 |
| POST | /api/trades/generate-normal | 1-Click normal baseline trade generator | `{}` | `Trade` (queued) | Member 1 |
| POST | /api/trades/generate | Trigger bulk synthetic trade generation | `{count}` | `{queued: n}` | Member 1 |
| GET | /api/trades | List trades (filterable) | query params | `[Trade]` | Member 1 |
| GET | /api/trades/{id} | Trade detail | — | `Trade` | Member 1 |
| GET | /api/alerts | List alerts (filterable) | query params | `[AnomalyAlert]` | Member 1 |
| GET | /api/alerts/latest | Fetch latest alerts (polling fallback) | `?since_id=x` | `[AnomalyAlert]` | Member 1 |
| WS | /ws/alerts | Real-time WebSocket alert stream for Admin | — | `Stream<AnomalyAlert>` | Member 1 |
| GET | /api/alerts/{id} | Alert detail | — | `AnomalyAlert` | Member 1 |
| POST | /api/investigations | Open investigation | `{alert_ids, notes}` | `Investigation` | Member 1 |
| PATCH | /api/investigations/{id} | Update status/notes | `{status, notes}` | `Investigation` | Member 1 |
| GET | /api/reports/{investigation_id} | Generate/fetch S3 report | — | `{s3_url}` | Member 1 |
| GET | /api/health | Health check (for ALB) | — | `{status: "ok"}` | Member 1 |

---

## 15. Cloud Architecture Requirements

| Component | Requirement |
|---|---|
| VPC | Custom CIDR (e.g., `10.0.0.0/16`) |
| Subnets | 2 public (ALB, EC2), 2 private (RDS), across 2 AZs for subnet-group requirements (RDS itself stays Single-AZ) |
| Route Tables | Public RT → 0.0.0.0/0 via IGW; Private RT → no direct internet route |
| Internet Gateway | Attached to VPC, associated with public route table |
| Security Groups | ALB-SG (80/443 from internet), EC2-SG (app port from ALB-SG only), RDS-SG (5432 from EC2-SG only) |
| EC2 | Small instance type (e.g., t3.micro/t2.micro), in public subnet or behind ALB in public subnet with app not directly exposed |
| RDS | PostgreSQL, Single-AZ, `db.t3.micro` or free-tier eligible, private subnet, not publicly accessible |
| S3 | One bucket, versioning optional, bucket policy scoped to the app's IAM role |
| SQS | One standard queue for trade events |
| SNS | One topic, email subscription for the team |
| IAM | One EC2 instance role with scoped policies (SQS, S3, Parameter Store, CloudWatch only) |
| Parameter Store | Parameters for DB URL, DB password (SecureString), SECRET_KEY, SNS topic ARN, S3 bucket name |
| CloudWatch | Log group for app logs, custom or default metrics, ≥1 alarm |
| ALB | Public-facing, target group = EC2 Auto Scaling Group, health check on `/api/health` |
| Auto Scaling | Min 1, Max 2 (kept small for cost), scaling policy on CPU or left as manual demo |
| AWS Budgets | One budget with an email alert threshold (e.g., $5–10) |

---

## 16. Security Requirements

- **Least privilege:** IAM policies list exact actions (`sqs:SendMessage`, `sqs:ReceiveMessage`, `s3:PutObject`, `s3:GetObject`, `ssm:GetParameter`, `cloudwatch:PutMetricData`) scoped to the specific resource ARNs — never `"*"` on `"*"`.
- **IAM roles:** EC2 uses an instance profile/role; no IAM user access keys are ever placed on the instance.
- **No hardcoded AWS credentials:** anywhere in the codebase, config files, or Git history.
- **Parameter Store:** DB credentials, Django `SECRET_KEY`, and SNS topic ARN are stored as `SecureString` parameters, fetched at runtime.
- **Private RDS:** RDS lives in a private subnet with no public accessibility flag, reachable only from the EC2 security group.
- **Security Groups:** only necessary ports open (80/443 on ALB, app port from ALB-SG only on EC2, 5432 from EC2-SG only on RDS).
- **Required ports:** 443/80 (ALB, public), app port e.g. 8000 (EC2, internal only), 5432 (RDS, internal only).
- **Authentication:** JWT (or session) tokens for the dashboard; passwords hashed (Django's built-in hasher or `bcrypt`/`argon2` if FastAPI).
- **Secrets handling:** `.env`/local secrets are git-ignored; production secrets live only in Parameter Store.

---

## 17. Monitoring Requirements

- **Metrics:** EC2 CPU utilization, ALB request count/latency/5xx errors, SQS `ApproximateNumberOfMessagesVisible`, RDS connections/CPU.
- **Logs:** Application logs shipped to a CloudWatch Log Group (via CloudWatch agent or the app's logging handler).
- **CloudWatch alarm (required, at least one):** e.g., alarm on `ApproximateNumberOfMessagesVisible > 20 for 5 minutes` on the SQS queue (indicates the worker is falling behind) — notifies the SNS topic.
- **SNS notification:** the alarm's action publishes to the same (or a separate ops-specific) SNS topic, emailing the team.
- **Example meaningful alarm condition:** SQS queue depth alarm as above, or EC2 CPU > 80% for 5 minutes (indicates scaling may be needed).

---

## 18. Cost-Control Requirements

- Use small EC2 instance types (`t3.micro`/`t2.micro`, free-tier eligible where possible).
- Use Single-AZ RDS (`db.t3.micro`), not Multi-AZ.
- Avoid a NAT Gateway — private subnet (RDS) doesn't need outbound internet access for this project; if the worker must run in a private subnet and needs outbound access, prefer keeping the worker on the public-subnet EC2 instead of paying for NAT.
- Keep Auto Scaling limits small (min 1, max 2).
- Keep synthetic datasets small (hundreds to low thousands of trades, not millions).
- Set up an **AWS Budget** with an email alert at a low threshold (e.g., $5).
- **Stop or delete unused resources** (EC2, RDS) between work sessions if not actively demoing/testing.
- Capture all required screenshots (Section 25) **before** final teardown.

---

## 19. Exact 3-Person Work Division

### Member 1 — Backend + Anomaly Detection

| Category | Details |
|---|---|
| Responsibilities | Django/FastAPI backend, REST APIs, auth, DB models, synthetic trade generator, SQS producer/consumer, Z-score + optional Isolation Forest, risk scoring, alert generation, S3 report upload code, Parameter Store client code |
| Deliverables | Working local backend, migrations, API docs, `requirements.txt`, deployable backend package |
| Technologies | Python, Django or FastAPI, PostgreSQL, scikit-learn, boto3 |
| Files/Modules | `backend/`, `models/`, `api/`, `anomaly_engine/`, `trade_generator/`, `workers/sqs_worker.py` |
| Needs from others | ALB/backend URL & CORS origin from Member 3 (or localhost while developing); confirmed AWS resource names (queue URL, bucket name, SNS topic ARN, Parameter Store paths) from Member 3 |
| Must give others | API contract (OpenAPI spec/README), DB schema, required env vars, SQS message format (Section 11), S3 file naming convention, SNS message format, port/startup command |
| Testing | Unit tests for models & anomaly logic, API tests (e.g., pytest + DRF/FastAPI test client), local SQS testing (LocalStack optional) |
| Documentation | API reference, anomaly detection explanation |
| Faculty-demo role | Explains backend flow, anomaly logic, and runs the trade generator live |

### Member 2 — Frontend

| Category | Details |
|---|---|
| Responsibilities | React dashboard, login UI, trade/alert tables, risk visualization, charts, investigation UI, API integration, loading/error states |
| Deliverables | Working React app, production build, demo screens |
| Technologies | React.js, a charting library (e.g., Recharts), fetch/axios |
| Files/Modules | `frontend/src/pages/`, `components/`, `api/client.js` |
| Needs from others | API contract & base URL from Member 1/3; CORS confirmation |
| Must give others | List of expected API response shapes it needs; confirmed production build settings (env vars, API base URL) |
| Testing | Component tests, manual API-integration testing against local and deployed backend |
| Documentation | Component/page overview, setup instructions |
| Faculty-demo role | Drives the dashboard live during the demo |

### Member 3 — AWS Cloud + Deployment

| Category | Details |
|---|---|
| Responsibilities | VPC/subnets/route tables/IGW, security groups, EC2, RDS, S3, SQS, SNS, IAM, Parameter Store, CloudWatch + alarm, ALB, Auto Scaling, AWS Budgets, backend deployment, connecting backend to RDS |
| Deliverables | Fully deployed & working AWS environment, architecture diagram, cost estimate, cleanup script/checklist |
| Technologies | AWS Console/CLI, (optionally) Terraform/CloudFormation for reproducibility |
| Files/Modules | `infra/` (IaC scripts if used), `infra/README.md`, deployment scripts |
| Needs from others | Backend env vars list, required ports, startup command, SQS/S3/SNS naming needs, IAM permissions the app requires, production frontend build for hosting/CORS origin |
| Must give others | RDS connection details (host/port/db name — not the password, which goes to Parameter Store), production API URL for frontend, confirmed resource names/ARNs |
| Testing | Network connectivity tests (EC2→RDS, EC2→SQS/S3/SNS/Parameter Store), security group verification, alarm trigger test |
| Documentation | Architecture diagram, service justification, cost breakdown |
| Faculty-demo role | Explains AWS architecture, security, and cost controls |

---

## 20. Dependency Matrix

| Task | Owner | Depends On | Output Required | Consumed By |
|---|---|---|---|---|
| DB schema design | Member 1 | Project requirements | Schema/migrations | Member 3 (RDS setup) |
| Local backend working | Member 1 | DB schema | Working API + local DB | Member 2 (frontend integration), Member 3 (deployment) |
| API contract | Member 1 | Local backend | OpenAPI/README | Member 2 |
| React dashboard | Member 2 | API contract | Working frontend | Faculty demo |
| VPC/networking | Member 3 | — (independent) | VPC/subnets/SGs | EC2, RDS, ALB |
| RDS instance | Member 3 | VPC/networking | RDS endpoint | Member 1 (connection string) |
| SQS/SNS/S3 provisioning | Member 3 | — (independent) | Resource names/ARNs | Member 1 (integration code) |
| IAM role | Member 3 | Known permissions needed | Instance profile | EC2 |
| Parameter Store values | Member 3 | RDS + SNS/S3 provisioned | Parameter paths | Member 1 (backend config) |
| Backend deployment | Member 3 | Working backend + AWS infra | Running EC2 app | ALB, faculty demo |
| ALB + Auto Scaling | Member 3 | EC2 deployment | Public URL | Member 2 (frontend API URL) |
| CloudWatch alarm | Member 3 | Running system | Alarm + SNS link | Faculty demo |
| Frontend production build | Member 2 | ALB URL | Deployed/served frontend | Faculty demo |

**Independent work:** Members 1, 2, and 3 can all start immediately — Member 1 builds locally, Member 2 builds against a local/mock API, Member 3 builds AWS infrastructure. **Integration is required** once local backend works (Member 1 → Member 2) and once the backend is ready to deploy (Member 1 → Member 3).

---

## 21. Development Timeline

### Phase 1 — Planning + Architecture
- All: finalize scope, schema, API contract skeleton, AWS service list, and this document.

### Phase 2 — Independent Development
- Member 1: build backend, DB models, synthetic generator, anomaly engine locally.
- Member 2: build React app against a mocked/local API.
- Member 3: build AWS infrastructure (VPC, IAM, RDS, S3, SQS, SNS, Parameter Store) independently.

### Phase 3 — Local Integration
- Member 1 finalizes local backend + real API contract.
- Member 2 connects React app to the real local backend; fixes integration issues.

### Phase 4 — AWS Deployment
- Member 3 deploys the working backend to EC2, connects it to RDS, wires up Parameter Store.

### Phase 5 — AWS Service Integration
- Member 1 & 3 together: verify SQS producer/consumer, S3 uploads, SNS alerts all work against real AWS resources.

### Phase 6 — Testing
- All: run the full testing plan (Section 23) end-to-end.

### Phase 7 — Evidence/Screenshots
- All: capture every required screenshot (Section 25) while the system is live.

### Phase 8 — Final Demo/Documentation
- All: rehearse the faculty demo flow (Section 24), finalize documentation and architecture diagram, then clean up resources.

---

## 22. Integration Checklist

**Backend ↔ Frontend**
- [ ] Final API contract agreed (endpoints, request/response shapes)
- [ ] Auth token format agreed (header name, token type)
- [ ] CORS origins configured on backend
- [ ] Error response format agreed (status codes, error body shape)
- [ ] Pagination/filtering query param names agreed

**Backend ↔ Cloud**
- [ ] Required environment variables listed
- [ ] Ports and startup command confirmed
- [ ] SQS queue URL/name confirmed
- [ ] S3 bucket name + key structure confirmed
- [ ] SNS topic ARN confirmed
- [ ] IAM permissions required by the app listed and matched to the role's policy
- [ ] RDS connection details (host, port, db name) confirmed; password path in Parameter Store confirmed

**Frontend ↔ Cloud**
- [ ] Production API base URL (ALB DNS name) confirmed
- [ ] CORS allowed origin (frontend hosting URL) confirmed
- [ ] Frontend hosting approach confirmed (served from EC2/S3+CloudFront/static host)

---

## 23. Testing Plan

- **Unit testing:** models, anomaly scoring functions, utility functions.
- **API testing:** every endpoint in Section 14's table, happy path + error cases.
- **Frontend testing:** component rendering, API integration, loading/error states.
- **Database testing:** migrations apply cleanly, relationships/constraints hold.
- **SQS testing:** message sent on trade creation, message consumed and processed correctly, malformed message handled gracefully.
- **Anomaly detection testing:** known synthetic outliers are correctly flagged; known normal trades are not.
- **S3 testing:** report upload succeeds, file retrievable.
- **SNS testing:** high-risk alert triggers a received notification.
- **IAM testing:** confirm EC2 role can perform only its intended actions (attempt an out-of-scope action and confirm it's denied).
- **CloudWatch alarm testing:** artificially trigger the alarm condition (e.g., pause the worker to build up queue depth) and confirm notification fires.
- **End-to-end testing:** generate trades → see them processed → see alert appear on dashboard → receive SNS notification.
- **Failure scenarios:** backend restarts mid-processing, SQS message redelivery, RDS temporarily unreachable, invalid trade data submitted.

---

## 24. Faculty Demo Flow (5–10 minutes, Dual-Laptop Live Scenario)

**Live Demo Setup:**
* **Laptop 1 (Student A — Trader Terminal)**: Simulates the market participant / broker placing orders.
* **Laptop 2 (Student B — Surveillance Admin Dashboard)**: Simulates the exchange compliance & surveillance desk monitoring the market in real time.
* **Mobile / Projector (Student C — Cloud Infrastructure)**: Displays incoming AWS SNS email alerts, AWS Console (SQS, RDS, CloudWatch), and architecture slides.

**Step-by-Step Viva Execution:**
1. **Initial Baseline Display (Laptop 2)**: Open the Surveillance Admin Dashboard; show the live summary cards (total trades, open alerts) and baseline normal trades already processed into RDS.
2. **Normal Trading Demonstration (Laptop 1)**: 
   - Click the 1-click **"Generate Normal Trade"** preset on the Trader Terminal.
   - Show that the trade is ingested smoothly into SQS, processed without raising risk, and appears in the Admin feed as `LOW` risk (green badge).
3. **Option 1: 1-Click Suspicious Trade Injection (Laptop 1)**:
   - Click the **"Generate Random Suspicious Trade"** button.
   - The backend crafts a realistic anomaly (e.g., a massive 5x notional trade, off-hours trade, or uncharacteristic stock pre-earnings).
4. **Real-Time Synchronous Detection (Both Laptops)**:
   - Within 1–2 seconds, **Laptop 2 flashes a red High-Risk Anomaly Toast Alert** on the screen (no page refresh required, delivered via WebSocket/SSE).
   - Simultaneously, **an AWS SNS email notification arrives** on Student C's phone / screen: *"CRITICAL ALERT: TRD001 placed abnormal trade on ALPHATECH with Z-score +4.2"*.
5. **Option 2: Interactive Manual Trade Entry (Live Professor Challenge)**:
   - Switch to the manual trade form on Laptop 1.
   - Ask the faculty evaluator to pick a stock and trade size (e.g., *"Let's buy 5,000 shares of ZETAPHARMA for a conservative trader"*).
   - Click **"Execute Trade"**.
   - Show the anomaly engine calculating the Z-score live, classifying it dynamically based on the evaluator's custom numbers, and updating Laptop 2 in real time.
6. **Investigation & S3 Report Generation (Laptop 2)**:
   - On the Admin Dashboard, click the newly flagged alert to open the **Alert Investigation Modal**.
   - Review the detailed mathematical explanation (Z-score, trade vs. trader baseline, pre-event timing).
   - Click **"Open Investigation"** and **"Export Compliance Report"**; show the generated surveillance report saved into the **Amazon S3** bucket.
7. **Cloud Infrastructure Proof (Student C / AWS Console)**:
   - **SQS Console**: Show trade messages moving through the queue.
   - **RDS Console / Query**: Show the newly created trade and alert rows in PostgreSQL.
   - **S3 Console**: Show the uploaded surveillance report artifact.
   - **CloudWatch**: Show real-time CPU/queue metrics and the configured alarm.
8. **Architecture, Security & Cost Defense (All Members)**:
   - Walk through the architecture diagram (ALB → EC2 → SQS → Worker → RDS + SNS + S3).
   - Explain security: IAM least privilege, private RDS, Parameter Store (no hardcoded passwords).
   - Explain cost control: Free-tier friendly instance sizing, Single-AZ RDS, no NAT Gateway, and active AWS Budgets alert.

---

## 25. Evidence/Screenshot Checklist

| Screenshot | Console/Page | What Should Be Visible | Why Faculty Needs It |
|---|---|---|---|
| VPC overview | VPC Console | Custom VPC, subnets, route tables, IGW | Proves custom networking |
| Security Groups | EC2 → Security Groups | Scoped inbound rules per SG | Proves least-privilege networking |
| EC2 instance | EC2 Console | Running instance, instance type | Proves compute deployment |
| Auto Scaling Group | EC2 → Auto Scaling | Min/max/desired, launch template | Proves elasticity |
| ALB | EC2 → Load Balancers | DNS name, healthy targets | Proves load balancing |
| RDS instance | RDS Console | Engine, Single-AZ, private subnet, "Not publicly accessible" | Proves managed DB + security |
| S3 bucket | S3 Console | Bucket + at least one uploaded object | Proves genuine storage use |
| SQS queue | SQS Console | Queue + message metrics during demo | Proves async processing |
| SNS topic | SNS Console | Topic + subscription + a sent notification | Proves alerting |
| IAM role/policy | IAM Console | Instance role, attached policy JSON | Proves least privilege |
| Parameter Store | Systems Manager → Parameter Store | List of parameters (values hidden) | Proves no hardcoded secrets |
| CloudWatch metrics | CloudWatch Console | Relevant metric graphs | Proves monitoring |
| CloudWatch alarm | CloudWatch → Alarms | Alarm configuration + triggered state (if tested) | Proves the required alarm |
| AWS Budgets | Billing → Budgets | Budget + threshold + alert email setup | Proves cost control |
| Dashboard live | Browser | Trades/alerts visible | Proves working frontend |
| Anomaly alert detail | Browser | Risk level + reason for a flagged trade | Proves anomaly detection works |

---

## 26. Architecture Diagram Checklist

The final diagram must include:
- [ ] End user / browser
- [ ] Internet Gateway
- [ ] VPC boundary with CIDR
- [ ] Public subnets (ALB, EC2/Auto Scaling Group)
- [ ] Private subnets (RDS)
- [ ] Route tables (public vs private)
- [ ] Security Groups (as labels/boundaries around each component)
- [ ] ALB
- [ ] EC2 / Auto Scaling Group
- [ ] RDS PostgreSQL
- [ ] SQS queue (with direction of flow)
- [ ] SNS topic (with direction of flow)
- [ ] S3 bucket (with direction of flow)
- [ ] IAM role (annotation on EC2)
- [ ] Parameter Store (annotation/connection to EC2)
- [ ] CloudWatch (metrics/logs/alarm, connected to relevant components)
- [ ] AWS Budgets (can be shown as a side annotation, not necessarily inside the VPC)

---

## 27. Source Code / Repository Structure

```
market-surveillance-project/
├── backend/
│   ├── config/                 # settings, env loading, Parameter Store client
│   ├── apps/ (or modules/)
│   │   ├── users/
│   │   ├── trades/
│   │   ├── alerts/
│   │   └── investigations/
│   ├── anomaly_engine/
│   │   ├── zscore.py
│   │   └── isolation_forest.py   # optional
│   ├── trade_generator/
│   ├── workers/
│   │   └── sqs_worker.py
│   ├── requirements.txt
│   └── manage.py / main.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── api/
│   │   └── App.jsx
│   ├── package.json
│   └── build/                  # production build output
├── infra/
│   ├── vpc/
│   ├── iam/
│   ├── README.md               # deployment steps, resource names
│   └── (optional) terraform/ or cloudformation/
├── docs/
│   ├── architecture-diagram.png
│   ├── api-reference.md
│   ├── screenshots/
│   └── cost-estimate.md
└── README.md
```

---

## 28. Git/Collaboration Rules

- **Branches:** `main` (stable, demo-ready), `backend`, `frontend`, `cloud/infrastructure`.
- Each member works on their own branch and opens a pull request into `main` when a feature is stable.
- No direct commits to `main` — at least a self-review before merging in a small team.
- Commit small and often, with descriptive messages (e.g., `backend: add SQS worker for trade processing`).
- Never commit `.env` files, AWS credentials, or `.pem` key files — add them to `.gitignore` from day one.
- Pull `main` regularly into your feature branch to avoid large merge conflicts near the deadline.
- Tag or note the commit used for the final faculty demo.

---

## 29. Definition of Done

- [ ] React frontend deployed and reachable via the ALB URL
- [ ] Backend API deployed on EC2, responding through the ALB
- [ ] RDS PostgreSQL storing real data from the live system
- [ ] Synthetic trade generator working end-to-end
- [ ] SQS queue actively used for trade processing
- [ ] Z-score anomaly detection working (Isolation Forest optional but noted if included)
- [ ] Risk levels (Low/Medium/High) correctly assigned and displayed
- [ ] SNS notification received for at least one High-risk alert
- [ ] S3 report generated and stored for at least one investigation
- [ ] Custom VPC with public/private subnets, route tables, IGW all configured
- [ ] Security Groups scoped correctly (no open RDS to the world)
- [ ] IAM role with least-privilege policy attached to EC2
- [ ] Parameter Store used for all secrets/config — nothing hardcoded
- [ ] CloudWatch logging + at least one working alarm
- [ ] AWS Budget configured with an alert
- [ ] Architecture diagram matches the actual deployed system
- [ ] All required screenshots captured
- [ ] Cost estimate documented
- [ ] Faculty demo rehearsed end-to-end
- [ ] Source code and documentation finalized in the repository
- [ ] Non-essential AWS resources stopped/deleted after evidence collection

---

## 30. Risks and Backup Plans

| Component | Risk | Backup Plan |
|---|---|---|
| AWS free-tier limits | Costs exceed budget | Use smallest instance sizes, Single-AZ, delete resources between sessions, rely on AWS Budgets alert |
| RDS connectivity | EC2 cannot reach RDS | Double-check security group source rules (SG-to-SG, not CIDR); verify subnet routing |
| SQS integration complexity | Worker fails to process messages | Fall back to a simpler synchronous processing path for the demo, keep SQS for architecture credit, document the issue |
| Isolation Forest (optional) | Model underperforms or is hard to tune in time | Ship Z-score only as the primary detector; mention Isolation Forest as a documented "future enhancement" |
| Auto Scaling demo | Hard to trigger real scaling live | Show configuration + explain policy rather than forcing a live scale event |
| CloudWatch alarm | Alarm doesn't trigger during demo | Pre-test the alarm before the demo and have a screenshot/recording as backup evidence |
| Team member unavailable near deadline | A section is incomplete | Cross-train: each member should understand at least the basics of the other two roles (Section 19 emphasizes shared understanding for the viva) |
| Frontend/backend integration mismatch | API contract drifts | Lock the API contract early (Phase 1–2) and communicate any changes immediately |
| Git conflicts | Overwritten work | Follow the branch strategy in Section 28; merge frequently |

---

## 31. Final Team Rules

1. Do not start advanced features until the MVP works.
2. Do not add AWS services without a functional purpose.
3. Do not hardcode credentials.
4. Do not expose RDS publicly.
5. Do not use real financial/trading data.
6. Do not claim the system proves insider trading.
7. Test every component before integration.
8. Commit code regularly.
9. Keep screenshots/evidence as you build.
10. Keep AWS costs under control.
11. Before deleting anything, capture all required evidence.
12. All three members must understand the complete architecture before the final viva.
