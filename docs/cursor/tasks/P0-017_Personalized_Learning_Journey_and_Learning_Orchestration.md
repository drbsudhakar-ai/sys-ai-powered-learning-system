# P0-017 — Personalized Learning Journey & Learning Orchestration

## 1. Objective

Implement the SYS Personalized Learning Journey & Learning Orchestration layer.

Its purpose is to answer one central question:

> **"What should this student do next, and why?"**

P0-017 coordinates existing SYS capabilities into a coherent personalized learning path.

It must NOT replace or duplicate:

- P0-010 Question Intelligence
- P0-011 Assessment Engine
- P0-012 Performance Analyzer / Learning Gap Detection
- P0-013 Learning Sessions / AI Lecturer / Digital Classroom
- P0-014 Remedial Learning & Student Group Formation
- P0-015 Adaptive Practice & Mastery Engine
- P0-016 Learning Intelligence & Early-Warning Analytics
- Notification Engine

P0-017 is an **orchestration layer**, not a new academic intelligence engine.

---

# 2. Position in SYS Architecture

```text
                    ┌─────────────────────┐
                    │   Student Profile   │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ P0-012 Performance  │
                    │ + Learning Gaps     │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ P0-014 Remediation  │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ P0-015 Mastery      │
                    │ + Practice          │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ P0-016 Intelligence │
                    │ + Early Warning     │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │     P0-017          │
                    │ Learning            │
                    │ Orchestration       │
                    └──────────┬──────────┘
                               ↓
              ┌────────────────┼────────────────┐
              ↓                ↓                ↓
         Learn/Revise       Practice        Assess
              ↓                ↓                ↓
         AI Lecturer       Adaptive       Reassessment
              │             Practice           │
              └────────────────┼────────────────┘
                               ↓
                         P0-012/P0-015
                         evaluate state
                               ↓
                       P0-017 next action
```

P0-017 should continuously coordinate the student's journey based on authoritative current state.

---

# 3. Core Principle

P0-017 does not decide whether a student is mastered, weak, at risk, or eligible for reassessment.

Those decisions remain with the appropriate authoritative engines.

P0-017 answers:

```text
Current authoritative state
        ↓
Available learning actions
        ↓
Select the most appropriate next action
        ↓
Present clear reason
        ↓
Student performs action
        ↓
Existing engine updates state
        ↓
P0-017 recalculates next action
```

---

# 4. Personalized Learning Journey

The student should see a coherent journey instead of unrelated modules.

Example:

```text
Current Topic: Integration

Status:
Needs Support

Recommended Path:

1. Review fundamentals
        ↓
2. Attend AI Lecturer lesson
        ↓
3. Practice foundational questions
        ↓
4. Adaptive practice
        ↓
5. Check readiness
        ↓
6. Reassessment
        ↓
7. MASTERED
```

The path should dynamically change as the student's authoritative state changes.

---

# 5. Learning Action Model

Introduce a normalized concept of a **Learning Action**.

Possible actions:

```text
CONTINUE_LEARNING
REVIEW_TOPIC
WATCH_LECTURE
START_AI_LECTURE
ASK_LECTURER
PRACTICE
ADAPTIVE_PRACTICE
COMPLETE_REMEDIATION
SELF_STUDY
HUMAN_EXPERT_SUPPORT
TAKE_ASSESSMENT
TAKE_REASSESSMENT
REVIEW_MISTAKES
MOVE_TO_NEXT_TOPIC
RETRY
WAIT_FOR_FACULTY_ACTION
```

Do not create duplicate implementations of these capabilities.

A learning action should reference the existing resource/session/assessment where appropriate.

---

# 6. Learning Action Structure

Each recommended action should have:

```text
action_id
action_type
title
description
reason
priority
status
source
target_course
target_subject
target_unit
target_topic
resource_reference
prerequisites
created_at
expires_at (optional)
```

Example:

```text
Action:
ADAPTIVE_PRACTICE

Topic:
Newton's Laws

Reason:
Practice accuracy has improved, but mastery has not yet
been established.

Priority:
HIGH

Source:
P0-015
```

---

# 7. Recommendation Priority

Recommendations should be deterministic and explainable.

Possible priority:

```text
CRITICAL
HIGH
MEDIUM
LOW
OPTIONAL
```

Priority should consider existing authoritative signals such as:

- active learning gap
- persistent gap
- remediation assignment
- reassessment readiness
- failed reassessment
- mastery state
- early-warning signal
- unfinished learning activity
- prerequisite dependency
- upcoming assessment where supported

Do not introduce a new opaque risk score.

---

# 8. Decision Hierarchy

When multiple actions are available, use a clear hierarchy.

Suggested order:

```text
1. Required/unfinished action
2. Active remediation
3. Failed reassessment follow-up
4. Persistent learning gap
5. Required adaptive practice
6. Topic learning/revision
7. Reassessment when eligible
8. Continue curriculum
9. Optional enrichment
```

The exact ordering must respect existing academic policies and repository conventions.

Do not hard-code assumptions that conflict with existing policy.

---

# 9. Topic Progression

P0-017 should understand the course hierarchy:

```text
Course
  ↓
Subject
  ↓
Unit
  ↓
Topic
```

Use existing curriculum structure.

The orchestrator may determine:

- current topic
- completed topic
- next topic
- blocked topic
- prerequisite topic
- topic requiring support

It must not create a separate curriculum structure.

---

# 10. Prerequisite Awareness

Where prerequisite relationships exist in the repository, use them.

Example:

```text
Topic A
  ↓ prerequisite
Topic B
```

If Topic A is not sufficiently completed:

```text
Recommended:
Complete Topic A before continuing Topic B.
```

Do not invent prerequisite relationships automatically without a defined source.

If prerequisite metadata does not yet exist, do not create a complex prerequisite engine in P0-017 unless necessary.

---

# 11. Mastery-Aware Progression

Use P0-015 mastery state.

Example:

```text
MASTERED
→ Move forward

DEVELOPING
→ Continue practice

NEEDS_PRACTICE
→ Adaptive practice

NEEDS_REMEDIATION
→ Remedial learning

READY_FOR_REASSESSMENT
→ Reassessment

REASSESSMENT_FAILED
→ Return to targeted practice/remediation
```

The orchestrator must consume P0-015 state rather than calculate mastery itself.

---

# 12. Learning-Gap-Aware Orchestration

Consume P0-012 learning gaps.

Example:

```text
Gap detected
    ↓
Check existing remedial intervention
    ↓
If assigned → complete intervention
    ↓
If not assigned → recommend remedial path
    ↓
After intervention → practice
    ↓
P0-015 determines reassessment readiness
```

Do not create another gap detector or remedial engine.

---

# 13. Early-Warning-Aware Orchestration

Consume P0-016 attention signals.

Example:

```text
WATCH
→ encourage practice

ATTENTION_REQUIRED
→ targeted learning/support

URGENT_ATTENTION
→ recommend faculty/human support where appropriate
```

P0-017 may change the recommended action based on warning severity.

It must not recalculate the warning.

---

# 14. Student Learning Modes

The journey should support multiple learning routes:

```text
AI Lecturer
Self Study
Adaptive Practice
Human Subject Expert
Remedial Learning
Assessment
Reassessment
```

Students should not be forced into AI-only learning.

Where appropriate, allow the student to choose:

```text
Learn with AI Lecturer
Study Myself
Practice Questions
Request/Attend Expert Support
```

Choice should still respect academic requirements.

---

# 15. Student Control

The system should recommend, not unnecessarily force.

Example:

```text
Recommended:
Adaptive Practice

Other available options:
Review Topic
Watch Lecture
Self Study
```

However, mandatory academic activities must remain mandatory when defined by existing academic policy.

---

# 16. Learning Journey States

Possible journey states:

```text
NOT_STARTED
IN_PROGRESS
WAITING_FOR_ACTION
READY_FOR_ASSESSMENT
READY_FOR_REASSESSMENT
COMPLETED
BLOCKED
NEEDS_SUPPORT
MASTERED
```

Do not create state duplication if equivalent authoritative states already exist.

Use orchestration state only for journey coordination.

---

# 17. Action Lifecycle

Possible action lifecycle:

```text
RECOMMENDED
→ ACCEPTED
→ STARTED
→ IN_PROGRESS
→ COMPLETED
→ SUPERSEDED
→ EXPIRED
→ CANCELLED
```

Not every action requires every state.

Actions should reference existing sessions/assessments/interventions where possible.

---

# 18. Resume Learning

Students should be able to return to where they stopped.

Example:

```text
Welcome back.

You were studying:
Unit II → Topic 4

Last activity:
AI Lecturer — Step 6 of 10

Continue Learning
```

Use existing learning-session progress.

Do not create duplicate progress tracking where P0-013 already provides it.

---

# 19. Next Best Action

Provide one clear primary recommendation.

Example:

```text
Your next best step

Practice Newton's Laws

Why?
You completed the lesson and your latest practice
accuracy is improving, but mastery has not yet been
established.

[Start Practice]
```

Secondary actions may also be shown.

Avoid presenting a confusing list of ten equally important tasks.

---

# 20. Explainability

Every primary recommendation should explain:

```text
WHAT:
What should I do?

WHY:
Why am I being asked to do it?

SOURCE:
Which learning state caused this recommendation?

OUTCOME:
What happens after I complete it?
```

Example:

```text
Practice Topic

Why:
Your recent assessment identified this topic as needing
additional practice.

After completion:
Your practice evidence will update your learning status.
```

---

# 21. Personalized Daily Learning Plan

If sufficient data exists, provide a daily plan.

Example:

```text
Today's Learning Plan

1. Review — 15 min
2. AI Lecture — 20 min
3. Adaptive Practice — 15 min
4. Reassessment — when eligible
```

The plan should be generated from existing recommended actions.

Do not build a complex scheduling/optimization engine in P0-017.

---

# 22. Time-Aware Recommendations

Where supported, recommendations may consider:

- upcoming assessment
- overdue action
- unfinished activity
- available learning session
- academic schedule

Do not invent deadlines.

If no scheduling data exists, do not fabricate urgency.

---

# 23. Student Dashboard

Create/extend a student-facing personalized learning home.

Suggested layout:

```text
┌─────────────────────────────────────┐
│ Good morning                        │
│ Here's what to focus on next       │
└─────────────────────────────────────┘

NEXT BEST ACTION
─────────────────
Practice: Integration
Why: Persistent learning gap
[Start]

YOUR LEARNING JOURNEY
─────────────────────
✓ Topic 1 — Mastered
✓ Topic 2 — Mastered
→ Topic 3 — Learning
! Topic 4 — Needs Support
○ Topic 5 — Upcoming

TODAY'S PLAN
─────────────
Learn → Practice → Assess

PROGRESS
────────
Mastered | Improving | Needs Support

RECENT ACTIVITY
───────────────
...
```

The experience should feel like a personalized learning system rather than a collection of administrative pages.

---

# 24. Faculty View

Faculty should be able to understand:

```text
Student
Current Learning State
Recommended Next Action
Reason
Support Needed
```

Faculty may override/recommend an action only where existing permissions allow it.

Do not allow arbitrary changes to authoritative mastery/performance state.

---

# 25. Faculty Intervention

Where appropriate:

```text
Faculty sees:
Persistent gap in Topic X

Suggested:
Human expert support

Faculty action:
Assign intervention / learning session
```

Reuse P0-014 and P0-013.

Do not create another intervention mechanism.

---

# 26. Admin Visibility

Admins may receive aggregate orchestration information:

- students waiting for support
- demand for remedial learning
- topic-level learning bottlenecks
- unresolved learning journeys
- completion trends

Avoid exposing unnecessary individual student details.

---

# 27. API Design

Follow repository conventions.

Possible capabilities:

```text
GET /learning-journey/me
GET /learning-journey/me/next
GET /learning-journey/me/actions
GET /learning-journey/me/progress
POST /learning-journey/me/actions/{id}/start
POST /learning-journey/me/actions/{id}/complete
POST /learning-journey/me/actions/{id}/dismiss
POST /learning-journey/me/actions/{id}/choose

GET /learning-journey/faculty/students
GET /learning-journey/faculty/students/{id}
```

Reuse existing routes when they already expose the required capability.

Do not create duplicate endpoints solely for convenience.

---

# 28. Backend Architecture

A focused service may be introduced:

```text
services/learning_orchestrator.py
```

Possible responsibilities:

- gather authoritative student state
- identify available learning actions
- prioritize actions
- explain recommendations
- create/update journey state
- resolve completed/superseded actions
- select next best action

Keep domain logic in its authoritative service.

For example:

```text
Mastery → P0-015
Learning Gap → P0-012
Remediation → P0-014
Session → P0-013
Analytics/Warning → P0-016
Orchestration → P0-017
```

---

# 29. Data Persistence

Prefer using existing learning-session, assessment, remedial, mastery, and learning-evidence records.

A new persistence model may be introduced only if orchestration state cannot be derived safely.

If needed, a minimal model may store:

```text
student
action
source
status
priority
reason
resource_reference
timestamps
```

Do not duplicate authoritative academic facts.

Do not store another copy of:

- mastery state
- learning gap
- assessment result
- performance score
- remedial status

---

# 30. Personalization Rules

Initial personalization should be deterministic and explainable.

Examples:

```text
IF active remediation
THEN recommend remediation action

IF reassessment eligible
THEN recommend reassessment

IF practice required
THEN recommend adaptive practice

IF topic needs learning
THEN recommend AI lecture / self study

IF topic mastered
THEN recommend next eligible topic

IF early warning ATTENTION_REQUIRED
THEN recommend additional support
```

Do not introduce machine-learning personalization in P0-017.

Future versions may learn from validated historical behavior.

---

# 31. AI Usage

AI may assist with:

- friendly explanation of recommendations
- summarizing the learning journey
- conversationally explaining "why this is my next step"
- transforming structured recommendations into natural language

AI must NOT:

- determine mastery
- determine learning gaps
- override assessment outcomes
- invent prerequisites
- invent deadlines
- invent student performance
- create unauthorized actions
- silently modify academic state

Structured orchestration decisions must remain deterministic.

---

# 32. Notifications

Reuse the existing Notification Engine.

Potential notifications:

```text
NEXT_LEARNING_ACTION_AVAILABLE
REASSESSMENT_READY
REMEDIAL_ACTION_REQUIRED
LEARNING_PLAN_REMINDER
SUPPORT_RECOMMENDED
MASTERY_MILESTONE
```

Avoid notification spam.

Respect existing preferences and recipient rules.

---

# 33. Authorization

Reuse existing authorization and academic-scope utilities.

### Student

Only own learning journey.

### Faculty

Only students within authorized academic scope.

### Admin

Only authorized institutional scope.

Never expose another student's private learning journey.

---

# 34. Frontend UX Principles

The personalized journey should:

- minimize cognitive overload
- clearly show the next step
- explain why
- show progress
- allow reasonable choice
- avoid overwhelming dashboards
- use supportive language
- clearly distinguish required vs recommended actions

Avoid:

- chatbot-only interfaces
- giant text blocks
- unexplained AI recommendations
- excessive popups
- unnecessary gamification

---

# 35. Accessibility

Support:

- keyboard navigation
- readable typography
- sufficient contrast
- clear status labels
- accessible buttons
- screen-reader-friendly action descriptions
- responsive layouts

Do not rely only on color to communicate learning state.

---

# 36. Testing

## Backend

Test:

- next-best-action selection
- action priority
- explainability
- mastery-aware progression
- gap-aware orchestration
- remediation-aware orchestration
- reassessment readiness
- early-warning integration
- action lifecycle
- resume learning
- action completion
- action supersession
- authorization
- no cross-student leakage
- no duplicate academic calculations
- deterministic recommendations
- notification integration

## Frontend

Test/build:

- student journey
- next-best-action card
- journey timeline
- daily plan
- progress
- action start/complete
- resume learning
- faculty view
- responsive layout
- accessibility basics

---

# 37. Regression

Run:

- P0-010
- P0-011
- P0-012
- P0-013.1
- P0-013.2
- P0-013.3
- P0-013.4
- P0-014
- P0-015
- P0-016

P0-017 must not break authoritative engines.

---

# 38. Non-Goals

Do NOT implement:

- new mastery engine
- new performance analyzer
- new learning-gap detector
- new remedial engine
- new assessment engine
- new question-selection engine
- new AI Lecturer engine
- new notification engine
- predictive ML personalization
- autonomous academic decisions
- complex timetable optimizer
- curriculum authoring
- counselling agent
- English communication agent
- unrelated UI redesign
- P0-018+ functionality

---

# 39. Definition of Done

- [ ] Existing P0-010 through P0-016 architecture inspected
- [ ] Personalized learning journey implemented
- [ ] Learning Action model implemented
- [ ] Next Best Action implemented
- [ ] Explainable recommendation implemented
- [ ] Mastery-aware orchestration implemented
- [ ] Learning-gap-aware orchestration implemented
- [ ] Remediation-aware orchestration implemented
- [ ] Reassessment-aware orchestration implemented
- [ ] Early-warning integration implemented
- [ ] Resume-learning behavior implemented
- [ ] Student journey dashboard implemented
- [ ] Faculty journey visibility implemented
- [ ] Existing AI Lecturer/session capabilities reused
- [ ] Existing adaptive practice reused
- [ ] Existing remediation reused
- [ ] Existing assessment/reassessment reused
- [ ] Existing Notification Engine reused
- [ ] Authorization enforced
- [ ] No cross-student data leakage
- [ ] No duplicate academic intelligence engines
- [ ] No opaque AI decision-making
- [ ] Backend tests pass
- [ ] Frontend build/tests pass
- [ ] P0-010 through P0-016 regression passes
- [ ] No secrets introduced
- [ ] No broad unrelated refactoring
- [ ] No P0-018+ functionality introduced

---

# 40. Cursor Execution Rules

Before modifying code:

1. Inspect P0-012 Performance Analyzer and Learning Profile.
2. Inspect P0-013 learning sessions and AI Lecturer.
3. Inspect P0-014 remedial services/routes/models.
4. Inspect P0-015 mastery services/routes/models.
5. Inspect P0-016 analytics/early-warning implementation.
6. Inspect existing course/subject/unit/topic structure.
7. Inspect existing authorization.
8. Inspect existing student dashboard/navigation.
9. Identify reusable actions/routes before adding new APIs.
10. Implement the smallest coherent orchestration layer.

Strictly do NOT:

- recreate mastery calculations
- recreate performance calculations
- recreate learning-gap detection
- recreate remedial grouping
- recreate adaptive practice
- recreate assessment
- create a second notification engine
- create a second authorization framework
- add predictive ML
- introduce opaque AI recommendations
- perform broad refactoring

P0-017 is a **coordination layer over authoritative SYS learning capabilities**.

---

# 41. Required Final Implementation Report

After implementation, report only:

1. Files changed
2. Database/migration changes
3. APIs added/changed
4. Learning Action model
5. Next Best Action logic
6. Personalization rules
7. Student learning journey
8. Faculty visibility/actions
9. AI usage
10. Notification integration
11. Frontend changes
12. Tests executed and results
13. P0-010 through P0-016 regression results
14. Genuine blockers only
