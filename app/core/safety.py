"""
StudyOS 3-Tier AI Action Safety Framework.

SAFE: Automatically execute after validation.
MODERATE: Show confirmation preview before changing.
HIGH-RISK: Always require explicit user confirmation. The AI must NEVER silently make high-impact changes.
"""

from enum import Enum
from typing import List, Dict, Any, Tuple

class RiskLevel(str, Enum):
    SAFE = "SAFE"
    MODERATE = "MODERATE"
    HIGH_RISK = "HIGH_RISK"

# Action classification lookup
ACTION_RISK_MAP = {
    # Safe Actions
    "LOG_DSA_PROBLEM": RiskLevel.SAFE,
    "ADD_MISTAKE": RiskLevel.SAFE,
    "UPDATE_DAILY_PROGRESS": RiskLevel.SAFE,
    "COMPLETE_TASK": RiskLevel.SAFE,
    "ADD_TASK": RiskLevel.SAFE,
    "ADD_COLLEGE_EVENT": RiskLevel.SAFE,
    "UPDATE_CONCEPT_STATUS": RiskLevel.SAFE,
    "START_DAY": RiskLevel.SAFE,
    "END_DAY": RiskLevel.SAFE,
    "SEARCH_QUERY": RiskLevel.SAFE,
    "LOG_NOTE": RiskLevel.SAFE,
    "SHOW_REVISIONS": RiskLevel.SAFE,
    "SHOW_WEAKNESSES": RiskLevel.SAFE,
    "SHOW_RECOVERY_PLAN": RiskLevel.SAFE,
    "SET_MUST_WIN": RiskLevel.SAFE,
    "COMPLETE_REVISION": RiskLevel.SAFE,
    "START_WEEKLY_REVIEW": RiskLevel.SAFE,
    "UNKNOWN_COMMAND": RiskLevel.SAFE,

    # Moderate Actions (Requires Preview / Confirmation)
    "RESCHEDULE_TASK": RiskLevel.MODERATE,
    "POSTPONE_DEADLINE": RiskLevel.MODERATE,
    "MODIFY_DAILY_PLAN": RiskLevel.MODERATE,
    "ACTIVATE_DEADLINE_MODE": RiskLevel.MODERATE,
    "ACTIVATE_EXAM_MODE": RiskLevel.MODERATE,
    "DEACTIVATE_EXAM_MODE": RiskLevel.MODERATE,
    "CARRY_FORWARD_TASKS": RiskLevel.MODERATE,
    "SWITCH_TO_TEST_MODE": RiskLevel.MODERATE,
    "SWITCH_TO_DEMO_MODE": RiskLevel.MODERATE,

    # High-Risk Actions (Explicit Confirmation Mandatory)
    "MODIFY_ROADMAP": RiskLevel.HIGH_RISK,
    "CHANGE_DSA_TARGET": RiskLevel.HIGH_RISK,
    "DELETE_HISTORICAL_DATA": RiskLevel.HIGH_RISK,
    "DELETE_REPORT": RiskLevel.HIGH_RISK,
    "CHANGE_SPRINT_DATES": RiskLevel.HIGH_RISK,
    "ALTER_SENTINELAI_MILESTONE": RiskLevel.HIGH_RISK,
    "DELETE_TASK": RiskLevel.HIGH_RISK,
    "RESET_DATABASE": RiskLevel.HIGH_RISK,
    "SWITCH_TO_REAL_MODE": RiskLevel.HIGH_RISK,
    "START_SPRINT": RiskLevel.HIGH_RISK,
    "RESET_TEST_DATA": RiskLevel.HIGH_RISK,
    "RESET_DEMO_DATA": RiskLevel.HIGH_RISK,
}

class SafetyGuardrail:
    @staticmethod
    def classify_action(action_type: str) -> RiskLevel:
        return ACTION_RISK_MAP.get(action_type.upper(), RiskLevel.MODERATE)

    @staticmethod
    def validate_action(action_type: str, payload: Dict[str, Any], confirmed: bool = False) -> Tuple[bool, RiskLevel, str]:
        risk_level = SafetyGuardrail.classify_action(action_type)
        
        if risk_level == RiskLevel.SAFE:
            return True, risk_level, "Safe action approved for automatic execution."
        
        if risk_level == RiskLevel.MODERATE:
            if confirmed:
                return True, risk_level, "Moderate action confirmed by user."
            return False, risk_level, f"Moderate action [{action_type}] requires user confirmation preview."
        
        if risk_level == RiskLevel.HIGH_RISK:
            if confirmed:
                return True, risk_level, "High-risk action explicitly confirmed by user."
            return False, risk_level, f"HIGH-RISK action [{action_type}] requires explicit user confirmation. Silent execution prohibited."
        
        return False, RiskLevel.HIGH_RISK, "Unknown action blocked."
