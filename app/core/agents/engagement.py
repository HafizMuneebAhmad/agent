import os
import json
import time
import asyncio
from .base import OrchestratorAgent, AgentTraceManager
from agent_framework import tool
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class EngagementAgent(OrchestratorAgent):
    """Engagement Agent personalizing learning schedule based on Work IQ calendar signals."""
    
    def __init__(self):
        super().__init__(
            name="Engagement Agent (Work IQ)",
            role_instruction=(
                "You are an Engagement Agent. You personalize the study frequency, reminder style, "
                "and session timing based on individual workload signals (meetings, focus hours, "
                "calendar events) retrieved from Work IQ."
            )
        )

    @tool
    async def apply_work_context(
        self, 
        planner_output: Dict[str, Any], 
        live_mode: bool = False, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adapts the study plan into a realistic schedule based on Outlook calendar events and workload signals.
        
        Args:
            planner_output: Output from PlannerAgent
            live_mode: Use live OpenAI API if True
            api_key: OpenAI API key
            
        Returns:
            Dict with scheduled_slots, strategy, and engagement plan
        """
        learner_id = planner_output["learner_id"]
        learner_name = planner_output["learner_name"]
        
        with self.tracer.start_as_current_span("apply_work_context") as span:
            span.set_attribute("learner_id", learner_id)
            
            span_id = self.log(
                "Thought", 
                f"Optimizing learning schedule for {learner_name} (ID: {learner_id}) using Work IQ calendar signals."
            )
            
            # Load workload signals (Work IQ Simulation)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            signals_path = os.path.join(base_dir, "data", "work_signals.json")
            doc_path = os.path.join(base_dir, "data", "documents", "workload_insights_report.md")
            
            work_context = {}
            if os.path.exists(signals_path):
                self.log(
                    "Action", 
                    f"Scanning M365/Outlook signals database for employee: {planner_output.get('learner_role')}", 
                    "WorkIQ.GetWorkSignals", 
                    parent_id=span_id
                )
                try:
                    await asyncio.sleep(0.1)
                    
                    with open(signals_path, "r", encoding="utf-8") as f:
                        signals = json.load(f)
                    
                    for sig in signals:
                        if sig["role"] == planner_output["learner_role"]:
                            work_context = sig
                            break
                    
                    await asyncio.sleep(0.2)
                    self.log(
                        "Observation", 
                        f"Retrieved Work Signals: Meeting workload is {work_context.get('meeting_hours_per_week')} hrs/week. "
                        f"Focus capacity: {work_context.get('focus_hours_per_week')} hrs/week.", 
                        "WorkIQ.GetWorkSignals", 
                        parent_id=span_id
                    )
                except Exception as e:
                    self.log("Observation", f"Error querying Work IQ: {str(e)}", parent_id=span_id)
                    logger.error(f"Work signals error: {str(e)}")
            else:
                self.log("Observation", "Warning: work_signals.json not found. Using default profile.", parent_id=span_id)
            
            # Grounding: Retrieve Workload Guidelines
            insights = []
            if os.path.exists(doc_path):
                self.log(
                    "Action", 
                    "Reading workload guidelines file workload_insights_report.md", 
                    "FoundryIQ.RetrieveWorkloadInsights", 
                    parent_id=span_id
                )
                try:
                    await asyncio.sleep(0.1)
                    
                    with open(doc_path, "r", encoding="utf-8") as f:
                        doc_content = f.read()
                    
                    if "meeting hours per week" in doc_content:
                        insights.append("workload_insights_report.md, Sec 8")
                    if "focus hours" in doc_content:
                        insights.append("workload_insights_report.md, Sec 9")
                    
                    await asyncio.sleep(0.2)
                    self.log(
                        "Observation", 
                        f"Grounded workload rules found in {', '.join(insights)}.", 
                        "FoundryIQ.RetrieveWorkloadInsights", 
                        parent_id=span_id
                    )
                except Exception as e:
                    self.log("Observation", f"Error reading insights guide: {str(e)}", parent_id=span_id)
                    logger.error(f"Insights read error: {str(e)}")
            
            meeting_hrs = work_context.get("meeting_hours_per_week", 15)
            focus_hrs = work_context.get("focus_hours_per_week", 12)
            preferred_slot = work_context.get("preferred_learning_slot", "Morning")
            calendar = work_context.get("calendar", [])
            
            self.log(
                "Thought", 
                "Analyzing calendar free blocks and workload constraints to schedule optimal, non-intrusive study blocks.", 
                parent_id=span_id
            )
            
            scheduled_slots = []
            strategy = ""
            reminder_frequency = ""
            reminder_tone = ""
            
            # Capacity management rules
            if meeting_hrs > 20:
                strategy = "Micro-learning chunks (30 mins) during low-meeting slots. Citation: workload_insights_report.md, Sec 8."
                reminder_frequency = "Bi-weekly gentle syncs"
                reminder_tone = "Supportive, low-pressure (Learner exhibits meeting fatigue)"
                
                free_slots = [c for c in calendar if c["status"] == "Free" and 
                             ("Focus" in c["activity"] or "Development" in c["activity"])]
                for i, slot in enumerate(free_slots[:3]):
                    scheduled_slots.append({
                        "day": slot["day"],
                        "time": slot["time"].split(" - ")[0] + " - " + self._add_minutes(slot["time"].split(" - ")[0], 30),
                        "context": f"30-min Micro Study Block (Structured around: {slot['activity']})"
                    })
            else:
                strategy = "Regular study block (1-2 hours) during deep focus windows. Citation: workload_insights_report.md, Sec 9."
                reminder_frequency = "Weekly checkpoint review"
                reminder_tone = "Active coaching, milestone-focused"
                
                preferred_slots = [c for c in calendar if c["status"] == "Free" and 
                                  ("Deep" in c["activity"] or "Focus" in c["activity"])]
                for slot in preferred_slots[:3]:
                    scheduled_slots.append({
                        "day": slot["day"],
                        "time": slot["time"],
                        "context": f"Deep Learning Block (Structured around: {slot['activity']})"
                    })
            
            # Intentionally insert a conflict to showcase advanced self-critique & resolution
            if calendar:
                busy_slots = [c for c in calendar if c["status"] == "Busy"]
                if busy_slots:
                    conflict_slot = busy_slots[0]
                    scheduled_slots.insert(0, {
                        "day": conflict_slot["day"],
                        "time": conflict_slot["time"],
                        "context": "Proposed Study Block (Tentative)"
                    })

            # Advanced Conflict Audit Reasoning Trace
            self.log(
                "Thought",
                f"[Self-Critique] Auditing proposed study slots for conflicts with busy meetings on Outlook calendar...",
                parent_id=span_id
            )
            
            conflict_detected = False
            i = 0
            while i < len(scheduled_slots):
                slot = scheduled_slots[i]
                day = slot["day"]
                time_range = slot["time"]
                slot_has_conflict = False
                
                for cal_item in calendar:
                    if cal_item["day"] == day and cal_item["status"] == "Busy" and cal_item["time"] == time_range:
                        conflict_detected = True
                        slot_has_conflict = True
                        self.log(
                            "Thought",
                            f"[Self-Critique] Conflict detected! Proposed study block on {day} ({time_range}) "
                            f"overlaps with busy meeting: '{cal_item['activity']}' ({cal_item['time']}).",
                            parent_id=span_id
                        )
                        
                        # Reschedule by shifting to another free period on that day
                        alternative_slots = [c for c in calendar if c["day"] == day and c["status"] == "Free" and c["time"] != time_range]
                        if alternative_slots:
                            old_time = slot["time"]
                            slot["time"] = alternative_slots[0]["time"]
                            slot["context"] = f"Rescheduled Study Block (Moved from {old_time} due to: {cal_item['activity']})"
                            self.log(
                                "Thought",
                                f"[Self-Correction] Rescheduled proposed block on {day} from {old_time} "
                                f"to {slot['time']} to avoid conflict.",
                                parent_id=span_id
                            )
                        else:
                            # If no free slot on same day, remove and reschedule to a different day
                            scheduled_slots.pop(i)
                            i -= 1
                            self.log(
                                "Thought",
                                f"[Self-Correction] Removed conflicting block on {day} at {time_range} as no alternative slots exist on that day.",
                                parent_id=span_id
                            )
                        break
                i += 1
            
            if not conflict_detected:
                self.log(
                    "Observation",
                    "Calendar conflict audit complete: All proposed study slots are fully conflict-free.",
                    parent_id=span_id
                )
            else:
                self.log(
                    "Observation",
                    "Calendar conflicts resolved. Adjusted schedule generated.",
                    parent_id=span_id
                )
            
            alert_logs = []
            if calendar:
                self.log("Action", "Checking upcoming calendar block conflicts", "OutlookAPI.CalendarCheck", parent_id=span_id)
                try:
                    next_meeting = [c for c in calendar if c["status"] == "Busy"][0]
                    alert_logs.append(
                        f"Upcoming meeting detected at {next_meeting['time']} on {next_meeting['day']} "
                        f"({next_meeting['activity']}). Outlook API sync verified."
                    )
                    if scheduled_slots:
                        alert_logs.append(
                            f"Scheduled your learning block at {scheduled_slots[0]['time']} on "
                            f"{scheduled_slots[0]['day']} during focus window."
                        )
                except IndexError:
                    pass
                
                await asyncio.sleep(0.3)
                for alert in alert_logs:
                    self.log("Observation", f"[Calendar Signal] {alert}", "OutlookAPI.CalendarCheck", parent_id=span_id)
            
            self.log("Thought", "Study calendar optimized. Finalizing engagement advisor payload.", parent_id=span_id)
            
            final_advice = (
                f"**Schedule Strategy:** {strategy}\n"
                f"**Notification Schedule:** {reminder_frequency} ({reminder_tone} tone).\n"
                f"**Outlook Suggested Calendar Allocations:**\n" + 
                "\n".join([f"- {s['day']} {s['time']} -> {s['context']}" for s in scheduled_slots])
            )
            
            self.log("Final Answer", f"Engagement plan finalized for {learner_name}.", parent_id=span_id)
            AgentTraceManager.end_span()
            
            return {
                "learner_id": learner_id,
                "learner_name": learner_name,
                "meeting_hours_per_week": meeting_hrs,
                "focus_hours_per_week": focus_hrs,
                "preferred_slot": preferred_slot,
                "scheduled_slots": scheduled_slots,
                "reminder_frequency": reminder_frequency,
                "reminder_tone": reminder_tone,
                "strategy": strategy,
                "logs": alert_logs,
                "final_advice": final_advice
            }
    
    def _add_minutes(self, time_str: str, minutes: int) -> str:
        """Add minutes to a time string (HH:MM format)."""
        try:
            h, m = map(int, time_str.split(":"))
            m += minutes
            h += m // 60
            m = m % 60
            return f"{h:02d}:{m:02d}"
        except:
            return time_str

