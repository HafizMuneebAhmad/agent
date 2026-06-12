import os
import json
import time
import asyncio
from .base import OrchestratorAgent, AgentTraceManager
from agent_framework import tool
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ManagerInsightsAgent(OrchestratorAgent):
    """Manager Insights Agent aggregating team learning metrics and capacity."""
    
    def __init__(self):
        super().__init__(
            name="Manager Insights Agent",
            role_instruction=(
                "You are a Manager Insights Agent. You aggregate organizational signals, capacity logs, "
                "and certification outcomes to highlight skill gaps and workforce constraints without "
                "compromising privacy."
            )
        )

    @tool
    async def generate_team_insights(self) -> Dict[str, Any]:
        """Aggregates data to produce high-level insights for managers.
        
        Returns:
            Dict with pass_rate, alerts, and team_summaries
        """
        with self.tracer.start_as_current_span("generate_team_insights") as span:
            span_id = self.log(
                "Thought", 
                "Aggregating workforce metrics. Loading Fabric IQ learner data and Work IQ workload logs."
            )
            
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            learners_path = os.path.join(base_dir, "data", "learners.json")
            signals_path = os.path.join(base_dir, "data", "work_signals.json")
            
            learners = []
            signals = []
            
            if os.path.exists(learners_path):
                self.log(
                    "Action", 
                    "Loading learner logs from Fabric IQ database", 
                    "FabricIQ.GetAllLearnerLogs", 
                    parent_id=span_id
                )
                try:
                    await asyncio.sleep(0.1)
                    
                    with open(learners_path, "r", encoding="utf-8") as f:
                        learners = json.load(f)
                    
                    await asyncio.sleep(0.1)
                    self.log(
                        "Observation", 
                        f"Loaded {len(learners)} learner profiles.", 
                        "FabricIQ.GetAllLearnerLogs", 
                        parent_id=span_id
                    )
                except Exception as e:
                    logger.error(f"Learners load error: {str(e)}")
            
            if os.path.exists(signals_path):
                self.log(
                    "Action", 
                    "Loading workload metrics from Work IQ database", 
                    "WorkIQ.GetAllWorksignals", 
                    parent_id=span_id
                )
                try:
                    await asyncio.sleep(0.1)
                    
                    with open(signals_path, "r", encoding="utf-8") as f:
                        signals = json.load(f)
                    
                    await asyncio.sleep(0.1)
                    self.log(
                        "Observation", 
                        f"Loaded {len(signals)} workload schedules.", 
                        "WorkIQ.GetAllWorksignals", 
                        parent_id=span_id
                    )
                except Exception as e:
                    logger.error(f"Signals load error: {str(e)}")
            
            self.log(
                "Thought", 
                "Analyzing data to identify capacity bottlenecks, pass likelihoods, and risk zones.", 
                parent_id=span_id
            )
            
            # Compute aggregates
            total_learners = len(learners)
            passed_count = sum(1 for l in learners if l["learning_log"]["status"] == "Passed")
            in_progress_count = sum(1 for l in learners if l["learning_log"]["status"] == "In Progress")
            
            avg_study_hours = sum(l["learning_log"]["hours_studied"] for l in learners) / total_learners if total_learners > 0 else 0
            pass_rate = (passed_count / total_learners) * 100 if total_learners > 0 else 0
            
            alerts = []
            team_summaries = []
            
            # Grounding references
            insights_ref = "workload_insights_report.md, Sec 8"
            learning_ref = "team_learning_report.md, Sec 6"
            
            self.log(
                "Action", 
                "Evaluating predictive capacity and burnout risk model", 
                "Analytics.PredictiveModel", 
                parent_id=span_id
            )
            await asyncio.sleep(0.3)
            
            for l in learners:
                employee_id = l["employee_id"]
                sig = next((s for s in signals if s["employee_id"] == employee_id), {})
                meeting_hrs = sig.get("meeting_hours_per_week", 0)
                study_hrs = l["learning_log"]["hours_studied"]
                score = l["learning_log"]["practice_score_avg"]
                status = l["learning_log"]["status"]
                
                risk_level = "Low"
                risk_desc = "On track"
                
                # Rule check grounded in guide documents
                if meeting_hrs > 20 and status == "In Progress":
                    risk_level = "High"
                    risk_desc = (
                        f"Capacity Constrained. High meeting load ({meeting_hrs} hrs/week). "
                        f"Study completion rate is impacted. (Citation: {insights_ref})"
                    )
                elif score < 70 and study_hrs < 15 and status == "In Progress":
                    risk_level = "Medium"
                    risk_desc = (
                        f"Study Gap. Low study hours ({study_hrs} hrs) and practice score ({score}%). "
                        f"(Citation: {learning_ref})"
                    )
                
                if risk_level in ["Medium", "High"]:
                    alerts.append({
                        "role": l["role"],
                        "certification": l["target_certification"],
                        "risk_level": risk_level,
                        "reason": risk_desc
                    })
                
                team_summaries.append({
                    "role": l["role"],
                    "name": l["name"],
                    "certification": l["target_certification"],
                    "status": status,
                    "score": score,
                    "study_hours": study_hrs,
                    "meeting_hours": meeting_hrs,
                    "risk": risk_level
                })
            
            self.log(
                "Observation", 
                f"Analytics complete. Detected {len(alerts)} risk warnings.", 
                "Analytics.PredictiveModel", 
                parent_id=span_id
            )
            
            # Formulate insights summary
            summary_text = (
                f"### Executive Summary\n"
                f"- **Workforce Pass Rate:** {pass_rate:.1f}% ({passed_count}/{total_learners} completed).\n"
                f"- **Avg Study Time:** {avg_study_hours:.1f} hours.\n"
                f"### High Risk Alerts\n"
            )
            for a in alerts:
                summary_text += (
                    f"- **[{a['risk_level']} Risk]** {a['role']} preparation for {a['certification']}: "
                    f"{a['reason']}\n"
                )
            
            self.log("Final Answer", f"Insights report compiled with {len(alerts)} alerts.", parent_id=span_id)
            AgentTraceManager.end_span()
            
            return {
                "total_learners": total_learners,
                "passed_count": passed_count,
                "in_progress_count": in_progress_count,
                "avg_study_hours": round(avg_study_hours, 1),
                "pass_rate": round(pass_rate, 1),
                "alerts": alerts,
                "team_summaries": team_summaries,
                "summary_text": summary_text
            }

