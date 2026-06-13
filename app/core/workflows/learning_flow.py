import logging
from typing import Dict, Any, Optional
from agent_framework import workflow, step

# Import specialized agents
from app.core.agents.curator import CuratorAgent
from app.core.agents.planner import PlannerAgent
from app.core.agents.engagement import EngagementAgent
from app.core.agents.assessment import AssessmentAgent
from app.core.agents.manager import ManagerInsightsAgent

logger = logging.getLogger(__name__)

@step(name="curation_step")
async def curate_step(certification_id: str, live_mode: bool, api_key: Optional[str]) -> Dict[str, Any]:
    """Step 1: Curate approved certification guide and document references."""
    curator = CuratorAgent()
    return await curator.retrieve_content(
        certification_id=certification_id,
        live_mode=live_mode,
        api_key=api_key
    )

@step(name="planning_step")
async def plan_step(learner_id: str, curated_data: Dict[str, Any], live_mode: bool, api_key: Optional[str]) -> Dict[str, Any]:
    """Step 2: Compare skills gap and formulate milestones with Self-Critique."""
    planner = PlannerAgent()
    # Call generate_schedule (fixing the missing method bug)
    return await planner.generate_schedule(
        learner_id=learner_id,
        curated_data=curated_data,
        live_mode=live_mode,
        api_key=api_key
    )

@step(name="scheduling_and_synthesizing_step")
async def schedule_and_synthesize_step(
    planner_output: Dict[str, Any], 
    live_mode: bool, 
    api_key: Optional[str]
) -> Dict[str, Any]:
    """Step 3: Schedule slots, resolve conflicts, and run assessment/manager modules."""
    # 1. Adapt calendar using Engagement Agent
    engagement = EngagementAgent()
    engagement_output = await engagement.apply_work_context(
        planner_output=planner_output,
        live_mode=live_mode,
        api_key=api_key
    )
    
    # 2. Pre-generate Practice Assessment for the learner
    assessment = AssessmentAgent()
    await assessment.generate_assessment(
        certification_id=planner_output["certification_id"]
    )
    
    # 3. Compile Manager Analytics Update
    manager = ManagerInsightsAgent()
    await manager.generate_team_insights()
    
    return engagement_output

@workflow(name="LearningOrchestrationWorkflow")
async def run_learning_orchestration(
    learner_id: str,
    certification_id: str,
    live_mode: bool = False,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Microsoft Agent Framework multi-agent optimization workflow."""
    # This functional workflow runs the steps sequentially.
    # We coordinate the execution flow using native python control structures.
    logger.info(f"Starting LearningOrchestrationWorkflow for learner={learner_id}, cert={certification_id}")
    
    curator_output = await curate_step(certification_id, live_mode, api_key)
    planner_output = await plan_step(learner_id, curator_output, live_mode, api_key)
    engagement_output = await schedule_and_synthesize_step(planner_output, live_mode, api_key)
    
    return {
        "curator_output": curator_output,
        "planner_output": planner_output,
        "engagement_output": engagement_output
    }
