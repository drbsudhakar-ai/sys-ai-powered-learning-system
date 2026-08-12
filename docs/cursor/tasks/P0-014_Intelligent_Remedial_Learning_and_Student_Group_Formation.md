# P0-014 — Intelligent Remedial Learning & Student Group Formation

## 1. Objective

Implement the SYS Intelligent Remedial Learning layer that converts identified learning gaps into actionable remedial interventions.

The system must:

1. consume learning-gap and performance intelligence already produced by P0-012
2. identify students with sufficiently similar learning gaps
3. form explainable remedial learning groups where appropriate
4. generate an intervention plan for each student/group
5. connect the intervention plan to the existing AI Lecturer learning-session infrastructure
6. track remedial participation and outcomes
7. notify appropriate users through the existing Notification Engine where required

This task must build on existing SYS architecture rather than creating parallel performance, notification, student, course, or learning-session systems.

---

# 2. Core Learning Flow

The target flow is:

```text
Assessment Results
        ↓
Performance Analyzer
        ↓
Learning Gap Detection
        ↓
Learning Gap Profile
        ↓
Gap Similarity / Clustering
        ↓
Remedial Group Formation
        ↓
Intervention Planning
        ↓
AI Lecturer Learning Session
        ↓
Practice / Reassessment
        ↓
Updated Performance
        ↓
Remedial Outcome
```

P0-014 is primarily responsible for the middle section:

```text
Learning Gaps
    ↓
Grouping
    ↓
Intervention Planning
    ↓
Learning Session Assignment
```

Do not implement the complete adaptive mastery engine planned for P0-015.

---

# 3. Existing Architecture Must Be Reused

Before implementation, inspect and reuse:

- P0-012 Performance Analyzer
- Learning Gap Detection
- Student Learning Profile
- Trend Analysis
- Exam Readiness
- Notification Engine
- P0-013 learning-session infrastructure
- P0-013.3 COMMON / INDIVIDUAL / HYBRID behavior
- P0-013.4 AI Lecturer Digital Classroom layer, where already available
- existing student/course/subject/unit/topic models
- existing authorization and academic-scope rules

Do NOT create:

- a second performance analyzer
- a second learning-gap engine
- a second notification system
- a parallel student grouping architecture
- a parallel learning-session model
- a second authorization system

Extend existing services/contracts only where genuinely necessary.

---

# 4. Learning Gap Model

A remedial gap should be represented using existing performance intelligence.

A gap may include, as applicable:

- student
- course
- subject
- unit
- topic
- skill/concept
- gap category
- severity
- confidence/evidence
- source assessment(s)
- detected timestamp
- current status
- intervention status

Use the existing P0-012 learning-gap representation wherever possible.

Do not duplicate the same learning-gap facts into a new independent analytics model.

---

# 5. Gap Severity

Use existing P0-012 severity semantics if available.

If a classification is required, the system should distinguish at least conceptually between:

- low
- moderate
- high
- critical

The implementation must remain explainable.

For every remedial recommendation, the system should be able to explain:

```text
Why was this student selected?
Why was this topic selected?
Why was this intervention selected?
Why were these students grouped together?
```

Do not use an opaque clustering result with no explanation.

---

# 6. Student Group Formation

The system should identify students whose learning gaps are sufficiently similar for a common remedial intervention.

Potential grouping dimensions include:

- course
- subject
- unit
- topic
- concept/skill
- gap category
- severity range
- learning objective
- academic scope

Grouping must respect academic boundaries.

Students must not be grouped merely because their raw scores are similar.

The primary grouping signal should be **learning-gap similarity**.

---

# 7. Grouping Rules

The grouping engine should support:

### Common Remedial Group

Multiple students share sufficiently similar gaps.

```text
Student A ─┐
Student B ─┼── Topic X gap ──→ Remedial Group
Student C ─┘
```

### Individual Remediation

A student has a unique or sufficiently different gap.

```text
Student D
   ↓
Individual Remedial Intervention
```

### Mixed Situation

A student may participate in:

- one common remedial group for shared gaps
- individual remediation for unique gaps

Do not force every student into a group.

---

# 8. Group Similarity

Implement an explainable similarity mechanism.

The exact algorithm should follow the existing technology stack and remain replaceable.

Possible conceptual signals:

```text
Topic overlap
+ Concept overlap
+ Gap category overlap
+ Severity compatibility
+ Learning objective overlap
+ Course/subject compatibility
```

The implementation must expose enough information to explain the grouping decision.

Avoid introducing a heavyweight ML clustering dependency unless the repository already requires it.

A deterministic/rule-based baseline is acceptable for P0-014 if it is designed so that a more advanced clustering strategy can be introduced later.

---

# 9. Group Lifecycle

A remedial group should have a clear lifecycle, for example:

```text
PROPOSED
   ↓
APPROVED / ACTIVATED
   ↓
IN_PROGRESS
   ↓
COMPLETED
   ↓
EVALUATED
```

The exact enum should follow existing repository conventions.

The system should support:

- creation
- activation
- participant membership
- intervention assignment
- progress tracking
- completion
- evaluation

Avoid unnecessary workflow complexity.

---

# 10. Academic Scope and Authorization

All grouping and intervention operations must respect existing SYS authorization.

At minimum:

- students can view their own remedial assignments/groups where permitted
- students cannot access another student's private remedial information
- faculty can access groups within their academic responsibility
- admins can access according to existing admin scope
- grouping must never cross unauthorized academic boundaries

Do not expose sensitive performance details to students about other students.

A student-facing group view should reveal only the information necessary for participation.

---

# 11. Intervention Planning

For each remedial group or individual intervention, generate an explainable intervention plan.

The plan should identify:

- target topic/concept
- learning gap
- learning objective
- intervention type
- recommended sequence
- estimated learning scope
- prerequisite concepts where applicable
- success criteria
- reassessment requirement

Possible intervention types:

- AI Lecturer explanation
- visual explanation
- 3D visualization where educationally useful
- worked example
- guided practice
- targeted assessment
- individual explanation
- group remedial lecture

The plan must use the existing P0-013 learning-session architecture.

Do NOT create a separate remedial lecture/session system.

---

# 12. Integration With AI Lecturer

P0-014 should generate the **remedial teaching intent/context** consumed by the existing AI Lecturer.

Conceptually:

```text
Learning Gap
    ↓
Intervention Plan
    ↓
AI Lecturer Session
    ↓
Digital Classroom
    ↓
Animated / 2D / 3D Teaching
```

The AI Lecturer should receive relevant context such as:

- target topic
- identified gap
- learning objective
- prerequisite weakness
- intervention goal
- student/group context
- appropriate difficulty/context

The remedial engine should not implement the Digital Classroom itself.

P0-013 remains responsible for the teaching-session experience.

---

# 13. Group Session Mode

Use the existing P0-013 session modes.

For shared gaps:

```text
COMMON
```

should normally be preferred.

For unique student gaps:

```text
INDIVIDUAL
```

should normally be used.

Where shared and individual remediation are combined:

```text
HYBRID
```

may be used.

Reuse the P0-013.3 participant, activity, visibility, evidence, and progress architecture.

Do not create another grouping/session implementation.

---

# 14. Intervention Prioritization

When a student has multiple learning gaps, prioritize interventions using existing performance intelligence.

Potential factors:

- severity
- foundational/prerequisite importance
- frequency of errors
- recency
- assessment importance
- topic priority
- dependency on other concepts
- exam relevance

The priority decision must be explainable.

Example:

```text
Priority 1:
High-severity prerequisite gap in Topic A

Priority 2:
Moderate gap in Topic B

Priority 3:
Low-severity gap in Topic C
```

Do not implement full adaptive mastery logic from P0-015.

---

# 15. Intervention Status

Track intervention state independently from the underlying learning gap.

Conceptually:

```text
Learning Gap:
OPEN

Intervention:
ASSIGNED

Session:
IN_PROGRESS

Outcome:
PENDING
```

After intervention:

```text
Learning Gap:
IMPROVING / RESOLVED / PERSISTING

Intervention:
COMPLETED

Outcome:
EVALUATED
```

Use existing models/status conventions where available.

---

# 16. Reassessment Integration

P0-014 should define the requirement for reassessment but must not implement the full P0-015 mastery engine.

The system should be able to record:

- intervention completed
- reassessment required
- reassessment completed
- gap status after reassessment

The actual adaptive mastery progression belongs to P0-015.

---

# 17. Notification Integration

Use the existing unified Notification Engine.

Possible notifications include:

- remedial intervention assigned
- student added to remedial group
- remedial session scheduled/available
- intervention completed
- reassessment required
- intervention outcome available

Use existing:

- recipient resolution
- preferences
- academic-scope authorization
- email
- in-app
- audit/retry

Do NOT create notification-specific tables/services outside the existing Notification Engine unless an existing capability genuinely requires a minimal extension.

---

# 18. API Requirements

Follow existing API naming/versioning conventions.

Provide the equivalent of:

- identify eligible learning gaps for remediation
- generate/view remedial group proposals
- create/activate remedial group
- view group participants within authorization scope
- create/view intervention plan
- assign intervention
- view student remedial assignments
- update intervention status
- record intervention completion
- mark reassessment required

Do not expose internal clustering implementation details unnecessarily.

All APIs must use existing authentication and authorization dependencies.

---

# 19. Frontend Requirements

Provide the minimum UI required to make P0-014 operational.

### Faculty/Admin

Support:

- learning-gap overview
- remedial group proposals
- grouping rationale
- group activation
- intervention plan review
- participant list
- intervention status
- reassessment status

### Student

Support:

- own remedial assignments
- target topic/concept
- why the intervention was assigned, in student-friendly language
- scheduled/available remedial session
- intervention status
- reassessment status

Do not expose other students' performance details.

Do not create a large new dashboard if an existing performance UI can be extended.

---

# 20. Explainability

Every automatically generated remedial group/intervention should have an explanation.

Example:

```text
Group reason:
Students share a high-severity learning gap in
"Binary Tree Traversal".

Common evidence:
- repeated errors in traversal questions
- same topic identified by Learning Gap Detection
- compatible academic scope
- compatible intervention objective
```

The explanation should be stored or reproducibly generated from the underlying evidence.

Do not present unexplained AI decisions.

---

# 21. Data Model

Reuse existing models wherever possible.

Only introduce new entities where the repository genuinely lacks the required capability.

Potential entities, only if required:

- remedial group
- remedial group membership
- intervention plan
- intervention status/outcome

If database changes are necessary:

- create Alembic migration
- use foreign keys
- add appropriate indexes
- preserve referential integrity
- respect existing naming conventions
- avoid duplicated analytics facts

---

# 22. Tests

### Backend

Test at minimum:

- learning gaps can be selected for remediation
- grouping uses learning-gap similarity
- unrelated students are not incorrectly grouped
- academic boundaries are respected
- individual remediation is supported
- common remediation is supported
- hybrid remediation uses existing session infrastructure
- grouping rationale is generated
- intervention plan is created
- intervention priority is explainable
- unauthorized users cannot access groups/interventions
- student cannot see another student's private performance information
- intervention status changes correctly
- reassessment requirement can be recorded
- notification engine integration uses existing service
- no duplicate session/activity model is created

### Frontend

Test:

- faculty/admin remedial workflow
- student remedial assignment view
- grouping rationale display
- intervention status
- authorization/error handling

Run relevant regression suites from:

- P0-010
- P0-011
- P0-012
- P0-013.1
- P0-013.2
- P0-013.3
- P0-013.4, if available

---

# 23. Non-Goals

Do NOT implement:

- P0-015 adaptive mastery engine
- full adaptive practice engine
- automatic mastery scoring
- advanced reinforcement-learning algorithms
- new authentication/RBAC system
- new Notification Engine
- new Performance Analyzer
- new Learning Gap Detection engine
- new learning-session architecture
- unrelated analytics dashboards
- unrelated UI redesign

---

# 24. Definition of Done

- [ ] Existing P0-012 learning-gap/performance architecture inspected
- [ ] Existing P0-013 session architecture inspected
- [ ] P0-013.3 COMMON/INDIVIDUAL/HYBRID behavior reused
- [ ] Learning-gap selection implemented
- [ ] Explainable similarity/grouping implemented
- [ ] Common remedial groups supported
- [ ] Individual remediation supported
- [ ] Hybrid remediation supported where required
- [ ] Academic-scope authorization enforced
- [ ] Remedial group lifecycle implemented
- [ ] Intervention planning implemented
- [ ] Intervention prioritization implemented
- [ ] AI Lecturer integration implemented through existing session architecture
- [ ] Existing Notification Engine integrated
- [ ] Student remedial view implemented
- [ ] Faculty/admin remedial management implemented
- [ ] Reassessment requirement supported without implementing P0-015 mastery
- [ ] Database migration added only if genuinely required
- [ ] Backend tests pass
- [ ] Frontend tests/build pass
- [ ] Relevant P0 regression tests pass
- [ ] No duplicate session/activity/performance/notification architecture introduced
- [ ] No secrets introduced
- [ ] No P0-015 functionality introduced
- [ ] No unrelated refactoring performed

---

# 25. Cursor Execution Rule

Work only within **P0-014**.

Before modifying code:

1. Inspect P0-012 Performance Analyzer and Learning Gap Detection.
2. Inspect the existing Notification Engine.
3. Inspect P0-013.1 through P0-013.3.
4. Inspect P0-013.4 if it is already implemented.
5. Identify reusable services, schemas, models, APIs, and frontend components.
6. Reuse existing authorization and academic-scope mechanisms.
7. Extend existing architecture minimally.

Do not create parallel implementations.

Do not implement P0-015.

Do not perform broad refactoring.

Do not ask for confirmation for routine implementation decisions already determined by the repository architecture.

Leave the repository in a testable state.

---

# 26. Required Final Report

Keep the implementation report concise.

Report only:

1. files changed
2. database/migration changes
3. APIs added/changed
4. remedial grouping/intervention capabilities implemented
5. AI Lecturer integration
6. Notification integration
7. frontend components/pages changed
8. tests executed and results
9. regression results
10. any genuine blocker

Do not provide a long architectural explanation after implementation.
