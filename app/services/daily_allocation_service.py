import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import select, and_

from app.db.models import (
    SprintConfig, RoadmapWeek, Task, DSALog, Concept, 
    SentinelAIMilestone, CollegeEvent, SpacedRevision
)
from app.services.revision_service import SpacedRevisionService
from app.services.recovery_service import RecoveryService

class DailyAllocationService:
    """
    Deterministic Daily Allocation Layer with Milestone-Aware Knowledge Dependency Mapping.
    Translates 16-week high-level roadmap objectives into realistic daily execution plans
    (2–5 meaningful tasks/day, 210m ceiling) following LEARN -> PRACTICE -> APPLY.
    Guarantees SentinelAI tasks ONLY apply concepts that are CURRENT or PREVIOUSLY_LEARNED.
    """

    # Knowledge Dependency Map: Maps week number to available technologies & milestone deliverables
    SENTINELAI_KNOWLEDGE_MAP = {
        1: {
            "applied_concept": "NumPy & Pandas Data Ingestion",
            "concept_learned_week": 1,
            "deliverables": {
                1: "Set up repository structure & inspect network security raw dataset",
                2: "Build data ingestion pipeline for network logs using Pandas",
                3: "Implement data validation and schema checks using NumPy",
                4: "Build feature preprocessing and normalization pipeline",
                5: "Implement baseline statistical classifier for network traffic",
                6: "Evaluate baseline precision/recall on test log dataset",
                7: "Review V0.1 baseline code & document findings"
            }
        },
        2: {
            "applied_concept": "Classification & Evaluation Metrics",
            "concept_learned_week": 2,
            "deliverables": {
                1: "Inspect V0.1 data pipeline and design classification target labels",
                2: "Implement normal vs attack classification target labels",
                3: "Train Logistic Regression attack classifier on traffic features",
                4: "Integrate precision, recall & F1 score logger",
                5: "Run cross-validation on V0.2 classification model",
                6: "Log confusion matrix & classification metrics summary",
                7: "Review V0.2 classifier performance & code refactoring"
            }
        },
        3: {
            "applied_concept": "Model Selection & Tree Ensembles",
            "concept_learned_week": 3,
            "deliverables": {
                1: "Inspect V0.2 pipeline and design modular model comparison harness",
                2: "Build modular model comparison harness extending V0.2",
                3: "Train Random Forest classifier on network traffic logs",
                4: "Train XGBoost classifier & compare execution latency",
                5: "Evaluate model trade-offs (Random Forest vs XGBoost vs Logistic)",
                6: "Select top-performing model artifact for V0.3 baseline",
                7: "Review model comparison results & source structure"
            }
        },
        4: {
            "applied_concept": "Isolation Forest & One-Class SVM Anomaly Detection",
            "concept_learned_week": 4,
            "deliverables": {
                1: "Inspect network traffic feature distribution for anomaly detection",
                2: "Implement Isolation Forest model for unsupervised threat detection",
                3: "Implement One-Class SVM for zero-day attack identification",
                4: "Combine supervised classifier with unsupervised anomaly detector",
                5: "Evaluate ROC-AUC & PR-AUC anomaly detection metrics",
                6: "Run benchmark tests on Month 1 Checkpoint anomaly pipeline",
                7: "Consolidate V0.3 anomaly detection module & code review"
            }
        },
        5: {
            "applied_concept": "PyTorch & Neural Network Baseline",
            "concept_learned_week": 5,
            "deliverables": {
                1: "Inspect existing V0.3 pipeline and identify where neural-network baseline will be integrated",
                2: "Implement minimal PyTorch model tensor loader separately",
                3: "Prepare SentinelAI network traffic tensors for PyTorch model",
                4: "Implement SentinelAI PyTorch neural-network threat baseline model",
                5: "Train & evaluate PyTorch model against V0.3 baseline",
                6: "Perform error analysis & hyperparameter inspection",
                7: "Integrate PyTorch baseline into main SentinelAI repository"
            }
        },
        6: {
            "applied_concept": "DL Optimizers & Regularization (Adam, Dropout)",
            "concept_learned_week": 6,
            "deliverables": {
                1: "Inspect PyTorch model loss curves and identify regularization points",
                2: "Add Adam optimizer & learning rate scheduler to PyTorch model",
                3: "Add Dropout and Batch Normalization layers to neural network",
                4: "Run ML vs DL comparative benchmarks (Random Forest vs PyTorch)",
                5: "Analyze trade-offs between inference speed, memory & accuracy",
                6: "Generate ML vs DL comparison report artifact",
                7: "Review V0.5 model trade-offs & code cleanup"
            }
        },
        7: {
            "applied_concept": "CNN & Convolutional Feature Extractor",
            "concept_learned_week": 7,
            "deliverables": {
                1: "Inspect packet payload structures for 1D CNN feature extraction",
                2: "Design 1D CNN architecture for sequential network packet logs",
                3: "Implement 1D Conv layers for automatic spatial feature extraction",
                4: "Train 1D CNN model on packet payloads extending V0.5",
                5: "Evaluate 1D CNN threat detection performance against PyTorch MLP",
                6: "Validate visual pipeline data structures for Month 2 CV module",
                7: "Review visual intelligence pipeline architecture"
            }
        },
        8: {
            "applied_concept": "OpenCV & Image Preprocessing",
            "concept_learned_week": 8,
            "deliverables": {
                1: "Apply learned image preprocessing operations to existing visual threat pipeline",
                2: "Build OpenCV video frame ingestion and bounding box pipeline",
                3: "Apply frame preprocessing to SentinelAI security camera feeds",
                4: "Implement visual feature extraction pipeline for security feeds",
                5: "Integrate visual threat detection module into SentinelAI",
                6: "Evaluate visual threat detector accuracy on test video logs",
                7: "Perform visual model error analysis & Month 2 checkpoint review"
            }
        },
        9: {
            "applied_concept": "Autoencoders for Anomaly Detection",
            "concept_learned_week": 9,
            "deliverables": {
                1: "Inspect unsupervised baseline and design PyTorch Autoencoder architecture",
                2: "Build PyTorch Autoencoder architecture for network payload logs",
                3: "Train Autoencoder on normal network traffic to learn baseline representation",
                4: "Compute reconstruction error thresholds for anomaly detection",
                5: "Compare Autoencoder vs Isolation Forest vs One-Class SVM",
                6: "Benchmark anomaly detection latency across all 3 unsupervised models",
                7: "Consolidate V0.7 Autoencoder anomaly comparison pipeline"
            }
        },
        10: {
            "applied_concept": "Transfer Learning & Pretrained Backbones",
            "concept_learned_week": 10,
            "deliverables": {
                1: "Inspect existing V0.6 visual model and identify where transfer learning can improve it",
                2: "Prepare pretrained backbone selection (ResNet/MobileNet) for SentinelAI",
                3: "Build fine-tuning pipeline for pretrained visual backbone",
                4: "Prepare SentinelAI image dataset & data loader for fine-tuning",
                5: "Apply transfer learning fine-tuning to SentinelAI visual model",
                6: "Evaluate fine-tuned visual model against V0.6 OpenCV baseline",
                7: "Perform error analysis & consolidate V0.7 visual pipeline"
            }
        },
        11: {
            "applied_concept": "Graph Representation of Security Events",
            "concept_learned_week": 11,
            "deliverables": {
                1: "Inspect multi-vector incident logs and design event graph schema",
                2: "Construct graph adjacency data structures for security incident logs",
                3: "Map network IPs, user sessions & visual threats as connected graph nodes",
                4: "Implement graph traversal algorithm for threat correlation",
                5: "Run multi-source incident correlation experiments",
                6: "Validate correlation engine output on multi-vector attack scenarios",
                7: "Review V0.8 Threat & Event Correlation Engine architecture"
            }
        },
        12: {
            "applied_concept": "AI Explainability (SHAP / Grad-CAM) & Risk Scoring",
            "concept_learned_week": 12,
            "deliverables": {
                1: "Inspect threat model predictions and design explainability hooks",
                2: "Implement SHAP feature importance explainer for ML threat models",
                3: "Implement Grad-CAM heatmap visualization for visual threat model",
                4: "Build composite threat risk scoring algorithm (0-100 score)",
                5: "Generate human-readable explanation summaries for security incidents",
                6: "Run Month 3 Checkpoint end-to-end evaluation with explanations",
                7: "Review risk scoring and explainability pipeline"
            }
        },
        13: {
            "applied_concept": "FastAPI & Model Serving APIs",
            "concept_learned_week": 13,
            "deliverables": {
                1: "Design the prediction API contract around existing SentinelAI trained models",
                2: "Implement request/response Pydantic schemas for threat inference",
                3: "Implement `/predict` threat detection endpoint in FastAPI router",
                4: "Connect trained PyTorch & ML model inference to FastAPI prediction endpoint",
                5: "Add async batch prediction endpoints & error handling",
                6: "Validate API endpoint latency & run integration test payloads",
                7: "Generate API OpenAPI documentation & review endpoint security"
            }
        },
        14: {
            "applied_concept": "SQLite Persistence & Incident History",
            "concept_learned_week": 14,
            "deliverables": {
                1: "Design database schema for SentinelAI incident logs & risk scores",
                2: "Implement async database persistence layer for prediction API",
                3: "Build incident query endpoints (`/incidents/history`, `/incidents/search`)",
                4: "Test transaction safety, filtering & historical log retrieval",
                5: "Verify API integration with persistent SQLite database backend",
                6: "Run stress test on database incident logger under concurrent requests",
                7: "Review V1.2 Database-Backed Incident History system"
            }
        },
        15: {
            "applied_concept": "Docker Containerization & Monitoring",
            "concept_learned_week": 15,
            "deliverables": {
                1: "Inspect SentinelAI microservices and write Dockerfile build configuration",
                2: "Write Dockerfile & multi-stage build script for SentinelAI service",
                3: "Configure structured JSON logging & error boundary handlers",
                4: "Implement health check `/health` endpoint & system metrics logger",
                5: "Run containerized SentinelAI service in isolated Docker container",
                6: "Validate API performance & memory usage under load in container",
                7: "Review V1.3 Containerized System architecture"
            }
        },
        16: {
            "applied_concept": "Portfolio Documentation & Interview Defense",
            "concept_learned_week": 16,
            "deliverables": {
                1: "Draft SentinelAI system architecture & comprehensive README",
                2: "Create end-to-end dataflow & ML pipeline architecture diagram",
                3: "Prepare end-to-end demo workflow across V0.1 to V1.3 modules",
                4: "Record SentinelAI live demonstration video walkthrough",
                5: "Document model trade-offs, system limitations & future work",
                6: "Practice interview defense questions on SentinelAI architecture",
                7: "Final portfolio review & freeze system repository"
            }
        }
    }

    @staticmethod
    async def get_daily_allocation(
        session, 
        mode: str = "REAL", 
        custom_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        target_date_str = custom_date_str or date.today().isoformat()
        
        # 1. Sprint Config & Position
        cfg_res = await session.execute(select(SprintConfig))
        config = cfg_res.scalar_one_or_none()
        
        sprint_activated = config.sprint_activated if config else False
        exam_mode_active = config.exam_mode_active if config else False
        
        if not sprint_activated:
            current_day = 1
            current_week = 1
            day_in_week = 1
            total_days_in_week = 7
        else:
            start_dt = datetime.strptime(config.actual_start_date, "%Y-%m-%d").date()
            cur_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            days_elapsed = (cur_dt - start_dt).days + 1
            current_day = max(1, min(days_elapsed, 120))
            
            if current_day <= 105:
                current_week = ((current_day - 1) // 7) + 1
                day_in_week = ((current_day - 1) % 7) + 1
                total_days_in_week = 7
            else:
                current_week = 16
                day_in_week = current_day - 105
                total_days_in_week = 15

        # 2. Fetch Active Roadmap Week
        week_res = await session.execute(
            select(RoadmapWeek).where(RoadmapWeek.week_number == current_week)
        )
        week_obj = week_res.scalar_one_or_none()
        if not week_obj:
            weekly_dsa_target = 18 if current_week <= 8 else (20 if current_week <= 12 else 15)
            focus_dsa = "Core DSA Patterns"
            focus_ml_dl = "Core ML/DL Foundations"
            focus_sentinelai = "SentinelAI Engineering"
        else:
            weekly_dsa_target = week_obj.dsa_target_count
            focus_dsa = week_obj.focus_dsa
            focus_ml_dl = week_obj.focus_ml_dl
            focus_sentinelai = week_obj.focus_sentinelai

        # 3. Adaptive DSA Calculation (Interview Mastery Principle)
        dsa_logs_res = await session.execute(select(DSALog))
        all_dsa_logs = dsa_logs_res.scalars().all()
        
        weekly_completed = len([d for d in all_dsa_logs if d.independent_solve or d.solve_type in ["solved", "solved_with_help", "studied_solution"]]) if mode == "DEMO" else 0
        weekly_remaining = max(0, weekly_dsa_target - weekly_completed)
        
        remaining_days_in_week = max(1, total_days_in_week - day_in_week + 1)
        
        if weekly_remaining == 0:
            daily_dsa_count = 0
            dsa_task_type = "NONE"
        else:
            if day_in_week == 1:
                dsa_task_type = "LEARNING"
                # LEARNING tasks prioritize pattern exposure & theory -> lower problem count (1-2 problems)
                daily_dsa_count = min(2, max(1, math.ceil(weekly_remaining / remaining_days_in_week)))
            elif day_in_week == total_days_in_week:
                dsa_task_type = "CATCHUP" if weekly_remaining > 0 else "NONE"
                daily_dsa_count = min(2, weekly_remaining) if weekly_remaining > 0 else 0
            elif current_week >= 13:
                dsa_task_type = "INTERVIEW/MOCK"
                daily_dsa_count = min(3, max(1, math.ceil(weekly_remaining / remaining_days_in_week)))
            else:
                dsa_task_type = "PRACTICE"
                daily_dsa_count = min(3, max(1, math.ceil(weekly_remaining / remaining_days_in_week)))

        # 4. Spaced Revisions Due
        revisions_summary = await SpacedRevisionService.get_todays_revisions(session, target_date_str)
        due_revisions = revisions_summary["today"] + revisions_summary["overdue"]
        
        # 5. College Events Today
        college_events_res = await session.execute(
            select(CollegeEvent).where(
                and_(
                    CollegeEvent.due_date == target_date_str,
                    CollegeEvent.status != "completed"
                )
            )
        )
        college_events_today = college_events_res.scalars().all()
        
        # 6. Recovery Mode Status
        rec_plan = await RecoveryService.get_recovery_plan(session)
        recovery_active = rec_plan["recovery_mode_active"]

        # 7. Construct Deterministic Task List (2–5 tasks, max scheduled cap 210m)
        # Priority Order: 1. College, 2. Today's Must Win, 3. DSA Learning, 4. ML/DL Learning, 5. SentinelAI Application, 6. Revision, 7. Recovery
        scheduled_tasks: List[Dict[str, Any]] = []
        total_mins = 0
        MAX_SCHEDULED_MINS = 210  # 240m budget - 30m protected buffer

        # Fetch knowledge dependency mapping for active week
        week_sentinel_info = DailyAllocationService.SENTINELAI_KNOWLEDGE_MAP.get(
            current_week, 
            DailyAllocationService.SENTINELAI_KNOWLEDGE_MAP[16]
        )

        # EXAM MODE BUDGET ALLOCATION
        if exam_mode_active:
            exam_task_title = f"College Exam Prep & Review ({college_events_today[0].title if college_events_today else 'Midterm Review'})"
            scheduled_tasks.append({
                "title": exam_task_title,
                "category": "College",
                "priority": "high",
                "estimated_minutes": 120,
                "type": "EXAM_PREP"
            })
            total_mins += 120
            
            if due_revisions and total_mins + 15 <= MAX_SCHEDULED_MINS:
                rev = due_revisions[0]
                scheduled_tasks.append({
                    "title": f"Spaced Revision: [{rev['domain']}] {rev['concept_name']}",
                    "category": "Review",
                    "priority": "high",
                    "estimated_minutes": 15,
                    "type": "REVISION"
                })
                total_mins += 15

            if daily_dsa_count > 0 and total_mins + 45 <= MAX_SCHEDULED_MINS:
                scheduled_tasks.append({
                    "title": f"DSA Maintenance ({dsa_task_type}): Solve 1 problem on {focus_dsa.split(',')[0]}",
                    "category": "DSA",
                    "priority": "medium",
                    "estimated_minutes": 45,
                    "type": dsa_task_type
                })
                total_mins += 45

        # NORMAL / RECOVERY MODE ALLOCATION
        else:
            # Step 1: Actual College Deadlines/Events
            for ce in college_events_today:
                if total_mins + 60 <= MAX_SCHEDULED_MINS:
                    scheduled_tasks.append({
                        "title": f"College Task: {ce.title} ({ce.subject_name})",
                        "category": "College",
                        "priority": "high",
                        "estimated_minutes": 60,
                        "type": "COLLEGE"
                    })
                    total_mins += 60

            # Step 2: Today's DSA Learning/Practice Task
            if daily_dsa_count > 0:
                dsa_est = 60 if dsa_task_type == "LEARNING" else (75 if dsa_task_type == "PRACTICE" else 50)
                if total_mins + dsa_est <= MAX_SCHEDULED_MINS:
                    topic_subset = focus_dsa.split(',')[0].strip()
                    dsa_title = f"DSA ({dsa_task_type}): Study {topic_subset} pattern & solve {daily_dsa_count} problem{'s' if daily_dsa_count > 1 else ''}"
                    scheduled_tasks.append({
                        "title": dsa_title,
                        "category": "DSA",
                        "priority": "high" if dsa_task_type in ["LEARNING", "INTERVIEW/MOCK"] else "medium",
                        "estimated_minutes": dsa_est,
                        "type": dsa_task_type
                    })
                    total_mins += dsa_est

            # Step 3: ML / DL / CV Learning Task (Occurs BEFORE SentinelAI application)
            if day_in_week != 7: # Light Day 7 skips heavy ML lecture
                ml_est = 45
                if total_mins + ml_est <= MAX_SCHEDULED_MINS:
                    ml_topic = focus_ml_dl.split(',')[0].strip()
                    ml_stage = "LEARNING" if day_in_week in [1, 2, 4] else "PRACTICE"
                    scheduled_tasks.append({
                        "title": f"ML/DL ({ml_stage}): Learn {ml_topic} concept & complete exercise",
                        "category": "ML",
                        "priority": "medium",
                        "estimated_minutes": ml_est,
                        "type": ml_stage
                    })
                    total_mins += ml_est

            # Step 4: SentinelAI Milestone Application Task (Strictly applies CURRENT or PREVIOUSLY_LEARNED concepts)
            if day_in_week != 7 and not recovery_active:
                sentinel_est = 45
                if total_mins + sentinel_est <= MAX_SCHEDULED_MINS:
                    deliv_dict = week_sentinel_info["deliverables"]
                    day_key = min(day_in_week, len(deliv_dict))
                    sentinel_deliv_text = deliv_dict[day_key]
                    
                    concept_status = "CURRENT" if week_sentinel_info["concept_learned_week"] == current_week else "PREVIOUSLY_LEARNED"
                    
                    scheduled_tasks.append({
                        "title": f"SentinelAI (Day {day_in_week}): {sentinel_deliv_text}",
                        "category": "SentinelAI",
                        "priority": "medium",
                        "estimated_minutes": sentinel_est,
                        "type": "SENTINELAI",
                        "applied_concept": week_sentinel_info["applied_concept"],
                        "concept_learned_week": week_sentinel_info["concept_learned_week"],
                        "concept_status": concept_status,
                        "dependency_status": "AVAILABLE_FOR_APPLICATION",
                        "application_lifecycle": "APPLIED"
                    })
                    total_mins += sentinel_est

            # Step 5: Spaced Revisions (if due)
            if due_revisions:
                rev = due_revisions[0]
                if total_mins + 15 <= MAX_SCHEDULED_MINS:
                    scheduled_tasks.append({
                        "title": f"Spaced Revision: [{rev['domain']}] {rev['concept_name']}",
                        "category": "Review",
                        "priority": "medium",
                        "estimated_minutes": 15,
                        "type": "REVISION"
                    })
                    total_mins += 15

            # Step 6: Light Day 7 Consolidation Tasks
            if day_in_week == 7:
                if total_mins + 45 <= MAX_SCHEDULED_MINS:
                    scheduled_tasks.append({
                        "title": "Weekly Review: Complete 4 reflection questions & generate report",
                        "category": "Review",
                        "priority": "high",
                        "estimated_minutes": 45,
                        "type": "WEEKLY_REVIEW"
                    })
                    total_mins += 45

            # Step 7: Recovery Overlay (if active)
            if recovery_active and total_mins + 30 <= MAX_SCHEDULED_MINS:
                scheduled_tasks.append({
                    "title": f"Recovery Mode: Overdue backlog clearing ({rec_plan['recovery_workload_hours']}h capped)",
                    "category": "General",
                    "priority": "high",
                    "estimated_minutes": 30,
                    "type": "RECOVERY"
                })
                total_mins += 30

        # 8. Capacity Risk Warning Check
        required_weekly_mins = (weekly_remaining * 30) + 120
        available_weekly_capacity = remaining_days_in_week * MAX_SCHEDULED_MINS
        capacity_risk_warning = None
        if required_weekly_mins > available_weekly_capacity and not exam_mode_active:
            capacity_risk_warning = (
                f"⚠️ WEEKLY CAPACITY RISK: {weekly_remaining} DSA problems cannot fit into "
                f"remaining {remaining_days_in_week} days without exceeding daily 210m cap. "
                f"Deficit delegated to Recovery Mode."
            )

        return {
            "sprint_activated": sprint_activated,
            "current_day": current_day,
            "current_week": current_week,
            "day_in_week": day_in_week,
            "total_days_in_week": total_days_in_week,
            "week_title": week_obj.title if week_obj else f"Week {current_week}",
            "focus_dsa": focus_dsa,
            "focus_ml_dl": focus_ml_dl,
            "focus_sentinelai": focus_sentinelai,
            "weekly_dsa_target": weekly_dsa_target,
            "weekly_completed": weekly_completed,
            "weekly_remaining": weekly_remaining,
            "daily_dsa_count": daily_dsa_count,
            "dsa_task_type": dsa_task_type,
            "exam_mode_active": exam_mode_active,
            "recovery_mode_active": recovery_active,
            "sentinelai_applied_concept": week_sentinel_info["applied_concept"],
            "sentinelai_concept_learned_week": week_sentinel_info["concept_learned_week"],
            "tasks": scheduled_tasks,
            "total_scheduled_mins": total_mins,
            "protected_buffer_mins": 30,
            "unscheduled_rest_mins": max(0, MAX_SCHEDULED_MINS - total_mins),
            "capacity_risk_warning": capacity_risk_warning
        }
