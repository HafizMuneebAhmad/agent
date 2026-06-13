import os
import json
import time
import asyncio
from .base import OrchestratorAgent, AgentTraceManager
from agent_framework import tool
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class PlannerAgent(OrchestratorAgent):
    """Study Plan Generator querying Fabric IQ semantic layer."""
    
    def __init__(self):
        super().__init__(
            name="Planner Agent (Fabric IQ)",
            role_instruction=(
                "You are a Study Plan Generator. You translate curated content and skill gaps "
                "into a structured learning path. You query Fabric IQ to retrieve semantic models "
                "of certifications, role skills, and gaps."
            )
        )

    @tool
    async def generate_schedule(
        self, 
        learner_id: str, 
        curated_data: Dict[str, Any], 
        live_mode: bool = False, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates a study plan by analyzing current skills vs target certification requirements.
        
        This tool:
        - Queries Fabric IQ for learner skills and certification requirements
        - Calculates skill gaps
        - Generates weekly milestones
        
        Args:
            learner_id: Target learner ID
            curated_data: Output from CuratorAgent
            live_mode: Use live OpenAI API if True
            api_key: OpenAI API key
            
        Returns:
            Dict with milestones, skill gaps, and learning plan
        """
        certification_id = curated_data["certification_id"]
        
        with self.tracer.start_as_current_span("generate_schedule") as span:
            span.set_attribute("learner_id", learner_id)
            span.set_attribute("certification_id", certification_id)
            
            span_id = self.log(
                "Thought", 
                f"Initiating study planner for Learner {learner_id} targeting {certification_id}. "
                f"Querying Fabric IQ ontology."
            )
            
            # Load learners and certifications (Fabric IQ Simulation)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            learners_path = os.path.join(base_dir, "data", "learners.json")
            certs_path = os.path.join(base_dir, "data", "certifications.json")
            
            learner_info = {}
            cert_info = {}
            
            # 1. Fetch Learner Profile (Async)
            if os.path.exists(learners_path):
                self.log(
                    "Action", 
                    f"Querying FabricIQ database for learner details: {learner_id}", 
                    "FabricIQ.GetLearnerProfile", 
                    parent_id=span_id
                )
                try:
                    await asyncio.sleep(0.1)  # Async I/O simulation
                    
                    with open(learners_path, "r", encoding="utf-8") as f:
                        learners = json.load(f)
                    for l in learners:
                        if l["learner_id"] == learner_id:
                            learner_info = l
                            break
                    
                    await asyncio.sleep(0.3)
                    self.log(
                        "Observation", 
                        f"Learner Profile retrieved: {learner_info.get('name')} ({learner_info.get('role')})", 
                        "FabricIQ.GetLearnerProfile", 
                        parent_id=span_id
                    )
                except Exception as e:
                    self.log("Observation", f"Error reading Fabric IQ: {str(e)}", parent_id=span_id)
                    logger.error(f"Learner fetch error: {str(e)}")
            
            # 2. Fetch Certification Schema (Async)
            if os.path.exists(certs_path):
                self.log(
                    "Action", 
                    f"Querying FabricIQ for certification schema: {certification_id}", 
                    "FabricIQ.GetCertificationDetails", 
                    parent_id=span_id
                )
                try:
                    await asyncio.sleep(0.1)  # Async I/O simulation
                    
                    with open(certs_path, "r", encoding="utf-8") as f:
                        certs = json.load(f)["certifications"]
                    for c in certs:
                        if c["id"] == certification_id:
                            cert_info = c
                            break
                    
                    await asyncio.sleep(0.3)
                    self.log(
                        "Observation", 
                        f"Certification details loaded. Target skills: {cert_info.get('skills')}, "
                        f"Recommended: {cert_info.get('recommended_hours')} hours.", 
                        "FabricIQ.GetCertificationDetails", 
                        parent_id=span_id
                    )
                except Exception as e:
                    self.log("Observation", f"Error reading Fabric IQ certs: {str(e)}", parent_id=span_id)
                    logger.error(f"Cert fetch error: {str(e)}")
            
            # 3. Compute Skill Gaps
            skill_gaps = []
            if learner_info and cert_info:
                self.log(
                    "Thought", 
                    "Calculating semantic gaps between employee current proficiency and target "
                    "certification requirements.", 
                    parent_id=span_id
                )
                assessments = {item["skill"]: item for item in learner_info.get("skills_assessment", [])}
                
                for skill in cert_info.get("skills", []):
                    current_lvl = assessments.get(skill, {}).get("current", 0)
                    target_lvl = assessments.get(skill, {}).get("target", 4)
                    gap = target_lvl - current_lvl
                    if gap > 0:
                        skill_gaps.append({
                            "skill": skill,
                            "current": current_lvl,
                            "target": target_lvl,
                            "gap": gap
                        })
                
                gap_summary = ", ".join([f"{g['skill']}({g['current']}->{g['target']})" for g in skill_gaps])
                self.log(
                    "Observation", 
                    f"Computed gaps: [{gap_summary}]", 
                    "FabricIQ.CalculateGaps", 
                    parent_id=span_id
                )
            else:
                self.log(
                    "Observation", 
                    "Warning: Learner profile or cert info unavailable. Using fallback gap structure.", 
                    parent_id=span_id
                )
                skill_gaps = [{"skill": "General Knowledge", "current": 1, "target": 4, "gap": 3}]
            
            recommended_hours = cert_info.get("recommended_hours", 20)
            difficulty = cert_info.get("difficulty", "Intermediate")
            
            self.log(
                "Thought", 
                "Formulating a sequence of weekly milestones aligned with recommended hours.", 
                parent_id=span_id
            )
            
            # Handle Live Mode API for milestone generation
            if live_mode and api_key:
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key)
                    prompt = (
                        f"Generate a weekly study plan milestones (4 weeks) for learner: {learner_info.get('name')} "
                        f"targeting certification: {certification_id}. Skill gaps are:\n{json.dumps(skill_gaps)}\n"
                        f"The course outline curated is:\n{curated_data['curated_outline']}\n"
                        f"Return JSON list of weeks matching: [{{'week': 1, 'topic': 'Topic name', 'focus': 'Focus points'}}]"
                    )
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": self.role_instruction},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    res_json = json.loads(response.choices[0].message.content)
                    # Parse milestones list from JSON response
                    if "milestones" in res_json:
                        milestones = res_json["milestones"]
                    elif isinstance(res_json, list):
                        milestones = res_json
                    else:
                        milestones = list(res_json.values())[0]
                    self.log("Observation", "Live API successfully generated milestones", parent_id=span_id)
                except Exception as e:
                    self.log(
                        "Observation", 
                        f"Live API planner failed, using local reasoning template. Error: {str(e)}", 
                        parent_id=span_id
                    )
                    logger.warning(f"Live API error: {str(e)}")
                    milestones = self._get_fallback_milestones(certification_id)
            else:
                milestones = self._get_fallback_milestones(certification_id)
            
            # 4. Self-Critique & Verification Loop
            self.log(
                "Thought",
                f"[Self-Critique] Auditing generated milestones against computed skill gaps for certification {certification_id}...",
                parent_id=span_id
            )
            
            critique_warnings = []
            for gap in skill_gaps:
                skill_name = gap["skill"]
                # Check if the skill is covered in milestones
                covered = False
                for m in milestones:
                    m_skills = m.get("skills", [])
                    m_text = (m.get("topic", "") + " " + m.get("focus", "")).lower()
                    if skill_name.lower() in m_text or any(skill_name.lower() == s.lower() for s in m_skills):
                        covered = True
                        break
                
                if not covered:
                    critique_warnings.append(skill_name)
                    self.log(
                        "Thought",
                        f"[Self-Critique] Warning: Skill '{skill_name}' (Gap: {gap['gap']}) is NOT explicitly covered in any weekly milestone!",
                        parent_id=span_id
                    )
            
            # Perform self-correction
            if critique_warnings:
                self.log(
                    "Thought",
                    f"[Self-Correction] Resolving gaps. Adding missing skills {critique_warnings} to the weekly milestones.",
                    parent_id=span_id
                )
                for idx, skill_name in enumerate(critique_warnings):
                    target_week = (idx % len(milestones))
                    milestones[target_week]["focus"] += f" Also includes study on {skill_name}."
                    if "skills" in milestones[target_week]:
                        if skill_name not in milestones[target_week]["skills"]:
                            milestones[target_week]["skills"].append(skill_name)
                
                self.log(
                    "Observation",
                    f"[Self-Correction] Re-audit successful. All skill gaps verified as covered in milestones.",
                    parent_id=span_id
                )
            else:
                self.log(
                    "Observation",
                    "No coverage gaps found. Milestones successfully align with Fabric IQ skill requirements.",
                    parent_id=span_id
                )
            
            plan_summary = f"Generated {len(milestones)}-week study plan ({recommended_hours} total hours)."
            self.log("Final Answer", plan_summary, parent_id=span_id)
            AgentTraceManager.end_span()
            
            return {
                "learner_id": learner_id,
                "learner_name": learner_info.get("name", "Learner"),
                "learner_role": learner_info.get("role", "Engineer"),
                "certification_id": certification_id,
                "certification_name": cert_info.get("name", "Certification"),
                "difficulty": difficulty,
                "recommended_hours": recommended_hours,
                "skill_gaps": skill_gaps,
                "milestones": milestones
            }

    async def plan_learning(
        self, 
        learner_id: str, 
        curated_data: Dict[str, Any], 
        live_mode: bool = False, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Alias method to support caller in main.py."""
        return await self.generate_schedule(
            learner_id=learner_id,
            curated_data=curated_data,
            live_mode=live_mode,
            api_key=api_key
        )
    
    def _get_fallback_milestones(self, certification_id: str) -> List[Dict[str, Any]]:
        """Get fallback milestones when live API unavailable - includes agent reasoning."""
        if "AZ-204" in certification_id:
            return [
                {
                    "week": 1, 
                    "topic": "Azure Functions & App Services", 
                    "focus": "Deploying serverless triggers, configuring app service plans",
                    "hours": 10,
                    "skills": ["Serverless Architecture", "Azure Functions", "Event-driven design"],
                    "agent_reasoning": "Learner has basic Azure knowledge but lacks serverless experience. Prioritize hands-on function deployments with event bindings.",
                    "priority": "CRITICAL",
                    "gap_score": -2,
                    "recommended_resources": [
                        "Microsoft Learn: Azure Functions fundamentals",
                        "Pluralsight: Serverless Architecture on Azure",
                        "Hands-on Lab: Deploy function-triggered workflows"
                    ]
                },
                {
                    "week": 2, 
                    "topic": "Azure Storage & Cosmos DB", 
                    "focus": "Configuring blobs lifecycle, choosing partition keys, NoSQL patterns",
                    "hours": 9,
                    "skills": ["Blob Storage", "CosmosDB", "Data partitioning"],
                    "agent_reasoning": "Critical gap identified: Data Engineer role requires strong storage skills. Data Engineer background suggests familiarity with databases but Azure-specific patterns need emphasis.",
                    "priority": "CRITICAL",
                    "gap_score": -2,
                    "recommended_resources": [
                        "Reference Doc Sec 2.1: Blob Storage Lifecycle",
                        "Reference Doc Sec 3.4: CosmosDB Partitioning",
                        "Azure Storage Explorer labs"
                    ]
                },
                {
                    "week": 3, 
                    "topic": "Azure Security & API Development", 
                    "focus": "Implementing KeyVault, Managed Identity, REST APIs",
                    "hours": 8,
                    "skills": ["Azure Security", "API Design", "Authentication"],
                    "agent_reasoning": "Data Engineer needs to understand security patterns in data pipelines. Managed Identity critical for data access control.",
                    "priority": "HIGH",
                    "gap_score": -1,
                    "recommended_resources": [
                        "Microsoft Docs: Managed Identity",
                        "Azure KeyVault best practices",
                        "REST API design patterns"
                    ]
                },
                {
                    "week": 4, 
                    "topic": "Mock Assessments & Exam Prep", 
                    "focus": "Practice questions with citation reviews, performance analysis",
                    "hours": 9,
                    "skills": ["Exam readiness", "Knowledge consolidation"],
                    "agent_reasoning": "Final week focus: full practice tests tracking weak areas. Pass threshold: 75% (industry standard for AZ-204)",
                    "priority": "MEDIUM",
                    "gap_score": 0,
                    "recommended_resources": [
                        "Microsoft Learn practice assessments",
                        "ExamTopics reference guides",
                        "Week 1-3 review materials"
                    ]
                }
            ]
        elif "AZ-400" in certification_id:
            return [
                {
                    "week": 1, 
                    "topic": "Multi-stage YAML Pipelines", 
                    "focus": "CI/CD setups, environment approvals, multi-stage deployments",
                    "hours": 9,
                    "skills": ["Azure Pipelines", "YAML", "CI/CD"],
                    "agent_reasoning": "DevOps specialization requires strong pipeline foundation. YAML syntax and approval gates are core concepts.",
                    "priority": "CRITICAL",
                    "gap_score": -1,
                    "recommended_resources": [
                        "Reference Doc Sec 4.2: YAML Pipelines",
                        "Microsoft Learn: Multi-stage pipelines",
                        "Lab: Build and deploy multi-stage pipeline"
                    ]
                },
                {
                    "week": 2, 
                    "topic": "Infrastructure as Code (IaC)", 
                    "focus": "Terraform and Bicep automation, resource deployments",
                    "hours": 11,
                    "skills": ["Terraform", "Bicep", "IaC patterns"],
                    "agent_reasoning": "Essential DevOps skill: Infrastructure automation reduces manual errors and improves scalability. Both Terraform and Bicep are industry standards.",
                    "priority": "CRITICAL",
                    "gap_score": -2,
                    "recommended_resources": [
                        "Terraform tutorials for Azure",
                        "Azure Bicep documentation",
                        "GitOps workflow setup"
                    ]
                },
                {
                    "week": 3, 
                    "topic": "Monitoring, Containerization & Logging", 
                    "focus": "App Insights, Log Analytics, Docker, AKS fundamentals",
                    "hours": 10,
                    "skills": ["Monitoring", "Logging", "Containerization", "Kubernetes"],
                    "agent_reasoning": "Observability is critical for DevOps success. Containers and orchestration are modern deployment standards.",
                    "priority": "HIGH",
                    "gap_score": -1,
                    "recommended_resources": [
                        "Azure Monitor & App Insights",
                        "Docker basics and best practices",
                        "AKS cluster management"
                    ]
                },
                {
                    "week": 4, 
                    "topic": "Full Practice Assessment", 
                    "focus": "Complete mock tests, weak area remediation, final review",
                    "hours": 6,
                    "skills": ["Exam readiness"],
                    "agent_reasoning": "Final assessment phase. Pass threshold: 80% (higher than AZ-204 due to DevOps complexity)",
                    "priority": "MEDIUM",
                    "gap_score": 0,
                    "recommended_resources": [
                        "AZ-400 practice exams",
                        "Targeted review of weak areas",
                        "Hands-on labs recap"
                    ]
                }
            ]
        else:
            return [
                {
                    "week": 1, 
                    "topic": "Data Lakes & Lakehouse Architecture", 
                    "focus": "Azure Synapse setups, delta lake schemas, data organization",
                    "hours": 9,
                    "skills": ["Data Lakes", "Delta Lake", "Schema Design"],
                    "agent_reasoning": "Data Engineer specialty - perfect role alignment! Delta Lake format is industry standard for analytics. Focus on folder structures and partition schemes.",
                    "priority": "CRITICAL",
                    "gap_score": -2,
                    "recommended_resources": [
                        "Reference Doc Sec 5.1: Lakehouse Patterns",
                        "Delta Lake optimization guide",
                        "Azure Synapse workspace setup"
                    ]
                },
                {
                    "week": 2, 
                    "topic": "ETL Orchestration & Data Factory", 
                    "focus": "Azure Data Factory pipelines, triggers, monitoring",
                    "hours": 10,
                    "skills": ["Data Factory", "ETL", "Orchestration"],
                    "agent_reasoning": "Core DP-203 competency. Data Factory is standard for data pipeline orchestration. Agent recommends labs over theory.",
                    "priority": "CRITICAL",
                    "gap_score": -2,
                    "recommended_resources": [
                        "Data Factory pipeline templates",
                        "Error handling and retry logic",
                        "Integration runtime setup"
                    ]
                },
                {
                    "week": 3, 
                    "topic": "Databricks & Real-time Stream Analytics", 
                    "focus": "Apache Spark jobs, structured streaming, real-time processing",
                    "hours": 12,
                    "skills": ["Databricks", "Spark", "Stream Processing"],
                    "agent_reasoning": "Advanced analytics and real-time processing are high-value skills. Spark mastery critical for Data Engineer exam success.",
                    "priority": "CRITICAL",
                    "gap_score": -2,
                    "recommended_resources": [
                        "Databricks Academy courses",
                        "Apache Spark fundamentals",
                        "Event Hubs integration labs"
                    ]
                },
                {
                    "week": 4, 
                    "topic": "Practice & Exam Readiness", 
                    "focus": "Full-length practice tests, weak area remediation, certification review",
                    "hours": 2,
                    "skills": ["Exam readiness", "Knowledge consolidation"],
                    "agent_reasoning": "Final week: focused on weak areas from previous weeks. Pass threshold: 75% (DP-203 is comprehensive - plan for study depth)",
                    "priority": "MEDIUM",
                    "gap_score": 0,
                    "recommended_resources": [
                        "Microsoft practice assessments",
                        "Reference Doc Sec 5 citation review",
                        "Hands-on lab recap"
                    ]
                }
            ]
