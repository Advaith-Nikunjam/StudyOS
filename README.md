# StudyOS — Personal AI-Powered Study Operating System

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-51%20passed-brightgreen.svg)

**StudyOS** is a production-grade, local-first personal study operating system designed to manage a 4-month (16-week / 120-day) intensive DSA + ML + DL + Computer Vision + SentinelAI preparation sprint while integrating college workloads, semester exams, and an always-on distance-viewable wall display.

---

## 🚀 Highlights & Features

- 🧠 **JARVIS AI Assistant**: Voice/text command engine with 3-tier action safety (Safe, Moderate, High-Risk) and fallback offline command parsing.
- 📺 **Wall Kiosk Display Engine**: Ultra-lightweight Vanilla JS frontend auto-rotating across 4 dedicated screens (`TODAY`, `PROGRESS`, `ACCOUNTABILITY`, `URGENT`) with offline caching and sleep mode.
- ⚡ **Local-First & Fast**: Built on FastAPI & Async SQLite (`aiosqlite`) with near-zero latency (<150 MB RAM client footprint).
- 📊 **Automated Reporting**: Daily plain Markdown reports, weekly retrospectives, and monthly summaries stored cleanly on disk.
- 💾 **Automated Backups & Exports**: Automatic daily database backups and weekly full-system ZIP archives (DB + notes + reports).
- 🎓 **Semester Exam Mode**: Dynamic workload scaling when college exams approach without disrupting long-term learning goals.

---

## 🏛️ System Architecture

```
                       ┌────────────────────────────────────────────────────────┐
                       │                   MAIN LAPTOP                          │
                       │               (Controller & Server)                    │
                       │                                                        │
                       │   FastAPI + Async SQLAlchemy + SQLite                  │
                       │   JARVIS AI Assistant Engine (3-Tier Safety)          │
                       │   APScheduler (Automated Backups & Reports)            │
                       └──────────────────────────┬─────────────────────────────┘
                                                  │
                                   Local LAN      │   HTTP / REST API
                                 (Port 8000)      │
                                                  ▼
                       ┌────────────────────────────────────────────────────────┐
                       │               OLD UBUNTU LAPTOP                        │
                       │             (Wall Display Kiosk)                       │
                       │                                                        │
                       │   Chromium Fullscreen Kiosk Mode                       │
                       │   Vanilla JS Display Engine (Auto-Rotates)             │
                       │   Local Storage Resiliency + Screen Saver              │
                       └────────────────────────────────────────────────────────┘
```

---

## 📂 Repository Structure

```
StudyOS/
├── app/                          # FastAPI Application Source
│   ├── api/                      # REST API Endpoints & Router Definitions
│   ├── core/                     # Configuration, Safety Rules & Core Logic
│   ├── db/                       # SQLAlchemy Async Models & DB Initialization
│   ├── services/                 # JARVIS Engine, Backups & Reporting Services
│   └── static/                   # Controller & Wall Display Frontend Assets
├── config/                       # Custom System Configuration & Metadata
├── data/
│   ├── database/                 # SQLite Database (studyos.db)
│   └── backups/                  # Daily (.sqlite) & Weekly (.zip) Backups
├── exports/                      # Exported CSV, JSON, and Markdown files
├── reports/                      # Daily, Weekly, Monthly & Milestone Reports
│   ├── daily/                    # Plain Markdown Daily Reports (YYYY/MM/)
│   ├── weekly/                   # Retrospective Weekly Reports
│   └── monthly/                  # Retrospective Monthly Reports
├── scripts/                      # Setup scripts (e.g. ubuntu_wall_setup.sh)
├── sentinelai/                   # SentinelAI Project Notes, Docs & Benchmarks
├── study/                        # DSA, ML, DL, CV & College Study Notes
├── tests/                        # Pytest Test Suite (51 unit & integration tests)
├── .env.example                  # Environment Configuration Template
├── .gitignore                    # Git Ignore Configuration
├── CONTRIBUTING.md               # Contribution Guidelines
├── LICENSE                       # MIT License
├── main.py                       # Application Entry Point
├── PRE_SPRINT_CONFIGURATION_CHECKLIST.md # Pre-sprint setup guide
└── requirements.txt              # Python Dependencies
```

---

## 🛠️ Quickstart Guide

### 1. Requirements
- **Python 3.10+**
- **Git**

### 2. Setup & Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/StudyOS.git
cd StudyOS

# Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your local environment configuration
cp .env.example .env

# Initialize database & seed 16-week sprint roadmap
python -m app.db.init_db

# Start the StudyOS Server
python main.py
```

- **Controller Interface**: `http://localhost:8000`
- **Wall Kiosk Display Interface**: `http://localhost:8000/wall`

---

## 📺 Ubuntu Wall Display Kiosk Setup

1. Copy `scripts/ubuntu_wall_setup.sh` to your secondary/Ubuntu laptop.
2. Edit `MAIN_LAPTOP_IP` in the script with your main laptop's local IP (e.g., `192.168.1.100`).
3. Make executable and run:
   ```bash
   chmod +x scripts/ubuntu_wall_setup.sh
   ./scripts/ubuntu_wall_setup.sh
   ```
4. Reboot the laptop. It will automatically boot into fullscreen kiosk mode targeting `http://<MAIN_LAPTOP_IP>:8000/wall`.

---

## 🛡️ 3-Tier AI Action Safety & Commands

JARVIS enforces 3 risk levels before executing commands:
1. **SAFE**: Automatically executed after validation (e.g., logging solved DSA problems, recording study notes, updating daily progress).
2. **MODERATE**: Returns a confirmation preview before applying changes (e.g., rescheduling tasks, changing daily plan).
3. **HIGH-RISK**: Requires explicit user confirmation (e.g., modifying 16-week roadmap, resetting sprint state, deleting history).

### Offline Command Vocabulary
When no LLM API key (`OPENAI_API_KEY` / `GEMINI_API_KEY`) is set, JARVIS seamlessly uses a deterministic command parser supporting:
- `start day` — Launches Day Start wizard
- `end day` — Triggers Day End review & generates daily Markdown report
- `complete task <title>` — Marks task completed
- `add task <title>` — Creates a new planned task
- `add mistake <type> <description>` — Records a mistake in accountability log
- `log dsa <count> <topic>` — Logs solved DSA problem(s)
- `activate exam mode` / `deactivate exam mode` — Toggles Semester Exam Mode
- `show progress` — Returns sprint progress summary

---

## 🧪 Testing

Run the test suite using `pytest`:

```bash
pytest
```

All 51 test cases cover API routes, database initialization, backup creation, reporting services, and JARVIS safety engine.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](file:///d:/StudyOS/LICENSE) file for details.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Check out [CONTRIBUTING.md](file:///d:/StudyOS/CONTRIBUTING.md) for details on setting up your local environment and submitting pull requests.
