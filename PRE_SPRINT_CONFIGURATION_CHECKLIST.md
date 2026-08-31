# StudyOS — Pre-Sprint Configuration Checklist & Audit Document

> **Document Purpose**: This document provides an exhaustive, empirical configuration audit of the StudyOS project codebase. It details all parameters, credentials, environment variables, roadmap settings, network endpoints, and operational configurations required before launching your real 120-day interview sprint.
>
> **Audit Status Legend**:
> - `USER CONFIGURATION REQUIRED`: Settings that require manual entry or setup before starting the real sprint.
> - `ALREADY CONFIGURED`: Settings already hardcoded, pre-seeded, or defaulted cleanly in the codebase.
> - `OPTIONAL`: Optional settings that enhance functionality but are not strictly required for operation.
> - `NOT IMPLEMENTED`: Documented or planned capabilities that do not currently have backend implementation code.

---

## 1. REQUIRED CONFIGURATION

### 1.1 One-Time 120-Day Sprint Activation Start Date
- **Setting name**: `actual_start_date`
- **What it does**: Permanently locks in your Day 1 calendar start date and calculates your 120-day sprint completion target (`actual_start_date` + 119 days).
- **Status**: `USER CONFIGURATION REQUIRED`
- **Requirement**: `REQUIRED`
- **Where to configure**: Main Controller Dashboard UI modal dialog (**🚀 START 120-DAY SPRINT** button) or API `POST /api/v1/sprint/start`.
- **Exact file / path / UI location**: Controller UI Navbar -> `start-sprint-modal` -> `#sprint-start-date-input` (`http://localhost:8000/`)
- **Expected format**: ISO Date String `YYYY-MM-DD`
- **Example value**: `2026-08-26`
- **Mode impact**: `REAL` mode (can also be tested independently in `TEST` mode).
- **Changeable after sprint start**: `NO` (One-time action; UI removes activation button post-activation).
- **Post-activation change risk**: `HIGH_RISK` (Modifying sprint dates after activation requires explicit confirmation via `POST /api/v1/sprint/update-dates` with `confirmed: true`).

### 1.2 Local Secret Key
- **Setting name**: `LAN_SECRET`
- **What it does**: Authentication secret token for LAN network access and session safety.
- **Status**: `ALREADY CONFIGURED` (Default set to `"studyos-local-secret"` in `app/core/config.py`).
- **Requirement**: `OPTIONAL` (Can override in `.env`).
- **Where to configure**: `.env` file in root directory.
- **Exact file / path / UI location**: [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L51)
- **Expected format**: String
- **Example value**: `LAN_SECRET=studyos-super-secret-key-2026`
- **Mode impact**: Affects `REAL`, `TEST`, and `DEMO` modes globally.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 2. AI / GEMINI API CONFIGURATION

### Empirical Codebase Inspection Results
- **Is Gemini implemented in code?**: `NOT IMPLEMENTED` in current version. `app/core/config.py` defines `GEMINI_API_KEY: str = ""` in Pydantic settings, but no Google Generative AI client or API call exists in `jarvis_engine.py` or anywhere in `app/`.
- **Dependencies installed**: `google-generativeai` and `openai` are **NOT** listed in [requirements.txt](file:///d:/StudyOS/requirements.txt).
- **Current JARVIS Engine**: Operates **100% OFFLINE** using a deterministic regex pattern parser (`_parse_command_intent` in [app/services/jarvis_engine.py](file:///d:/StudyOS/app/services/jarvis_engine.py#L65)).
- **Functions requiring Gemini**: `NONE` currently.
- **What works without Gemini**: 100% of StudyOS features (Task management, DSA logging, mistake tracking, exam mode, wall kiosk, reports, backups, mode switching, sprint activation).
- **Safe to start with no Gemini key?**: `YES` — 100% safe.
- **Is key stored in SQLite or exposed to browser/wall?**: `NO` — environment variable only.

### 2.1 Gemini API Key
- **Setting name**: `GEMINI_API_KEY`
- **What it does**: Environment variable placeholder for Google Gemini LLM API integration.
- **Status**: `NOT IMPLEMENTED` (Codebase readiness only; JARVIS runs offline).
- **Requirement**: `OPTIONAL`
- **Where to configure**: Root `.env` file.
- **Exact file / path / UI location**: [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L51)
- **Expected format**: String
- **Example value**: `GEMINI_API_KEY=AIzaSyA1234567890ExampleKey`
- **Mode impact**: All modes (`REAL`, `TEST`, `DEMO`).
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

### 2.2 OpenAI API Key
- **Setting name**: `OPENAI_API_KEY`
- **What it does**: Alternative LLM provider key placeholder.
- **Status**: `NOT IMPLEMENTED`
- **Requirement**: `OPTIONAL`
- **Where to configure**: Root `.env` file.
- **Exact file / path / UI location**: [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L50)
- **Expected format**: String
- **Example value**: `OPENAI_API_KEY=sk-proj-1234567890ExampleKey`
- **Mode impact**: All modes (`REAL`, `TEST`, `DEMO`).
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 3. STUDY PLAN CONFIGURATION

### 3.1 16-Week Interview Sprint Master Roadmap
- **Setting name**: `RoadmapWeek` database table (16 pre-seeded weeks).
- **What it does**: Defines weekly study focus across DSA, ML/DL/CV, and SentinelAI.
- **Status**: `ALREADY CONFIGURED` (Pre-seeded in [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L10-L123)).
- **Requirement**: `REQUIRED`
- **Where to configure**: Automatically populated into database upon initialization.
- **Exact file / path / UI location**: [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L10) -> `ROADMAP_WEEKS_DATA`
- **Expected format**: List of Dict objects (Week 1 to Week 16).
- **Example value**:
  - Month 1 (Weeks 1–4): Foundation (Arrays, Strings, Hashing, NumPy, Pandas, Baseline Classifier).
  - Month 2 (Weeks 5–8): DL + CV (Neural Networks, PyTorch, CNNs, OpenCV, Threat Module).
  - Month 3 (Weeks 9–12): Advanced Intelligence (Greedy, DP, Autoencoders, Explainability SHAP/Grad-CAM).
  - Month 4 (Weeks 13–16): Engineering + Interview Mocks (FastAPI, Persistence, Docker, Defense Prep).
- **Mode impact**: `REAL`, `TEST`, `DEMO` databases.
- **Changeable after sprint start**: `NO` (Protects master roadmap integrity).
- **Post-activation change risk**: `HIGH_RISK`

---

## 4. DSA CONFIGURATION

### 4.1 Independent Solved Target Count
- **Setting name**: `dsa_target`
- **What it does**: Overall target number of independent DSA problems solved across 120 days.
- **Status**: `ALREADY CONFIGURED` (Hardcoded target of `270` problems derived from weekly counts: W1-W8 = 18/wk, W9-W12 = 20/wk, W13-W16 = 15/wk).
- **Requirement**: `REQUIRED`
- **Where to configure**: [app/services/roadmap_service.py](file:///d:/StudyOS/app/services/roadmap_service.py#L62) & `ROADMAP_WEEKS_DATA` in `init_db.py`.
- **Exact file / path / UI location**: [app/services/roadmap_service.py](file:///d:/StudyOS/app/services/roadmap_service.py#L62)
- **Expected format**: Integer
- **Example value**: `270`
- **Mode impact**: `REAL`, `TEST`, `DEMO` modes.
- **Changeable after sprint start**: `NO`
- **Post-activation change risk**: `HIGH_RISK`

### 4.2 DSA Daily Log Submission
- **Setting name**: `DSALog`
- **What it does**: Records individual problem attempt, topic, difficulty, solve status, time taken, and mistake patterns.
- **Status**: `USER CONFIGURATION REQUIRED` (Entered daily as you solve problems).
- **Requirement**: `OPTIONAL` (Logged dynamically during study sessions).
- **Where to configure**: JARVIS natural language command (`"I solved 3 Array problems today"`) or API `POST /api/v1/dsa/log`.
- **Exact file / path / UI location**: Controller UI -> JARVIS Console or API endpoint `/api/v1/dsa/log`.
- **Expected format**: JSON payload
- **Example value**: `{"problem_name": "Two Sum", "topic": "Hashing", "difficulty": "Easy", "time_taken_mins": 15, "independent_solve": true}`
- **Mode impact**: Modifies active environment DB (`REAL`, `TEST`, or `DEMO`).
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 5. ML CONFIGURATION

### 5.1 Machine Learning Concepts Master List
- **Setting name**: `Concept` (domain="ML")
- **What it does**: Tracks status of core ML topics (preprocessing, train/val/test split, cross-validation, decision trees, ensembles, metrics ROC-AUC, anomaly detection).
- **Status**: `ALREADY CONFIGURED` (Pre-seeded in `ML_DL_CV_CONCEPTS` inside [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L142-L156)).
- **Requirement**: `REQUIRED`
- **Where to configure**: Auto-populated in database.
- **Exact file / path / UI location**: [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L142)
- **Expected format**: String tuple (`domain`, `concept_name`, `initial_status`)
- **Example value**: `("ML", "train/validation/test", "not_started")`
- **Mode impact**: All modes.
- **Changeable after sprint start**: `YES` (Concept status updates: `not_started` -> `learning` -> `mastered`).
- **Post-activation change risk**: `SAFE`

---

## 6. DL CONFIGURATION

### 6.1 Deep Learning Concepts Master List
- **Setting name**: `Concept` (domain="DL")
- **What it does**: Tracks mastery of PyTorch, Neural Networks, Activations, Backpropagation, Optimizers (Adam, SGD), Loss functions, CNNs, Dropout, BatchNorm.
- **Status**: `ALREADY CONFIGURED` (Pre-seeded in `ML_DL_CV_CONCEPTS` inside [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L157-L168)).
- **Requirement**: `REQUIRED`
- **Where to configure**: Auto-populated in database.
- **Exact file / path / UI location**: [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L157)
- **Expected format**: String tuple (`domain`, `concept_name`, `initial_status`)
- **Example value**: `("DL", "backpropagation", "not_started")`
- **Mode impact**: All modes.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 7. COMPUTER VISION CONFIGURATION

### 7.1 Computer Vision Concepts Master List
- **Setting name**: `Concept` (domain="CV")
- **What it does**: Tracks progress across OpenCV image preprocessing, convolution, classification, transfer learning, object detection, and video stream processing.
- **Status**: `ALREADY CONFIGURED` (Pre-seeded in `ML_DL_CV_CONCEPTS` inside [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L169-L177)).
- **Requirement**: `REQUIRED`
- **Where to configure**: Auto-populated in database.
- **Exact file / path / UI location**: [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L169)
- **Expected format**: String tuple (`domain`, `concept_name`, `initial_status`)
- **Example value**: `("CV", "OpenCV", "not_started")`
- **Mode impact**: All modes.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 8. SENTINELAI CONFIGURATION

### 8.1 Flagship Portfolio Project Milestones
- **Setting name**: `SentinelAIMilestone`
- **What it does**: Tracks 14 structural milestones (V0.1 Data Ingestion to V1.4 Final Portfolio Defense) mapped to specific roadmap weeks.
- **Status**: `ALREADY CONFIGURED` (Pre-seeded in `SENTINELAI_MILESTONES_DATA` inside [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L125-L140)).
- **Requirement**: `REQUIRED`
- **Where to configure**: Auto-populated in database upon initialization.
- **Exact file / path / UI location**: [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L125)
- **Expected format**: List of Dict objects (Version V0.1 to V1.4).
- **Example value**: `{"version": "V0.1", "target_week": 1, "title": "Data Ingestion & Baseline Classifier"}`
- **Mode impact**: All modes (`DEMO` mode has V0.1-V0.4 pre-completed).
- **Changeable after sprint start**: `YES` (Marking milestone complete).
- **Post-activation change risk**: `HIGH_RISK` (Marking milestones complete via JARVIS requires explicit confirmation).

---

## 9. COLLEGE SUBJECT CONFIGURATION

### 9.1 Academic Subjects & Syllabus Topics
- **Setting name**: `CollegeSubject` & `CollegeSyllabusTopic`
- **What it does**: Tracks college courses (Deep Learning, Computer Vision, Algorithms) and their syllabus units/topics to prevent academic conflict.
- **Status**: `ALREADY CONFIGURED` (Pre-seeded in `COLLEGE_SUBJECTS` inside [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L179-L205)).
- **Requirement**: `REQUIRED` (Can be modified or expanded).
- **Where to configure**: Auto-populated in database; additional custom subjects can be added in `init_db.py` or via custom API endpoint.
- **Exact file / path / UI location**: [app/db/init_db.py](file:///d:/StudyOS/app/db/init_db.py#L179)
- **Expected format**: List of Subject dicts with unit/topic tuples.
- **Example value**: `{"name": "Deep Learning", "code": "CS-701", "units": [...]}`
- **Mode impact**: All modes.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 10. COLLEGE ASSIGNMENTS / DEADLINES

### 10.1 College Events & Deadlines Tracker
- **Setting name**: `CollegeEvent`
- **What it does**: Logs upcoming college quizzes, lab submissions, project presentations, and assignments. Triggers Screen 4 Urgent Alerts on Wall Display.
- **Status**: `USER CONFIGURATION REQUIRED` (Enter your actual semester dates/deadlines).
- **Requirement**: `OPTIONAL` (Add as deadlines are assigned by university).
- **Where to configure**: Controller UI or direct database API.
- **Exact file / path / UI location**: Controller API `POST /api/v1/tasks` or custom event logger.
- **Expected format**: Event Record `{"title": "...", "subject_name": "...", "event_type": "quiz", "due_date": "YYYY-MM-DD"}`
- **Example value**: `{"title": "DL Quiz 1", "subject_name": "Deep Learning", "due_date": "2026-09-10"}`
- **Mode impact**: Active environment database.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 11. SEMESTER EXAM CONFIGURATION

### 11.1 Semester Exam Period & Exam Mode
- **Setting name**: `ExamPeriod` & `SprintConfig.exam_mode_active`
- **What it does**: Temporarily reduces/pauses interview roadmap intensity during college midterms/finals to protect academic GPA.
- **Status**: `ALREADY CONFIGURED` & `USER CONFIGURATION REQUIRED` (Toggle available via UI button or JARVIS command `"Activate exam mode"`).
- **Requirement**: `OPTIONAL` (Activated when college exams begin).
- **Where to configure**: Controller UI navbar **Exam Mode** button or API `POST /api/v1/mode/exam`.
- **Exact file / path / UI location**: Navbar -> `Exam Mode` button (`http://localhost:8000/`) or API `/api/v1/mode/exam`
- **Expected format**: `{"enable": true}`
- **Example value**: `{"enable": true}`
- **Mode impact**: Active environment (`REAL`, `TEST`, `DEMO`).
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `MODERATE` (Requires confirmation preview via JARVIS).

---

## 12. DAILY SCHEDULE / AVAILABLE HOURS

### 12.1 Daily Start Wizard (Session Hours & Constraints)
- **Setting name**: `DayLog` (`available_hours`, `constraints`, `energy_level`, `top_priority`)
- **What it does**: Logs daily available study time, college constraints, and top priority at the beginning of each day.
- **Status**: `USER CONFIGURATION REQUIRED` (Executed daily).
- **Requirement**: `OPTIONAL` (Recommended daily habit).
- **Where to configure**: Controller UI **Start Day** button or JARVIS command `"Start my day"`.
- **Exact file / path / UI location**: Controller UI Navbar -> `start-day-modal` (`http://localhost:8000/`)
- **Expected format**: Form inputs (Hours: Float, Constraints: Text, Energy: High/Medium/Low).
- **Example value**: Available Hours: `4.5`, Constraints: `"College classes 9 AM - 2 PM"`, Priority: `"Solve 3 Graph problems"`
- **Mode impact**: Active environment database (`DayLog` table).
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 13. JARVIS CONFIGURATION

### 13.1 Deterministic Command Vocabulary
- **Setting name**: `JarvisEngine._parse_command_intent`
- **What it does**: Parses natural language commands for task completion, DSA problem logging, mistake recording, exam mode toggling, and mode switching.
- **Status**: `ALREADY CONFIGURED` (Deterministic pattern matcher implemented in [app/services/jarvis_engine.py](file:///d:/StudyOS/app/services/jarvis_engine.py#L65)).
- **Requirement**: `REQUIRED`
- **Where to configure**: Fully functional out-of-the-box.
- **Exact file / path / UI location**: [app/services/jarvis_engine.py](file:///d:/StudyOS/app/services/jarvis_engine.py#L65)
- **Expected format**: Natural language text in JARVIS console.
- **Example commands**:
  - `"I solved 4 DSA problems today"` (SAFE)
  - `"Start day"` (SAFE)
  - `"Activate exam mode"` (MODERATE)
  - `"Switch to real mode"` (HIGH_RISK — requires explicit preview confirmation)
  - `"Start 120-day sprint"` (HIGH_RISK)
- **Mode impact**: Active environment mode.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: Depends on command risk level (`SAFE`, `MODERATE`, `HIGH_RISK`).

---

## 14. WALL DISPLAY CONFIGURATION

### 14.1 Main Controller Server IP Address
- **Setting name**: `MAIN_LAPTOP_IP`
- **What it does**: Configures the Ubuntu Wall Laptop kiosk script to target the Main Controller Laptop API server.
- **Status**: `USER CONFIGURATION REQUIRED` (Set to your Main Laptop's LAN IP).
- **Requirement**: `REQUIRED`
- **Where to configure**: [scripts/ubuntu_wall_setup.sh](file:///d:/StudyOS/scripts/ubuntu_wall_setup.sh#L7)
- **Exact file / path / UI location**: [scripts/ubuntu_wall_setup.sh:7](file:///d:/StudyOS/scripts/ubuntu_wall_setup.sh#L7)
- **Expected format**: IPv4 Address String `XXX.XXX.XXX.XXX`
- **Example value**: `MAIN_LAPTOP_IP="192.168.1.102"`
- **Mode impact**: Wall display kiosk connection across all modes.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

### 14.2 Kiosk Target URL & Port
- **Setting name**: `TARGET_URL` & `PORT`
- **What it does**: Defines full kiosk target URL launched in Chromium full-screen mode.
- **Status**: `ALREADY CONFIGURED` (`PORT="8000"`, `TARGET_URL="http://${MAIN_LAPTOP_IP}:${PORT}/wall"`).
- **Requirement**: `REQUIRED`
- **Where to configure**: [scripts/ubuntu_wall_setup.sh](file:///d:/StudyOS/scripts/ubuntu_wall_setup.sh#L8-L9)
- **Exact file / path / UI location**: [scripts/ubuntu_wall_setup.sh:8-9](file:///d:/StudyOS/scripts/ubuntu_wall_setup.sh#L8-L9)
- **Expected format**: URL String
- **Example value**: `http://192.168.1.102:8000/wall`
- **Mode impact**: Wall display kiosk.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

### 14.3 Wall Screen Rotation & Polling Parameters
- **Setting name**: Screen Rotation Interval & API Poll Interval
- **What it does**: Polls `/api/display-state` every 10s and rotates kiosk views (Screen 1 Today -> Screen 2 Progress -> Screen 3 Accountability -> Screen 4 Urgent) every 25s.
- **Status**: `ALREADY CONFIGURED` (Set in [app/static/js/wall.js](file:///d:/StudyOS/app/static/js/wall.js#L14-L128)).
- **Requirement**: `REQUIRED`
- **Where to configure**: [app/static/js/wall.js](file:///d:/StudyOS/app/static/js/wall.js#L14)
- **Expected format**: Integer milliseconds (`10000` polling, `25000` rotation).
- **Example value**: `25000` (25 seconds)
- **Mode impact**: Wall Display rendering.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 15. NETWORK CONFIGURATION

### 15.1 Main Laptop Static IP / DHCP Reservation
- **Setting name**: Main Laptop LAN IP Reservation
- **What it does**: Ensures Main Controller laptop maintains a constant IP address on your Wi-Fi/LAN router so Ubuntu Wall display never loses API connection.
- **Status**: `USER CONFIGURATION REQUIRED` (Router settings action).
- **Requirement**: `REQUIRED`
- **Where to configure**: Wi-Fi Router Admin Portal -> DHCP Static IP Reservation.
- **Exact file / path / UI location**: Router Web Interface (e.g., `http://192.168.1.1/`) -> DHCP Settings
- **Expected format**: MAC Address to IPv4 Mapping
- **Example value**: Bind Laptop MAC `AA:BB:CC:DD:EE:FF` to IP `192.168.1.102`
- **Mode impact**: System-wide LAN communication.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

### 15.2 Server Host & Port Binding
- **Setting name**: `HOST` & `PORT`
- **What it does**: Binds FastAPI Uvicorn web server to all network interfaces (`0.0.0.0`) on port `8000`.
- **Status**: `ALREADY CONFIGURED` in [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L10-L11).
- **Requirement**: `REQUIRED`
- **Where to configure**: [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L10-L11)
- **Expected format**: `HOST: str = "0.0.0.0"`, `PORT: int = 8000`
- **Example value**: `HOST="0.0.0.0"`, `PORT=8000`
- **Mode impact**: Main server.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 16. BACKUP CONFIGURATION

### 16.1 Automated Backup Directories
- **Setting name**: `DAILY_BACKUPS_DIR`, `WEEKLY_BACKUPS_DIR`, `TEST_BACKUPS_DIR`, `DEMO_BACKUPS_DIR`
- **What it does**: Target directories for automated SQLite snapshot backups and full ZIP archives.
- **Status**: `ALREADY CONFIGURED` (Auto-created in [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L43-L46)).
- **Requirement**: `REQUIRED`
- **Where to configure**: [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L43-L46)
- **Exact file / path / UI location**:
  - REAL Daily: `data/backups/daily/`
  - REAL Weekly: `data/backups/weekly/`
  - TEST: `data/backups/test/`
  - DEMO: `data/backups/demo/`
- **Expected format**: Path objects
- **Example value**: `data/backups/daily/studyos_real_2026-08-26.sqlite`
- **Mode impact**: Mode isolated.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

### 16.2 External Cloud Synchronization (Optional)
- **Setting name**: External Drive / Cloud Sync Folder (e.g. Google Drive, OneDrive, Syncthing)
- **What it does**: Copies `data/backups/` folder off-device for physical hardware fault tolerance.
- **Status**: `OPTIONAL` (Manual OS-level folder sync setup).
- **Requirement**: `OPTIONAL`
- **Where to configure**: OS File System / Cloud Sync Client (e.g. Syncthing, OneDrive).
- **Exact file / path / UI location**: Synchronize local `d:\StudyOS\data\backups\` directory.
- **Expected format**: Folder Path
- **Example value**: `d:\StudyOS\data\backups\` -> Cloud Vault
- **Mode impact**: Backup redundancy.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 17. REPORTING CONFIGURATION

### 17.1 Markdown Reports Generation Directories
- **Setting name**: `DAILY_REPORTS_DIR`, `WEEKLY_REPORTS_DIR`, `MONTHLY_REPORTS_DIR`, `TEST_REPORTS_DIR`, `DEMO_REPORTS_DIR`
- **What it does**: Stores generated Markdown reports for daily reviews, weekly summaries, and monthly retrospectives.
- **Status**: `ALREADY CONFIGURED` (Auto-created in [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L28-L36)).
- **Requirement**: `REQUIRED`
- **Where to configure**: [app/core/config.py](file:///d:/StudyOS/app/core/config.py#L28-L36)
- **Exact file / path / UI location**:
  - REAL Daily: `reports/daily/YYYY/MM/`
  - REAL Weekly: `reports/weekly/YYYY/`
  - REAL Monthly: `reports/monthly/YYYY/`
  - TEST: `reports/test/`
  - DEMO: `reports/demo/`
- **Expected format**: Markdown files (`.md`)
- **Example value**: `reports/daily/2026/08/2026-08-26_daily_report.md`
- **Mode impact**: Mode isolated.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 18. NOTIFICATION / ALERT CONFIGURATION

### 18.1 Wall Display Urgent Item Alerts
- **Setting name**: `has_pending_urgent` Screen 4 Trigger
- **What it does**: Automatically adds Screen 4 (Yellow Urgent Alert Banner) to Wall Display rotation if overdue tasks or upcoming college events exist.
- **Status**: `ALREADY CONFIGURED` (Evaluated dynamically in [app/api/routes.py](file:///d:/StudyOS/app/api/routes.py#L62) & [app/static/js/wall.js](file:///d:/StudyOS/app/static/js/wall.js#L104)).
- **Requirement**: `REQUIRED`
- **Where to configure**: Automated based on task/event due dates.
- **Exact file / path / UI location**: [app/api/routes.py:62](file:///d:/StudyOS/app/api/routes.py#L62)
- **Expected format**: Boolean threshold
- **Example value**: `has_pending_urgent: true`
- **Mode impact**: All modes.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 19. ENVIRONMENT CONFIGURATION

### 19.1 Active Environment Mode State
- **Setting name**: `CURRENT_ENV_MODE`
- **What it does**: Controls active database engine, report directory, and backup directory (`REAL`, `TEST`, or `DEMO`).
- **Status**: `ALREADY CONFIGURED` (Default is `REAL`; selectable via Navbar Pills or API `POST /api/v1/env/switch`).
- **Requirement**: `REQUIRED`
- **Where to configure**: Controller UI Navbar Pills (`REAL`, `TEST`, `DEMO`) or API `/api/v1/env/switch`.
- **Exact file / path / UI location**: [app/db/session.py:8](file:///d:/StudyOS/app/db/session.py#L8) -> `CURRENT_ENV_MODE`
- **Expected format**: String (`"REAL"`, `"TEST"`, `"DEMO"`)
- **Example value**: `"REAL"`
- **Mode impact**: Global environment selection.
- **Changeable after sprint start**: `YES` (Administrative confirmation required when entering `REAL`).
- **Post-activation change risk**: `HIGH_RISK` for REAL mode switch (requires confirmation modal).

---

## 20. SECURITY / API KEY CONFIGURATION

### 20.1 Git Exclusion & Secrets Safeguards
- **Setting name**: `.gitignore` rules & storage safety
- **What it does**: Ensures private keys (`.env`), SQLite databases (`.db`), backups, and personal reports are never committed to GitHub.
- **Status**: `USER CONFIGURATION REQUIRED` (Verify `.gitignore` contains sensitive patterns).
- **Requirement**: `REQUIRED`
- **Where to configure**: `.gitignore` in repository root.
- **Exact file / path / UI location**: `d:\StudyOS\.gitignore`
- **Expected format**: File glob patterns
- **Example value**:
  ```text
  .env
  *.db
  data/database/
  data/backups/
  reports/
  exports/
  ```
- **Mode impact**: All environments.
- **Changeable after sprint start**: `YES`
- **Post-activation change risk**: `SAFE`

---

## 21. PRE-SPRINT FINAL CHECKLIST

Complete every item before clicking **🚀 START 120-DAY SPRINT**:

- [ ] **[1] Environment configuration complete**: Main Laptop & Ubuntu Wall Laptop powered and connected to LAN.
- [ ] **[2] Gemini / AI status verified**: Verified JARVIS runs 100% offline out-of-the-box without requiring API keys.
- [ ] **[3] Master roadmap verified**: Inspected 16-week DSA, ML/DL/CV, and SentinelAI curriculum in `ROADMAP_WEEKS_DATA`.
- [ ] **[4] DSA targets verified**: Solved target locked at 270 independent problems (18/wk W1-W8, 20/wk W9-W12, 15/wk W13-W16).
- [ ] **[5] ML/DL/CV roadmap verified**: Verified 31 pre-seeded concepts across NumPy, Pandas, PyTorch, CNNs, and OpenCV.
- [ ] **[6] SentinelAI milestones verified**: Confirmed 14 milestones (V0.1 Data Ingestion to V1.4 Final Portfolio System Defense).
- [ ] **[7] College subjects entered**: Verified Deep Learning (CS-701), Computer Vision (CS-702), and Algorithms (CS-503).
- [ ] **[8] College syllabus entered**: Syllabus units and topics populated into `college_syllabus_topics`.
- [ ] **[9] Assignments entered**: Logged known semester quizzes, lab dates, and submission deadlines.
- [ ] **[10] Exam dates entered**: Exam periods defined for midterm/final schedules.
- [ ] **[11] Exam Mode tested**: Clicked **Exam Mode** button on navbar to confirm UI badge and schedule adjustment.
- [ ] **[12] Daily schedule configured**: Tested **Start Day** modal with sample hours (e.g. 4.5 hrs) and priority notes.
- [ ] **[13] JARVIS tested**: Tested commands in JARVIS console (`"Start day"`, `"I solved 2 DSA problems"`, `"Switch to test mode"`).
- [ ] **[14] TEST MODE tested**: Switched to `TEST MODE`, ran operations, and verified **RESET TEST DATA** safely clears sandbox.
- [ ] **[15] DEMO MODE tested**: Switched to `DEMO MODE`, verified curated demonstration state, and tested **RESET DEMO DATA**.
- [ ] **[16] REAL MODE verified**: Switched back to `REAL MODE` and confirmed administrative confirmation prompt.
- [ ] **[17] Wall kiosk tested**: Opened `http://<MAIN_LAPTOP_IP>:8000/wall` on Ubuntu laptop and verified 4-screen rotation.
- [ ] **[18] Network verified**: Configured Router DHCP reservation / Static IP for Main Laptop (`192.168.1.102`).
- [ ] **[19] Backups verified**: Created test backup via **Backup** button; verified file in `data/backups/`.
- [ ] **[20] Reports verified**: Generated test daily report via **End Day**; verified Markdown file formatting.
- [ ] **[21] API/security audit complete**: Verified `.env`, `*.db`, `reports/`, and `backups/` are listed in `.gitignore`.
- [ ] **[22] Ready to START 120-DAY SPRINT**: Click **🚀 START 120-DAY SPRINT**, pick your start date, and confirm!

---

## WHAT I NEED TO GIVE YOU

This is the exact, minimal list of information and credentials you need to supply before launching your real sprint:

1. **Sprint Start Date**: Pick your official Day 1 start date (e.g. `2026-08-26`) in the **🚀 START 120-DAY SPRINT** UI modal.
2. **Main Laptop Static LAN IP**: Set a DHCP reservation on your Wi-Fi router for your Main Laptop (e.g. `192.168.1.102`), and update `MAIN_LAPTOP_IP` in `scripts/ubuntu_wall_setup.sh`.
3. **Upcoming College Quiz / Assignment Dates**: Input any specific assignment or exam deadlines you currently have for Semester 7.
4. **Daily Available Study Hours**: Input your available focused study hours during your daily **Start Day** wizard (e.g. `4.5` hours).
5. **(Optional) LLM API Keys**: If you build external API LLM features in the future, add `GEMINI_API_KEY=your_key` to `.env`. (Not required for current StudyOS operation).
