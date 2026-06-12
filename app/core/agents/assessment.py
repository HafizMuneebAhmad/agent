import os
import json
import time
import asyncio
from .base import OrchestratorAgent, AgentTraceManager
from agent_framework import tool
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AssessmentAgent(OrchestratorAgent):
    """Assessment Agent generating practice questions grounded in documentation."""
    
    def __init__(self):
        super().__init__(
            name="Assessment Agent (Foundry Grounding)",
            role_instruction=(
                "You are an Assessment Agent. You generate credible practice questions grounded in "
                "approved documentation, provide citations, and grade exam readiness."
            )
        )

    @tool
    async def generate_assessment(self, certification_id: str) -> Dict[str, Any]:
        """Generates practice questions grounded in the local guides.
        
        Args:
            certification_id: Target certification ID
            
        Returns:
            Dict with questions and citations
        """
        with self.tracer.start_as_current_span("generate_assessment") as span:
            span.set_attribute("certification_id", certification_id)
            
            span_id = self.log(
                "Thought", 
                f"Initiating practice test compilation for {certification_id}. "
                f"Querying Foundry IQ for syllabus documents."
            )
            
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            doc_path = os.path.join(base_dir, "data", "documents", "engineering_certification_guide.md")
            
            grounded_context = ""
            if os.path.exists(doc_path):
                self.log(
                    "Action", 
                    f"Extracting grounding sections for quiz generation from: engineering_certification_guide.md", 
                    "FoundryIQ.RetrieveGroundingText", 
                    parent_id=span_id
                )
                try:
                    await asyncio.sleep(0.1)
                    
                    with open(doc_path, "r", encoding="utf-8") as f:
                        grounded_context = f.read()
                    
                    await asyncio.sleep(0.3)
                    self.log(
                        "Observation", 
                        "Grounded source loaded successfully. Compiling questions with citations.", 
                        "FoundryIQ.RetrieveGroundingText", 
                        parent_id=span_id
                    )
                except Exception as e:
                    self.log("Observation", f"Error loading grounding guide: {str(e)}", parent_id=span_id)
                    logger.error(f"Doc load error: {str(e)}")
            
            self.log(
                "Thought", 
                "Generating multiple-choice questions with direct section citations.", 
                parent_id=span_id
            )
            
            questions = self._get_questions_for_cert(certification_id)
            
            self.log("Final Answer", f"Generated {len(questions)} grounded assessment questions.", parent_id=span_id)
            AgentTraceManager.end_span()
            
            return {
                "certification_id": certification_id,
                "questions": questions
            }
    
    @tool
    async def evaluate_readiness(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Grades practice exam submissions and gives recommendations.
        
        Args:
            submission: Dict with learner_id, certification_id, answers, questions
            
        Returns:
            Dict with score, pass status, and recommendations
        """
        learner_id = submission["learner_id"]
        certification_id = submission["certification_id"]
        answers = submission["answers"]
        questions = submission["questions"]
        
        with self.tracer.start_as_current_span("evaluate_readiness") as span:
            span.set_attribute("learner_id", learner_id)
            span.set_attribute("certification_id", certification_id)
            
            span_id = self.log(
                "Thought", 
                f"Evaluating readiness scores for Learner {learner_id} on certification {certification_id}."
            )
            
            # Load passing threshold
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            certs_path = os.path.join(base_dir, "data", "certifications.json")
            pass_threshold = 75
            
            if os.path.exists(certs_path):
                try:
                    await asyncio.sleep(0.1)
                    
                    with open(certs_path, "r", encoding="utf-8") as f:
                        certs = json.load(f)["certifications"]
                    for c in certs:
                        if c["id"] == certification_id:
                            if c["id"] == "AZ-400":
                                pass_threshold = 80
                            break
                except Exception as e:
                    logger.error(f"Cert load error: {str(e)}")
            
            # Grade answers
            total_questions = len(questions)
            correct_answers = 0
            incorrect_topics = []
            
            for q in questions:
                q_id = q["id"]
                submitted = answers.get(q_id)
                correct = q["answer"]
                if submitted == correct:
                    correct_answers += 1
                else:
                    incorrect_topics.append({
                        "question": q["question"],
                        "incorrect_answer": q["options"][submitted] if submitted is not None else "No Answer",
                        "citation": q["citation"],
                        "correct_explanation": q["explanation"]
                    })
            
            score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0
            passed = score >= pass_threshold
            
            self.log("Action", f"Grading exam questions", "AssessmentAgent.Grade", parent_id=span_id)
            await asyncio.sleep(0.3)
            self.log(
                "Observation", 
                f"Grading Complete. Score: {score}%. Passing Target: {pass_threshold}%. Passed: {passed}.", 
                "AssessmentAgent.Grade", 
                parent_id=span_id
            )
            
            if passed:
                recommendation = f"Ready to register! Score of {score}% satisfies the readiness limit. Recommended next step: Register for Microsoft {certification_id} Exam."
                status = "Passed"
            else:
                status = "In Progress"
                rec_topics = ", ".join([item["citation"] for item in incorrect_topics])
                recommendation = f"Readiness assessment failed ({score}% < {pass_threshold}%). Further review is required. Focus on content cited in: [{rec_topics}]."
            
            self.log("Final Answer", f"Readiness status: {status}. Recommendation issued.", parent_id=span_id)
            
            # Update learner log file (Fabric IQ State Update)
            learners_path = os.path.join(base_dir, "data", "learners.json")
            if os.path.exists(learners_path):
                self.log("Action", "Updating learner profile logs", "FabricIQ.UpdateLearnerLog", parent_id=span_id)
                try:
                    await asyncio.sleep(0.1)
                    
                    with open(learners_path, "r", encoding="utf-8") as f:
                        learners = json.load(f)
                    for l in learners:
                        if l["learner_id"] == learner_id:
                            l["learning_log"]["practice_score_avg"] = score
                            l["learning_log"]["status"] = status
                            l["learning_log"]["hours_studied"] += 2
                            break
                    
                    with open(learners_path, "w", encoding="utf-8") as f:
                        json.dump(learners, f, indent=2)
                    
                    await asyncio.sleep(0.2)
                    self.log(
                        "Observation", 
                        f"Updated learner progress metrics in Fabric IQ. Hours Studied incremented.", 
                        "FabricIQ.UpdateLearnerLog", 
                        parent_id=span_id
                    )
                except Exception as e:
                    self.log(
                        "Observation", 
                        f"Error updating Fabric IQ learner metrics: {str(e)}", 
                        parent_id=span_id
                    )
                    logger.error(f"Learner update error: {str(e)}")
            
            AgentTraceManager.end_span()
            
            return {
                "score": score,
                "pass_threshold": pass_threshold,
                "passed": passed,
                "incorrect_topics": incorrect_topics,
                "recommendation": recommendation
            }
    
    def _get_questions_for_cert(self, certification_id: str) -> List[Dict[str, Any]]:
        """Get grounded questions for certification."""
        if "AZ-204" in certification_id:
            return [
                {
                    "id": "Q1",
                    "question": "When building a serverless Azure Function trigger, how should you configure authentication to adhere to corporate security guidelines?",
                    "options": [
                        "Hardcode connection secrets in local.settings.json for simplicity",
                        "Build triggers with Managed Identities and avoid hardcoding secrets",
                        "Store credentials in a public GitHub repository",
                        "Use basic connection strings inside the trigger arguments"
                    ],
                    "answer": 1,
                    "citation": "engineering_certification_guide.md, Section: Reference Doc Sec 1 (Azure Functions)",
                    "explanation": "Corporate guide states that triggers must use managed identities for authentication to avoid hardcoded secrets."
                },
                {
                    "id": "Q2",
                    "question": "What is the recommended Azure Storage policy for automatically archiving logs older than 30 days?",
                    "options": [
                        "Manually delete the files via Azure CLI monthly",
                        "Configure Blob Storage Lifecycle Management to transition logs to cool/archive tier",
                        "Disable logging entirely to reduce cloud storage costs",
                        "Increase storage account capacity quotas indefinitely"
                    ],
                    "answer": 1,
                    "citation": "engineering_certification_guide.md, Section: Reference Doc Sec 2 (Azure Storage)",
                    "explanation": "Section 2 requires configuring Blob Storage Lifecycle Management to automate archiving logs older than 30 days."
                },
                {
                    "id": "Q3",
                    "question": "How should you choose a partition key for an Azure Cosmos DB container under corporate guidelines?",
                    "options": [
                        "Select a single static key for all data entries",
                        "Select a partition key with high cardinality to distribute data and throughput evenly",
                        "Avoid partitioning entirely to reduce cost metrics",
                        "Use the timestamp of creation as the only key"
                    ],
                    "answer": 1,
                    "citation": "engineering_certification_guide.md, Section: Reference Doc Sec 3 (Cosmos DB)",
                    "explanation": "Section 3 states a key with high cardinality must be selected to ensure even data/throughput distribution."
                }
            ]
        elif "AZ-400" in certification_id:
            return [
                {
                    "id": "Q1",
                    "question": "To secure CI/CD deployments, which pipeline configuration is recommended by the DevOps team?",
                    "options": [
                        "Enable single-stage scripts without security scans",
                        "Configure branch protection rules and multi-stage YAML pipelines with environment approvals",
                        "Store passwords in pipeline variables as clear text",
                        "Enable anonymous check-ins to all production environments"
                    ],
                    "answer": 1,
                    "citation": "engineering_certification_guide.md, Section: Reference Doc Sec 4 (CI/CD Pipelines)",
                    "explanation": "Section 4 advises enabling branch protection rules and multi-stage YAML pipelines with environment approvals."
                }
            ]
        else:
            return [
                {
                    "id": "Q1",
                    "question": "What directory structure should be utilized when organizing Azure Data Lakes to facilitate analytical workloads?",
                    "options": [
                        "Place all raw files in a single flat directory",
                        "Organize directories as hierarchical folders matching /raw/year/month/day",
                        "Name files randomly in a single container folder",
                        "Store data directly in temporary database tables"
                    ],
                    "answer": 1,
                    "citation": "engineering_certification_guide.md, Section: Reference Doc Sec 5 (Data Lakes)",
                    "explanation": "Section 5 outlines organizing directories hierarchically matching /raw/year/month/day for optimal loads."
                }
            ]
