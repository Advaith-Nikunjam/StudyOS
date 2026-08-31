import asyncio
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import select, text
from app.db.session import _engines, _sessionmakers, Base
from app.db.models import (
    SprintConfig, RoadmapWeek, SentinelAIMilestone, Concept, 
    CollegeSubject, CollegeSyllabusTopic, Task, DayLog, DSALog, Mistake, CollegeEvent,
    SpacedRevision, WeaknessRecord, WeeklyReview
)

ROADMAP_WEEKS_DATA = [
    {
        "week_number": 1, "month_number": 1, "title": "Month 1 - Foundation: Week 1",
        "focus_dsa": "Big-O, Arrays, Strings, Hashing, Basic Sorting",
        "focus_ml_dl": "NumPy, Pandas, Visualization, Statistics Basics",
        "focus_sentinelai": "Repository setup, Data Ingestion, Preprocessing, Baseline Model",
        "dsa_target_count": 18
    },
    {
        "week_number": 2, "month_number": 1, "title": "Month 1 - Foundation: Week 2",
        "focus_dsa": "Prefix Sums, Two Pointers, Sliding Window, Binary Search Basics",
        "focus_ml_dl": "Train/Val/Test split, Data Leakage, Classification, Regression, Metrics",
        "focus_sentinelai": "Normal vs Attack Classifier, Metrics Logged",
        "dsa_target_count": 18
    },
    {
        "week_number": 3, "month_number": 1, "title": "Month 1 - Foundation: Week 3",
        "focus_dsa": "Linked Lists, Stack, Queue, Recursion",
        "focus_ml_dl": "KNN, SVM, Decision Trees, Random Forest, XGBoost concepts",
        "focus_sentinelai": "Model Comparison, Clean Source Structure, Model Selection",
        "dsa_target_count": 18
    },
    {
        "week_number": 4, "month_number": 1, "title": "Month 1 - Foundation: Week 4",
        "focus_dsa": "Trees, BST",
        "focus_ml_dl": "Cross-Validation, Class Imbalance, Precision/Recall/F1, ROC-AUC/PR-AUC, Anomaly Detection",
        "focus_sentinelai": "Isolation Forest, One-Class SVM (Month 1 Checkpoint)",
        "dsa_target_count": 18
    },
    {
        "week_number": 5, "month_number": 2, "title": "Month 2 - DL + CV: Week 5",
        "focus_dsa": "Heaps, Priority Queues",
        "focus_ml_dl": "Perceptron, Neural Networks, Activations, Loss Functions, Forward/Backprop",
        "focus_sentinelai": "NumPy Neural Network, PyTorch Baseline",
        "dsa_target_count": 18
    },
    {
        "week_number": 6, "month_number": 2, "title": "Month 2 - DL + CV: Week 6",
        "focus_dsa": "Tree Traversal, BFS, DFS",
        "focus_ml_dl": "SGD, Adam, Learning Rate, Batch Size, Dropout, BatchNorm, Regularization",
        "focus_sentinelai": "ML vs DL Comparison Module",
        "dsa_target_count": 18
    },
    {
        "week_number": 7, "month_number": 2, "title": "Month 2 - DL + CV: Week 7",
        "focus_dsa": "Graph Basics",
        "focus_ml_dl": "CNN, Convolution, Kernels, Stride, Padding, Pooling",
        "focus_sentinelai": "Start Visual Intelligence Pipeline",
        "dsa_target_count": 18
    },
    {
        "week_number": 8, "month_number": 2, "title": "Month 2 - DL + CV: Week 8",
        "focus_dsa": "Graph Practice",
        "focus_ml_dl": "OpenCV, Image Preprocessing, Video Processing, Transfer Learning, Object Detection",
        "focus_sentinelai": "Visual Threat/Event Module (Month 2 Checkpoint)",
        "dsa_target_count": 18
    },
    {
        "week_number": 9, "month_number": 3, "title": "Month 3 - Advanced Intelligence: Week 9",
        "focus_dsa": "Greedy Algorithms, Intervals",
        "focus_ml_dl": "Autoencoders, Anomaly Detection",
        "focus_sentinelai": "Compare Isolation Forest, One-Class SVM & Autoencoder",
        "dsa_target_count": 20
    },
    {
        "week_number": 10, "month_number": 3, "title": "Month 3 - Advanced Intelligence: Week 10",
        "focus_dsa": "Dynamic Programming Fundamentals",
        "focus_ml_dl": "Transfer Learning, Fine-tuning",
        "focus_sentinelai": "Improve Visual Model",
        "dsa_target_count": 20
    },
    {
        "week_number": 11, "month_number": 3, "title": "Month 3 - Advanced Intelligence: Week 11",
        "focus_dsa": "Dijkstra, Topological Sort, Union Find",
        "focus_ml_dl": "Graph Representation of Events",
        "focus_sentinelai": "Threat/Event Correlation Engine",
        "dsa_target_count": 20
    },
    {
        "week_number": 12, "month_number": 3, "title": "Month 3 - Advanced Intelligence: Week 12",
        "focus_dsa": "Mixed Revision",
        "focus_ml_dl": "AI Explainability, Feature Importance, SHAP, Grad-CAM",
        "focus_sentinelai": "Risk Score, Explanations, Correlated Incidents (Month 3 Checkpoint)",
        "dsa_target_count": 20
    },
    {
        "week_number": 13, "month_number": 4, "title": "Month 4 - Engineering + Interview Mode: Week 13",
        "focus_dsa": "Timed Interview Sets",
        "focus_ml_dl": "FastAPI, Model Serving",
        "focus_sentinelai": "Prediction APIs",
        "dsa_target_count": 15
    },
    {
        "week_number": 14, "month_number": 4, "title": "Month 4 - Engineering + Interview Mode: Week 14",
        "focus_dsa": "Mock Interview Sets",
        "focus_ml_dl": "SQLite/PostgreSQL Schema, Persistence, Incident History",
        "focus_sentinelai": "Database-backed Incident History",
        "dsa_target_count": 15
    },
    {
        "week_number": 15, "month_number": 4, "title": "Month 4 - Engineering + Interview Mode: Week 15",
        "focus_dsa": "Mixed Mocks",
        "focus_ml_dl": "Docker, Logging, Error Handling, Monitoring",
        "focus_sentinelai": "Containerized System",
        "dsa_target_count": 15
    },
    {
        "week_number": 16, "month_number": 4, "title": "Month 4 - Engineering + Interview Mode: Week 16",
        "focus_dsa": "Final Revision",
        "focus_ml_dl": "Interview Defense Preparation",
        "focus_sentinelai": "README, Architecture Diagram, Demo Video, Limitations (Final Checkpoint)",
        "dsa_target_count": 15
    }
]

SENTINELAI_MILESTONES_DATA = [
    {"version": "V0.1", "target_week": 1, "title": "Data Ingestion & Baseline Classifier", "deliverables": ["data ingestion", "preprocessing", "baseline classifier"]},
    {"version": "V0.2", "target_week": 2, "title": "Model Comparison & Evaluation", "deliverables": ["normal vs attack classifier", "metrics logged", "model comparison"]},
    {"version": "V0.3", "target_week": 4, "title": "ML Anomaly Detection", "deliverables": ["Isolation Forest", "One-Class SVM", "anomaly metrics"]},
    {"version": "V0.4", "target_week": 5, "title": "Neural Network + PyTorch Baseline", "deliverables": ["NumPy neural network", "PyTorch baseline pipeline"]},
    {"version": "V0.5", "target_week": 6, "title": "ML vs DL Experiments", "deliverables": ["ML vs DL comparison report", "model trade-offs"]},
    {"version": "V0.6", "target_week": 8, "title": "Computer Vision Threat Module", "deliverables": ["OpenCV module", "image/video preprocessing", "visual threat detection"]},
    {"version": "V0.7", "target_week": 9, "title": "Autoencoder Anomaly Comparison", "deliverables": ["Autoencoder model", "comparison with Isolation Forest & One-Class SVM"]},
    {"version": "V0.8", "target_week": 11, "title": "Threat & Event Correlation Graph", "deliverables": ["graph representation of events", "threat correlation engine"]},
    {"version": "V0.9", "target_week": 12, "title": "Correlation + Risk Scoring", "deliverables": ["risk scoring algorithm", "correlated incidents summary"]},
    {"version": "V1.0", "target_week": 12, "title": "Explainable AI (SHAP / Grad-CAM)", "deliverables": ["feature importance", "SHAP explanations", "Grad-CAM concepts"]},
    {"version": "V1.1", "target_week": 13, "title": "FastAPI Model Serving APIs", "deliverables": ["FastAPI prediction endpoints", "model serving infrastructure"]},
    {"version": "V1.2", "target_week": 14, "title": "Database-Backed Incident History", "deliverables": ["SQLite schema", "persistence layer", "incident history querying"]},
    {"version": "V1.3", "target_week": 15, "title": "Containerization & Monitoring", "deliverables": ["Docker setup", "logging", "error handling", "monitoring"]},
    {"version": "V1.4", "target_week": 16, "title": "Final Portfolio System & Defense Prep", "deliverables": ["final dashboard/demo", "README", "architecture diagram", "interview defense"]}
]

ML_DL_CV_CONCEPTS = [
    # ML
    ("ML", "preprocessing", "learning"),
    ("ML", "feature engineering", "learning"),
    ("ML", "train/validation/test", "mastered"),
    ("ML", "cross-validation", "learning"),
    ("ML", "regression", "learning"),
    ("ML", "classification", "learning"),
    ("ML", "trees", "not_started"),
    ("ML", "ensembles", "not_started"),
    ("ML", "imbalance", "not_started"),
    ("ML", "metrics", "learning"),
    ("ML", "anomaly detection", "not_started"),
    ("ML", "model selection", "not_started"),
    ("ML", "explainability", "not_started"),
    # DL
    ("DL", "neural networks", "not_started"),
    ("DL", "activations", "not_started"),
    ("DL", "losses", "not_started"),
    ("DL", "gradient descent", "not_started"),
    ("DL", "backpropagation", "not_started"),
    ("DL", "optimizers", "not_started"),
    ("DL", "regularization", "not_started"),
    ("DL", "dropout", "not_started"),
    ("DL", "batch normalization", "not_started"),
    ("DL", "PyTorch", "not_started"),
    ("DL", "CNNs", "not_started"),
    # CV
    ("CV", "image preprocessing", "not_started"),
    ("CV", "OpenCV", "not_started"),
    ("CV", "convolution", "not_started"),
    ("CV", "classification", "not_started"),
    ("CV", "transfer learning", "not_started"),
    ("CV", "object detection", "not_started"),
    ("CV", "video processing", "not_started")
]

COLLEGE_SUBJECTS = [
    {
        "name": "Deep Learning",
        "code": "CS-701",
        "units": [
            ("Unit 1", ["Perceptron & Multilayer Perceptron", "Activation Functions", "Loss Functions & Gradient Descent"]),
            ("Unit 2", ["Backpropagation Algorithm", "Optimizers (SGD, Adam)", "Regularization & Dropout"]),
            ("Unit 3", ["Convolutional Neural Networks (CNN)", "Pooling & Stride", "PyTorch Implementations"])
        ]
    },
    {
        "name": "Computer Vision",
        "code": "CS-702",
        "units": [
            ("Unit 1", ["Image Preprocessing & Filtering", "Edge Detection", "OpenCV Fundamentals"]),
            ("Unit 2", ["Feature Extraction & Matching", "Convolution Operations", "Transfer Learning & Fine-tuning"])
        ]
    },
    {
        "name": "Design and Analysis of Algorithms",
        "code": "CS-503",
        "units": [
            ("Unit 1", ["Asymptotic Analysis (Big-O)", "Divide and Conquer", "Sorting & Searching"]),
            ("Unit 2", ["Greedy Algorithms", "Dynamic Programming", "Graph Algorithms (BFS, DFS, Dijkstra)"])
        ]
    }
]

async def safe_schema_upgrade(engine):
    """Executes safe ALTER TABLE statements to add new columns to existing SQLite tables without wiping data."""
    async with engine.begin() as conn:
        # Check day_logs columns
        res = await conn.execute(text("PRAGMA table_info(day_logs);"))
        columns = [row[1] for row in res.fetchall()]
        if "must_win_text" not in columns:
            await conn.execute(text("ALTER TABLE day_logs ADD COLUMN must_win_text TEXT;"))
        if "must_win_result" not in columns:
            await conn.execute(text("ALTER TABLE day_logs ADD COLUMN must_win_result TEXT;"))

        # Check dsa_logs columns
        res_dsa = await conn.execute(text("PRAGMA table_info(dsa_logs);"))
        dsa_columns = [row[1] for row in res_dsa.fetchall()]
        if dsa_columns and "solve_type" not in dsa_columns:
            await conn.execute(text("ALTER TABLE dsa_logs ADD COLUMN solve_type VARCHAR(30) DEFAULT 'solved';"))

async def init_db_for_mode(mode: str = "REAL", force_recreate: bool = False):
    """Initializes and seeds database for REAL, TEST, or DEMO mode while protecting existing data."""
    engine = _engines[mode]
    sessionmaker = _sessionmakers[mode]
    
    async with engine.begin() as conn:
        if force_recreate:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await safe_schema_upgrade(engine)

    async with sessionmaker() as session:
        result = await session.execute(select(SprintConfig))
        config = result.scalar_one_or_none()
        
        if not config:
            is_demo = (mode == "DEMO")
            today_str = date.today().isoformat()
            yesterday_str = (date.today() - timedelta(days=1)).isoformat()
            
            # 1. Sprint Config
            config = SprintConfig(
                env_mode=mode,
                sprint_activated=is_demo, # Active by default in DEMO
                actual_start_date="2026-08-24" if is_demo else None,
                actual_end_date="2026-12-21" if is_demo else None,
                total_days=120,
                current_mode="NORMAL",
                exam_mode_active=False
            )
            session.add(config)
            
            # 2. Seed Roadmap Weeks
            for w in ROADMAP_WEEKS_DATA:
                week_obj = RoadmapWeek(**w)
                session.add(week_obj)
                
            # 3. Seed SentinelAI Milestones
            for m in SENTINELAI_MILESTONES_DATA:
                m_data = m.copy()
                if is_demo and m["version"] in ["V0.1", "V0.2", "V0.3", "V0.4"]:
                    m_data["status"] = "completed"
                    m_data["completion_percentage"] = 100
                session.add(SentinelAIMilestone(**m_data))
                
            # 4. Seed Concepts
            for domain, name, status in ML_DL_CV_CONCEPTS:
                c_status = status
                if is_demo and domain in ["ML", "DL"]:
                    c_status = "mastered" if name in ["preprocessing", "train/validation/test", "neural networks", "activations"] else "learning"
                session.add(Concept(domain=domain, name=name, status=c_status))
                
            # 5. Seed College Subjects
            for s in COLLEGE_SUBJECTS:
                subj = CollegeSubject(name=s["name"], code=s["code"])
                session.add(subj)
                await session.flush()
                for unit_name, topics in s["units"]:
                    for top in topics:
                        t_status = "mastered" if is_demo and "Perceptron" in top else "not_started"
                        session.add(CollegeSyllabusTopic(subject_id=subj.id, unit_name=unit_name, topic_name=top, status=t_status))
                        
            # 6. Seed Demo Logs if DEMO mode (Constraint 7)
            if is_demo:
                for i in range(45):
                    session.add(DSALog(
                        problem_name=f"Demo DSA Problem #{i+1}",
                        topic="Arrays" if i < 20 else "Trees",
                        difficulty="Medium",
                        independent_solve=True,
                        time_taken_mins=25
                    ))
                session.add(Mistake(category="technical", mistake_type="missed pattern", description="Confused Sliding Window edge case", occurrences_count=2, resolved=False))
                session.add(CollegeEvent(title="Deep Learning Quiz 1", subject_name="Deep Learning", event_type="quiz", due_date="2026-08-28", priority="high", status="upcoming"))

                # Spaced Revisions (Today & Overdue)
                session.add(SpacedRevision(concept_name="Backpropagation", domain="DL", revision_number=1, scheduled_date=today_str, completed=False))
                session.add(SpacedRevision(concept_name="Binary Search", domain="DSA", revision_number=2, scheduled_date=today_str, completed=False))
                session.add(SpacedRevision(concept_name="CNN Architectures", domain="CV", revision_number=3, scheduled_date=yesterday_str, completed=False, overdue=True))
                session.add(SpacedRevision(concept_name="Bias-Variance Tradeoff", domain="ML", revision_number=1, scheduled_date=today_str, completed=False))

                # Weakness Records (Multiple levels)
                session.add(WeaknessRecord(topic="Dynamic Programming", category="DSA", mistake_count=8, severity="critical", resolved=False))
                session.add(WeaknessRecord(topic="Binary Search", category="DSA", mistake_count=6, severity="critical", resolved=False))
                session.add(WeaknessRecord(topic="CNN Architectures", category="CV", mistake_count=4, severity="high", resolved=False))
                session.add(WeaknessRecord(topic="Probability", category="ML", mistake_count=3, severity="medium", resolved=False))

                # Overdue Task for Recovery Mode demo
                session.add(Task(title="Overdue DSA DP Problem Set", category="DSA", priority="high", status="planned", due_date=yesterday_str, estimated_minutes=60))

                # Day Log with Must Win
                session.add(DayLog(
                    date=today_str,
                    day_number=2,
                    available_hours=4.0,
                    must_win_text="Solve 4 DSA problems and complete CNN backpropagation revision.",
                    status="active"
                ))

                # Weekly Review Data
                session.add(WeeklyReview(
                    week_number=1,
                    year=2026,
                    period_key="2026-W01",
                    dsa_target=18,
                    dsa_solved=16,
                    ml_dl_cv_target=4,
                    ml_dl_cv_completed=4,
                    sentinelai_version="V0.4",
                    sentinelai_status="100% Complete",
                    college_tasks_total=5,
                    college_tasks_completed=4,
                    top_weakness="Dynamic Programming",
                    revisions_scheduled=8,
                    revisions_completed=7,
                    must_win_success_rate=85.0,
                    q1_missed_work_cause="Overestimated college project time",
                    q2_biggest_difficulty="DP state space reduction",
                    q3_next_week_improvements="Start DSA early in morning",
                    q4_next_week_priority="Master Knapsack & Tree DP"
                ))

            await session.commit()
            print(f"StudyOS Database [{mode}] Initialized and Seeded Successfully!")

async def init_db():
    await init_db_for_mode("REAL")
    await init_db_for_mode("TEST")
    await init_db_for_mode("DEMO")

if __name__ == "__main__":
    asyncio.run(init_db())
