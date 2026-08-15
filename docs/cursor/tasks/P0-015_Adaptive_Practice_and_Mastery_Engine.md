# P0-015 — Adaptive Practice & Mastery Engine

## 1. Objective

Implement the SYS Adaptive Practice & Mastery Engine that closes the learning loop:

```text
LEARN
  ↓
PRACTICE
  ↓
ASSESS
  ↓
ANALYZE
  ↓
REMEDIATE
  ↓
REASSESS
  ↓
MASTER
```

P0-015 must determine whether a student has actually achieved mastery of a topic/concept based on assessment and reassessment evidence.

The engine must adapt practice and reassessment according to demonstrated performance while reusing the existing SYS architecture.

### Critical principle

**Mastery is determined by demonstrated competence in reassessment, not by completion of a remedial activity.**

A student may learn through AI Lecturer, self-study, human subject expert, classroom teaching, approved external learning/materials, or combinations of these.

The source of remediation must not, by itself, determine mastery.

---

## 2. Existing Architecture Must Be Reused

Before implementation, inspect and reuse:

- P0-010 Question Intelligence & Selection Engine
- P0-011 Assessment / Answer Key / Explanation architecture
- P0-012 Performance Analyzer
- P0-012 Learning Gap Detection
- P0-012 Student Learning Profile
- P0-012 Notification Engine
- P0-013 learning-session infrastructure
- P0-013.3 COMMON / INDIVIDUAL / HYBRID behavior
- P0-013.4 AI Lecturer Digital Classroom
- P0-014 Intelligent Remedial Learning & Student Group Formation

Do NOT create:

- a second assessment engine
- a second question-selection engine
- a second performance analyzer
- a second learning-gap engine
- a parallel learning-session system
- a second notification system
- a separate student mastery database containing duplicated performance facts
- a second authorization system

Extend existing services/contracts minimally where genuinely required.

---

## 3. Core Learning Loop

```text
Initial Learning
      ↓
Practice
      ↓
Assessment
      ↓
Performance Analysis
      ↓
Learning Gap
      ↓
Remediation
      ↓
Reassessment Eligibility
      ↓
Reassessment
      ↓
Mastery Decision
      ↓
 ┌───────────────┬────────────────────┐
 │ MASTERED      │ GAP PERSISTS       │
 ↓               ↓                    │
Update indicators Further remediation │
Update profile    Adaptive practice   │
Close/reduce gap  Reassessment later  │
                                      │
              ────────────────────────┘
```

P0-015 owns the adaptive practice/mastery decision layer.

P0-012 remains responsible for core performance analysis and learning-gap detection.

P0-014 remains responsible for remedial intervention planning.

P0-013 remains responsible for teaching/session delivery.

---

## 4. Mastery Principle

Incorrect:

```text
Student completed AI remedial lecture
        ↓
MASTERED
```

Correct:

```text
Student received remediation
        ↓
Student practices / prepares
        ↓
Reassessment
        ↓
Performance evidence
        ↓
Mastery criteria satisfied
        ↓
MASTERED
```

A student who learns independently and performs well must be treated equivalently to a student who learned through SYS remediation.

---

## 5. Topic / Concept Mastery

Mastery should be tracked at the most useful existing academic level:

- topic
- concept/skill where supported
- unit as an aggregate indicator
- subject/course as derived aggregates

The system should answer:

- What topics has the student mastered?
- What topics are weak?
- What topics require remediation?
- What topics are improving?
- Which topics were recently reassessed?
- Which topics have persistent gaps?
- What evidence supports the current mastery status?

Do not create unnecessary duplicate academic hierarchy models.

---

## 6. Mastery States

Use existing repository enum/status conventions where available.

Conceptually support:

```text
NOT_ASSESSED
LEARNING
NEEDS_PRACTICE
NEEDS_REMEDIATION
REMEDIATION_IN_PROGRESS
READY_FOR_REASSESSMENT
REASSESSMENT_PENDING
MASTERED
MASTERY_REGRESSED
```

Do not add every state if existing architecture can express the lifecycle more cleanly.

The important distinction is between learning, weakness, remediation, reassessment, and mastery.

---

## 7. Mastery Decision

The mastery decision must be configurable and explainable.

Potential evidence:

- reassessment score
- topic-level performance
- concept-level performance
- question difficulty
- required mastery threshold
- consistency across relevant questions
- recent performance
- prior performance
- assessment validity/quality

Example:

```text
Topic: Binary Tree Traversal
Reassessment: 86%
Mastery threshold: 80%
Relevant questions: 10
Correct: 9
Decision: MASTERED
```

The system must record or reproduce why the mastery decision was made.

Do not use an unexplained AI/LLM decision for mastery.

---

## 8. Configurable Mastery Threshold

Mastery thresholds must not be hard-coded into frontend logic.

Support centrally configurable:

- mastery threshold
- practice threshold
- reassessment threshold

Reuse existing configuration infrastructure where available.

A reasonable default may be defined where required, but it must be centrally configurable.

---

## 9. Reassessment Independence From Remediation Source

A student must be allowed to reach reassessment after learning through any valid route.

Examples:

```text
Learning Gap
    ↓
Self-study
    ↓
Reassessment
    ↓
MASTERED
```

```text
Learning Gap
    ↓
Human subject expert
    ↓
Reassessment
    ↓
MASTERED
```

```text
Learning Gap
    ↓
AI Lecturer remediation
    ↓
Practice
    ↓
Reassessment
    ↓
MASTERED
```

P0-015 must not require completion of P0-014 remediation before reassessment.

---

## 10. Remediation Source

Where appropriate, record the source as evidence/context:

```text
AI_LECTURER
SELF_STUDY
HUMAN_EXPERT
CLASSROOM
EXTERNAL_RESOURCE
MIXED
UNKNOWN
```

Follow repository enum conventions.

**Remediation source MUST NOT influence the mastery decision unless an explicit academic policy later requires it.**

---

## 11. Reassessment Eligibility

Support multiple eligibility pathways, potentially including:

- sufficient practice completed
- intervention completed
- student/self-reported readiness
- teacher approval
- configured waiting period
- sufficient time since previous assessment
- topic remains unresolved

Do not make completed SYS remediation the only pathway.

---

## 12. Reassessment

Reuse P0-010/P0-011 assessment infrastructure.

Reassessment should:

- target unresolved topic/concept
- avoid identical questions where possible
- respect difficulty configuration
- use existing quality/novelty protections
- produce normal assessment evidence
- feed results into P0-012 Performance Analyzer

P0-015 orchestrates reassessment eligibility and mastery evaluation; it does not create a parallel assessment engine.

---

## 13. Adaptive Practice

Adaptive practice should use the existing Question Intelligence Engine.

Selection may consider:

- learning gap
- topic/concept
- previous mistakes
- difficulty
- quality
- novelty
- historical exam relevance
- prerequisite relationships
- recent performance

A deterministic, explainable adaptive strategy is preferred for P0-015.

Do not introduce sophisticated reinforcement learning unless already justified by the repository.

---

## 14. Practice Progression

Conceptually:

```text
Weak understanding
      ↓
Foundational practice
      ↓
Basic application
      ↓
Moderate application
      ↓
Advanced/application questions
      ↓
Reassessment readiness
```

Avoid immediately giving highly difficult questions to students with foundational gaps.

---

## 15. Adaptive Practice Rules

Support explainable rules such as:

```text
Repeated errors
    ↓
reduce difficulty / reinforce prerequisite

Consistent success
    ↓
increase difficulty

Strong performance
    ↓
move toward reassessment

Persistent errors
    ↓
recommend further remediation
```

Example:

```text
Previous practice accuracy: 62%
Current practice accuracy: 81%
Action: Increase difficulty one level
```

---

## 16. Mastery Transition

When reassessment satisfies mastery criteria:

```text
NEEDS_REMEDIATION
        ↓
REASSESSMENT
        ↓
MASTERED
```

Update relevant indicators automatically.

Example:

```text
Before:
Topic: Binary Trees
Mastery: 42%
Status: NEEDS_REMEDIATION
Indicator: RED

After:
Topic: Binary Trees
Mastery: 86%
Status: MASTERED
Indicator: GREEN
Gap: RESOLVED
```

Do not require manual faculty/admin toggling after successful reassessment unless existing academic policy explicitly requires approval.

---

## 17. Failed Reassessment

If mastery criteria are not met:

```text
REASSESSMENT
    ↓
FAIL / INSUFFICIENT EVIDENCE
    ↓
GAP PERSISTS
    ↓
ADAPTIVE PRACTICE OR REMEDIATION
```

The system should:

- retain new evidence
- update mastery indicators
- keep/reopen the learning gap as appropriate
- recommend the next action
- never incorrectly mark mastery

A failed reassessment must not erase historical evidence.

---

## 18. Mastery Regression

Mastery must be capable of changing when later evidence demonstrates meaningful decline.

```text
MASTERED
   ↓
Later assessments show repeated weakness
   ↓
MASTERY_REGRESSED
   ↓
Practice / remediation recommended
```

Do not immediately remove mastery because of a single minor mistake.

Regression rules should be conservative and explainable. If full regression logic is beyond P0-015 scope, implement the data/status foundation and a simple configurable rule.

---

## 19. Learning Indicators

Indicators must reflect authoritative backend state.

Conceptually:

```text
🟢 MASTERED
🟡 LEARNING / DEVELOPING
🟠 NEEDS_PRACTICE
🔴 NEEDS_REMEDIATION
⚪ NOT_ASSESSED
```

Frontend must not calculate mastery independently.

---

## 20. Student Learning Profile

Update the existing P0-012 Student Learning Profile when mastery changes.

Reflect:

- mastered topics
- weak topics
- improving topics
- persistent gaps
- recent reassessments
- mastery trends
- practice history
- relevant evidence

Do not create a second student profile.

---

## 21. Intervention Integration

Consume P0-014 intervention information where available:

```text
P0-012 Learning Gap
        ↓
P0-014 Intervention Plan
        ↓
P0-013 Teaching / Remediation
        ↓
P0-015 Practice + Reassessment
        ↓
Mastery Decision
```

But also support:

```text
Learning Gap
    ↓
Self Study / Human Expert / Classroom
    ↓
P0-015 Reassessment
    ↓
Mastery
```

Therefore P0-015 must not tightly couple reassessment to P0-014.

---

## 22. P0-013 Integration

When practice or reassessment requires an AI Lecturer session, reuse P0-013.

Use:

```text
COMMON
INDIVIDUAL
HYBRID
```

as appropriate and reuse session, activity, participant, visibility, evidence, progress, and Digital Classroom infrastructure.

Do not create another practice-session or lecture-session architecture.

---

## 23. Assessment Integration

Use the existing assessment flow:

```text
Assessment
    ↓
Attempt
    ↓
Evaluation
    ↓
Performance Analyzer
    ↓
Learning Gap / Mastery Engine
```

Do not bypass existing assessment/evaluation infrastructure.

---

## 24. Explainability

Every important adaptive decision must be explainable.

Examples:

```text
Why was this practice question selected?

Because:
- Topic = Binary Trees
- Student previously missed traversal questions
- Current mastery = 58%
- Question difficulty = Basic
```

```text
Why is the student ready for reassessment?

Because:
- Practice accuracy = 84%
- Required readiness = 80%
- Recent trend = improving
```

```text
Why is the topic now mastered?

Because:
- Reassessment score = 86%
- Mastery threshold = 80%
- Relevant questions = 10
- Correct = 9
```

LLM reasoning must not be the authoritative mastery calculation.

---

## 25. Historical Evidence

Preserve the learning history:

```text
Initial assessment
↓
Practice attempts
↓
Remediation
↓
Reassessment
↓
Mastery
↓
Later performance
```

Do not overwrite previous performance records.

Mastery is a current interpretation of accumulated evidence.

---

## 26. Authorization and Privacy

Reuse existing SYS authorization.

### Student

Can:

- view own mastery
- view own practice
- practice assigned topics
- enter eligible reassessment
- view own outcomes

Cannot:

- view another student's mastery/performance
- manipulate mastery state

### Faculty

Can view students within existing academic responsibility and review evidence/outcomes within scope.

### Admin

Uses existing admin authorization.

No new RBAC mechanism.

---

## 27. Notifications

Reuse the existing Notification Engine.

Potential events:

- practice recommended
- reassessment available
- reassessment completed
- topic mastered
- further remediation recommended
- mastery regression detected

Reuse recipient resolution, preferences, email, in-app, audit, and retry.

---

## 28. APIs

Follow existing API conventions and reuse existing endpoints where possible.

Provide equivalent capabilities for:

- get student mastery state
- get topic mastery/evidence
- get adaptive practice recommendation
- start practice
- submit practice evidence
- evaluate practice progress
- check reassessment eligibility
- request/start reassessment
- evaluate reassessment for mastery
- get mastery decision/explanation
- get updated learning indicators
- associate remediation source where appropriate

Do not create duplicate assessment or learning-session endpoints unnecessarily.

---

## 29. Frontend

### Student

Support:

```text
My Learning
    ↓
Topic indicators
    ↓
Weak topic
    ↓
Practice
    ↓
Progress
    ↓
Ready for reassessment
    ↓
Reassessment
    ↓
MASTERED
```

Indicators must visibly change after successful reassessment.

### Faculty/Admin

Extend existing performance UI where practical to show:

- mastery
- topic trends
- reassessment outcomes
- persistent gaps
- mastery changes

Do not create an unrelated dashboard.

---

## 30. Mastery Calculation Architecture

The authoritative calculation must reside in the backend:

```text
Evidence
   ↓
Mastery Policy
   ↓
Mastery Evaluator
   ↓
Mastery State
   ↓
Learning Profile
   ↓
Frontend Indicators
```

The mastery evaluator must be deterministic and testable.

AI/LLM may provide explanations or recommendations, but must not silently override the authoritative mastery policy.

---

## 31. Data Model

Reuse existing assessment/performance/evidence models.

Only introduce new persistence where genuinely required.

Potential entities, only if necessary:

- mastery state/history
- adaptive practice state
- reassessment eligibility state

If mastery history is required, prefer append-only/history-aware records.

Any database change requires:

- Alembic migration
- foreign keys
- indexes
- existing naming conventions
- referential integrity

Do not duplicate assessment or performance facts.

---

## 32. Testing

### Backend

Test at minimum:

- practice recommendation
- topic/gap targeting
- adaptive difficulty
- repeated-error adjustment
- successful practice → reassessment eligibility
- reassessment without SYS remediation
- self-study pathway
- human-expert pathway
- AI Lecturer pathway
- reuse of existing assessment architecture
- successful reassessment → MASTERED
- indicator update
- failed reassessment → gap persists/reopens
- explainable mastery decision
- configurable mastery threshold
- historical evidence preservation
- conservative mastery regression
- authorization boundaries
- student cannot manipulate mastery
- learning profile update
- Notification Engine integration
- P0-013 integration
- no duplicate assessment/session/performance architecture

### Frontend

Test:

- topic mastery indicators
- practice workflow
- reassessment workflow
- successful mastery transition
- failed reassessment
- indicator updates
- student authorization
- faculty/admin visibility
- responsive behavior

### Regression

Run relevant suites from:

- P0-010
- P0-011
- P0-012
- P0-013.1
- P0-013.2
- P0-013.3
- P0-013.4
- P0-014, if available

---

## 33. Non-Goals

Do NOT implement:

- new assessment engine
- new question bank
- new performance analyzer
- new learning-gap engine
- new learning-session system
- new notification system
- full reinforcement learning
- opaque LLM-based mastery decisions
- autonomous curriculum generation
- unrelated counselling/career/English agents
- unrelated UI redesign

Do not turn P0-015 into a generic AI tutor.

---

## 34. Definition of Done

- [ ] Existing P0-010 through P0-014 architecture inspected
- [ ] Existing assessment/question-selection architecture reused
- [ ] Existing Performance Analyzer reused
- [ ] Existing Learning Gap Detection reused
- [ ] Existing Student Learning Profile reused
- [ ] Existing P0-013 learning sessions reused
- [ ] Existing P0-013.4 Digital Classroom reused where applicable
- [ ] Existing P0-014 intervention architecture consumed where available
- [ ] Adaptive practice implemented
- [ ] Practice difficulty adapts based on evidence
- [ ] Reassessment eligibility implemented
- [ ] Reassessment independent of remediation source
- [ ] Self-study reassessment pathway supported
- [ ] Human-expert remediation pathway supported
- [ ] AI remediation pathway supported
- [ ] Mastery evaluation implemented
- [ ] Mastery threshold configurable
- [ ] Mastery decision deterministic and explainable
- [ ] Successful reassessment changes topic state to MASTERED
- [ ] Mastery indicators update automatically
- [ ] Student Learning Profile updates
- [ ] Historical evidence preserved
- [ ] Mastery regression foundation implemented
- [ ] Notification Engine integrated
- [ ] Authorization enforced
- [ ] Backend tests pass
- [ ] Frontend tests/build pass
- [ ] Relevant regression tests pass
- [ ] No duplicate architecture introduced
- [ ] No P0-016+ functionality introduced
- [ ] No secrets introduced
- [ ] No unrelated refactoring performed

---

## 35. Cursor Execution Rule

Work only within P0-015.

Before modifying code:

1. Inspect P0-010 question intelligence and assessment integration.
2. Inspect P0-011 assessment/evaluation flow.
3. Inspect P0-012 performance, learning gaps, learning profile, and notifications.
4. Inspect P0-013.1 through P0-013.4.
5. Inspect P0-014 if already implemented.
6. Identify reusable models, services, schemas, APIs, and UI.
7. Reuse existing authorization and academic-scope mechanisms.
8. Extend existing architecture minimally.

Do not create parallel systems.

Do not implement P0-016 or later functionality.

Do not perform broad refactoring.

Do not replace existing assessment/performance/session architecture.

Keep mastery decisions deterministic, policy-driven, testable, and explainable.

---

## 36. Required Final Implementation Report

After implementation, report only:

1. files changed
2. database/migration changes
3. APIs added/changed
4. adaptive practice capabilities
5. reassessment capabilities
6. mastery evaluation and indicator changes
7. remediation-source handling
8. P0-012/P0-013/P0-014 integrations
9. frontend changes
10. tests executed and results
11. regression results
12. genuine blockers only
