import re
import urllib.request
from datetime import datetime, date, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.models import TimetableSlot, CalendarConfig, CollegeEvent

class CalendarService:
    """
    Calendar Integration & Sync Engine.
    Parses standard iCal (.ics) format feeds (Google Calendar, Apple, Outlook, University Portals),
    extracts VEVENT instances, creates TimetableSlot records, and blocks conflicting time slots.
    """

    @staticmethod
    def parse_ics_datetime(dt_str: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parses iCal DTSTART/DTEND string (e.g., '20260910T090000Z' or '20260910T090000' or '20260910').
        Returns (date_str 'YYYY-MM-DD', time_str 'HH:MM').
        """
        if not dt_str:
            return None, None
        
        # Clean parameter prefixes if any (e.g. VALUE=DATE:20260910)
        if ":" in dt_str:
            dt_str = dt_str.split(":")[-1]
            
        dt_str = dt_str.strip()
        
        if len(dt_str) >= 8:
            y = dt_str[0:4]
            m = dt_str[4:6]
            d = dt_str[6:8]
            date_str = f"{y}-{m}-{d}"
            
            time_str = "09:00"
            if "T" in dt_str and len(dt_str) >= 13:
                t_part = dt_str.split("T")[1]
                hh = t_part[0:2]
                mm = t_part[2:4]
                time_str = f"{hh}:{mm}"
            return date_str, time_str
            
        return None, None

    @classmethod
    def parse_ics_text(cls, ics_content: str) -> List[Dict[str, Any]]:
        """
        Parses iCal format string and extracts VEVENT entries.
        """
        events = []
        in_vevent = False
        current_evt = {}
        
        # Unfold lines wrapped per RFC 5545
        lines = ics_content.replace("\r\n ", "").replace("\n ", "").splitlines()
        
        for line in lines:
            line = line.strip()
            if line == "BEGIN:VEVENT":
                in_vevent = True
                current_evt = {}
            elif line == "END:VEVENT":
                if in_vevent and "summary" in current_evt and current_evt["summary"]:
                    events.append(current_evt)
                in_vevent = False
            elif in_vevent:
                if ":" in line:
                    key_raw, value = line.split(":", 1)
                    key = key_raw.split(";")[0].upper().strip()
                    value = value.strip()
                    
                    if key == "SUMMARY":
                        current_evt["summary"] = value
                    elif key == "UID":
                        current_evt["uid"] = value
                    elif key == "DTSTART":
                        date_str, time_str = cls.parse_ics_datetime(line)
                        current_evt["date_str"] = date_str
                        current_evt["start_time"] = time_str
                    elif key == "DTEND":
                        date_str, time_str = cls.parse_ics_datetime(line)
                        current_evt["end_time"] = time_str
                    elif key == "DESCRIPTION":
                        current_evt["description"] = value
                    elif key == "LOCATION":
                        current_evt["location"] = value
                        
        return events

    @classmethod
    async def import_ics_events(cls, db: AsyncSession, ics_content: str, source: str = "google_cal") -> int:
        """
        Processes parsed VEVENT objects and inserts/updates TimetableSlot & CollegeEvent records in SQLite.
        Marks imported slots as is_blocked = True.
        """
        parsed_events = cls.parse_ics_text(ics_content)
        imported_count = 0
        
        for evt in parsed_events:
            summary = evt.get("summary", "Calendar Event")
            date_str = evt.get("date_str") or date.today().isoformat()
            start_time = evt.get("start_time") or "09:00"
            end_time = evt.get("end_time") or "10:00"
            uid = evt.get("uid") or f"evt_{date_str}_{start_time}_{summary}"
            
            # Determine Day of Week
            try:
                dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
                day_of_week = dt_obj.strftime("%A")
            except Exception:
                day_of_week = "Monday"
                
            # Check if event exists by external_event_id or (date_str + start_time + title)
            stmt = select(TimetableSlot).where(
                (TimetableSlot.external_event_id == uid) |
                ((TimetableSlot.date_str == date_str) & (TimetableSlot.start_time == start_time) & (TimetableSlot.title == summary))
            )
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            
            spoken = f"Attention! Calendar Event: {summary} starts now at {start_time}."
            if "exam" in summary.lower() or "test" in summary.lower() or "quiz" in summary.lower():
                spoken = f"Attention! Important Academic Event: {summary} is scheduled now at {start_time}."
                category = "Exam"
            else:
                category = "College"
                
            if existing:
                existing.title = summary
                existing.start_time = start_time
                existing.end_time = end_time
                existing.date_str = date_str
                existing.day_of_week = day_of_week
                existing.category = category
                existing.spoken_announcement = spoken
                existing.is_blocked = True
                existing.source = source
            else:
                slot = TimetableSlot(
                    day_of_week=day_of_week,
                    date_str=date_str,
                    start_time=start_time,
                    end_time=end_time,
                    title=summary,
                    category=category,
                    spoken_announcement=spoken,
                    is_blocked=True,
                    is_active=True,
                    source=source,
                    external_event_id=uid
                )
                db.add(slot)
                
            imported_count += 1
            
        await db.commit()
        return imported_count

    @classmethod
    async def sync_remote_feed(cls, db: AsyncSession, ics_url: str) -> Dict[str, Any]:
        """
        Fetches external iCal URL and runs import_ics_events.
        """
        if not ics_url or not ics_url.startswith("http"):
            return {"status": "error", "message": "Invalid iCal / Google Calendar URL"}
            
        try:
            req = urllib.request.Request(
                ics_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StudyOS/2.0 CalendarSync"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                
            count = await cls.import_ics_events(db, content, source="ical_sync")
            
            # Update CalendarConfig
            cfg_res = await db.execute(select(CalendarConfig))
            cfg = cfg_res.scalar_one_or_none()
            if not cfg:
                cfg = CalendarConfig(ics_url=ics_url, auto_sync=True, voice_enabled=True, last_synced_at=datetime.now(timezone.utc))
                db.add(cfg)
            else:
                cfg.ics_url = ics_url
                cfg.last_synced_at = datetime.now(timezone.utc)
            await db.commit()
            
            return {
                "status": "success",
                "events_synced": count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {"status": "error", "message": f"Calendar sync error: {str(e)}"}
