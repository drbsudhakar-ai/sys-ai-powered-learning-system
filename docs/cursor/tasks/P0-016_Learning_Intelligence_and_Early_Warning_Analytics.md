# P0-016 — Learning Intelligence & Early-Warning Analytics

## Objective

Implement the SYS analytics and decision-support layer that converts authoritative outputs from P0-010 through P0-015 into explainable, actionable insights for students, faculty, and administrators.

P0-016 must NOT replace or duplicate the existing Question Intelligence, Assessment, Performance Analyzer, Learning Gap, Remedial, Learning Session, AI Lecturer, Adaptive Practice, Mastery, or Notification engines.

## Architecture

```text
P0-010 Question Intelligence
        ↓
P0-011 Assessment
        ↓
P0-012 Performance + Learning Gaps
        ↓
P0-014 Remediation
        ↓
P0-013 AI Digital Classroom
        ↓
P0-015 Practice + Reassessment + Mastery
        ↓
P0-016 Learning Intelligence
        ↓
   ┌──────┼────────┐
   ↓      ↓        ↓
Student Faculty   Admin
```

P0-016 is an aggregation, trend-analysis, early-warning, and recommendation layer.

### Source of truth

- Question intelligence → P0-010
- Assessment → P0-011
- Performance and learning gaps → P0-012
- Learning sessions / AI Lecturer → P0-013
- Remediation → P0-014
- Practice and mastery → P0-015
- Notifications → existing Notification Engine

Do not independently recalculate authoritative academic state.

---

## 1. Student Learning Intelligence

Provide a student-facing summary of:

- mastered topics
- improving topics
- topics needing practice
- topics needing additional support
- active and resolved learning gaps
- recent assessments
- recent reassessments
- practice progress
- mastery transitions
- actionable recommendations

Example:

```text
Binary Trees
Previous: NEEDS_REMEDIATION
Current: MASTERED
Trend: Improving
```

Use P0-015 mastery state directly. Do not calculate a competing mastery value in the frontend.

---

## 2. Topic Mastery Trends

Consume P0-015 mastery states/events.

Show:

- topic
- current state
- indicator
- recent change
- previous state
- last assessment/reassessment
- evidence summary
- trend over time where supported

If numeric historical mastery data exists, display it. Otherwise derive state transitions from authoritative mastery events without creating a second mastery algorithm.

---

## 3. Learning-Gap Analytics

Consume P0-012 learning-gap data.

Show:

- active gaps
- resolved gaps
- reopened gaps
- persistent gaps
- severity
- gap duration
- topic concentration
- improvement after intervention

Example:

```text
Active gaps: 4
Resolved this cycle: 6
Persistent gaps: 2
Reopened gaps: 1
```

Do not create a new learning-gap detector.

---

## 4. Remediation Effectiveness

Consume P0-014 intervention outcomes and P0-015 reassessment/mastery outcomes.

Support analytics such as:

```text
Gap
 ↓
Intervention
 ↓
Practice
 ↓
Reassessment
 ↓
MASTERED / GAP PERSISTS
```

Possible metrics:

- interventions assigned/completed
- reassessments completed
- mastery after intervention
- persistent gaps
- time from intervention to reassessment
- group vs individual outcomes where data supports comparison

Do not claim causality unless the data supports it. Prefer phrases such as “followed by mastery” or “associated with improvement.”

---

## 5. Learning-Route Analytics

Where remediation-source evidence exists, support:

- SELF_STUDY
- HUMAN_EXPERT
- AI_LECTURER
- CLASSROOM
- MIXED

Possible analytics:

- usage
- reassessment completion
- mastery outcome
- time to reassessment
- improvement trend

Remediation source is contextual evidence only. It must not alter mastery decisions.

Do not rank learning sources as inherently better/worse without sufficient evidence.

---

## 6. Adaptive-Practice Analytics

Consume P0-015 evidence.

Show:

- practice activity
- completion
- accuracy
- difficulty progression
- repeated-error patterns
- readiness for reassessment
- practice-to-reassessment progression

Example:

```text
Practice accuracy:
62% → 71% → 79% → 84%

Action:
Ready for reassessment
```

Do not duplicate P0-015 adaptive-practice logic.

---

## 7. Reassessment Analytics

Show:

- reassessment eligibility
- started/completed reassessments
- mastery outcomes
- failed reassessments
- repeated reassessments
- mastery transitions

Example:

```text
Reassessments: 18
Mastered: 13
Still developing: 5
```

Use P0-015 as the authoritative source.

---

## 8. Learning Consistency

Identify explainable patterns such as:

- consistently strong performance
- improving performance
- unstable performance
- persistent weakness
- repeated assessment difficulty
- improvement followed by regression

Do not label a student at risk based on a single low score.

Use multiple evidence points where available.

---

## 9. Early-Warning Analytics

Implement deterministic, explainable rules.

### Persistent learning gap

```text
Active gap
+
Persists across configured period/cycles
```

→ ATTENTION_REQUIRED

### Repeated assessment difficulty

```text
Repeated below-threshold performance
+
Same topic/concept
```

→ ATTENTION_REQUIRED

### Limited improvement

```text
Remediation completed
+
Practice completed
+
Insufficient improvement
```

→ FURTHER_SUPPORT_RECOMMENDED

### Reassessment failure

```text
Reassessment attempted
+
Mastery criteria not met
```

→ FURTHER_PRACTICE_OR_REMEDIATION

### Regression

```text
Previously MASTERED
+
Later meaningful decline
```

→ REVIEW_RECOMMENDED

### Positive improvement

```text
Prior weakness
+
Repeated improvement
+
Mastery progression
```

→ POSITIVE_PROGRESS

---

## 10. Early-Warning Severity

Use explainable levels where appropriate:

```text
INFO
WATCH
ATTENTION_REQUIRED
URGENT_ATTENTION
```

Do not expose unexplained numeric risk scores.

Every warning must contain evidence/reason.

Example:

```text
ATTENTION_REQUIRED

Reason:
The student has an unresolved topic gap across two
assessment cycles and did not reach the configured
mastery threshold on reassessment.
```

---

## 11. No Opaque AI Risk Score

Do NOT implement unexplained outputs such as:

```text
AI Risk Score = 0.83
```

Any aggregate indicator must be:

- deterministic
- policy-driven
- explainable
- documented
- testable

LLM output may summarize existing evidence but must never override authoritative academic state or invent evidence.

---

## 12. Faculty Analytics

Provide:

### Class overview

- total students
- active learning gaps
- improving students
- students requiring attention
- mastery distribution
- reassessment outcomes
- remediation outcomes

### Topic analytics

For each topic:

```text
Students assessed
Students mastered
Students developing
Students needing remediation
Persistent gap count
Improvement trend
```

### Student attention list

```text
Student
Topic
Current State
Evidence
Reason
Recommended Action
```

Use existing academic-scope authorization.

---

## 13. Faculty Recommendations

Recommendations should consume existing authoritative states.

Examples:

```text
Persistent topic weakness
→ Consider additional subject-expert teaching

Multiple students with the same gap
→ Consider COMMON remedial session

Individual persistent gap
→ Consider INDIVIDUAL intervention

Practice improves but reassessment fails
→ Encourage additional practice

Mastered after intervention
→ No further remediation required
```

Recommendations are advisory unless an existing policy explicitly permits automation.

Do not create another intervention engine.

---

## 14. Admin / Institutional Analytics

Aggregate by authorized scope:

- institution
- campus
- course
- subject
- unit
- topic
- academic period

Metrics may include:

- assessment participation
- mastery distribution
- active learning gaps
- remediation demand
- intervention completion
- reassessment success
- persistent gaps
- topic difficulty patterns
- improvement trends

Do not expose individual student information outside authorized scope.

---

## 15. Authorization and Privacy

Reuse existing SYS authorization.

### Student

Can view:

- own analytics
- own mastery
- own gaps
- own practice
- own reassessment history
- own recommendations

Cannot view another student's data.

### Faculty

Can view only students/classes/subjects within existing academic responsibility.

### Admin

Can view institutionally authorized aggregate analytics.

Do not create a new RBAC system.

Avoid unnecessary personal information and peer-performance exposure.

---

## 16. Historical Trends

Support time-based views where source evidence exists:

- assessment cycles
- academic periods
- recent weeks/months
- before vs after intervention
- mastery transitions

Never fabricate historical values.

---

## 17. Before / After Intervention

Where evidence is sufficient:

```text
Before Intervention
        ↓
Intervention
        ↓
Practice
        ↓
Reassessment
        ↓
After Intervention
```

Example:

```text
Before: 54%
After: 82%
Mastery: NOT_MASTERED → MASTERED
```

Clearly distinguish score change, mastery-state change, and causal claims.

---

## 18. Explainability

Every important insight must be traceable to evidence.

Example:

```text
Insight:
Topic requires attention

Evidence:
- 3 active student gaps
- 2 reassessment failures
- mastery below configured threshold
- persistent across 2 assessment cycles
```

Use supportive student-facing language:

- “Needs additional support”
- “Still developing”
- “Practice recommended”

Avoid stigmatizing labels.

---

## 19. Student Recommendations

Examples:

```text
MASTERED
→ Continue to next topic

NEEDS_PRACTICE
→ Start adaptive practice

READY_FOR_REASSESSMENT
→ Take reassessment

REASSESSMENT_FAILED
→ Continue targeted practice

PERSISTENT_GAP
→ Consider remedial learning

IMPROVING
→ Continue current learning path
```

Reuse P0-014/P0-015 capabilities rather than implementing them again.

---

## 20. Notifications

Reuse the existing Notification Engine.

Potential events:

- important learning attention signal
- reassessment reminder
- persistent learning gap
- positive mastery milestone
- improvement milestone
- faculty attention summary

Respect existing recipient resolution, preferences, email/in-app delivery, audit, and retry.

Do not create another notification service.

---

## 21. APIs

Follow repository conventions and reuse existing endpoints where equivalent functionality already exists.

Possible capabilities:

```text
GET /analytics/me
GET /analytics/me/topics
GET /analytics/me/trends
GET /analytics/me/attention

GET /analytics/faculty/overview
GET /analytics/faculty/topics
GET /analytics/faculty/students
GET /analytics/faculty/attention
GET /analytics/faculty/interventions

GET /analytics/admin/overview
GET /analytics/admin/courses
GET /analytics/admin/subjects
GET /analytics/admin/trends
GET /analytics/admin/attention
```

Support appropriate filters:

- course
- subject
- unit
- topic
- academic period
- date range

Authorization must be applied before returning data.

Do not create duplicate routes unnecessarily.

---

## 22. Backend Architecture

A focused analytics layer may be introduced if consistent with the repository:

```text
services/learning_analytics.py
services/early_warning.py
```

Possible responsibilities:

### Learning Analytics

- aggregate authoritative data
- calculate trends
- compare periods
- summarize outcomes

### Early Warning

- evaluate deterministic rules
- generate evidence-backed signals
- assign explainable severity
- produce recommended actions

Keep mastery calculation in P0-015 and performance/gap detection in P0-012.

---

## 23. Early-Warning Configuration

Where thresholds are required, prefer configuration over hard-coding.

Potential policies:

- consecutive below-threshold assessments
- persistence duration
- minimum improvement
- reassessment failure count
- regression trigger
- minimum evidence count

Reuse existing configuration patterns.

Do not create excessive configuration without a real requirement.

---

## 24. Frontend — Student

Extend the existing student learning experience.

Suggested structure:

```text
My Learning Intelligence

Overall Learning Progress
Mastered Topics
Improving Topics
Needs Practice
Needs Support
Learning Trends
Attention / Recommendations
Recent Reassessments
Learning Journey
```

Indicators must come from backend authoritative state.

---

## 25. Frontend — Faculty

Suggested structure:

```text
Learning Intelligence

Class Overview
Topic Analytics
Student Attention
Mastery Trends
Remediation Effectiveness
Reassessment Outcomes
Recommendations
```

Provide useful filtering without unnecessary dashboard complexity.

---

## 26. Frontend — Admin

Suggested structure:

```text
Institution Learning Intelligence

Overall KPIs
Mastery Distribution
Learning Gap Trends
Remediation Demand
Reassessment Outcomes
Course / Subject Trends
Attention Signals
```

Aggregate views should be the default.

---

## 27. Visualization

Use visualizations only where they improve understanding.

Appropriate:

- trend charts
- mastery distributions
- topic heatmaps
- intervention outcome charts
- status cards
- progress indicators

Avoid:

- decorative charts
- misleading 3D charts
- excessive dashboard widgets
- unsupported precision

P0-016 is an analytics task, not a visual-effects task.

---

## 28. AI Usage

AI may optionally assist with:

- natural-language summaries of existing analytics
- student/faculty-friendly explanations
- recommendation wording

AI must NOT:

- override mastery
- invent performance data
- invent learning gaps
- invent warning evidence
- silently change severity
- make unauthorized academic decisions

Authoritative analytics must remain deterministic and testable.

---

## 29. Performance

Avoid N+1 database queries.

Use:

- scoped joins
- aggregation queries
- indexes
- pagination
- appropriate filtering

Do not build an analytics warehouse unless genuinely required.

If summary/materialized data becomes necessary, document the source of truth and refresh strategy.

---

## 30. Database / Migration

Prefer **no migration** if existing authoritative data is sufficient.

Only add persistence for a demonstrated need such as:

- expensive computed summaries
- historical analytics unavailable from source records
- verified performance requirements

If migration is required:

- use Alembic
- follow repository conventions
- add indexes
- preserve foreign keys
- document source-of-truth ownership
- avoid duplicating P0-012/P0-014/P0-015 facts

---

## 31. Testing

### Backend

Test at minimum:

- student analytics
- faculty analytics
- admin analytics
- authorization boundaries
- topic aggregation
- mastery trend aggregation
- learning-gap aggregation
- remediation effectiveness
- reassessment outcomes
- before/after comparisons
- persistent-gap warning
- repeated-failure warning
- limited-improvement warning
- reassessment-failure warning
- regression warning
- positive improvement signal
- warning severity
- explainability/evidence
- configurable thresholds
- no duplicate mastery calculation
- no duplicate performance calculation
- notification integration
- pagination/filtering
- no cross-student data leakage

### Frontend

Verify:

- student dashboard
- faculty dashboard
- admin dashboard
- filters
- trends
- topic indicators
- attention signals
- recommendations
- authorization behavior
- responsive layout

---

## 32. Regression

Run relevant suites from:

- P0-010
- P0-011
- P0-012
- P0-013.1
- P0-013.2
- P0-013.3
- P0-013.4
- P0-014
- P0-015

P0-016 must not break any existing authoritative engine.

---

## 33. Non-Goals

Do NOT implement:

- new assessment engine
- new question-selection engine
- new performance analyzer
- new learning-gap detector
- new mastery engine
- new remedial engine
- new learning-session engine
- new notification engine
- opaque AI risk scoring
- predictive student-failure model
- dropout prediction
- autonomous academic decisions
- curriculum-generation system
- counselling agent
- English communication agent
- unrelated UI redesign
- analytics data warehouse

Predictive ML may be considered later after sufficient validated historical data exists.

---

## 34. Definition of Done

- [ ] P0-010 through P0-015 architecture inspected
- [ ] Student analytics implemented
- [ ] Faculty analytics implemented
- [ ] Admin analytics implemented
- [ ] Topic mastery trends implemented
- [ ] Learning-gap trends implemented
- [ ] Remediation effectiveness implemented
- [ ] Reassessment analytics implemented
- [ ] Practice progression analytics implemented
- [ ] Explainable early-warning rules implemented
- [ ] Early-warning severity implemented
- [ ] Evidence/reason supplied for every warning
- [ ] Recommendations implemented
- [ ] Existing Notification Engine reused where appropriate
- [ ] Academic-scope authorization enforced
- [ ] No cross-student data leakage
- [ ] No duplicate mastery/performance/gap engines
- [ ] No opaque AI risk score
- [ ] No unsupported causal claims
- [ ] Backend tests pass
- [ ] Frontend build/tests pass
- [ ] P0-010 through P0-015 regression passes
- [ ] No secrets introduced
- [ ] No broad unrelated refactoring
- [ ] No P0-017+ functionality introduced

---

## 35. Cursor Execution Rules

Before modifying code:

1. Inspect P0-012 Performance Analyzer and Learning Profile.
2. Inspect P0-014 remedial models/services/routes.
3. Inspect P0-015 mastery models/services/routes.
4. Inspect existing assessment/question-intelligence services.
5. Inspect authorization and academic-scope utilities.
6. Inspect existing dashboards/components.
7. Identify reusable APIs and aggregation patterns.
8. Implement the smallest coherent analytics layer.

Strictly do not:

- recreate mastery calculations
- recreate performance analysis
- recreate learning-gap detection
- recreate remedial grouping
- recreate adaptive practice
- create a second notification engine
- create a second authorization system
- add predictive ML
- introduce LLM-based risk scoring
- perform broad refactoring

P0-016 is a **read/aggregate/analyze/advise layer over authoritative SYS learning data**.

---

## 36. Required Final Implementation Report

After implementation, report only:

1. Files changed
2. Database/migration changes
3. APIs added/changed
4. Student analytics capabilities
5. Faculty analytics capabilities
6. Admin analytics capabilities
7. Early-warning rules
8. Explainability/evidence approach
9. Recommendation logic
10. Notification integration
11. Frontend changes
12. Tests executed and results
13. P0-010 through P0-015 regression results
14. Genuine blockers only
