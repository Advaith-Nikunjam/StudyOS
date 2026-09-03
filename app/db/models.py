from datetime import datetime, date, timezone
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, Float, ForeignKey, JSON
from app.db.session import Base

class SprintConfig(Base):
    __tablename__ = "sprint_config"
    
    id = Column(Integer, primary_key=True, index=True)
    env_mode = Column(String, default="REAL") # REAL, TEST, DEMO
    sprint_activated = Column(Boolean, default=False) # Permanent Pre-Sprint state flag
    actual_start_date = Column(String, nullable=True) # e.g., "2026-08-24"
    actual_end_date = Column(String, nullable=True)   # start_date + 119 days
    activated_at = Column(DateTime, nullable=True)
    
    total_days = Column(Integer, default=120)
    current_mode = Column(String, default="NORMAL") # NORMAL, DEADLINE, EXAM, CUSTOM
    exam_mode_active = Column(Boolean, default=False)
    wall_sleep_mode = Column(Boolean, default=False) # Explicit wall display sleep state
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class RoadmapWeek(Base):
    __tablename__ = "roadmap_weeks"
    
    id = Column(Integer, primary_key=True, index=True)
    week_number = Column(Integer, unique=True, index=True) # 1 to 16
    month_number = Column(Integer) # 1 to 4
    title = Column(String)
    focus_dsa = Column(Text)
    focus_ml_dl = Column(Text)
    focus_sentinelai = Column(Text)
    dsa_target_count = Column(Integer, default=15)
    is_completed = Column(Boolean, default=False)

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    category = Column(String, index=True) # DSA, ML, DL, CV, SentinelAI, College, Interview, Review, General
    priority = Column(String, default="medium") # high, medium, low
    status = Column(String, default="planned", index=True) # planned, in_progress, completed, skipped, postponed
    estimated_minutes = Column(Integer, default=45)
    due_date = Column(String, default=lambda: date.today().isoformat())
    source = Column(String, default="roadmap") # roadmap, generated, manual
    notes = Column(Text, nullable=True)
    contribution_tags = Column(JSON, default=list) # Overlap tags: e.g. ["DL_INTERVIEW", "COLLEGE_DL", "SENTINELAI"]
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class DSALog(Base):
    __tablename__ = "dsa_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    problem_name = Column(String, index=True)
    topic = Column(String, index=True) # Big-O, Arrays, Strings, Hashing, Two Pointers, Sliding Window, Trees, Graphs, DP...
    difficulty = Column(String, default="Medium") # Easy, Medium, Hard
    time_taken_mins = Column(Integer, default=30)
    independent_solve = Column(Boolean, default=True) # True = mastered candidate, False = hint/solution
    hint_used = Column(Boolean, default=False)
    solution_seen = Column(Boolean, default=False)
    solve_type = Column(String(30), default="solved") # solved, solved_with_help, studied_solution, needs_revisit
    mistake_type = Column(String, nullable=True) # misunderstood problem, missed pattern, brute force trap, etc.
    revisit_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Mistake(Base):
    __tablename__ = "mistakes"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, default="technical") # technical, conceptual, productivity
    mistake_type = Column(String, index=True)
    description = Column(Text)
    topic = Column(String, nullable=True)
    severity = Column(String, default="medium") # low, medium, high, critical
    occurrences_count = Column(Integer, default=1)
    resolved = Column(Boolean, default=False)
    last_occurred_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Concept(Base):
    __tablename__ = "concepts"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True) # ML, DL, CV
    name = Column(String, index=True)
    status = Column(String, default="not_started") # not_started, learning, implemented, explained, mastered, needs_revision
    notes = Column(Text, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)

class SentinelAIMilestone(Base):
    __tablename__ = "sentinelai_milestones"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, index=True) # V0.1, V0.2 ... V1.4
    title = Column(String)
    target_week = Column(Integer)
    status = Column(String, default="pending") # pending, in_progress, completed
    deliverables = Column(JSON, default=list)
    completion_percentage = Column(Integer, default=0)
    lessons_learned = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class CollegeSubject(Base):
    __tablename__ = "college_subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Deep Learning, Computer Vision, DAA, etc.
    code = Column(String, nullable=True)
    exam_date = Column(String, nullable=True)
    exam_time = Column(String, nullable=True)
    target_prep_percentage = Column(Integer, default=100)
    priority = Column(String, default="high")

class CollegeSyllabusTopic(Base):
    __tablename__ = "college_syllabus_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("college_subjects.id"))
    unit_name = Column(String) # Unit 1, Unit 2...
    topic_name = Column(String)
    status = Column(String, default="not_started") # not_started, learning, revised, mastered
    notes = Column(Text, nullable=True)

class CollegeEvent(Base):
    __tablename__ = "college_events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    subject_name = Column(String, nullable=True)
    event_type = Column(String) # exam, assignment, quiz, lab, presentation, viva, project_submission, registration, attendance_deadline, other
    due_date = Column(String, index=True)
    due_time = Column(String, nullable=True)
    priority = Column(String, default="high")
    status = Column(String, default="upcoming") # upcoming, in_progress, completed, postponed, missed, cancelled
    alert_preset = Column(String, default="default") # default, 7d_3d_1d, exam_preset, quiz_preset
    notes = Column(Text, nullable=True)

class ExamPeriod(Base):
    __tablename__ = "exam_periods"
    
    id = Column(Integer, primary_key=True, index=True)
    semester_name = Column(String) # e.g. "Semester 5 Exams"
    start_date = Column(String)
    end_date = Column(String)
    active = Column(Boolean, default=False)
    policy = Column(Text, nullable=True)

class DayLog(Base):
    __tablename__ = "day_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True) # YYYY-MM-DD
    day_number = Column(Integer) # Day 1 to 120 (0 if pre-sprint)
    available_hours = Column(Float, default=4.0)
    constraints = Column(Text, nullable=True)
    energy_level = Column(String, default="High")
    top_priority = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    what_learned = Column(Text, nullable=True)
    mistakes_noted = Column(Text, nullable=True)
    completed_task_ids = Column(JSON, default=list)
    focused_hours = Column(Float, default=0.0)
    status = Column(String, default="active") # active, closed
    must_win_text = Column(Text, nullable=True)
    must_win_result = Column(String, nullable=True) # achieved, partially_achieved, missed

class SpacedRevision(Base):
    __tablename__ = "spaced_revisions"
    
    id = Column(Integer, primary_key=True, index=True)
    concept_name = Column(String, index=True)
    domain = Column(String, index=True) # ML, DL, CV, DSA, College
    original_date = Column(String, default=lambda: date.today().isoformat())
    revision_number = Column(Integer) # 1, 2, 3, 4, 5
    scheduled_date = Column(String, index=True) # YYYY-MM-DD
    completed = Column(Boolean, default=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    overdue = Column(Boolean, default=False)
    confidence_rating = Column(String, nullable=True) # low, medium, high
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class WeaknessRecord(Base):
    __tablename__ = "weakness_records"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    category = Column(String, index=True) # DSA, ML, DL, CV, College
    mistake_count = Column(Integer, default=1)
    successful_revisions_count = Column(Integer, default=0)
    severity = Column(String, default="medium", index=True) # low, medium, high, critical
    most_recent_mistake = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_revision_at = Column(DateTime, nullable=True)
    resolved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    week_number = Column(Integer, index=True)
    year = Column(Integer, default=2026)
    period_key = Column(String, unique=True, index=True) # e.g. "2026-W34" or "week_04"
    dsa_target = Column(Integer, default=18)
    dsa_solved = Column(Integer, default=0)
    ml_dl_cv_target = Column(Integer, default=4)
    ml_dl_cv_completed = Column(Integer, default=0)
    sentinelai_version = Column(String, nullable=True)
    sentinelai_status = Column(String, nullable=True)
    college_tasks_total = Column(Integer, default=0)
    college_tasks_completed = Column(Integer, default=0)
    top_weakness = Column(String, nullable=True)
    revisions_scheduled = Column(Integer, default=0)
    revisions_completed = Column(Integer, default=0)
    must_win_success_rate = Column(Float, default=0.0)
    q1_missed_work_cause = Column(Text, nullable=True)
    q2_biggest_difficulty = Column(Text, nullable=True)
    q3_next_week_improvements = Column(Text, nullable=True)
    q4_next_week_priority = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ReportLog(Base):
    __tablename__ = "report_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String) # daily, weekly, monthly, milestone
    period_key = Column(String) # YYYY-MM-DD or week_01 or YYYY-MM
    file_path = Column(String)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class JarvisLog(Base):
    __tablename__ = "jarvis_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_input = Column(Text)
    risk_level = Column(String, default="SAFE") # SAFE, MODERATE, HIGH_RISK
    actions_taken = Column(JSON, default=list)
    confirmed = Column(Boolean, default=True)
    status = Column(String, default="success") # success, pending_confirmation, rejected

class TimetableSlot(Base):
    __tablename__ = "timetable_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(String, index=True) # Monday..Sunday, Daily
    date_str = Column(String, nullable=True, index=True) # Specific date if synced (e.g. "2026-09-10")
    start_time = Column(String, index=True) # HH:MM (e.g. "09:00")
    end_time = Column(String)               # HH:MM (e.g. "11:00")
    title = Column(String)                  # e.g. "DAA Exam", "College Lecture"
    category = Column(String, default="College") # College, Exam, Assignment, DSA, ML, DL, SentinelAI, Break, General
    spoken_announcement = Column(Text, nullable=True) # Text spoken out loud at start time
    is_blocked = Column(Boolean, default=True) # True = blocks roadmap tasks during window
    is_active = Column(Boolean, default=True)
    source = Column(String, default="manual")  # manual, ical_sync, google_cal
    external_event_id = Column(String, nullable=True, index=True) # UID from iCal
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CalendarConfig(Base):
    __tablename__ = "calendar_config"
    
    id = Column(Integer, primary_key=True, index=True)
    ics_url = Column(String, nullable=True)
    auto_sync = Column(Boolean, default=True)
    voice_enabled = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)


