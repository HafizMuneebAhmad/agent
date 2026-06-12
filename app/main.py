import os
import json
import time
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Import our refactored agents & session manager
from app.core.agents.base import AgentTraceManager, WorkflowSessionManager
from app.core.agents.curator import CuratorAgent
from app.core.agents.planner import PlannerAgent
from app.core.agents.engagement import EngagementAgent
from app.core.agents.assessment import AssessmentAgent
from app.core.agents.manager import ManagerInsightsAgent

# Load local environment if any
load_dotenv()

app = FastAPI(title="Nexus Learning Orchestrator API")

# Mount static files folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    os.makedirs(os.path.join(static_dir, "css"))
    os.makedirs(os.path.join(static_dir, "js"))

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Request Models
class WorkflowRequest(BaseModel):
    learner_id: str
    certification_id: str
    live_mode: bool = False
    api_key: Optional[str] = None

class ResumeRequest(BaseModel):
    session_id: str
    approved: bool
    user_feedback: Optional[str] = None
    live_mode: bool = False
    api_key: Optional[str] = None

class SubmissionRequest(BaseModel):
    learner_id: str
    certification_id: str
    answers: Dict[str, int]
    questions: List[Dict[str, Any]]

# Endpoints
@app.get("/")
def read_root():
    html_path = os.path.join(static_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Nexus Learning Orchestrator</h1><p>Static files are not yet initialized. Please wait.</p>")

@app.get("/api/learners")
def get_learners():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    learners_path = os.path.join(base_dir, "data", "learners.json")
    if os.path.exists(learners_path):
        with open(learners_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Learners data not found")

@app.get("/api/certifications")
def get_certifications():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    certs_path = os.path.join(base_dir, "data", "certifications.json")
    if os.path.exists(certs_path):
        with open(certs_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Certifications data not found")

# Get OpenTelemetry traces
@app.get("/api/workflow/traces")
def get_traces():
    return {
        "success": True,
        "traces": AgentTraceManager.get_traces()
    }

# Step 1: Start Workflow with MAF Async Agents (Phase 1)
@app.post("/api/workflow")
async def run_orchestrator_workflow(req: WorkflowRequest):
    """
    Execute learning optimization workflow using Microsoft Agent Framework async agents.
    
    This endpoint:
    1. Creates a new workflow session
    2. Executes all agent tools sequentially
    3. Returns results with trace visualization
    
    Request body:
    - learner_id: str
    - certification_id: str
    - live_mode: bool (optional)
    - api_key: str (optional)
    """
    # Clear telemetry logs at the beginning of a fresh workflow run
    AgentTraceManager.clear_traces()
    
    try:
        # Create session context
        session_id = WorkflowSessionManager.create_session(
            learner_id=req.learner_id,
            certification_id=req.certification_id
        )
        
        # Execute all agents in sequence (Curator → Planner → Engagement → Assessment → Manager)
        # Using MAF async patterns and @tool decorators
        
        curator = CuratorAgent()
        curator_output = await curator.retrieve_content(
            certification_id=req.certification_id,
            live_mode=req.live_mode,
            api_key=req.api_key
        )
        WorkflowSessionManager.update_session(session_id, {
            "status": "curator_complete",
            "curator_output": curator_output
        })
        
        # HITL Checkpoint 1
        return {
            "success": True,
            "session_id": session_id,
            "status": "awaiting_approval",
            "current_step": "curator_complete",
            "curator_output": curator_output,
            "traces": AgentTraceManager.get_traces()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

# Step 2: Resume Workflow after user approval (HITL Decision)
@app.post("/api/workflow/resume")
async def resume_workflow(req: ResumeRequest):
    """
    Resume workflow after human-in-the-loop approval or rejection.
    
    Request body:
    - session_id: str
    - approved: bool
    - user_feedback: str (optional)
    - live_mode: bool (optional)
    - api_key: str (optional)
    """
    try:
        session = WorkflowSessionManager.get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not req.approved:
            WorkflowSessionManager.update_session(req.session_id, {"status": "rejected"})
            AgentTraceManager.add_trace({
                "id": f"rejection-{req.session_id}",
                "parent_id": "root",
                "agent_name": "User (HITL)",
                "step_type": "Decision",
                "content": f"User rejected with feedback: {req.user_feedback or 'None'}",
                "timestamp": time.strftime("%H:%M:%S")
            })
            return {
                "success": True,
                "session_id": req.session_id,
                "status": "rejected",
                "traces": AgentTraceManager.get_traces()
            }
        
        # If approved, continue with next agents
        current_step = session.get("status")
        
        if current_step == "curator_complete":
            planner = PlannerAgent()
            plan_output = await planner.plan_learning(
                learner_id=session["learner_id"],
                curator_data=session["curator_output"],
                live_mode=req.live_mode,
                api_key=req.api_key
            )
            WorkflowSessionManager.update_session(req.session_id, {
                "status": "planner_complete",
                "planner_output": plan_output
            })
            return {
                "success": True,
                "session_id": req.session_id,
                "status": "awaiting_approval",
                "current_step": "planner_complete",
                "planner_output": plan_output,
                "traces": AgentTraceManager.get_traces()
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Cannot resume from: {current_step}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {str(e)}")

@app.get("/api/assessment/generate/{certification_id}")
async def generate_practice_test(certification_id: str):
    """Generate practice test for a certification."""
    assessment_agent = AssessmentAgent()
    try:
        assessment_data = await assessment_agent.generate_assessment(
            certification_id=certification_id
        )
        return {
            "success": True,
            "logs": [],
            "assessment": assessment_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/assessment/submit")
async def submit_practice_test(req: SubmissionRequest):
    """Submit and evaluate practice test answers."""
    assessment_agent = AssessmentAgent()
    try:
        evaluation = await assessment_agent.evaluate_readiness(
            submission={
                "learner_id": req.learner_id,
                "certification_id": req.certification_id,
                "answers": req.answers,
                "questions": req.questions
            }
        )
        return {
            "success": True,
            "logs": [],
            "evaluation": evaluation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/manager/insights")
def get_manager_insights():
    manager_agent = ManagerInsightsAgent()
    try:
        insights = manager_agent.generate_team_insights()
        return {
            "success": True,
            "logs": [],
            "insights": insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
