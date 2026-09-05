import shutil
import subprocess
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from app.core.config import settings
from app.db.session import get_db, set_current_env_mode, get_current_env_mode
from app.db.init_db import init_db_for_mode
from app.db.models import (
    SprintConfig, RoadmapWeek, Task, DSALog, Mistake, Concept, SentinelAIMilestone, 
    CollegeSubject, CollegeEvent, CollegeSyllabusTopic, DayLog, ReportLog, ExamPeriod,
    SpacedRevision, WeaknessRecord, WeeklyReview, TimetableSlot, CalendarConfig
)
from app.services.roadmap_service import RoadmapService
from app.services.jarvis_engine import JarvisEngine
from app.services.reporting_service import ReportingService
from app.services.backup_service import BackupService
from app.services.revision_service import SpacedRevisionService
from app.services.weakness_service import WeaknessService
from app.services.recovery_service import RecoveryService
from app.services.weekly_review_service import WeeklyReviewService
from app.services.daily_allocation_service import DailyAllocationService
from app.services.calendar_service import CalendarService

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health check endpoint."""
    try:
        res = await db.execute(select(func.count(Task.id)))
        task_count = res.scalar() or 0
        return {
            "status": "healthy",
            "env_mode": get_current_env_mode(),
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "task_count": task_count
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@router.get("/api/display-state")
async def get_display_state(db: AsyncSession = Depends(get_db)):
    """
    Authoritative state endpoint for Wall Display Kiosk.
    Returns lightweight, distance-viewable payload for 4-screen rotation engine.
    Now includes Today's Must Win, Spaced Revisions, Weakness Radar, & Recovery status.
    """
    env_mode = get_current_env_mode()
    await DailyAllocationService.ensure_today_tasks_exist(db, mode=env_mode)
    sprint_status = await RoadmapService.get_sprint_status(db)
    today_str = date.today().isoformat()
    
    # 1. Today's Tasks
    tasks_res = await db.execute(
        select(Task).where(Task.due_date == today_str).order_by(Task.priority.desc())
    )
    today_tasks = tasks_res.scalars().all()
    
    # 2. Overdue Tasks & Events
    overdue_res = await db.execute(
        select(Task).where(Task.due_date < today_str, Task.status != "completed")
    )
    overdue_tasks = overdue_res.scalars().all()
    
    # 3. Active Assignments & College Work (Any date)
    assignments_res = await db.execute(
        select(Task).where(
            Task.category.in_(["Assignment", "College"]),
            Task.status != "completed"
        ).order_by(Task.due_date)
    )
    active_assignments = assignments_res.scalars().all()

    urgent_events_res = await db.execute(
        select(CollegeEvent).where(CollegeEvent.status == "upcoming").order_by(CollegeEvent.due_date)
    )
    urgent_events = urgent_events_res.scalars().all()

    # 4. Today's DayLog & Must Win
    day_res = await db.execute(select(DayLog).where(DayLog.date == today_str))
    day_log = day_res.scalar_one_or_none()
    must_win_text = day_log.must_win_text if (day_log and day_log.must_win_text) else "Maintain 100% roadmap discipline today."
    must_win_result = day_log.must_win_result if day_log else None

    # 5. Spaced Revisions
    revisions_data = await SpacedRevisionService.get_todays_revisions(db, today_str=today_str)

    # 6. Weakness Radar
    weakness_data = await WeaknessService.get_weakness_radar_summary(db)

    # 7. Recovery Mode
    recovery_data = await RecoveryService.get_recovery_plan(db, today_str=today_str)

    # 8. Timetable & Calendar Sync Slots for Today
    today_dow = datetime.now().strftime("%A")
    tt_res = await db.execute(
        select(TimetableSlot).where(
            TimetableSlot.is_active == True,
            (TimetableSlot.day_of_week.in_([today_dow, "Daily", "All"])) | (TimetableSlot.date_str == today_str)
        ).order_by(TimetableSlot.start_time)
    )
    all_slots = tt_res.scalars().all()
    seen_slots = set()
    today_timetable_slots = []
    for s in all_slots:
        slot_key = (s.title.strip(), s.start_time, s.end_time)
        if slot_key not in seen_slots:
            seen_slots.add(slot_key)
            today_timetable_slots.append(s)

    cfg_res = await db.execute(select(CalendarConfig))
    calendar_cfg = cfg_res.scalar_one_or_none()

    # Conditional Screen 4 trigger: true if active assignments, overdue tasks, urgent events, overdue revisions, or critical weaknesses exist
    has_critical_weakness = any(w["severity"] == "critical" for w in weakness_data["top_weaknesses"])
    has_pending_urgent = (
        len(active_assignments) > 0 or
        len(overdue_tasks) > 0 or 
        len(urgent_events) > 0 or 
        revisions_data["overdue_count"] > 0 or 
        has_critical_weakness or
        len(sprint_status["unresolved_mistakes"]) > 0
    )
    
    return {
        "env_mode": sprint_status["env_mode"],
        "sprint_activated": sprint_status["sprint_activated"],
        "actual_start_date": sprint_status["actual_start_date"],
        "actual_end_date": sprint_status["actual_end_date"],
        "current_time": datetime.now().strftime("%H:%M:%S"),
        "current_date_formatted": datetime.now().strftime("%A, %b %d, %Y"),
        "date_iso": today_str,
        "day_number": sprint_status["day_number"],
        "total_days": 120,
        "current_week": sprint_status["current_week"],
        "current_month": sprint_status["current_month"],
        "current_mode": sprint_status["current_mode"],
        "exam_mode_active": sprint_status["exam_mode_active"],
        "wall_sleep_mode": sprint_status["wall_sleep_mode"],
        "health": sprint_status["health"],
        
        # Screen 1 - TODAY (with MUST WIN)
        "must_win": {
            "text": must_win_text,
            "result": must_win_result
        },
        "today_top_tasks": [
            {
                "id": t.id, "title": t.title, "category": t.category, 
                "priority": t.priority, "status": t.status, "est_mins": t.estimated_minutes,
                "due_date": t.due_date, "notes": t.notes
            } for t in today_tasks[:10]
        ],
        "active_assignments": [
            {
                "id": a.id, "title": a.title, "category": a.category,
                "priority": a.priority, "status": a.status, "est_mins": a.estimated_minutes,
                "due_date": a.due_date, "notes": a.notes
            } for a in active_assignments
        ],
        "completion_percentage": sprint_status["tasks_summary"]["completion_percentage"],
        "sentinelai_version": sprint_status["sentinelai"]["active_version"],
        "sentinelai_pct": sprint_status["sentinelai"]["percentage"],
        "todays_revisions_summary": revisions_data,
        
        # Screen 2 - PROGRESS
        "dsa": sprint_status["dsa"],
        "concepts": sprint_status["concepts"],
        "sentinelai": sprint_status["sentinelai"],
        "current_week_info": sprint_status["current_week_info"],
        "weakness_radar": weakness_data,
        
        # Screen 3 - ACCOUNTABILITY
        "unresolved_mistakes": sprint_status["unresolved_mistakes"],
        "top_weaknesses": weakness_data["top_weaknesses"],
        "recovery_plan": recovery_data,
        "status_motivational_line": "Consistency beats intensity. Protect the 16-week master roadmap.",
        
        # Screen 4 - PENDING / URGENT (Conditional)
        "has_pending_urgent": has_pending_urgent,
        "overdue_tasks_count": len(overdue_tasks),
        "overdue_revisions_count": revisions_data["overdue_count"],
        "urgent_events": [
            {"title": e.title, "due_date": e.due_date, "subject": e.subject_name} for e in urgent_events[:3]
        ],
        "today_timetable": [
            {
                "id": s.id, "title": s.title, "day_of_week": s.day_of_week, "date_str": s.date_str,
                "start_time": s.start_time, "end_time": s.end_time, "category": s.category,
                "spoken_announcement": s.spoken_announcement or f"Attention! {s.title} is starting now at {s.start_time}.",
                "is_blocked": s.is_blocked, "is_active": s.is_active, "source": s.source
            } for s in today_timetable_slots
        ],
        "calendar_config": {
            "ics_url": calendar_cfg.ics_url if calendar_cfg else None,
            "auto_sync": calendar_cfg.auto_sync if calendar_cfg else True,
            "voice_enabled": calendar_cfg.voice_enabled if calendar_cfg else True,
            "last_synced_at": calendar_cfg.last_synced_at.isoformat() if (calendar_cfg and calendar_cfg.last_synced_at) else None
        }
    }

@router.get("/api/v1/dashboard")
async def get_controller_dashboard(db: AsyncSession = Depends(get_db)):
    """Full data payload for Main Controller interface."""
    env_mode = get_current_env_mode()
    await DailyAllocationService.ensure_today_tasks_exist(db, mode=env_mode)
    sprint_status = await RoadmapService.get_sprint_status(db)
    today_str = date.today().isoformat()
    
    tasks_res = await db.execute(select(Task).order_by(Task.due_date.desc()))
    all_tasks = tasks_res.scalars().all()
    
    mistakes_res = await db.execute(select(Mistake).order_by(Mistake.occurrences_count.desc()))
    all_mistakes = mistakes_res.scalars().all()
    
    concepts_res = await db.execute(select(Concept))
    all_concepts = concepts_res.scalars().all()
    
    events_res = await db.execute(select(CollegeEvent).order_by(CollegeEvent.due_date))
    all_events = events_res.scalars().all()

    # Must Win & Day Log
    day_res = await db.execute(select(DayLog).where(DayLog.date == today_str))
    day_log = day_res.scalar_one_or_none()

    # Spaced Revisions, Weakness Radar, Recovery Plan
    revisions_data = await SpacedRevisionService.get_todays_revisions(db, today_str=today_str)
    weakness_data = await WeaknessService.get_weakness_radar_summary(db)
    recovery_data = await RecoveryService.get_recovery_plan(db, today_str=today_str)

    # Weekly Reviews
    weekly_res = await db.execute(select(WeeklyReview).order_by(WeeklyReview.week_number.desc()))
    all_weekly_reviews = weekly_res.scalars().all()

    return {
        "sprint_status": sprint_status,
        "must_win": {
            "text": day_log.must_win_text if (day_log and day_log.must_win_text) else "Solve 4 DSA problems and review CNNs",
            "result": day_log.must_win_result if day_log else None
        },
        "tasks": [
            {
                "id": t.id, "title": t.title, "category": t.category, 
                "priority": t.priority, "status": t.status, "due_date": t.due_date,
                "estimated_minutes": t.estimated_minutes, "notes": t.notes,
                "contribution_tags": t.contribution_tags
            } for t in all_tasks
        ],
        "mistakes": [
            {
                "id": m.id, "type": m.mistake_type, "description": m.description,
                "severity": m.severity, "count": m.occurrences_count, "resolved": m.resolved
            } for m in all_mistakes
        ],
        "concepts": [
            {"id": c.id, "domain": c.domain, "name": c.name, "status": c.status} for c in all_concepts
        ],
        "college_events": [
            {
                "id": e.id, "title": e.title, "subject": e.subject_name,
                "event_type": e.event_type, "due_date": e.due_date, "status": e.status
            } for e in all_events
        ],
        "revisions": revisions_data,
        "weaknesses": weakness_data,
        "recovery_plan": recovery_data,
        "weekly_reviews": [
            {
                "id": w.id, "week_number": w.week_number, "top_weakness": w.top_weakness,
                "dsa_solved": w.dsa_solved, "must_win_rate": w.must_win_success_rate,
                "q4_next_week_priority": w.q4_next_week_priority
            } for w in all_weekly_reviews
        ]
    }

# ================= SPACED REVISION ENDPOINTS =================
@router.get("/api/v1/revisions/today")
async def get_todays_revisions_endpoint(db: AsyncSession = Depends(get_db)):
    """Returns today's due revisions and overdue queue."""
    return await SpacedRevisionService.get_todays_revisions(db)

@router.post("/api/v1/revisions/schedule")
async def schedule_concept_revision_endpoint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Schedules 5-stage spaced revisions for a learning concept/topic (Constraint 1)."""
    concept_name = body.get("concept_name")
    domain = body.get("domain", "ML")
    if not concept_name:
        raise HTTPException(status_code=400, detail="concept_name is required.")
        
    created = await SpacedRevisionService.create_schedule_for_concept(
        db, concept_name=concept_name, domain=domain
    )
    return {
        "message": f"Spaced revision schedule created for '{concept_name}' ({len(created)} new items created).",
        "created_count": len(created)
    }

@router.post("/api/v1/revisions/complete")
async def complete_revision_endpoint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Marks a scheduled revision as completed and contributes to evidence-based weakness improvement."""
    revision_id = body.get("revision_id")
    confidence = body.get("confidence_rating", "medium")
    if not revision_id:
        raise HTTPException(status_code=400, detail="revision_id is required.")
        
    rev = await SpacedRevisionService.complete_revision(db, revision_id=revision_id, confidence_rating=confidence)
    if not rev:
        raise HTTPException(status_code=404, detail="Revision schedule item not found.")
        
    # Record evidence-based weakness improvement
    await WeaknessService.record_successful_revision(db, topic=rev.concept_name, category=rev.domain)

    return {"message": f"Revision #{rev.revision_number} for '{rev.concept_name}' marked COMPLETED.", "revision_id": rev.id}

# ================= WEAKNESS RADAR ENDPOINTS =================
@router.get("/api/v1/weaknesses")
async def get_weakness_radar_endpoint(db: AsyncSession = Depends(get_db)):
    """Returns persistent Weakness Radar summary."""
    return await WeaknessService.get_weakness_radar_summary(db)

# ================= RECOVERY MODE ENDPOINTS =================
@router.get("/api/v1/recovery/plan")
async def get_recovery_plan_endpoint(db: AsyncSession = Depends(get_db)):
    """Returns controlled, capped Recovery Plan for missed work."""
    return await RecoveryService.get_recovery_plan(db)

# ================= DAILY ALLOCATION ENDPOINTS =================
@router.get("/api/v1/allocation/today")
async def get_today_allocation_endpoint(db: AsyncSession = Depends(get_db)):
    """Returns deterministic daily allocation task breakdown for active sprint position."""
    env_mode = get_current_env_mode()
    return await DailyAllocationService.get_daily_allocation(db, mode=env_mode)

@router.post("/api/v1/dsa/log")
async def log_dsa_problem_endpoint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Logs a solved or studied DSA problem with solve_type quality classification
    ('solved', 'solved_with_help', 'studied_solution', 'needs_revisit').
    None of these solve types cause daily failure penalties.
    """
    problem_name = body.get("problem_name", "DSA Problem")
    topic = body.get("topic", "Arrays")
    difficulty = body.get("difficulty", "Medium")
    time_taken_mins = body.get("time_taken_mins", 30)
    solve_type = body.get("solve_type", "solved") # solved, solved_with_help, studied_solution, needs_revisit
    
    independent = (solve_type == "solved")
    hint_used = (solve_type in ["solved_with_help", "studied_solution"])
    solution_seen = (solve_type == "studied_solution")
    
    dsa_log = DSALog(
        problem_name=problem_name,
        topic=topic,
        difficulty=difficulty,
        time_taken_mins=time_taken_mins,
        independent_solve=independent,
        hint_used=hint_used,
        solution_seen=solution_seen,
        solve_type=solve_type
    )
    db.add(dsa_log)
    
    # If flagged as needs_revisit or studied_solution, schedule spaced revision follow-up
    if solve_type in ["needs_revisit", "studied_solution"]:
        await SpacedRevisionService.create_schedule_for_concept(db, concept_name=f"DSA: {problem_name} ({topic})", domain="DSA")
        
    await db.commit()
    return {
        "message": f"DSA Problem '{problem_name}' logged successfully as solve_type='{solve_type}'.",
        "solve_type": solve_type,
        "dsa_log_id": dsa_log.id
    }

# ================= WEEKLY REVIEW ENDPOINTS =================
@router.post("/api/v1/weekly-review")
async def create_weekly_review_endpoint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Saves structured Weekly Review and updates weekly report."""
    sprint_status = await RoadmapService.get_sprint_status(db)
    week_num = body.get("week_number", max(1, sprint_status["current_week"]))
    
    review_obj = await WeeklyReviewService.create_or_update_weekly_review(
        db,
        week_number=week_num,
        q1=body.get("q1_missed_work_cause", ""),
        q2=body.get("q2_biggest_difficulty", ""),
        q3=body.get("q3_next_week_improvements", ""),
        q4=body.get("q4_next_week_priority", "")
    )
    
    report_file = await ReportingService.generate_weekly_report(db, week_number=week_num)
    return {
        "message": f"Weekly Review for Week {week_num} saved successfully.",
        "review_id": review_obj.id,
        "report_file": report_file
    }

# ================= TODAY'S MUST WIN ENDPOINTS =================
@router.post("/api/v1/must-win")
async def update_must_win_endpoint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Sets or updates Today's Must Win accountability priority."""
    today_str = date.today().isoformat()
    sprint_status = await RoadmapService.get_sprint_status(db)
    
    day_res = await db.execute(select(DayLog).where(DayLog.date == today_str))
    day_log = day_res.scalar_one_or_none()
    if not day_log:
        day_log = DayLog(date=today_str, day_number=sprint_status["day_number"])
        db.add(day_log)
        
    if "must_win_text" in body:
        day_log.must_win_text = body["must_win_text"]
    if "must_win_result" in body:
        day_log.must_win_result = body["must_win_result"]
        
    await db.commit()
    return {"message": "Today's Must Win updated.", "must_win_text": day_log.must_win_text, "must_win_result": day_log.must_win_result}


@router.post("/api/v1/day/start")
async def start_day_endpoint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Initializes daily schedule, sets Today's Must Win outcome, and ensures today's tasks exist.
    """
    must_win_text = body.get("must_win_text", "")
    available_hours = float(body.get("available_hours", 4.0))
    
    today_str = date.today().isoformat()
    sprint_status = await RoadmapService.get_sprint_status(db)
    
    # Ensure sprint is activated if user explicitly starts day
    cfg_res = await db.execute(select(SprintConfig))
    cfg = cfg_res.scalar_one_or_none()
    if cfg and not cfg.sprint_activated:
        cfg.sprint_activated = True
        cfg.actual_start_date = today_str
        end_dt = date.today() + timedelta(days=119)
        cfg.actual_end_date = end_dt.isoformat()
        cfg.activated_at = datetime.now(timezone.utc)
        await db.commit()
    
    env_mode = get_current_env_mode()
    tasks = await DailyAllocationService.ensure_today_tasks_exist(db, mode=env_mode, force_recreate=True)
    
    day_res = await db.execute(select(DayLog).where(DayLog.date == today_str))
    day_log = day_res.scalar_one_or_none()
    if not day_log:
        day_log = DayLog(
            date=today_str,
            day_number=sprint_status["day_number"] or 1,
            available_hours=available_hours,
            must_win_text=must_win_text,
            constraints=body.get("constraints", ""),
            energy_level=body.get("energy_level", "High"),
            top_priority=body.get("top_priority", ""),
            status="active"
        )
        db.add(day_log)
    else:
        day_log.available_hours = available_hours
        if must_win_text:
            day_log.must_win_text = must_win_text
        if "constraints" in body:
            day_log.constraints = body["constraints"]
        if "energy_level" in body:
            day_log.energy_level = body["energy_level"]
        if "top_priority" in body:
            day_log.top_priority = body["top_priority"]
        day_log.status = "active"
        
    await db.commit()
    return {
        "message": f"Day Start initialized for Day {day_log.day_number}.",
        "must_win_text": day_log.must_win_text,
        "available_hours": day_log.available_hours,
        "tasks_count": len(tasks)
    }

@router.post("/api/v1/day/end")
async def end_day_endpoint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Completes daily review and generates daily report.
    """
    must_win_result = body.get("must_win_result", "achieved")
    focused_hours = float(body.get("focused_hours", 4.0))
    what_learned = body.get("what_learned", "")
    mistakes_noted = body.get("mistakes_noted", "")
    
    today_str = date.today().isoformat()
    day_res = await db.execute(select(DayLog).where(DayLog.date == today_str))
    day_log = day_res.scalar_one_or_none()
    if day_log:
        day_log.must_win_result = must_win_result
        day_log.focused_hours = focused_hours
        day_log.what_learned = what_learned
        day_log.mistakes_noted = mistakes_noted
        day_log.notes = f"Learned: {what_learned}\nMistakes: {mistakes_noted}"
        day_log.status = "completed"
        await db.commit()
        
    report_file = await ReportingService.generate_daily_report(db, target_date_str=today_str)
    return {
        "message": "Day completed & daily report generated successfully.",
        "report_file": report_file
    }

@router.post("/api/v1/sprint/start")
async def activate_sprint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    ONE-TIME SPRINT ACTIVATION ENDPOINT.
    Permanently transitions system from PRE-SPRINT to ACTIVE SPRINT.
    Calculates actual_end_date = start_date + 119 days.
    Can be performed ONLY once!
    """
    cfg_res = await db.execute(select(SprintConfig))
    cfg = cfg_res.scalar_one_or_none()
    
    if not cfg:
        cfg = SprintConfig(env_mode=get_current_env_mode())
        db.add(cfg)
        
    if cfg.sprint_activated:
        raise HTTPException(status_code=400, detail="120-Day Sprint is ALREADY activated and running. Cannot re-activate.")
        
    start_date_str = body.get("start_date", date.today().isoformat())
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_date format. Expected YYYY-MM-DD.")
        
    end_dt = start_dt + timedelta(days=119)
    end_date_str = end_dt.isoformat()
    
    cfg.sprint_activated = True
    cfg.actual_start_date = start_date_str
    cfg.actual_end_date = end_date_str
    cfg.activated_at = datetime.now(timezone.utc)
    
    await db.commit()
    env_mode = get_current_env_mode()
    created_tasks = await DailyAllocationService.ensure_today_tasks_exist(db, mode=env_mode, force_recreate=True)
    
    return {
        "message": "120-DAY SPRINT ACTIVATED SUCCESSFULLY!",
        "sprint_activated": True,
        "actual_start_date": start_date_str,
        "actual_end_date": end_date_str,
        "activated_at": cfg.activated_at.isoformat(),
        "created_tasks_count": len(created_tasks)
    }

@router.post("/api/v1/sprint/restart")
async def restart_sprint(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    RESTART 120-DAY SPRINT ENDPOINT (BACKUP).
    Allows resetting and restarting the 120-day sprint cycle from Day 01.
    Wipes old sprint allocated tasks, resets timeline to Day 01, and re-materializes fresh tasks for today.
    """
    cfg_res = await db.execute(select(SprintConfig))
    cfg = cfg_res.scalar_one_or_none()
    
    if not cfg:
        cfg = SprintConfig(env_mode=get_current_env_mode())
        db.add(cfg)
        
    start_date_str = body.get("start_date", date.today().isoformat())
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_date format. Expected YYYY-MM-DD.")
        
    end_dt = start_dt + timedelta(days=119)
    end_date_str = end_dt.isoformat()
    
    cfg.sprint_activated = True
    cfg.actual_start_date = start_date_str
    cfg.actual_end_date = end_date_str
    cfg.activated_at = datetime.now(timezone.utc)
    
    today_str = date.today().isoformat()

    # 1. Clear previous auto-generated sprint tasks and today's tasks so Day 01 is freshly allocated
    await db.execute(
        delete(Task).where(
            (Task.due_date == today_str) |
            (Task.notes.like("%Allocated Task%")) |
            (Task.notes.like("%Sprint Day%")) |
            (Task.source == "roadmap")
        )
    )
    
    # 2. Reset DayLog for today
    await db.execute(
        delete(DayLog).where(DayLog.date == today_str)
    )

    await db.commit()
    
    # 3. Ensure tasks for TODAY exist based on the new sprint start date & day number calculation
    env_mode = get_current_env_mode()
    created_tasks = await DailyAllocationService.ensure_today_tasks_exist(db, mode=env_mode, force_recreate=True)
    
    return {
        "message": "120-DAY SPRINT RESTARTED SUCCESSFULLY!",
        "sprint_activated": True,
        "actual_start_date": start_date_str,
        "actual_end_date": end_date_str,
        "activated_at": cfg.activated_at.isoformat(),
        "created_tasks_count": len(created_tasks)
    }

@router.post("/api/v1/env/switch")
async def switch_environment(
    body: Dict[str, Any] = Body(...)
):
    """Switches active environment mode between REAL, TEST, and DEMO with administrative confirmation."""
    target_mode = body.get("env_mode", "REAL").upper()
    confirmed = body.get("confirmed", False)
    
    if target_mode not in ["REAL", "TEST", "DEMO"]:
        raise HTTPException(status_code=400, detail="Invalid env_mode. Expected REAL, TEST, or DEMO.")
        
    if target_mode == "REAL" and not confirmed:
        return {
            "success": False,
            "requires_confirmation": True,
            "warning_title": "REAL MODE CONFIRMATION REQUIRED",
            "warning_message": "You are entering REAL MODE.\nAll changes from this point will affect your actual study data.",
            "target_mode": "REAL"
        }
        
    active_mode = set_current_env_mode(target_mode)
    
    if active_mode == "REAL":
        msg = "⚠️ Switched to REAL MODE. All changes from this point will affect your actual study data."
    elif active_mode == "TEST":
        msg = "🧪 Switched to TEST MODE. Real study data is isolated and untouched."
    else:
        msg = "📊 Switched to DEMO MODE. Real study data is isolated and untouched (Curated Showcase Dataset)."
        
    return {
        "success": True,
        "requires_confirmation": False,
        "message": msg,
        "env_mode": active_mode
    }


@router.get("/api/v1/roadmap")
async def get_full_roadmap(db: AsyncSession = Depends(get_db)):
    """Returns full 16-week 4-month roadmap with all focus areas, DSA targets, and active progress."""
    sprint_status = await RoadmapService.get_sprint_status(db)
    
    weeks_res = await db.execute(select(RoadmapWeek).order_by(RoadmapWeek.week_number))
    weeks = weeks_res.scalars().all()
    
    milestones_res = await db.execute(select(SentinelAIMilestone).order_by(SentinelAIMilestone.target_week))
    milestones = milestones_res.scalars().all()
    
    concepts_res = await db.execute(select(Concept))
    concepts = concepts_res.scalars().all()
    
    return {
        "sprint_status": sprint_status,
        "weeks": [
            {
                "week_number": w.week_number,
                "month_number": w.month_number,
                "title": w.title,
                "focus_dsa": w.focus_dsa,
                "focus_ml_dl": w.focus_ml_dl,
                "focus_sentinelai": w.focus_sentinelai,
                "dsa_target_count": w.dsa_target_count
            } for w in weeks
        ],
        "sentinel_milestones": [
            {
                "id": m.id,
                "version": m.version,
                "target_week": m.target_week,
                "title": m.title,
                "status": m.status,
                "deliverables": m.deliverables
            } for m in milestones
        ],
        "concepts": [
            {
                "id": c.id,
                "domain": c.domain,
                "concept_name": c.name,
                "name": c.name,
                "status": c.status
            } for c in concepts
        ]
    }

@router.post("/api/v1/sprint/update-dates")
async def update_sprint_dates(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    HIGH-RISK ENDPOINT: Updates sprint start date post-activation.
    Requires explicit confirmation (`confirmed = true`).
    """
    confirmed = body.get("confirmed", False)
    if not confirmed:
        raise HTTPException(
            status_code=400, 
            detail="Changing sprint start date after activation is HIGH-RISK and requires explicit confirmation ('confirmed': true)."
        )
        
    start_date_str = body.get("start_date")
    if not start_date_str:
        raise HTTPException(status_code=400, detail="start_date parameter is required.")
        
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_date format. Expected YYYY-MM-DD.")
        
    end_dt = start_dt + timedelta(days=119)
    end_date_str = end_dt.isoformat()
    
    cfg_res = await db.execute(select(SprintConfig))
    cfg = cfg_res.scalar_one_or_none()
    if not cfg:
        cfg = SprintConfig(env_mode=get_current_env_mode(), sprint_activated=True)
        db.add(cfg)
        
    cfg.actual_start_date = start_date_str
    cfg.actual_end_date = end_date_str
    await db.commit()
    
    return {
        "message": "⚠️ Sprint start date updated successfully.",
        "actual_start_date": start_date_str,
        "actual_end_date": end_date_str
    }

@router.post("/api/v1/test/reset")
async def reset_test_data():
    """Resets and re-seeds isolated TEST database and wipes test report files."""
    current_mode = get_current_env_mode()
    if current_mode != "TEST":
        raise HTTPException(status_code=400, detail="RESET TEST DATA can only be called while in TEST mode.")
        
    await init_db_for_mode("TEST", force_recreate=True)
    
    # Clean test reports directory
    if settings.TEST_REPORTS_DIR.exists():
        shutil.rmtree(settings.TEST_REPORTS_DIR)
        settings.TEST_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
    return {"message": "✅ TEST DATA & REPORTS SAFELY RESET.", "env_mode": "TEST"}

@router.post("/api/v1/demo/reset")
async def reset_demo_data():
    """Resets and restores clean curated DEMO database and wipes demo report files."""
    current_mode = get_current_env_mode()
    if current_mode != "DEMO":
        raise HTTPException(status_code=400, detail="RESET DEMO DATA can only be called while in DEMO mode.")
        
    await init_db_for_mode("DEMO", force_recreate=True)
    
    # Clean demo reports directory
    if settings.DEMO_REPORTS_DIR.exists():
        shutil.rmtree(settings.DEMO_REPORTS_DIR)
        settings.DEMO_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
    return {"message": "✅ DEMO DATA SAFELY RESTORED TO CURATED BASELINE.", "env_mode": "DEMO"}

@router.post("/api/v1/jarvis/command")
async def process_jarvis_command(
    body: Dict[str, Any] = Body(...), 
    db: AsyncSession = Depends(get_db)
):
    """JARVIS Natural Language command processor."""
    user_input = body.get("user_input", "")
    confirmed = body.get("confirmed", False)
    
    if not user_input:
        raise HTTPException(status_code=400, detail="Command input cannot be empty.")
        
    result = await JarvisEngine.process_user_input(db, user_input, confirmed=confirmed)
    return result



@router.post("/api/v1/mode/exam")
async def toggle_exam_mode(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Toggles Semester Exam Mode (pauses/reduces interview roadmap temporarily)."""
    enable = body.get("enable", True)
    mode = "EXAM" if enable else "NORMAL"
    
    cfg_res = await db.execute(select(SprintConfig))
    cfg = cfg_res.scalar_one_or_none()
    if cfg:
        cfg.current_mode = mode
        cfg.exam_mode_active = enable
        await db.commit()
        
    return {"message": f"Exam mode set to {enable}. Sprint mode: {mode}"}

@router.post("/api/v1/tasks")
async def create_task(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new study task."""
    task = Task(
        title=body.get("title", "New Task"),
        category=body.get("category", "General"),
        priority=body.get("priority", "medium"),
        status="planned",
        estimated_minutes=body.get("estimated_minutes", 45),
        due_date=body.get("due_date", date.today().isoformat()),
        notes=body.get("notes", ""),
        contribution_tags=body.get("contribution_tags", [])
    )
    db.add(task)
    await db.commit()
    return {"message": f"Task '{task.title}' created successfully.", "task_id": task.id}

@router.put("/api/v1/tasks/{task_id}")
async def update_task_status(
    task_id: int,
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Updates task status."""
    task_res = await db.execute(select(Task).where(Task.id == task_id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.status = body.get("status", task.status)
    await db.commit()
    return {"message": f"Task {task_id} status updated to {task.status}."}

@router.delete("/api/v1/tasks/{task_id}")
async def delete_task_endpoint(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Deletes a task or assignment by ID."""
    task_res = await db.execute(select(Task).where(Task.id == task_id))
    task = task_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    await db.delete(task)
    await db.commit()
    return {"message": f"Task '{task.title}' deleted successfully."}




@router.post("/api/v1/backup/create")
async def trigger_backup(
    db: AsyncSession = Depends(get_db)
):
    """Manually triggers SQLite backup & data export."""
    sqlite_file = BackupService.create_daily_sqlite_backup()
    json_file = await BackupService.export_json(db)
    csv_files = await BackupService.export_csv(db)
    
    return {
        "message": "Manual backup and exports completed successfully.",
        "sqlite_backup": sqlite_file,
        "json_export": json_file,
        "csv_exports": csv_files
    }

# ==========================================
# TIMETABLE & CALENDAR SYNC API ENDPOINTS
# ==========================================

@router.get("/api/v1/timetable")
async def get_timetable_slots(
    day: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Fetches all timetable & calendar synced schedule slots."""
    stmt = select(TimetableSlot).where(TimetableSlot.is_active == True)
    if day:
        stmt = stmt.where((TimetableSlot.day_of_week == day) | (TimetableSlot.day_of_week == "Daily") | (TimetableSlot.day_of_week == "All"))
    stmt = stmt.order_by(TimetableSlot.start_time)
    
    res = await db.execute(stmt)
    slots = res.scalars().all()
    
    cfg_res = await db.execute(select(CalendarConfig))
    cfg = cfg_res.scalar_one_or_none()
    
    return {
        "slots": [
            {
                "id": s.id, "day_of_week": s.day_of_week, "date_str": s.date_str,
                "start_time": s.start_time, "end_time": s.end_time, "title": s.title,
                "category": s.category, "spoken_announcement": s.spoken_announcement,
                "is_blocked": s.is_blocked, "is_active": s.is_active, "source": s.source
            } for s in slots
        ],
        "calendar_config": {
            "ics_url": cfg.ics_url if cfg else None,
            "auto_sync": cfg.auto_sync if cfg else True,
            "voice_enabled": cfg.voice_enabled if cfg else True,
            "last_synced_at": cfg.last_synced_at.isoformat() if (cfg and cfg.last_synced_at) else None
        }
    }

@router.post("/api/v1/timetable")
async def create_timetable_slot(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new timetable slot."""
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
        
    start_time = body.get("start_time", "09:00")
    spoken = body.get("spoken_announcement") or f"Attention! {title} is starting now at {start_time}."
    
    slot = TimetableSlot(
        day_of_week=body.get("day_of_week", "Daily"),
        date_str=body.get("date_str"),
        start_time=start_time,
        end_time=body.get("end_time", "10:00"),
        title=title,
        category=body.get("category", "College"),
        spoken_announcement=spoken,
        is_blocked=body.get("is_blocked", True),
        is_active=True,
        source="manual"
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return {"message": "Timetable slot created successfully.", "id": slot.id}

@router.put("/api/v1/timetable/{slot_id}")
async def update_timetable_slot(
    slot_id: int,
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Updates an existing timetable slot."""
    res = await db.execute(select(TimetableSlot).where(TimetableSlot.id == slot_id))
    slot = res.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Timetable slot not found")
        
    if "title" in body: slot.title = body["title"]
    if "day_of_week" in body: slot.day_of_week = body["day_of_week"]
    if "date_str" in body: slot.date_str = body["date_str"]
    if "start_time" in body: slot.start_time = body["start_time"]
    if "end_time" in body: slot.end_time = body["end_time"]
    if "category" in body: slot.category = body["category"]
    if "spoken_announcement" in body: slot.spoken_announcement = body["spoken_announcement"]
    if "is_blocked" in body: slot.is_blocked = body["is_blocked"]
    if "is_active" in body: slot.is_active = body["is_active"]
    
    await db.commit()
    return {"message": "Timetable slot updated successfully."}

@router.delete("/api/v1/timetable/{slot_id}")
async def delete_timetable_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Deletes a timetable slot."""
    res = await db.execute(select(TimetableSlot).where(TimetableSlot.id == slot_id))
    slot = res.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Timetable slot not found")
        
    await db.delete(slot)
    await db.commit()
    return {"message": "Timetable slot deleted successfully."}

@router.post("/api/v1/calendar/sync")
async def sync_calendar_feed(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Syncs external Google Calendar / iCal URL and imports VEVENT records as time-blocked slots."""
    ics_url = body.get("ics_url", "").strip()
    if not ics_url:
        # Check saved config
        cfg_res = await db.execute(select(CalendarConfig))
        cfg = cfg_res.scalar_one_or_none()
        if cfg and cfg.ics_url:
            ics_url = cfg.ics_url
        else:
            raise HTTPException(status_code=400, detail="No iCal / Google Calendar URL provided")
            
    result = await CalendarService.sync_remote_feed(db, ics_url)
    return result

@router.post("/api/v1/calendar/import")
async def import_calendar_file(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Imports raw iCal (.ics) file text content."""
    content = body.get("ics_content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="ics_content is required")
        
    count = await CalendarService.import_ics_events(db, content, source="ics_file_upload")
    return {"message": f"Successfully imported {count} calendar events.", "events_imported": count}

@router.post("/api/v1/system/speak")
async def system_speak_announcement(body: Dict[str, Any] = Body(...)):
    """Executes Linux / Ubuntu OS speech command (spd-say / espeak / say) if available on the host machine."""
    text = body.get("text", "").strip()
    if not text:
        return {"status": "ignored"}
        
    try:
        if shutil.which("spd-say"):
            subprocess.Popen(["spd-say", "-r", "0", "-p", "0", text])
            return {"status": "success", "engine": "spd-say"}
        elif shutil.which("espeak"):
            subprocess.Popen(["espeak", text])
            return {"status": "success", "engine": "espeak"}
        elif shutil.which("say"):
            subprocess.Popen(["say", text])
            return {"status": "success", "engine": "say"}
    except Exception as e:
        print("System speech exception:", e)
        
    return {"status": "client_speech_only"}

@router.post("/api/v1/wall/sleep")
async def toggle_wall_sleep(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Toggles or sets wall_sleep_mode state in SprintConfig."""
    cfg_res = await db.execute(select(SprintConfig))
    cfg = cfg_res.scalar_one_or_none()
    if not cfg:
        cfg = SprintConfig(env_mode=get_current_env_mode())
        db.add(cfg)
        
    sleep_state = body.get("sleep", not cfg.wall_sleep_mode)
    cfg.wall_sleep_mode = sleep_state
    await db.commit()
    return {"message": f"Wall Sleep Mode set to {sleep_state}", "wall_sleep_mode": cfg.wall_sleep_mode}

