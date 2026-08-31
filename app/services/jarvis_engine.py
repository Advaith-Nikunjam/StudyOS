import re
import json
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.safety import SafetyGuardrail, RiskLevel
from app.db.session import set_current_env_mode, get_current_env_mode
from app.db.models import (
    Task, DSALog, Mistake, Concept, SentinelAIMilestone, SprintConfig, 
    DayLog, JarvisLog, CollegeEvent, SpacedRevision, WeaknessRecord, WeeklyReview
)
from app.services.roadmap_service import RoadmapService
from app.services.revision_service import SpacedRevisionService
from app.services.weakness_service import WeaknessService
from app.services.recovery_service import RecoveryService
from app.services.weekly_review_service import WeeklyReviewService

class JarvisEngine:
    @staticmethod
    def _extract_and_normalize_date(text: str) -> Tuple[str, Optional[str]]:
        """
        Extracts date in DD-MM-YYYY, DD/MM/YYYY, or YYYY-MM-DD format.
        Normalizes to YYYY-MM-DD. Returns (cleaned_text_without_date, iso_date_str).
        """
        # 1. Check DD-MM-YYYY or DD/MM/YYYY
        m_dmy = re.search(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', text)
        if m_dmy:
            day = int(m_dmy.group(1))
            month = int(m_dmy.group(2))
            year = int(m_dmy.group(3))
            try:
                dt_obj = date(year, month, day)
                iso_date = dt_obj.isoformat()
                cleaned = text[:m_dmy.start()] + text[m_dmy.end():]
                return cleaned.strip(), iso_date
            except ValueError:
                pass
                
        # 2. Check YYYY-MM-DD
        m_ymd = re.search(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b', text)
        if m_ymd:
            year = int(m_ymd.group(1))
            month = int(m_ymd.group(2))
            day = int(m_ymd.group(3))
            try:
                dt_obj = date(year, month, day)
                iso_date = dt_obj.isoformat()
                cleaned = text[:m_ymd.start()] + text[m_ymd.end():]
                return cleaned.strip(), iso_date
            except ValueError:
                pass

        return text, None

    @staticmethod
    async def process_user_input(
        session: AsyncSession, 
        user_input: str, 
        confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Processes natural language user input.
        Enforces 3-Tier Safety Guardrails and Mode Isolation.
        """
        cleaned_input = user_input.strip()
        
        action_type, payload = JarvisEngine._parse_command_intent(cleaned_input)
        
        is_allowed, risk_level, safety_msg = SafetyGuardrail.validate_action(action_type, payload, confirmed=confirmed)
        
        if action_type == "UNKNOWN_COMMAND":
            log_entry = JarvisLog(
                user_input=cleaned_input,
                risk_level=risk_level.value,
                actions_taken=[{"action": action_type, "payload": payload}],
                confirmed=confirmed,
                status="unrecognized"
            )
            session.add(log_entry)
            await session.commit()
            return {
                "success": False,
                "requires_confirmation": False,
                "risk_level": risk_level.value,
                "action_type": action_type,
                "message": "JARVIS could not understand that command. Try 'show today's revisions', 'show weaknesses', 'show recovery plan', or 'set must win ...'.",
                "data": None
            }

        log_entry = JarvisLog(
            user_input=cleaned_input,
            risk_level=risk_level.value,
            actions_taken=[{"action": action_type, "payload": payload}],
            confirmed=confirmed,
            status="pending" if not is_allowed else "success"
        )
        session.add(log_entry)
        
        if not is_allowed:
            await session.commit()
            return {
                "success": False,
                "requires_confirmation": True,
                "risk_level": risk_level.value,
                "action_type": action_type,
                "payload": payload,
                "message": safety_msg,
                "preview": f"Preview: Request to perform [{action_type}] on target payload. Confirm execution?"
            }
            
        execution_result = await JarvisEngine._execute_action(session, action_type, payload)
        await session.commit()
        
        return {
            "success": True,
            "requires_confirmation": False,
            "risk_level": risk_level.value,
            "action_type": action_type,
            "message": execution_result["message"],
            "data": execution_result.get("data")
        }

    @staticmethod
    def _parse_command_intent(text: str) -> Tuple[str, Dict[str, Any]]:
        """Structured command fallback parser supporting exact study command vocabulary."""
        lower = text.lower()
        
        # Mode Switch Commands
        if "switch to real mode" in lower or "enter real mode" in lower or "real mode" in lower:
            return "SWITCH_TO_REAL_MODE", {"mode": "REAL"}
        if "switch to test mode" in lower or "enter test mode" in lower or "test mode" in lower:
            return "SWITCH_TO_TEST_MODE", {"mode": "TEST"}
        if "switch to demo mode" in lower or "enter demo mode" in lower or "demo mode" in lower:
            return "SWITCH_TO_DEMO_MODE", {"mode": "DEMO"}

        # Start 120-Day Sprint (High-Risk action)
        if "start 120-day sprint" in lower or "activate sprint" in lower or "start sprint" in lower:
            return "START_SPRINT", {"action": "activate_sprint"}

        # Reset Test / Demo Data
        if "reset test data" in lower or "reset test" in lower:
            return "RESET_TEST_DATA", {}
        if "reset demo data" in lower or "reset demo" in lower:
            return "RESET_DEMO_DATA", {}

        # Show Revisions
        if "show today's revisions" in lower or "show revisions" in lower or "todays revisions" in lower or "my revisions" in lower:
            return "SHOW_REVISIONS", {}

        # Show Weaknesses
        if "show my weaknesses" in lower or "show weakness radar" in lower or "show weaknesses" in lower or "weakness radar" in lower:
            return "SHOW_WEAKNESSES", {}

        # Show Recovery Plan
        if "show recovery plan" in lower or "recovery plan" in lower or "recovery status" in lower:
            return "SHOW_RECOVERY_PLAN", {}

        # Set Today's Must Win
        if "set today's must win" in lower or "set must win" in lower or lower.startswith("must win:"):
            must_win_text = re.sub(r'^(set today\'s must win|set must win|must win:)\s*', '', text, flags=re.IGNORECASE).strip()
            return "SET_MUST_WIN", {"text": must_win_text}

        # Complete Revision
        if lower.startswith("complete revision") or lower.startswith("finish revision"):
            concept_name = re.sub(r'^(complete revision|finish revision)\s*', '', text, flags=re.IGNORECASE).strip()
            return "COMPLETE_REVISION", {"concept": concept_name}

        # Start Weekly Review
        if "start weekly review" in lower or "weekly review" in lower:
            return "START_WEEKLY_REVIEW", {}

        # Start Day
        if "start day" in lower or "start my study day" in lower or "start my day" in lower:
            return "START_DAY", {}
            
        # End Day
        if "end day" in lower or "end my study day" in lower or "end my day" in lower:
            return "END_DAY", {}
            
        # Activate Exam Mode
        if "activate exam mode" in lower or "enable exam mode" in lower:
            return "ACTIVATE_EXAM_MODE", {"mode": "EXAM"}
            
        # Deactivate Exam Mode
        if "deactivate exam mode" in lower or "exit exam mode" in lower:
            return "DEACTIVATE_EXAM_MODE", {"mode": "NORMAL"}

        # Log DSA Problem (with solve quality classification)
        if ("dsa" in lower or "problem" in lower or "leetcode" in lower) and ("solved" in lower or "studied" in lower or "revisit" in lower):
            solve_type = "solved"
            if "studied" in lower or "solution" in lower:
                solve_type = "studied_solution"
            elif "help" in lower or "hint" in lower:
                solve_type = "solved_with_help"
            elif "revisit" in lower:
                solve_type = "needs_revisit"
            
            nums = re.findall(r'\d+', lower)
            count = int(nums[0]) if nums else 1
            return "LOG_DSA_PROBLEM", {"count": count, "topic": "DSA Practice", "difficulty": "Medium", "solve_type": solve_type}

        # Add Mistake
        if "mistake" in lower or "struggled with" in lower:
            return "ADD_MISTAKE", {
                "category": "technical",
                "mistake_type": "missed pattern" if "pattern" in lower else "concept confusion",
                "description": text
            }

        # Milestone completion (High Risk)
        if "finished sentinelai" in lower or "completed milestone" in lower:
            ver_match = re.search(r'v\d+\.\d+', lower)
            ver = ver_match.group(0).upper() if ver_match else "V0.1"
            return "ALTER_SENTINELAI_MILESTONE", {"version": ver, "status": "completed"}

        # Complete task
        if lower.startswith("complete task") or lower.startswith("finish task"):
            title = text.replace("complete task", "").replace("finish task", "").strip()
            return "COMPLETE_TASK", {"title": title}

        # College Event Creation
        college_event_keywords = ["exam", "quiz", "midterm", "viva", "lab exam", "presentation"]
        if any(kw in lower for kw in college_event_keywords):
            cleaned_text, iso_date = JarvisEngine._extract_and_normalize_date(text)
            due_date = iso_date or date.today().isoformat()
            
            event_type = "exam"
            if "quiz" in lower:
                event_type = "quiz"
            elif "lab" in lower:
                event_type = "lab"
            elif "viva" in lower:
                event_type = "viva"
            elif "presentation" in lower:
                event_type = "presentation"

            subject = "College"
            if "daa" in lower or "algorithm" in lower:
                subject = "Design and Analysis of Algorithms"
            elif "deep learning" in lower or "dl" in lower:
                subject = "Deep Learning"
            elif "computer vision" in lower or "cv" in lower:
                subject = "Computer Vision"

            title_text = cleaned_text
            for prefix in ["add ", "create ", "my ", "i have a ", "i have an "]:
                if title_text.lower().startswith(prefix):
                    title_text = title_text[len(prefix):].strip()
                    break
            for prep in ["is on", "due on", "on", "is due"]:
                if title_text.lower().endswith(" " + prep):
                    title_text = title_text[:-len(prep)-1].strip()
                elif title_text.lower() == prep:
                    title_text = ""

            title = title_text if title_text else f"{subject} {event_type.capitalize()}"
            return "ADD_COLLEGE_EVENT", {
                "title": title,
                "subject_name": subject,
                "event_type": event_type,
                "due_date": due_date,
                "priority": "high"
            }

        # Add Task
        task_triggers = [
            "add task", "create task", "add college task", "add assignment", "assignment",
            "due", "i have a", "i have an"
        ]
        is_task_command = (
            lower.startswith("add ") or 
            lower.startswith("create ") or 
            any(t in lower for t in task_triggers)
        )
        if is_task_command:
            cleaned_text, iso_date = JarvisEngine._extract_and_normalize_date(text)
            due_date = iso_date or date.today().isoformat()

            title_text = cleaned_text
            prefixes = [
                "add college task ", "create task ", "add task ", "add assignment ",
                "add ", "create ", "i have a ", "i have an "
            ]
            for p in prefixes:
                if title_text.lower().startswith(p):
                    title_text = title_text[len(p):].strip()
                    break

            prepositions = ["due on", "is due on", "due", "on", "is on", "by"]
            for prep in prepositions:
                if title_text.lower().endswith(" " + prep):
                    title_text = title_text[:-len(prep)-1].strip()

            if title_text.lower().startswith("assignment "):
                sub_part = title_text[11:].strip()
                title_text = f"{sub_part} assignment"

            college_kws = ["assignment", "college", "exam", "quiz", "lab", "daa", "deep learning", "computer vision", "cs-701", "cs-702", "cs-503"]
            if any(kw in lower for kw in college_kws):
                category = "College"
            elif "dsa" in lower:
                category = "DSA"
            elif "ml" in lower:
                category = "ML"
            elif "dl" in lower:
                category = "DL"
            elif "cv" in lower:
                category = "ComputerVision"
            elif "sentinel" in lower:
                category = "SentinelAI"
            else:
                category = "General"

            title = title_text if title_text else "New Task"
            return "ADD_TASK", {
                "title": title,
                "category": category,
                "due_date": due_date,
                "priority": "high" if category == "College" else "medium"
            }

        # Show Progress
        if "show progress" in lower or "how am i doing" in lower or "status" in lower:
            return "SEARCH_QUERY", {"query": "progress"}

        return "UNKNOWN_COMMAND", {"query": text}

    @staticmethod
    async def _execute_action(session: AsyncSession, action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes validated safe or confirmed action on database models."""
        if action_type in ["SWITCH_TO_REAL_MODE", "SWITCH_TO_TEST_MODE", "SWITCH_TO_DEMO_MODE", "SWITCH_ENV_MODE"]:
            target_mode = payload.get("mode", "REAL")
            set_current_env_mode(target_mode)
            if target_mode == "REAL":
                msg = "⚠️ Switched to REAL MODE. You are operating on your actual study data!"
            elif target_mode == "TEST":
                msg = "🧪 Switched to TEST MODE. Real study data is isolated and untouched."
            else:
                msg = "📊 Switched to DEMO MODE. Pre-populated demonstration dataset active (Isolated)."
            return {"message": msg, "env_mode": target_mode}

        elif action_type == "SHOW_REVISIONS":
            rev_data = await SpacedRevisionService.get_todays_revisions(session)
            today_names = [f"☐ {r['concept_name']} (Rev #{r['revision_number']})" for r in rev_data["today"]]
            overdue_names = [f"⚠️ {r['concept_name']} ({r['days_overdue']}d overdue)" for r in rev_data["overdue"]]
            
            summary = "Today's Revisions:\n" + ("\n".join(today_names) if today_names else "None scheduled for today.")
            if overdue_names:
                summary += "\n\nOverdue Queue:\n" + "\n".join(overdue_names)
            return {"message": summary, "data": rev_data}

        elif action_type == "SHOW_WEAKNESSES":
            w_data = await WeaknessService.get_weakness_radar_summary(session)
            if not w_data["top_weaknesses"]:
                return {"message": "Weakness Radar: Zero active weaknesses recorded! Excellent mastery.", "data": w_data}
            lines = ["WEAKNESS RADAR:"]
            for w in w_data["top_weaknesses"]:
                lines.append(f"• [{w['category']}] {w['topic']}: {w['mistake_count']} mistakes (Severity: {w['severity'].upper()})")
            return {"message": "\n".join(lines), "data": w_data}

        elif action_type == "SHOW_RECOVERY_PLAN":
            rec_data = await RecoveryService.get_recovery_plan(session)
            if not rec_data["recovery_mode_active"]:
                return {"message": "Recovery Mode: No overdue backlog detected. You are 100% on schedule!", "data": rec_data}
            lines = [
                "RECOVERY PLAN:",
                f"• Missed Workload: {rec_data['total_missed_hours']} hrs ({rec_data['overdue_tasks_count']} tasks, {rec_data['overdue_revisions_count']} revisions)",
                f"• Normal Workload Today: {rec_data['normal_workload_hours']} hrs",
                f"• Capped Recovery Workload Today: {rec_data['recovery_workload_hours']} hrs (Cap: {rec_data['recovery_cap_hours']} hrs)",
                f"• Total Today's Target: {rec_data['total_workload_hours']} hrs",
                f"• Estimated Days to Clear Backlog: {rec_data['days_to_clear_backlog']} days"
            ]
            return {"message": "\n".join(lines), "data": rec_data}

        elif action_type == "SET_MUST_WIN":
            text_val = payload.get("text", "Execute today's study plan.")
            today_str = date.today().isoformat()
            d_res = await session.execute(select(DayLog).where(DayLog.date == today_str))
            day_log = d_res.scalar_one_or_none()
            if not day_log:
                sprint_status = await RoadmapService.get_sprint_status(session)
                day_log = DayLog(date=today_str, day_number=sprint_status["day_number"])
                session.add(day_log)
            day_log.must_win_text = text_val
            return {"message": f"Today's Must Win set to: '{text_val}'"}

        elif action_type == "COMPLETE_REVISION":
            concept_query = payload.get("concept", "")
            rev_res = await session.execute(
                select(SpacedRevision).where(
                    SpacedRevision.concept_name.ilike(f"%{concept_query}%"),
                    SpacedRevision.completed == False
                )
            )
            rev_item = rev_res.scalars().first()
            if rev_item:
                await SpacedRevisionService.complete_revision(session, rev_item.id)
                await WeaknessService.record_successful_revision(session, topic=rev_item.concept_name, category=rev_item.domain)
                return {"message": f"Completed revision for '{rev_item.concept_name}' (Rev #{rev_item.revision_number})."}
            return {"message": f"No pending revision schedule found matching '{concept_query}'."}

        elif action_type == "START_WEEKLY_REVIEW":
            sprint_status = await RoadmapService.get_sprint_status(session)
            week_num = max(1, sprint_status["current_week"])
            rev_obj = await WeeklyReviewService.create_or_update_weekly_review(session, week_number=week_num)
            report_file = await ReportingService.generate_weekly_report(session, week_number=week_num)
            return {"message": f"Weekly Review for Week {week_num} generated! Saved to report file: {report_file}"}

        elif action_type == "LOG_DSA_PROBLEM":
            count = payload.get("count", 1)
            topic = payload.get("topic", "General DSA")
            difficulty = payload.get("difficulty", "Medium")
            solve_type = payload.get("solve_type", "solved")
            
            independent = (solve_type == "solved")
            hint_used = (solve_type in ["solved_with_help", "studied_solution"])
            solution_seen = (solve_type == "studied_solution")

            for i in range(count):
                dsa_entry = DSALog(
                    problem_name=f"DSA Problem ({topic}) #{i+1}",
                    topic=topic,
                    difficulty=difficulty,
                    independent_solve=independent,
                    hint_used=hint_used,
                    solution_seen=solution_seen,
                    solve_type=solve_type,
                    time_taken_mins=30
                )
                session.add(dsa_entry)
                if solve_type in ["needs_revisit", "studied_solution"]:
                    await SpacedRevisionService.create_schedule_for_concept(session, concept_name=f"DSA: {topic} Problem #{i+1}", domain="DSA")

            return {"message": f"Successfully logged {count} DSA problem(s) ({solve_type}) under '{topic}'."}

        elif action_type == "ADD_MISTAKE":
            mistake_desc = payload.get("description", "Recorded via JARVIS")
            mistake_type = payload.get("mistake_type", "concept confusion")
            category = payload.get("category", "technical")
            
            # Record in WeaknessRecord for persistent weakness analysis
            topic = "General DSA"
            if "dp" in mistake_desc.lower() or "dynamic" in mistake_desc.lower():
                topic = "Dynamic Programming"
            elif "binary" in mistake_desc.lower() or "search" in mistake_desc.lower():
                topic = "Binary Search"
            elif "cnn" in mistake_desc.lower() or "convolution" in mistake_desc.lower():
                topic = "CNN Architectures"

            await WeaknessService.record_mistake_for_topic(
                session, topic=topic, category=category, description=mistake_desc, severity="medium"
            )
            return {"message": f"Mistake in '{topic}' recorded in Weakness Radar."}

        elif action_type == "COMPLETE_TASK":
            title_query = payload.get("title", "")
            task_res = await session.execute(
                select(Task).where(Task.title.ilike(f"%{title_query}%"))
            )
            task = task_res.scalars().first()
            if task:
                task.status = "completed"
                return {"message": f"Task '{task.title}' marked as COMPLETED."}
            return {"message": f"No active task matching '{title_query}' found."}

        elif action_type == "ADD_TASK":
            title = payload.get("title", "New Study Task")
            category = payload.get("category", "General")
            priority = payload.get("priority", "medium")
            due_date = payload.get("due_date", date.today().isoformat())
            
            new_task = Task(
                title=title,
                category=category,
                priority=priority,
                due_date=due_date,
                status="planned",
                source="generated"
            )
            session.add(new_task)
            return {
                "message": f"New task '{new_task.title}' [{category}] due {due_date} added to study schedule.",
                "data": {"task_id": new_task.id, "due_date": due_date, "category": category}
            }

        elif action_type == "ADD_COLLEGE_EVENT":
            title = payload.get("title", "College Event")
            subject_name = payload.get("subject_name", "College")
            event_type = payload.get("event_type", "other")
            due_date = payload.get("due_date", date.today().isoformat())
            priority = payload.get("priority", "high")
            
            new_event = CollegeEvent(
                title=title,
                subject_name=subject_name,
                event_type=event_type,
                due_date=due_date,
                priority=priority,
                status="upcoming"
            )
            session.add(new_event)
            return {
                "message": f"College Event '{new_event.title}' scheduled for {due_date}.",
                "data": {"event_id": new_event.id, "due_date": due_date}
            }

        elif action_type in ["ACTIVATE_EXAM_MODE", "DEACTIVATE_EXAM_MODE"]:
            mode = "EXAM" if action_type == "ACTIVATE_EXAM_MODE" else "NORMAL"
            cfg_res = await session.execute(select(SprintConfig))
            cfg = cfg_res.scalar_one_or_none()
            if cfg:
                cfg.current_mode = mode
                cfg.exam_mode_active = (mode == "EXAM")
            return {"message": f"Sprint mode changed to {mode}. Wall display and schedules updated."}

        elif action_type == "ALTER_SENTINELAI_MILESTONE":
            ver = payload.get("version", "V0.1")
            ms_res = await session.execute(
                select(SentinelAIMilestone).where(SentinelAIMilestone.version == ver)
            )
            ms = ms_res.scalar_one_or_none()
            if ms:
                ms.status = "completed"
                ms.completion_percentage = 100
                ms.completed_at = datetime.now(timezone.utc)
                return {"message": f"SentinelAI Milestone {ver} marked COMPLETED."}
            return {"message": f"Milestone {ver} not found."}

        return {"message": f"Action [{action_type}] executed successfully."}
