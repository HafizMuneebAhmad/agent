document.addEventListener("DOMContentLoaded", () => {
  // Application State
  const state = {
    learners: [],
    certifications: [],
    selectedLearnerId: null,
    selectedCertId: null,
    liveMode: false,
    apiKey: "",
    activeTab: "learner-space",
    currentSessionId: null,
    currentStatus: null,
    activeConsoleTab: "console-log"
  };

  // DOM Elements
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");
  const profilesList = document.getElementById("profiles-list");
  const optimizeBtn = document.getElementById("optimize-btn");
  const certSelect = document.getElementById("certification-select");
  const apiToggle = document.getElementById("api-toggle");
  const apiKeyInput = document.getElementById("api-key-input");
  
  // Terminal and result fields
  const terminalBody = document.getElementById("terminal-body");
  const traceGraphBody = document.getElementById("trace-graph-body");
  const consoleLogTab = document.getElementById("console-log-tab");
  const consoleTraceTab = document.getElementById("console-trace-tab");
  const executionStatus = document.getElementById("execution-status");
  const planSection = document.getElementById("plan-section");
  const curatorOutline = document.getElementById("curator-outline");
  const citationsList = document.getElementById("citations-list");
  const milestonesList = document.getElementById("milestones-list");
  
  // HITL (Human-in-the-loop)
  const hitlContainer = document.getElementById("hitl-checkpoint-container");
  const hitlMessage = document.getElementById("hitl-message");
  const hitlAgentBadge = document.getElementById("hitl-agent-badge");
  const hitlFeedbackInput = document.getElementById("hitl-feedback-input");
  const hitlApproveBtn = document.getElementById("hitl-approve-btn");
  const hitlRejectBtn = document.getElementById("hitl-reject-btn");

  // Work IQ
  const calendarSlots = document.getElementById("calendar-slots");
  const workStrategyText = document.getElementById("work-strategy-text");
  const reminderInfo = document.getElementById("reminder-info");

  // Fabric IQ
  const skillGapTableBody = document.getElementById("skill-gap-table-body");

  // Assessment
  const quizSection = document.getElementById("quiz-section");
  const quizQuestionsContainer = document.getElementById("quiz-questions-container");
  const quizSubmitBtn = document.getElementById("quiz-submit-btn");
  const quizResultsPanel = document.getElementById("quiz-results-panel");
  const quizScoreNum = document.getElementById("quiz-score-num");
  const quizResultTitle = document.getElementById("quiz-result-title");
  const quizExplanationList = document.getElementById("quiz-explanation-list");
  let activeQuestions = [];

  // Manager Portal
  const totalLearnersStat = document.getElementById("stat-total-learners");
  const passRateStat = document.getElementById("stat-pass-rate");
  const studyHoursStat = document.getElementById("stat-study-hours");
  const managerAlertsList = document.getElementById("manager-alerts-list");
  const managerTableBody = document.getElementById("manager-table-body");


  // Tab Switchers
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      
      btn.classList.add("active");
      document.getElementById(targetTab).classList.add("active");
      state.activeTab = targetTab;

      if (targetTab === "manager-portal") {
        fetchManagerInsights();
      } else if (targetTab === "assessment-center") {
        initAssessmentTab();
      }
    });
  });

  // Toggle API key view
  apiToggle.addEventListener("change", (e) => {
    state.liveMode = e.target.checked;
    if (state.liveMode) {
      apiKeyInput.style.display = "block";
    } else {
      apiKeyInput.style.display = "none";
      apiKeyInput.value = "";
      state.apiKey = "";
    }
  });

  apiKeyInput.addEventListener("input", (e) => {
    state.apiKey = e.target.value.trim();
  });

  // Console Tab Swapping
  consoleLogTab.addEventListener("click", () => {
    consoleLogTab.classList.add("active");
    consoleTraceTab.classList.remove("active");
    terminalBody.style.display = "block";
    traceGraphBody.style.display = "none";
    state.activeConsoleTab = "console-log";
  });

  consoleTraceTab.addEventListener("click", () => {
    consoleTraceTab.classList.add("active");
    consoleLogTab.classList.remove("active");
    terminalBody.style.display = "none";
    traceGraphBody.style.display = "flex";
    state.activeConsoleTab = "console-trace";
  });


  // Initial Fetch API
  async function init() {
    try {
      const [learnersRes, certsRes] = await Promise.all([
        fetch("/api/learners"),
        fetch("/api/certifications")
      ]);
      state.learners = await learnersRes.json();
      state.certifications = (await certsRes.json()).certifications;
      
      renderLearnerSelector();
      populateCertDropdown();
    } catch (e) {
      console.error("Initialization error:", e);
      alert("Error loading synthetic data profiles.");
    }
  }

  // Render Learners Selector
  function renderLearnerSelector() {
    profilesList.innerHTML = "";
    state.learners.forEach(learner => {
      const card = document.createElement("div");
      card.className = `profile-card ${state.selectedLearnerId === learner.learner_id ? 'active' : ''}`;
      card.dataset.id = learner.learner_id;
      
      let statusClass = "badge-in-progress";
      if (learner.learning_log.status === "Passed") statusClass = "badge-passed";
      
      card.innerHTML = `
        <div class="profile-info">
          <h3>${learner.name}</h3>
          <p>${learner.role} • ${learner.target_certification}</p>
        </div>
        <span class="badge ${statusClass}">${learner.learning_log.status}</span>
      `;
      
      card.addEventListener("click", () => {
        selectLearner(learner.learner_id);
      });
      profilesList.appendChild(card);
    });

    if (state.learners.length > 0 && !state.selectedLearnerId) {
      selectLearner(state.learners[0].learner_id);
    }
  }

  // Populate Dropdown
  function populateCertDropdown() {
    certSelect.innerHTML = "";
    state.certifications.forEach(cert => {
      const opt = document.createElement("option");
      opt.value = cert.id;
      opt.textContent = `${cert.id} - ${cert.name}`;
      certSelect.appendChild(opt);
    });
  }

  // Select a Learner Profile
  function selectLearner(id) {
    state.selectedLearnerId = id;
    const cards = document.querySelectorAll(".profile-card");
    cards.forEach(c => {
      if (c.dataset.id === id) c.classList.add("active");
      else c.classList.remove("active");
    });

    const learner = state.learners.find(l => l.learner_id === id);
    if (learner) {
      state.selectedCertId = learner.target_certification;
      certSelect.value = learner.target_certification;
      renderFabricTable(learner);
      
      // Hide plan results when switching learners to avoid confusion
      planSection.style.display = "none";
      terminalBody.innerHTML = `<div class="text-muted">> System Ready. Select 'Optimize & Curate Plan' to orchestrate.</div>`;
      quizSection.style.display = "none";
      quizResultsPanel.style.display = "none";
    }
  }

  // Render Skill Gaps Table (Fabric IQ View)
  function renderFabricTable(learner) {
    skillGapTableBody.innerHTML = "";
    learner.skills_assessment.forEach(s => {
      const diff = s.target - s.current;
      const pct = (s.current / s.target) * 100;
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${s.skill}</td>
        <td>
          <div class="proficiency-bar-bg">
            <div class="proficiency-bar-fill" style="width: ${pct}%"></div>
          </div>
          ${s.current}/${s.target}
        </td>
        <td>
          ${diff > 0 ? `<span class="gap-indicator">-${diff}</span>` : `<span class="badge badge-passed" style="padding:0.15rem 0.4rem;">Met</span>`}
        </td>
      `;
      skillGapTableBody.appendChild(row);
    });
  }

  // Render Traces (Console Logs & Visual Tree)
  function renderTraces(traces) {
    terminalBody.innerHTML = "";
    traceGraphBody.innerHTML = "";

    if (!traces || traces.length === 0) {
      terminalBody.innerHTML = `<div class="text-muted">> No logs available.</div>`;
      traceGraphBody.innerHTML = `<div class="text-muted" style="font-family: monospace; font-size: 0.8rem;">No execution traces available.</div>`;
      return;
    }

    traces.forEach(log => {
      // 1. Render to Standard Console
      const consoleDiv = document.createElement("div");
      consoleDiv.className = "log-entry";
      
      const agentClass = log.agent_name.toLowerCase().includes("curator") ? "curator" :
                         log.agent_name.toLowerCase().includes("planner") ? "planner" :
                         log.agent_name.toLowerCase().includes("engagement") ? "engagement" :
                         log.agent_name.toLowerCase().includes("assessment") ? "assessment" : 
                         log.agent_name.toLowerCase().includes("user") ? "user" : "manager";
                         
      const stepClass = log.step_type === "Thought" ? "step-thought" :
                        log.step_type === "Action" ? "step-action" :
                        log.step_type === "Observation" ? "step-observation" : "step-final";

      const toolSpan = log.tool_name ? ` <span class="log-tool">[Tool: ${log.tool_name}]</span>` : "";

      consoleDiv.innerHTML = `
        &gt; <span class="log-agent ${agentClass}">${log.agent_name}</span>
        <span class="log-step ${stepClass}">${log.step_type}</span>
        ${toolSpan}
        <span class="log-text">${log.content}</span>
      `;
      terminalBody.appendChild(consoleDiv);

      // 2. Render to Visual Tracing Tree (DevUI)
      const nodeDiv = document.createElement("div");
      nodeDiv.className = `trace-node ${log.parent_id !== "root" ? "child" : ""}`;
      nodeDiv.id = log.id;

      nodeDiv.innerHTML = `
        <div class="trace-node-header">
          <span class="trace-node-agent ${agentClass}">🤖 ${log.agent_name}</span>
          <span>${log.timestamp}</span>
        </div>
        <div class="trace-node-body">
          <span class="log-step ${stepClass}" style="margin-right: 0.25rem;">${log.step_type}</span>
          ${log.tool_name ? `<span class="log-tool" style="font-weight:600; font-size:0.75rem;">[${log.tool_name}]</span>` : ""}
          <span>${log.content}</span>
        </div>
        <div class="trace-node-footer">
          <span>Span ID: <code>${log.id}</code></span>
          <span>Latency: <code>${log.latency_ms || 0}ms</code></span>
        </div>
      `;
      traceGraphBody.appendChild(nodeDiv);
    });

    // Scroll to bottom
    terminalBody.scrollTop = terminalBody.scrollHeight;
    traceGraphBody.scrollTop = traceGraphBody.scrollHeight;
  }

  // Start Orchestrator Workflow (Curation Step)
  optimizeBtn.addEventListener("click", async () => {
    if (!state.selectedLearnerId || !state.selectedCertId) return;

    optimizeBtn.disabled = true;
    optimizeBtn.innerHTML = `<span class="loader-spinner"></span> Orchesterating...`;
    planSection.style.display = "none";
    hitlContainer.style.display = "none";
    executionStatus.textContent = "Status: CURATING...";
    executionStatus.style.color = "var(--color-primary)";

    try {
      const response = await fetch("/api/workflow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          learner_id: state.selectedLearnerId,
          certification_id: state.selectedCertId,
          live_mode: state.liveMode,
          api_key: state.apiKey
        })
      });

      const data = await response.json();
      if (data.success) {
        state.currentSessionId = data.session_id;
        state.currentStatus = data.status;

        // Render traces up to Curator completion
        renderTraces(data.traces);

        // Pre-render Curator syllabus in output section
        planSection.style.display = "block";
        curatorOutline.innerHTML = data.curator_output.curated_outline.replace(/\n/g, "<br>");
        citationsList.innerHTML = "";
        data.curator_output.citations.forEach(cit => {
          const li = document.createElement("div");
          li.className = "citation-card";
          li.innerHTML = `
            <div class="citation-source">📄 Source: ${cit.source} (Section: ${cit.section})</div>
            <div class="citation-text">"${cit.reference_text}"</div>
          `;
          citationsList.appendChild(li);
        });

        // Trigger Human-in-the-Loop Interruption dialog
        hitlAgentBadge.textContent = "Curator Agent";
        hitlAgentBadge.className = "badge badge-in-progress";
        hitlMessage.innerHTML = `<strong>Curator Agent</strong> has extracted syllabus guidelines for <strong>${state.selectedCertId}</strong>. Review outline on the right. Approve to proceed with Fabric IQ skills gaps matching.`;
        hitlFeedbackInput.value = "";
        hitlContainer.style.display = "flex";
        hitlContainer.scrollIntoView({ behavior: 'smooth' });
        
        executionStatus.textContent = "Status: PAUSED (User Review)";
        executionStatus.style.color = "var(--color-warning)";
      } else {
        alert("Workflow failed during Curation phase.");
        optimizeBtn.disabled = false;
        optimizeBtn.innerHTML = `Optimize & Curate Plan`;
        executionStatus.textContent = "Status: FAILED";
        executionStatus.style.color = "var(--color-danger)";
      }
    } catch (e) {
      console.error(e);
      alert("Error starting multi-agent flow.");
      optimizeBtn.disabled = false;
      optimizeBtn.innerHTML = `Optimize & Curate Plan`;
      executionStatus.textContent = "Status: ERROR";
      executionStatus.style.color = "var(--color-danger)";
    }
  });

  // Handle HITL Approval and Resume
  hitlApproveBtn.addEventListener("click", async () => {
    if (!state.currentSessionId) return;

    hitlApproveBtn.disabled = true;
    hitlRejectBtn.disabled = true;
    const feedback = hitlFeedbackInput.value.trim();
    
    executionStatus.textContent = "Status: RESUMING...";
    executionStatus.style.color = "var(--color-primary)";

    try {
      const response = await fetch("/api/workflow/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.currentSessionId,
          approved: true,
          user_feedback: feedback,
          live_mode: state.liveMode,
          api_key: state.apiKey
        })
      });

      const data = await response.json();
      if (data.success) {
        state.currentStatus = data.status;
        renderTraces(data.traces);

        if (data.status === "Paused_Planner") {
          // Pre-render milestones in Planner output section
          milestonesList.innerHTML = "";
          data.planner_output.milestones.forEach(m => {
            const li = document.createElement("li");
            li.style.marginBottom = "0.75rem";
            li.innerHTML = `<strong>Week ${m.week}: ${m.topic}</strong><br><span style="color:var(--text-secondary);font-size:0.8rem;">${m.focus}</span>`;
            milestonesList.appendChild(li);
          });

          // Show next checkpoint review
          hitlAgentBadge.textContent = "Planner Agent";
          hitlAgentBadge.className = "badge badge-in-progress";
          hitlMessage.innerHTML = `<strong>Planner Agent</strong> has matched learner skills against cert syllabus and generated 4-week milestones. Review milestones. Approve to allocate optimized calendar slots.`;
          hitlFeedbackInput.value = "";
          hitlApproveBtn.disabled = false;
          hitlRejectBtn.disabled = false;
          hitlContainer.scrollIntoView({ behavior: 'smooth' });

          executionStatus.textContent = "Status: PAUSED (User Review)";
          executionStatus.style.color = "var(--color-warning)";
        } else if (data.status === "Completed") {
          // Hide HITL and complete results
          hitlContainer.style.display = "none";
          displayPlanResults(data.curator_output, data.planner_output, data.engagement_output);
          
          executionStatus.textContent = "Status: COMPLETED";
          executionStatus.style.color = "var(--color-success)";
          
          optimizeBtn.disabled = false;
          optimizeBtn.innerHTML = `Optimize & Curate Plan`;
          
          // Reset session
          state.currentSessionId = null;
          state.currentStatus = null;
        }
      } else {
        alert("Workflow resume failed.");
        resetHITLState();
      }
    } catch (e) {
      console.error(e);
      alert("Error resuming multi-agent workflow.");
      resetHITLState();
    }
  });

  // Handle HITL Rejection
  hitlRejectBtn.addEventListener("click", async () => {
    if (!state.currentSessionId) return;

    hitlApproveBtn.disabled = true;
    hitlRejectBtn.disabled = true;
    const feedback = hitlFeedbackInput.value.trim();

    try {
      const response = await fetch("/api/workflow/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.currentSessionId,
          approved: false,
          user_feedback: feedback
        })
      });

      const data = await response.json();
      renderTraces(data.traces);
      
      hitlContainer.style.display = "none";
      executionStatus.textContent = "Status: REJECTED (Stopped)";
      executionStatus.style.color = "var(--color-danger)";
      
      optimizeBtn.disabled = false;
      optimizeBtn.innerHTML = `Optimize & Curate Plan`;
      
      state.currentSessionId = null;
      state.currentStatus = null;
    } catch (e) {
      console.error(e);
      alert("Error rejecting workflow segment.");
      resetHITLState();
    }
  });

  function resetHITLState() {
    hitlApproveBtn.disabled = false;
    hitlRejectBtn.disabled = false;
    optimizeBtn.disabled = false;
    optimizeBtn.innerHTML = `Optimize & Curate Plan`;
    executionStatus.textContent = "Status: ERROR";
    executionStatus.style.color = "var(--color-danger)";
  }


  // Display curated schedules & guides
  function displayPlanResults(curator, planner, engagement) {
    planSection.style.display = "block";

    // 1. Curator
    curatorOutline.innerHTML = curator.curated_outline.replace(/\n/g, "<br>");
    citationsList.innerHTML = "";
    curator.citations.forEach(cit => {
      const li = document.createElement("div");
      li.className = "citation-card";
      li.innerHTML = `
        <div class="citation-source">📄 Source: ${cit.source} (Section: ${cit.section})</div>
        <div class="citation-text">"${cit.reference_text}"</div>
      `;
      citationsList.appendChild(li);
    });

    // 2. Planner
    milestonesList.innerHTML = "";
    planner.milestones.forEach(m => {
      const li = document.createElement("li");
      li.style.marginBottom = "0.75rem";
      li.innerHTML = `<strong>Week ${m.week}: ${m.topic}</strong><br><span style="color:var(--text-secondary);font-size:0.8rem;">${m.focus}</span>`;
      milestonesList.appendChild(li);
    });

    // 3. Work IQ Calendar Slots
    calendarSlots.innerHTML = "";
    workStrategyText.innerHTML = `<strong>Scheduling Strategy:</strong> ${engagement.strategy}`;
    reminderInfo.innerHTML = `🔔 Reminders configured as: <strong>${engagement.reminder_frequency}</strong> using a <strong>${engagement.reminder_tone}</strong> tone.`;

    // Fetch original calendar signals
    const learner = state.learners.find(l => l.learner_id === planner.learner_id);
    const learnerRole = learner ? learner.role : "";

    // Load static calendar grid and overlay learning blocks
    fetch("/api/workflow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        learner_id: state.selectedLearnerId,
        certification_id: state.selectedCertId
      })
    }).then(res => res.json()).then(data => {
      // Load raw calendar list
      fetch("/api/learners").then(r => r.json()).then(learnersList => {
        const matchingLearner = learnersList.find(l => l.learner_id === state.selectedLearnerId);
        
        // Load original work signals to get calendar details
        fetch("/api/learners").then(() => {
          fetch("/api/learners").then(() => {
            // Draw visual calendar slots
            // Let's create a combined calendar representation
            const slotsToDraw = [];
            const scheds = engagement.scheduled_slots;

            // Simple calendar mock list for UI
            const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
            
            days.forEach(day => {
              const daySlots = scheds.filter(s => s.day === day);
              if (daySlots.length > 0) {
                daySlots.forEach(ds => {
                  slotsToDraw.push({
                    day: day,
                    time: ds.time,
                    status: "study",
                    activity: ds.context
                  });
                });
              } else {
                // Default placeholder
                slotsToDraw.push({
                  day: day,
                  time: "11:00 - 12:00",
                  status: "free",
                  activity: "Focus Window Study Opportunity"
                });
              }
            });

            // Put a header in cal cards
            slotsToDraw.slice(0, 3).forEach(slot => {
              const div = document.createElement("div");
              div.className = `calendar-slot ${slot.status}`;
              div.innerHTML = `
                <div>
                  <div class="calendar-header-day">${slot.day}</div>
                  <span class="calendar-activity">${slot.activity}</span>
                </div>
                <div class="calendar-time">${slot.time}</div>
              `;
              calendarSlots.appendChild(div);
            });
          });
        });
      });
    });
  }

  // -------------------------------------------------------------
  // ASSESSMENT TAB
  // -------------------------------------------------------------
  async function initAssessmentTab() {
    if (!state.selectedLearnerId) return;

    quizSection.style.display = "none";
    quizResultsPanel.style.display = "none";
    quizQuestionsContainer.innerHTML = `<p style="padding:1rem;color:var(--text-secondary);"><span class="loader-spinner"></span> Generating questions with citations from knowledge sources...</p>`;

    const certId = state.selectedCertId || "AZ-204";

    try {
      const res = await fetch(`/api/assessment/generate/${certId}`);
      const data = await res.json();
      
      if (data.success) {
        activeQuestions = data.assessment.questions;
        renderQuiz(activeQuestions);
      }
    } catch (e) {
      console.error(e);
      quizQuestionsContainer.innerHTML = `<p style="color:var(--color-danger)">Error loading assessment questions.</p>`;
    }
  }

  function renderQuiz(questions) {
    quizQuestionsContainer.innerHTML = "";
    quizSection.style.display = "block";

    questions.forEach((q, idx) => {
      const card = document.createElement("div");
      card.className = "quiz-card";
      card.style.marginBottom = "1.5rem";
      
      const citationText = `<div style="font-size:0.75rem;color:var(--color-primary);margin-bottom:0.5rem;font-weight:600;">Grounded Grounding Ref: [${q.citation}]</div>`;

      let optionsHtml = "";
      q.options.forEach((opt, optIdx) => {
        optionsHtml += `
          <div class="quiz-option" data-question-idx="${idx}" data-option-idx="${optIdx}">
            <span class="quiz-option-indicator">${String.fromCharCode(65 + optIdx)}</span>
            <span>${opt}</span>
          </div>
        `;
      });

      card.innerHTML = `
        ${citationText}
        <div class="quiz-question">${idx + 1}. ${q.question}</div>
        <div class="quiz-options">${optionsHtml}</div>
      `;

      quizQuestionsContainer.appendChild(card);
    });

    // Option selection listeners
    const options = quizQuestionsContainer.querySelectorAll(".quiz-option");
    options.forEach(opt => {
      opt.addEventListener("click", () => {
        const qIdx = opt.getAttribute("data-question-idx");
        // Deselect others in same question
        quizQuestionsContainer.querySelectorAll(`.quiz-option[data-question-idx="${qIdx}"]`).forEach(sibling => {
          sibling.classList.remove("selected");
        });
        opt.classList.add("selected");
      });
    });
  }

  // Quiz submission
  quizSubmitBtn.addEventListener("click", async () => {
    const answers = {};
    let allAnswered = true;

    activeQuestions.forEach((q, idx) => {
      const selectedOpt = quizQuestionsContainer.querySelector(`.quiz-option[data-question-idx="${idx}"].selected`);
      if (selectedOpt) {
        answers[q.id] = parseInt(selectedOpt.getAttribute("data-option-idx"));
      } else {
        allAnswered = false;
      }
    });

    if (!allAnswered) {
      alert("Please answer all questions before submitting.");
      return;
    }

    quizSubmitBtn.disabled = true;
    quizSubmitBtn.innerHTML = "Grading...";

    try {
      const res = await fetch("/api/assessment/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          learner_id: state.selectedLearnerId,
          certification_id: state.selectedCertId || "AZ-204",
          answers: answers,
          questions: activeQuestions
        })
      });

      const data = await res.json();
      if (data.success) {
        displayQuizResults(data.evaluation);
        // Reload profiles state (hours + scores updated)
        const currentSelectedId = state.selectedLearnerId;
        const learnersRes = await fetch("/api/learners");
        state.learners = await learnersRes.json();
        renderLearnerSelector();
        selectLearner(currentSelectedId);
      }
    } catch (e) {
      console.error(e);
      alert("Error submitting answers.");
    } finally {
      quizSubmitBtn.disabled = false;
      quizSubmitBtn.innerHTML = "Submit Assessment";
    }
  });

  function displayQuizResults(evalData) {
    quizResultsPanel.style.display = "block";
    quizScoreNum.textContent = `${evalData.score}%`;
    
    if (evalData.passed) {
      quizResultTitle.textContent = "Readiness Check Passed!";
      quizResultTitle.style.color = "var(--color-success)";
    } else {
      quizResultTitle.textContent = "Readiness Check Failed";
      quizResultTitle.style.color = "var(--color-danger)";
    }

    quizExplanationList.innerHTML = "";
    
    // Add evaluation recommendation
    const recDiv = document.createElement("div");
    recDiv.className = "citation-card";
    recDiv.style.borderColor = evalData.passed ? "var(--color-success)" : "var(--color-warning)";
    recDiv.innerHTML = `<strong>Advisor Decision:</strong> ${evalData.recommendation}`;
    quizExplanationList.appendChild(recDiv);

    if (evalData.incorrect_topics.length > 0) {
      const label = document.createElement("h4");
      label.style.marginTop = "1rem";
      label.style.marginBottom = "0.5rem";
      label.textContent = "Review Areas:";
      quizExplanationList.appendChild(label);

      evalData.incorrect_topics.forEach(topic => {
        const div = document.createElement("div");
        div.className = "citation-card";
        div.innerHTML = `
          <div style="font-weight:600;font-size:0.85rem;color:var(--color-danger)">Mismatch on question:</div>
          <div style="font-size:0.8rem;color:var(--text-primary);margin-bottom:0.25rem;">"${topic.question}"</div>
          <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:0.25rem;">Your response: ${topic.incorrect_answer}</div>
          <div style="font-size:0.8rem;color:var(--color-secondary);margin-bottom:0.25rem;">Grounding reference: [${topic.citation}]</div>
          <div style="font-style:italic;font-size:0.8rem;color:var(--text-muted);">"${topic.correct_explanation}"</div>
        `;
        quizExplanationList.appendChild(div);
      });
    }
    
    // Smooth scroll down to results
    quizResultsPanel.scrollIntoView({ behavior: 'smooth' });
  }

  // -------------------------------------------------------------
  // MANAGER PORTAL TAB
  // -------------------------------------------------------------
  async function fetchManagerInsights() {
    managerTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;"><span class="loader-spinner"></span> Synthesizing team analytics...</td></tr>`;
    managerAlertsList.innerHTML = "";

    try {
      const res = await fetch("/api/manager/insights");
      const data = await res.json();
      
      if (data.success) {
        const ins = data.insights;
        totalLearnersStat.textContent = ins.total_learners;
        passRateStat.textContent = `${ins.pass_rate}%`;
        studyHoursStat.textContent = ins.avg_study_hours;

        // Render Alerts
        if (ins.alerts.length === 0) {
          managerAlertsList.innerHTML = `<p style="color:var(--color-success);font-size:0.9rem;">All team members are currently on track.</p>`;
        } else {
          ins.alerts.forEach(alert => {
            const div = document.createElement("div");
            div.className = "alert-box";
            div.innerHTML = `
              <div class="alert-icon-red">⚠️</div>
              <div class="alert-details">
                <h4>${alert.role} - ${alert.certification}</h4>
                <p>${alert.reason}</p>
              </div>
            `;
            managerAlertsList.appendChild(div);
          });
        }

        // Render table
        managerTableBody.innerHTML = "";
        ins.team_summaries.forEach(team => {
          const row = document.createElement("tr");
          
          let statusClass = "badge-in-progress";
          if (team.status === "Passed") statusClass = "badge-passed";
          
          let riskStyle = "color:var(--text-primary)";
          if (team.risk === "High") riskStyle = "color:var(--color-danger);font-weight:600;";
          else if (team.risk === "Medium") riskStyle = "color:var(--color-warning);font-weight:600;";

          row.innerHTML = `
            <td><strong>${team.name}</strong></td>
            <td>${team.role}</td>
            <td>${team.certification}</td>
            <td><span class="badge ${statusClass}">${team.status}</span></td>
            <td>${team.study_hours} hrs (${team.meeting_hours} meetings/wk)</td>
            <td style="${riskStyle}">${team.risk}</td>
          `;
          managerTableBody.appendChild(row);
        });
      }
    } catch (e) {
      console.error(e);
      managerTableBody.innerHTML = `<tr><td colspan="6" style="color:var(--color-danger);text-align:center;">Error compiling manager dashboard data.</td></tr>`;
    }
  }

  // Bootstrap app
  init();
});
