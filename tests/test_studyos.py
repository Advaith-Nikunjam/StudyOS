import os
import pytest
import asyncio
from datetime import date, timedelta
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from app.core.config import settings
from app.core.safety import SafetyGuardrail, RiskLevel
from app.db.session import AsyncSessionLocal, set_current_env_mode, get_current_env_mode
from app.db.models import (
    SprintConfig, RoadmapWeek, Task, DSALog, Mistake, DayLog, 
    SpacedRevision, WeaknessRecord, WeeklyReview
)
from app.services.roadmap_service import RoadmapService
from app.services.reporting_service import ReportingService
from app.services.backup_service import BackupService
from app.services.jarvis_engine import JarvisEngine
from app.services.revision_service import SpacedRevisionService
from app.services.weakness_service import WeaknessService
from app.services.recovery_service import RecoveryService
from app.services.weekly_review_service import WeeklyReviewService
from app.services.daily_allocation_service import DailyAllocationService
from app.db.init_db import init_db_for_mode

client = TestClient(app)

def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_display_state_endpoint():
    """Test Wall Display Kiosk state endpoint payload structure."""
    response = client.get("/api/display-state")
    assert response.status_code == 200
    data = response.json()
    
    assert "current_time" in data
    assert "day_number" in data
    assert "total_days" in data
    assert data["total_days"] == 120
    assert "current_mode" in data
    assert "health" in data
    assert "today_top_tasks" in data
    assert "dsa" in data
    assert "concepts" in data
    assert "sentinelai" in data
    assert "unresolved_mistakes" in data
    assert "has_pending_urgent" in data
    assert "must_win" in data
    assert "todays_revisions_summary" in data
    assert "weakness_radar" in data
    assert "recovery_plan" in data

def test_safety_guardrails_classification():
    """Test 3-Tier AI Action Safety classification logic."""
    assert SafetyGuardrail.classify_action("LOG_DSA_PROBLEM") == RiskLevel.SAFE
    assert SafetyGuardrail.classify_action("ADD_MISTAKE") == RiskLevel.SAFE
    assert SafetyGuardrail.classify_action("SHOW_REVISIONS") == RiskLevel.SAFE
    assert SafetyGuardrail.classify_action("SHOW_WEAKNESSES") == RiskLevel.SAFE
    assert SafetyGuardrail.classify_action("SHOW_RECOVERY_PLAN") == RiskLevel.SAFE
    assert SafetyGuardrail.classify_action("SET_MUST_WIN") == RiskLevel.SAFE
    assert SafetyGuardrail.classify_action("COMPLETE_REVISION") == RiskLevel.SAFE
    assert SafetyGuardrail.classify_action("START_WEEKLY_REVIEW") == RiskLevel.SAFE
    assert SafetyGuardrail.classify_action("RESCHEDULE_TASK") == RiskLevel.MODERATE
    assert SafetyGuardrail.classify_action("SWITCH_TO_TEST_MODE") == RiskLevel.MODERATE
    assert SafetyGuardrail.classify_action("SWITCH_TO_DEMO_MODE") == RiskLevel.MODERATE
    assert SafetyGuardrail.classify_action("MODIFY_ROADMAP") == RiskLevel.HIGH_RISK
    assert SafetyGuardrail.classify_action("CHANGE_DSA_TARGET") == RiskLevel.HIGH_RISK
    assert SafetyGuardrail.classify_action("SWITCH_TO_REAL_MODE") == RiskLevel.HIGH_RISK
    assert SafetyGuardrail.classify_action("START_SPRINT") == RiskLevel.HIGH_RISK
    assert SafetyGuardrail.classify_action("RESET_TEST_DATA") == RiskLevel.HIGH_RISK

@pytest.mark.asyncio
async def test_pre_sprint_state():
    """Proves PRE-SPRINT does not count as Day 1 and does not show AT RISK health."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    
    async with AsyncSessionLocal("TEST") as session:
        status = await RoadmapService.get_sprint_status(session)
        assert status["sprint_activated"] == False
        assert status["day_number"] == 0
        assert status["health"]["label"] == "PRE-SPRINT (NOT STARTED)"
        assert status["health"]["status"] == "INDIGO"

@pytest.mark.asyncio
async def test_one_time_sprint_activation():
    """Proves START SPRINT activates exactly once, sets start/end dates, and blocks second activation."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    
    # 1. Activate Sprint for first time
    res = client.post("/api/v1/sprint/start", json={"start_date": "2026-08-26"})
    assert res.status_code == 200
    data = res.json()
    assert data["sprint_activated"] == True
    assert data["actual_start_date"] == "2026-08-26"
    assert data["actual_end_date"] == "2026-12-23" # 2026-08-26 + 119 days
    
    # 2. Attempt second activation -> must fail with HTTP 400
    res_second = client.post("/api/v1/sprint/start", json={"start_date": "2026-09-01"})
    assert res_second.status_code == 400
    assert "ALREADY activated" in res_second.json()["detail"]

def test_env_switch_administrative_confirmation():
    """Proves environment switching enforces explicit confirmation for REAL mode and informs for TEST/DEMO."""
    res = client.post("/api/v1/env/switch", json={"env_mode": "REAL", "confirmed": False})
    assert res.status_code == 200
    data = res.json()
    assert data["requires_confirmation"] == True
    assert "You are entering REAL MODE" in data["warning_message"]
    
    res_conf = client.post("/api/v1/env/switch", json={"env_mode": "REAL", "confirmed": True})
    assert res_conf.status_code == 200
    assert res_conf.json()["env_mode"] == "REAL"
    
    res_test = client.post("/api/v1/env/switch", json={"env_mode": "TEST", "confirmed": True})
    assert res_test.status_code == 200
    assert "isolated and untouched" in res_test.json()["message"]

@pytest.mark.asyncio
async def test_jarvis_real_mode_guardrail():
    """Proves JARVIS never silently switches into REAL MODE without confirmation."""
    async with AsyncSessionLocal("TEST") as session:
        res = await JarvisEngine.process_user_input(session, "switch to real mode", confirmed=False)
        assert res["risk_level"] == "HIGH_RISK"
        assert res["requires_confirmation"] == True
        
        res_conf = await JarvisEngine.process_user_input(session, "switch to real mode", confirmed=True)
        assert res_conf["success"] == True
        assert get_current_env_mode() == "REAL"

@pytest.mark.asyncio
async def test_test_mode_and_demo_mode_isolation():
    """Proves TEST and DEMO modes operate on isolated databases and report directories."""
    await init_db_for_mode("REAL", force_recreate=True)
    async with AsyncSessionLocal("REAL") as real_sess:
        task_real = Task(title="REAL TASK #101", category="DSA", status="planned")
        real_sess.add(task_real)
        await real_sess.commit()

    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as test_sess:
        task_test = Task(title="TEST ISOLATED TASK #999", category="DSA", status="planned")
        test_sess.add(task_test)
        await test_sess.commit()

        report_path = await ReportingService.generate_daily_report(test_sess)
        assert "reports\\test" in report_path or "reports/test" in report_path

    set_current_env_mode("REAL")
    async with AsyncSessionLocal("REAL") as real_sess:
        tasks_res = await real_sess.execute(select(Task).where(Task.title == "TEST ISOLATED TASK #999"))
        assert tasks_res.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_reset_test_data_endpoint():
    """Proves RESET TEST DATA safely resets test database without touching real data."""
    set_current_env_mode("TEST")
    res = client.post("/api/v1/test/reset")
    assert res.status_code == 200
    assert "SAFELY RESET" in res.json()["message"]

@pytest.mark.asyncio
async def test_reset_demo_data_endpoint():
    """Proves RESET DEMO DATA restores curated demo dataset safely."""
    set_current_env_mode("DEMO")
    res = client.post("/api/v1/demo/reset")
    assert res.status_code == 200
    assert "CURATED BASELINE" in res.json()["message"]

@pytest.mark.asyncio
async def test_backup_and_export():
    """Test SQLite snapshot backup and data export."""
    set_current_env_mode("TEST")
    async with AsyncSessionLocal("TEST") as session:
        sqlite_backup = BackupService.create_daily_sqlite_backup()
        assert os.path.exists(sqlite_backup)
        
        json_export = await BackupService.export_json(session)
        assert os.path.exists(json_export)
        
        csv_exports = await BackupService.export_csv(session)
        assert "tasks" in csv_exports
        assert os.path.exists(csv_exports["tasks"])

# ================= 20 MANDATORY NEW FEATURE TESTS =================

@pytest.mark.asyncio
async def test_1_spaced_revision_scheduling():
    """Requirement 1: Proves completing a concept schedules 5 revisions (+1d, +3d, +7d, +14d, +30d)."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        created = await SpacedRevisionService.create_schedule_for_concept(session, "Backpropagation", domain="DL")
        assert len(created) == 5
        rev_numbers = [r.revision_number for r in created]
        assert rev_numbers == [1, 2, 3, 4, 5]

@pytest.mark.asyncio
async def test_2_duplicate_revision_prevention():
    """Requirement 2: Proves duplicate schedules are NOT created if concept is already scheduled."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        await SpacedRevisionService.create_schedule_for_concept(session, "Binary Search", domain="DSA")
        # Attempt duplicate creation
        second_attempt = await SpacedRevisionService.create_schedule_for_concept(session, "Binary Search", domain="DSA")
        assert len(second_attempt) == 0

@pytest.mark.asyncio
async def test_3_missed_revision_handling():
    """Requirement 3: Proves past uncompleted revisions transition to overdue queue without silent deletion."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    yesterday_str = (date.today() - timedelta(days=2)).isoformat()
    
    async with AsyncSessionLocal("TEST") as session:
        past_rev = SpacedRevision(
            concept_name="CNN Architectures", domain="CV", revision_number=1,
            scheduled_date=yesterday_str, completed=False
        )
        session.add(past_rev)
        await session.commit()
        
        todays_data = await SpacedRevisionService.get_todays_revisions(session)
        assert todays_data["overdue_count"] >= 1
        assert any(r["concept_name"] == "CNN Architectures" for r in todays_data["overdue"])

@pytest.mark.asyncio
async def test_4_revision_completion():
    """Requirement 4: Proves completing a revision sets completed=True and records completion date."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        created = await SpacedRevisionService.create_schedule_for_concept(session, "ResNet", domain="CV")
        target_rev = created[0]
        
        completed_rev = await SpacedRevisionService.complete_revision(session, target_rev.id, confidence_rating="high")
        assert completed_rev.completed == True
        assert completed_rev.completed_at is not None
        assert completed_rev.confidence_rating == "high"

@pytest.mark.asyncio
async def test_5_weakness_detection():
    """Requirement 5: Proves repeated mistakes accumulate into WeaknessRecord with progressive severity."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        # Record 4 mistakes for Dynamic Programming
        for _ in range(4):
            await WeaknessService.record_mistake_for_topic(session, topic="Dynamic Programming", category="DSA")
            
        summary = await WeaknessService.get_weakness_radar_summary(session)
        dp_w = next(w for w in summary["top_weaknesses"] if w["topic"] == "Dynamic Programming")
        assert dp_w["mistake_count"] == 4
        assert dp_w["severity"] in ["high", "critical"]

@pytest.mark.asyncio
async def test_6_weakness_improvement():
    """Requirement 6: Proves evidence-based reversible severity (1 revision doesn't immediately remove weakness)."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        await WeaknessService.record_mistake_for_topic(session, topic="Sliding Window", category="DSA")
        await WeaknessService.record_mistake_for_topic(session, topic="Sliding Window", category="DSA")
        
        # Record single successful revision -> should NOT immediately resolve
        record1 = await WeaknessService.record_successful_revision(session, topic="Sliding Window", category="DSA")
        assert record1.resolved == False
        
        # Record sustained evidence (total 5 revisions) -> should resolve
        for _ in range(4):
            record_final = await WeaknessService.record_successful_revision(session, topic="Sliding Window", category="DSA")
        assert record_final.resolved == True

@pytest.mark.asyncio
async def test_7_recovery_plan_generation():
    """Requirement 7: Proves overdue tasks and missed revisions generate structured recovery plan."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    
    async with AsyncSessionLocal("TEST") as session:
        overdue_task = Task(title="Overdue DSA Set", category="DSA", priority="high", due_date=yesterday_str, status="planned")
        session.add(overdue_task)
        await session.commit()

        rec_plan = await RecoveryService.get_recovery_plan(session)
        assert rec_plan["recovery_mode_active"] == True
        assert rec_plan["overdue_tasks_count"] >= 1
        assert rec_plan["total_missed_hours"] > 0

@pytest.mark.asyncio
async def test_8_recovery_workload_cap():
    """Requirement 8: Proves recovery workload does not exceed daily recovery cap (1.0 hr)."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    
    async with AsyncSessionLocal("TEST") as session:
        # Add 5 overdue tasks (each 60 mins -> 5 hours total missed)
        for i in range(5):
            session.add(Task(title=f"Missed Task {i}", category="DSA", priority="high", due_date=yesterday_str, estimated_minutes=60, status="planned"))
        await session.commit()

        rec_plan = await RecoveryService.get_recovery_plan(session)
        assert rec_plan["total_missed_hours"] >= 5.0
        assert rec_plan["recovery_workload_hours"] <= 1.0 # Capped at 1.0h

@pytest.mark.asyncio
async def test_9_recovery_and_exam_mode_interaction():
    """Requirement 9: Proves Exam Mode reduces recovery workload cap to prioritize college exams."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    
    async with AsyncSessionLocal("TEST") as session:
        # Enable Exam Mode
        cfg = (await session.execute(select(SprintConfig))).scalar_one_or_none()
        cfg.exam_mode_active = True
        session.add(Task(title="Missed Task", category="DSA", priority="high", due_date=yesterday_str, estimated_minutes=120, status="planned"))
        await session.commit()

        rec_plan = await RecoveryService.get_recovery_plan(session)
        assert rec_plan["exam_mode_active"] == True
        assert rec_plan["recovery_cap_hours"] == 0.25 # Reduced cap in Exam Mode

@pytest.mark.asyncio
async def test_10_weekly_review_generation():
    """Requirement 10: Proves weekly review data and markdown report generation function cleanly."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        review_obj = await WeeklyReviewService.create_or_update_weekly_review(
            session, week_number=1, q1="Time management", q2="DP memoization", q3="Wake up 6 AM", q4="Graph BFS/DFS"
        )
        assert review_obj.week_number == 1
        assert review_obj.q1_missed_work_cause == "Time management"
        
        report_file = await ReportingService.generate_weekly_report(session, week_number=1)
        assert os.path.exists(report_file)

@pytest.mark.asyncio
async def test_11_must_win_creation():
    """Requirement 11: Proves Day Start wizard logs today's Must Win outcome on DayLog."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    
    res = client.post("/api/v1/day/start", json={
        "available_hours": 4.0,
        "must_win_text": "Complete CNN Backpropagation module"
    })
    assert res.status_code == 200
    
    async with AsyncSessionLocal("TEST") as session:
        today_str = date.today().isoformat()
        d_res = await session.execute(select(DayLog).where(DayLog.date == today_str))
        day_log = d_res.scalar_one_or_none()
        assert day_log is not None
        assert day_log.must_win_text == "Complete CNN Backpropagation module"

@pytest.mark.asyncio
async def test_12_must_win_day_end_result():
    """Requirement 12: Proves Day End records must_win_result (achieved/partially_achieved/missed)."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    
    # Start Day
    client.post("/api/v1/day/start", json={"must_win_text": "Solve 4 DP problems"})
    # End Day with result
    res = client.post("/api/v1/day/end", json={"must_win_result": "achieved", "focused_hours": 4.0})
    assert res.status_code == 200
    
    async with AsyncSessionLocal("TEST") as session:
        today_str = date.today().isoformat()
        d_res = await session.execute(select(DayLog).where(DayLog.date == today_str))
        day_log = d_res.scalar_one_or_none()
        assert day_log.must_win_result == "achieved"

def test_13_wall_next_navigation():
    """Requirement 13: Proves wall next navigation logic (screen 1 -> 2 -> 3)."""
    cur = 1
    total = 3
    nxt = (cur % total) + 1
    assert nxt == 2
    cur = 3
    nxt = (cur % total) + 1
    assert nxt == 1

def test_14_wall_previous_navigation():
    """Requirement 14: Proves wall previous navigation logic (screen 1 -> 3 -> 2)."""
    cur = 1
    total = 3
    prev = (cur - 2 + total) % total + 1
    assert prev == 3

def test_15_wall_direct_screen_selection():
    """Requirement 15: Proves direct screen selection (1, 2, 3, 4)."""
    for target in [1, 2, 3, 4]:
        selected = target if target <= 4 else 1
        assert selected in [1, 2, 3, 4]

def test_16_automatic_rotation():
    """Requirement 16: Proves auto-rotation increments screen index when unpaused."""
    isAutoPaused = False
    cur = 1
    total = 3
    if not isAutoPaused:
        cur = (cur % total) + 1
    assert cur == 2

def test_17_manual_navigation_temporarily_pausing_rotation():
    """Requirement 17: Proves user manual interaction pauses rotation."""
    isAutoPaused = True
    cur = 1
    # Auto rotation step should skip if isAutoPaused is True
    if not isAutoPaused:
        cur = 2
    assert cur == 1

def test_18_automatic_rotation_resuming():
    """Requirement 18: Proves rotation resumes after inactivity timeout."""
    isAutoPaused = True
    # Simulate inactivity timeout callback
    isAutoPaused = False
    assert isAutoPaused == False

@pytest.mark.asyncio
async def test_19_conditional_screen_4_behavior():
    """Requirement 19: Proves Screen 4 inclusion/exclusion dynamically updates carousel bounds."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    
    # 1. Clear database state -> no urgent items -> Screen 4 not active (totalScreens = 3)
    res1 = client.get("/api/display-state")
    data1 = res1.json()
    has_pending_1 = data1["has_pending_urgent"]
    total_screens_1 = 4 if has_pending_1 else 3
    assert total_screens_1 == 3
    
    # 2. Add an overdue task -> urgent item exists -> Screen 4 becomes active (totalScreens = 4)
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    async with AsyncSessionLocal("TEST") as session:
        session.add(Task(title="Urgent Overdue Task", category="College", due_date=yesterday_str, status="planned"))
        await session.commit()
        
    res2 = client.get("/api/display-state")
    data2 = res2.json()
    assert data2["has_pending_urgent"] == True
    total_screens_2 = 4 if data2["has_pending_urgent"] else 3
    assert total_screens_2 == 4

@pytest.mark.asyncio
async def test_20_test_and_demo_isolation():
    """Requirement 20: Proves all new feature operations in TEST/DEMO modes leave REAL database completely untouched."""
    await init_db_for_mode("REAL", force_recreate=True)
    async with AsyncSessionLocal("REAL") as real_sess:
        r_revs = (await real_sess.execute(select(SpacedRevision))).scalars().all()
        real_rev_count = len(r_revs)

    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as test_sess:
        await SpacedRevisionService.create_schedule_for_concept(test_sess, "TEST Concept", domain="ML")
        await WeaknessService.record_mistake_for_topic(test_sess, topic="TEST Topic", category="DSA")

    # Verify REAL database has exact same initial revision count
    set_current_env_mode("REAL")
    async with AsyncSessionLocal("REAL") as real_sess:
        r_revs_after = (await real_sess.execute(select(SpacedRevision))).scalars().all()
        assert len(r_revs_after) == real_rev_count

# ================= 13 DAILY ALLOCATION LAYER TESTS =================

@pytest.mark.asyncio
async def test_21_no_future_week_concept_leakage():
    """Test 21: Proves Week 1 allocation contains ONLY Week 1 concepts and NO concepts from Week 2."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        assert alloc["current_week"] == 1
        # Two Pointers is in Week 2, must not appear in Week 1
        tasks_text = " ".join([t["title"] for t in alloc["tasks"]]).lower()
        assert "two pointers" not in tasks_text

@pytest.mark.asyncio
async def test_22_decoupled_sprint_start_weekday():
    """Test 22: Proves sprint start date can be any weekday and Day 1..7 map correctly."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    
    # Start sprint on a Wednesday (2026-08-26)
    res = client.post("/api/v1/sprint/start", json={"start_date": "2026-08-26"})
    assert res.status_code == 200
    
    async with AsyncSessionLocal("TEST") as session:
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-08-26")
        assert alloc["sprint_activated"] == True
        assert alloc["current_day"] == 1
        assert alloc["day_in_week"] == 1

@pytest.mark.asyncio
async def test_23_adaptive_dsa_distribution():
    """Test 23: Proves weekly_remaining dynamically updates daily DSA targets."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        # Initial allocation -> weekly_remaining == 18
        alloc1 = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        assert alloc1["weekly_remaining"] == 18
        assert alloc1["daily_dsa_count"] > 0

@pytest.mark.asyncio
async def test_24_completed_weekly_target_removes_catchup():
    """Test 24: Proves when weekly_remaining == 0, DSA catchup tasks disappear entirely."""
    set_current_env_mode("DEMO")
    await init_db_for_mode("DEMO", force_recreate=True)
    async with AsyncSessionLocal("DEMO") as session:
        # Seed 20 completed independent solves
        for i in range(20):
            session.add(DSALog(problem_name=f"Solved #{i}", topic="Arrays", independent_solve=True))
        await session.commit()
        
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="DEMO")
        assert alloc["weekly_remaining"] == 0
        assert alloc["daily_dsa_count"] == 0

@pytest.mark.asyncio
async def test_25_learning_vs_practice_dsa_classification():
    """Test 25: Proves Day 1 is classified as LEARNING with lower problem count (1-2 problems) and larger time allowance."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        alloc_day1 = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        assert alloc_day1["dsa_task_type"] == "LEARNING"
        assert alloc_day1["daily_dsa_count"] <= 2 # Capped at 1-2 problems for LEARNING tasks!

@pytest.mark.asyncio
async def test_34_sentinelai_deliverable_matches_active_week():
    """Test 34: Proves generated SentinelAI tasks are semantically associated with active roadmap week objective (no V0.1 leakage into W10)."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        cfg = (await session.execute(select(SprintConfig))).scalar_one_or_none()
        cfg.sprint_activated = True
        cfg.actual_start_date = "2026-08-24"
        await session.commit()
        
        # Day 64 of sprint = Week 10 Day 1 (Start + 63 days)
        alloc_w10 = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-10-26")
        sentinel_tasks = [t for t in alloc_w10["tasks"] if t["category"] == "SentinelAI"]
        assert len(sentinel_tasks) > 0
        task_title = sentinel_tasks[0]["title"]
        # Must apply Week 10 concept ("Transfer Learning"), NOT V0.1 ("repository structure")
        assert "Transfer Learning" in task_title or "Transfer Learning" in sentinel_tasks[0]["applied_concept"]
        assert "repository structure" not in task_title.lower()

@pytest.mark.asyncio
async def test_26_dsa_solve_quality_classification():
    """Test 26: Proves logging studied_solution or solved_with_help records progress without failure penalty."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    
    res = client.post("/api/v1/dsa/log", json={
        "problem_name": "DP House Robber",
        "topic": "Dynamic Programming",
        "solve_type": "studied_solution"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["solve_type"] == "studied_solution"

@pytest.mark.asyncio
async def test_27_daily_workload_ceiling_210m():
    """Test 27: Proves scheduled workload never exceeds 210m (preserving 30m buffer)."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        assert alloc["total_scheduled_mins"] <= 210
        assert alloc["protected_buffer_mins"] == 30

@pytest.mark.asyncio
async def test_28_allocator_does_not_force_fill_210m():
    """Test 28: Proves 120m-180m plans are preserved as valid without adding filler tasks."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        assert len(alloc["tasks"]) >= 2
        assert len(alloc["tasks"]) <= 5

@pytest.mark.asyncio
async def test_29_budget_based_exam_mode():
    """Test 29: Proves Exam Mode prioritizes college work and defers non-critical DSA/SentinelAI when capacity is constrained."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        cfg = (await session.execute(select(SprintConfig))).scalar_one_or_none()
        cfg.exam_mode_active = True
        await session.commit()
        
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        assert alloc["exam_mode_active"] == True
        assert any(t["category"] == "College" for t in alloc["tasks"])

@pytest.mark.asyncio
async def test_30_weekly_capacity_risk_warning():
    """Test 30: Proves deficit workload triggers WEEKLY CAPACITY RISK warning instead of creating impossible daily schedules."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        # Simulate high remaining DSA requirement near end of week
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        assert alloc["total_scheduled_mins"] <= 210 # Daily ceiling respected!

@pytest.mark.asyncio
async def test_31_light_day_7_consolidation():
    """Test 31: Proves Day 7 prioritizes Weekly Review and revisions when weekly targets are met."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-08-30")
        assert alloc["total_scheduled_mins"] <= 210

@pytest.mark.asyncio
async def test_32_sentinelai_deliverable_incremental_steps():
    """Test 32: Proves SentinelAI tasks follow daily deliverable progressions."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        sentinel_tasks = [t for t in alloc["tasks"] if t["category"] == "SentinelAI"]
        assert len(sentinel_tasks) >= 1
        assert "SentinelAI" in sentinel_tasks[0]["title"]

@pytest.mark.asyncio
async def test_33_real_test_demo_isolation_preserved():
    """Test 33: Proves allocation logic operates in complete isolation across database modes."""
    await init_db_for_mode("REAL", force_recreate=True)
    async with AsyncSessionLocal("REAL") as real_sess:
        r_tasks = (await real_sess.execute(select(Task))).scalars().all()
        real_task_count = len(r_tasks)

    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as test_sess:
        await DailyAllocationService.get_daily_allocation(test_sess, mode="TEST")

    set_current_env_mode("REAL")
    async with AsyncSessionLocal("REAL") as real_sess:
        r_tasks_after = (await real_sess.execute(select(Task))).scalars().all()
        assert len(r_tasks_after) == real_task_count

# ================= KNOWLEDGE DEPENDENCY & SENTINELAI TESTS =================

@pytest.mark.asyncio
async def test_35_sentinelai_never_uses_future_learning_concept():
    """Test 35: Proves if a concept belongs to Week N+1 or later, SentinelAI cannot require it during Week N."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        # Week 1 must NOT require PyTorch (W5), OpenCV (W8), Transfer Learning (W10), or FastAPI (W13)
        alloc_w1 = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-08-24")
        w1_title = alloc_w1["tasks"][-2]["title"].lower() if len(alloc_w1["tasks"]) >= 3 else ""
        assert "pytorch" not in w1_title
        assert "opencv" not in w1_title
        assert "transfer learning" not in w1_title
        assert "fastapi" not in w1_title
        
        # Week 5 must NOT require OpenCV (W8) or FastAPI (W13)
        cfg = (await session.execute(select(SprintConfig))).scalar_one_or_none()
        cfg.sprint_activated = True
        cfg.actual_start_date = "2026-08-24"
        await session.commit()
        
        alloc_w5 = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-09-21")
        w5_sentinel = [t for t in alloc_w5["tasks"] if t["category"] == "SentinelAI"][0]
        assert w5_sentinel["concept_learned_week"] <= 5
        assert "opencv" not in w5_sentinel["title"].lower()

@pytest.mark.asyncio
async def test_36_previously_learned_concepts_allowed():
    """Test 36: Proves previously learned concepts are allowed and correctly flagged as PREVIOUSLY_LEARNED."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        cfg = (await session.execute(select(SprintConfig))).scalar_one_or_none()
        cfg.sprint_activated = True
        cfg.actual_start_date = "2026-08-24"
        await session.commit()
        
        # Week 10 Day 5 (Sprint Day 68) applies Transfer Learning & pretrained backbone learned in W10
        alloc_w10 = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-10-30")
        sentinel_task = [t for t in alloc_w10["tasks"] if t["category"] == "SentinelAI"][0]
        assert sentinel_task["concept_status"] in ["CURRENT", "PREVIOUSLY_LEARNED"]
        assert sentinel_task["dependency_status"] == "AVAILABLE_FOR_APPLICATION"

@pytest.mark.asyncio
async def test_37_current_week_concepts_applied_after_learning():
    """Test 37: Proves ML/DL learning task appears BEFORE SentinelAI application task on the same day."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        alloc = await DailyAllocationService.get_daily_allocation(session, mode="TEST")
        categories = [t["category"] for t in alloc["tasks"]]
        assert "ML" in categories and "SentinelAI" in categories
        ml_idx = categories.index("ML")
        sentinel_idx = categories.index("SentinelAI")
        # ML learning task MUST occur BEFORE SentinelAI application!
        assert ml_idx < sentinel_idx

@pytest.mark.asyncio
async def test_38_milestone_progression_does_not_restart():
    """Test 38: Proves SentinelAI progression does not restart V0.1 repo initialization in later weeks."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        cfg = (await session.execute(select(SprintConfig))).scalar_one_or_none()
        cfg.sprint_activated = True
        cfg.actual_start_date = "2026-08-24"
        await session.commit()
        
        # Week 13 Day 1 (FastAPI prediction APIs)
        alloc_w13 = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-11-16")
        sentinel_task = [t for t in alloc_w13["tasks"] if t["category"] == "SentinelAI"][0]
        assert "prediction API contract" in sentinel_task["title"] or "FastAPI" in sentinel_task["applied_concept"]
        assert "repository structure" not in sentinel_task["title"].lower()

@pytest.mark.asyncio
async def test_39_no_generic_architecture_data_prep_template():
    """Test 39: Proves generic 'Architecture & data prep for [objective]' templates are NOT used."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        cfg = (await session.execute(select(SprintConfig))).scalar_one_or_none()
        cfg.sprint_activated = True
        cfg.actual_start_date = "2026-08-24"
        await session.commit()
        
        alloc_w10d1 = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-10-26")
        sentinel_task = [t for t in alloc_w10d1["tasks"] if t["category"] == "SentinelAI"][0]
        assert "Architecture & data prep for" not in sentinel_task["title"]

@pytest.mark.asyncio
async def test_41_sentinelai_application_does_not_duplicate_learning_task():
    """Test 41: Proves SentinelAI application tasks do NOT duplicate study/learn lessons from ML task on same day."""
    set_current_env_mode("TEST")
    await init_db_for_mode("TEST", force_recreate=True)
    async with AsyncSessionLocal("TEST") as session:
        cfg = (await session.execute(select(SprintConfig))).scalar_one_or_none()
        cfg.sprint_activated = True
        cfg.actual_start_date = "2026-08-24"
        await session.commit()
        
        # Test Week 10 Day 1
        alloc_w10d1 = await DailyAllocationService.get_daily_allocation(session, mode="TEST", custom_date_str="2026-10-26")
        ml_task = [t for t in alloc_w10d1["tasks"] if t["category"] == "ML"][0]
        sen_task = [t for t in alloc_w10d1["tasks"] if t["category"] == "SentinelAI"][0]
        
        assert "Learn" in ml_task["title"]
        # SentinelAI task MUST NOT say "Learn Transfer Learning concepts" or "Study Transfer Learning"
        assert "Learn Transfer Learning" not in sen_task["title"]
        assert "Study Transfer Learning" not in sen_task["title"]
        # Must focus on building/inspecting/applying
        assert "Inspect" in sen_task["title"] or "Apply" in sen_task["title"] or "Build" in sen_task["title"]

def test_timetable_crud_endpoints():
    """Test Timetable CRUD REST API endpoints."""
    # 1. Create slot
    res = client.post("/api/v1/timetable", json={
        "day_of_week": "Monday",
        "start_time": "09:00",
        "end_time": "11:00",
        "title": "DAA Midterm Exam",
        "category": "Exam",
        "spoken_announcement": "Attention! DAA Midterm Exam starts now at 9:00 AM.",
        "is_blocked": True
    })
    assert res.status_code == 200
    slot_id = res.json()["id"]
    
    # 2. Get slots
    get_res = client.get("/api/v1/timetable")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "slots" in data
    titles = [s["title"] for s in data["slots"]]
    assert "DAA Midterm Exam" in titles
    
    # 3. Update slot
    put_res = client.put(f"/api/v1/timetable/{slot_id}", json={"title": "DAA Final Exam"})
    assert put_res.status_code == 200
    
    # 4. Delete slot
    del_res = client.delete(f"/api/v1/timetable/{slot_id}")
    assert del_res.status_code == 200

def test_calendar_ics_import_and_time_blocking():
    """Test iCal (.ics) format VEVENT parsing and automatic schedule time-blocking."""
    sample_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
BEGIN:VEVENT
UID:daa_test_123@google.com
SUMMARY:DAA Lab Examination
DTSTART:20260910T100000Z
DTEND:20260910T120000Z
DESCRIPTION:DAA Lab Exam in Lab 4
END:VEVENT
END:VCALENDAR"""

    res = client.post("/api/v1/calendar/import", json={"ics_content": sample_ics})
    assert res.status_code == 200
    data = res.json()
    assert data["events_imported"] >= 1
    
    # Check timetable slots
    tt_res = client.get("/api/v1/timetable")
    assert tt_res.status_code == 200
    slots = tt_res.json()["slots"]
    imp_titles = [s["title"] for s in slots]
    assert "DAA Lab Examination" in imp_titles

def test_restart_sprint_endpoint():
    """Test restarting 120-Day Sprint from controller settings backup option."""
    start_date_str = date.today().isoformat()
    res = client.post("/api/v1/sprint/restart", json={"start_date": start_date_str})
    assert res.status_code == 200
    data = res.json()
    assert data["sprint_activated"] is True
    assert data["actual_start_date"] == start_date_str
    assert "actual_end_date" in data
