# AGENTS.md — IBM Bob 2.0 Project Architecture & Guidelines

> Persistent Context for IBM Bob IDE (Agent Mode, Plan Mode, Code Mode, Ask Mode)
> Aligned with the IBM Bob 2.0 Hackathon: Build with Purpose

---

## 🎯 Project Mission & Overview

This project provides an Agentic Developer Workflow Acceleration Suite built natively for **IBM Bob IDE 2.0**. It enhances software engineering workflows across the entire development lifecycle:
- **Change Blast Radius Analysis**
- **Code Archeology & Decision Excavation ("Why Does This Code Exist?")**
- **Context Switch Recovery ("Resume Me")**
- **Smart Developer Onboarding**
- **Intelligent Code Review & Quality Coaching**
- **Automated Testing & Validation Hub**
- **Release Readiness & Deployment Assurance**
- **Legacy Application Modernization**

---

## 🛠️ IBM Bob 2.0 Operating Conventions

### 1. Modes Usage Policy
- **Plan Mode**: Use first for complex, multi-file architectural tasks (blast radius mapping, modernization roadmaps, test strategies). Never edit code until the plan is formulated.
- **Code Mode**: Use for direct implementation, refactoring, and literate coding.
- **Ask Mode**: Use for quick code explanations, context queries, and non-destructive analysis.
- **Agent Mode**: Use when delegating end-to-end multi-step procedures (subagents, parallel exploration).

### 2. Context Mentions (@-Mentions)
Always instruct developers and subagents to use exact context mentions to conserve context tokens and Bobcoins:
- `@file`: Point directly to the relevant source file (e.g., `@src/services/billing.ts`).
- `@folder`: Reference target modules without indexing entire trees (e.g., `@src/routes`).
- `@problems`: Inspect diagnostic lint/type errors.

### 3. Bobcoin Efficiency Best Practices (40 Bobcoins Allocation)
- **Focused Prompts**: Use the **Enhance Prompt** feature (sparkles icon) to generate crisp, deterministic prompts.
- **Subagents**: Spawn subagents for isolated investigations to avoid context bloat in the main session.
- **Selective Context**: Keep context windows clean; use `/init` or start fresh task sessions for distinct features.
- **Document Understanding**: Rely on structured skill templates rather than unbounded prompt repetitions.

---

## 🤖 Available Workspace Skills Catalog

All skills are available in `.agents/skills/` and mirrored in `skills/`:

| Skill | Mode Alignment | Core Focus |
| :--- | :--- | :--- |
| [`change-blast-radius-analyzer`](file:///.agents/skills/change-blast-radius-analyzer/SKILL.md) | Plan / Agent Mode | Dependency traversal, caller tracing, API/DB hazard detection |
| [`code-decision-detective`](file:///.agents/skills/code-decision-detective/SKILL.md) | Ask / Agent Mode | Git archaeology, commit context mining, "Why" deduction |
| [`context-switch-recovery`](file:///.agents/skills/context-switch-recovery/SKILL.md) | Agent Mode | Diff parsing, pending TODO detection, "Resume Me" briefing |
| [`smart-developer-onboarding`](file:///.agents/skills/smart-developer-onboarding/SKILL.md) | Ask / Plan Mode | Architecture walkthroughs, environment setup, starter tasks |
| [`intelligent-code-review`](file:///.agents/skills/intelligent-code-review/SKILL.md) | Code Review Mode | Automated PR reviews, security scanning, Bob tips alignment |
| [`automated-testing-hub`](file:///.agents/skills/automated-testing-hub/SKILL.md) | Code / Agent Mode | Test generation, edge case validation, coverage gap analysis |
| [`release-readiness-assistant`](file:///.agents/skills/release-readiness-assistant/SKILL.md) | Plan / Agent Mode | Dependency auditing, release note generation, deployment checks |
| [`legacy-modernization-accelerator`](file:///.agents/skills/legacy-modernization-accelerator/SKILL.md) | Plan / Code Mode | Stack modernization, deprecation upgrades, refactoring |
| [`hackathon-workflow-guide`](file:///.agents/skills/hackathon-workflow-guide/SKILL.md) | Workflow Guide | Submission checklist, Bob session capture, compliance |

---

## 🌐 Optional IBM watsonx Product Integrations

- **IBM watsonx Orchestrate**: Connect Bob skills into orchestrated multi-agent business workflows, BPMN process automation, and enterprise integrations.
- **IBM watsonx.ai**: Leverage IBM Granite foundation models via Prompt Lab as specialized inference providers for domain-specific reasoning and validation.

---

## 📸 Bob Session Logging (`bob_sessions/`)

Before marking any task complete:
1. Open **Tasks** in Bob IDE.
2. Click task header $\rightarrow$ **Task session consumption summary**.
3. Take PNG screenshot.
4. Save as `bob_sessions/<team>_<task>_<desc>_summary.png`.
