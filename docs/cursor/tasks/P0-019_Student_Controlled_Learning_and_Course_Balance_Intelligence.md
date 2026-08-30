# P0-019 — Student-Controlled Learning, Subject Progression & Course Balance Intelligence

## Objective

Implement the next pilot-critical layer of SYS learning intelligence so that students retain full control over **which subject they study**, while SYS provides intelligent guidance for **topic progression within the selected subject** and monitors **overall course-level subject balance**.

### Core principle

> **Freedom of learning, intelligence of guidance, visibility of risk.**

- The student chooses the subject.
- SYS recommends the best topic order within that subject.
- SYS warns about prerequisite deficiencies without unnecessarily blocking student choice.
- SYS monitors overall course balance and identifies significant subject imbalance.
- Authorized staff receive appropriate visibility and advisory signals.
- SYS must not impose a sequence among subjects.

## 1. Scope

### In scope

1. Student-controlled subject selection.
2. Subject-specific topic progression state.
3. Recommended topic order within a subject.
4. Prerequisite awareness and warnings.
5. Student override of recommended topic selection.
6. Course-level subject progress/balance analysis.
7. Subject imbalance early-warning signals.
8. Student/faculty/coordinator/admin visibility according to authorization.
9. Integration with existing Learning Journey, Mastery, Early Warning, Notifications, Assessment, Remedial Learning, and AI Lecturer services.
10. Pilot-ready UI for subject/topic navigation and course balance.

### Explicitly out of scope

- No forced ordering of subjects.
- No new ML recommendation model.
- No opaque AI risk score.
- No new assessment engine.
- No new mastery engine.
- No new remediation engine.
- No new notification engine.
- No mandatory prerequisite blocking unless an existing authoritative rule already requires it.
- No invented Unit database layer.
- No prerequisite graph for the entire curriculum unless the repository already has sufficient authoritative metadata.
- No implementation of English Communication Agent or Motivation & Support Agent in this task.
- No MS Office/Excel programme implementation in this task.

## 2. Student Subject Freedom

A student enrolled in a course may begin any enrolled subject at any time.

Example:

```text
NEET
├── Physics
├── Chemistry
└── Biology
```

The student may choose:

```text
Physics → Motion
Biology → Genetics
Chemistry → Atomic Structure
Biology → Cell Biology
Physics → Laws of Motion
```

This is valid.

SYS MUST NOT:

- force Physics before Chemistry;
- force Chemistry before Biology;
- rank subjects as a mandatory learning sequence;
- prevent a student from entering another subject because another subject is incomplete;
- create a course-wide linear subject path.

Subject selection remains student-controlled.

## 3. Topic Progression Within a Subject

Once a student chooses a subject, SYS may provide an intelligent recommended topic sequence.

Example:

```text
Physics

1. Units & Measurements       ✓ Mastered
2. Motion                     ✓ Mastered
3. Laws of Motion             ★ Recommended next
4. Work, Energy & Power       → Recommended after #3
5. System of Particles
6. Gravitation
```

Recommendations may consider:

- prerequisite relationships, where authoritative metadata exists;
- demonstrated mastery;
- learning gaps;
- assessment performance;
- practice performance;
- reassessment status;
- topic importance;
- syllabus position;
- historical difficulty/evidence already available in SYS.

The recommendation must be explainable.

Example:

> “Laws of Motion is recommended because Motion is mastered and Laws of Motion is the next prerequisite-supported topic in your Physics learning path.”

## 4. Subject Return / Resume Behavior

Each subject maintains its own independent learning state.

Example:

```text
Day 1:
Physics → Motion

Day 2:
Biology → Genetics

Day 3:
Chemistry → Atomic Structure

Day 4:
Return to Physics
```

When the student returns to Physics, SYS should resume the Physics state and recommend:

```text
Physics
✓ Units & Measurements
✓ Motion
★ Laws of Motion
→ Work, Energy & Power
```

SYS must NOT recommend a subject merely because it is “next” in a course-wide order.

The recommendation is calculated **inside the selected subject**.

## 5. Prerequisite Intelligence

If the student selects a topic whose prerequisite topic(s) are not sufficiently mastered, SYS should identify this.

Example:

```text
Student selects:

Physics → Capacitance
```

If Electric Potential is a prerequisite and mastery is insufficient:

> “You can continue to Capacitance, but Electric Potential is an important prerequisite and your current mastery is low. We recommend reviewing Electric Potential first.”

Provide appropriate options such as:

```text
[ Learn prerequisite first ]
[ Take quick prerequisite check ]
[ Continue to selected topic ]
```

### Important

The default behavior is **advisory, not unnecessarily restrictive**.

Do not invent prerequisite relationships. Use authoritative curriculum metadata when available.

If prerequisite metadata is incomplete:

- explain that SYS cannot establish a prerequisite confidently;
- do not fabricate a dependency;
- continue normal topic guidance.

## 6. Course-Level Subject Balance Intelligence

Student autonomy must not prevent SYS from monitoring overall preparation.

Example:

```text
NEET

Physics       82%  ████████████████
Chemistry     76%  ███████████████
Biology       31%  ██████             ⚠
```

SYS should identify a significant imbalance when evidence indicates that one or more subjects are substantially behind the student’s overall preparation.

Example student-facing message:

> **Course Balance Alert**
>
> You have made strong progress in Physics and Chemistry, but Biology is significantly behind your other NEET subjects. If this imbalance continues, it may affect your overall examination preparation.
>
> Suggested action: consider allocating additional study time to Biology.

This is a recommendation, NOT a command to stop studying another subject.

## 7. Balance Analysis

Do not determine imbalance from a single percentage alone.

Use available authoritative evidence such as:

- topic coverage;
- mastery status;
- mastery confidence/history;
- learning gaps;
- assessment performance;
- practice activity;
- reassessment outcomes;
- recent learning activity;
- course/syllabus coverage;
- subject importance where explicitly configured;
- student’s actual learning choices.

The balance engine should distinguish:

```text
Balanced
WATCH
ATTENTION_REQUIRED
URGENT_ATTENTION
```

Avoid arbitrary hard-coded assumptions when authoritative course data exists.

## 8. Early-Warning Integration

Reuse P0-016 Early Warning infrastructure.

Add an explainable signal such as:

```text
SUBJECT_PROGRESS_IMBALANCE
```

Each signal should follow the existing structure:

```text
code
severity
reason
evidence[]
recommended_action
source_of_truth
```

Do not create a second risk-scoring system.

## 9. Notifications

Reuse the existing Notification Engine.

Possible notification event:

```text
SUBJECT_PROGRESS_IMBALANCE
```

Notifications must be:

- explainable;
- role-aware;
- academic-scope aware;
- non-spammy;
- emitted only when a meaningful signal is newly detected or materially worsens.

Do not notify repeatedly on every dashboard request.

## 10. Role-Based Visibility

### Student

May see:

- enrolled subjects;
- own topic progress;
- recommended topic within the selected subject;
- prerequisite warnings;
- own course balance;
- recommended actions.

Must not see peer performance.

### Subject Expert / Faculty

Within authorized academic scope, may see:

- student subject progress;
- topic mastery;
- subject imbalance signals;
- evidence supporting the signal;
- advisory actions;
- appropriate existing remediation/learning-session/mastery entry points.

Faculty must not directly edit authoritative mastery or assessment facts through this feature.

### Course Coordinator

Within authorized course scope, may see:

- students with subject imbalance;
- subject-level cohort patterns;
- evidence;
- students needing attention;
- advisory support options.

### Admin

Within authorized institution scope, may see:

- course-level imbalance statistics;
- subject-level trends;
- attention counts;
- authorized student-level details.

Follow existing authorization and academic-scope rules.

## 11. Learning Journey Integration

P0-017 Learning Journey remains the orchestration layer.

Example:

```text
My Learning Journey

Course: NEET

Selected Subject: Physics

Recommended next:
→ Laws of Motion

Why:
Motion is mastered and Laws of Motion is the next
recommended Physics topic.

Course balance:
⚠ Biology is significantly behind your Physics/Chemistry progress.
```

If the student selects Biology, the recommendation context switches to Biology.

Do not create a new orchestration engine.

## 12. AI Lecturer Integration

When the student chooses the recommended topic:

```text
Start Learning
    ↓
P0-013 AI Digital Classroom
```

The AI Lecturer receives the selected topic and relevant learning context.

When the student chooses a non-recommended topic:

- allow it;
- provide prerequisite warning when appropriate;
- use the selected topic as the teaching target.

The AI Lecturer must not silently redirect the student to another subject or topic.

## 13. Assessment / Mastery / Remediation Integration

Reuse existing authoritative systems:

```text
Learning
   ↓
Practice
   ↓
Assessment
   ↓
Performance
   ↓
Learning Gap
   ↓
Remediation
   ↓
Reassessment
   ↓
Mastery
```

Topic recommendations must use authoritative states rather than maintain duplicate progress facts.

If a topic becomes mastered through P0-015, the subject recommendation should update accordingly.

If mastery regresses, the recommendation may return to review/practice.

## 14. Recommended Topic Algorithm

Implement deterministic, explainable logic:

```text
1. Identify selected subject.
2. Load topics in that subject.
3. Read authoritative student learning state.
4. Exclude topics already adequately mastered unless review is beneficial.
5. Identify prerequisite deficiencies.
6. Prefer topics whose prerequisites are satisfied.
7. Consider learning gaps and assessment evidence.
8. Consider syllabus/topic importance where available.
9. Produce one primary recommended topic.
10. Produce optional alternative topics.
11. Generate a human-readable reason.
```

The underlying decision must remain deterministic and auditable.

## 15. Subject Balance Algorithm

The balance calculation should be deterministic and explainable.

For each enrolled course:

```text
collect subject-level authoritative progress indicators

compare subjects within the same course

identify substantial persistent divergence

consider:
    coverage
    mastery
    recent activity
    assessment evidence
    learning gaps

generate:
    balance status
    reason
    evidence
    recommended action
```

Avoid treating normal differences as warnings.

## 16. Frontend Requirements

The student course view should make subject autonomy obvious.

Example:

```text
NEET

[ Physics ] [ Chemistry ] [ Biology ]

Selected: Physics

Recommended next topic:
★ Laws of Motion

[ Start Learning ]

Other Physics topics:
- Work, Energy & Power
- System of Particles
- Gravitation

Course Balance:
⚠ Biology is currently behind your other NEET subjects.
```

The interface must NOT visually imply a required subject sequence.

Subject cards/tabs communicate **choice**, not ordering.

## 17. Data Model Guidance

Prefer existing tables and derived state.

If persistence is required, add only minimal fields/tables necessary for:

- prerequisite metadata;
- topic recommendation configuration;
- subject balance policy.

Do not duplicate:

- scores;
- assessment attempts;
- mastery;
- learning gaps;
- remedial status;
- learning evidence.

Before adding a migration, inspect the existing schema carefully.

## 18. API Expectations

Reuse existing routes where possible.

Potential additions should remain narrow, for example:

```text
GET /learning-journey/me/subjects/{subject_id}
GET /learning-journey/me/subjects/{subject_id}/next
GET /analytics/me/courses/{course_id}/balance
```

Exact names may differ if existing API conventions provide a better fit.

Do not duplicate P0-016 analytics or P0-017 orchestration endpoints.

## 19. Testing Requirements

Add deterministic backend tests covering at minimum:

### Subject autonomy

- student can access any enrolled subject;
- no course-wide subject ordering is imposed;
- switching subjects does not alter another subject’s progression state.

### Topic recommendation

- recommended topic is calculated within the selected subject;
- mastered topics are handled correctly;
- prerequisite deficiency produces a warning;
- prerequisite-satisfied topic can become recommended;
- recommendation changes after mastery;
- returning to a subject restores its own recommendation state.

### Override

- student can select a non-recommended topic;
- selected topic becomes the teaching target;
- prerequisite warning remains explainable.

### Course balance

- balanced subjects produce no unnecessary warning;
- persistent subject imbalance produces the appropriate signal;
- evidence supports the signal;
- warning does not force subject switching.

### Authorization

- students see only their own data;
- faculty/coordinator/admin visibility respects existing scope;
- peer data is protected.

### Regression

Run relevant P0-010 through P0-018 tests.

## 20. Frontend Verification

Run:

```text
npm run build
```

Confirm:

- student subject navigation works;
- selected subject state works;
- topic recommendation displays correctly;
- prerequisite warning displays correctly;
- course balance indicator displays correctly;
- existing dashboard and learning journey routes remain functional.

## 21. Acceptance Criteria

P0-019 is complete only when:

- [ ] Students can freely choose any enrolled subject.
- [ ] SYS does not impose a subject order.
- [ ] Each subject maintains independent topic progression.
- [ ] SYS recommends topic order within the selected subject.
- [ ] Recommendation is deterministic and explainable.
- [ ] Prerequisite deficiencies are identified when authoritative metadata exists.
- [ ] Students can override topic recommendations.
- [ ] Returning to a subject restores that subject’s recommendation context.
- [ ] Course-level subject imbalance is detected using meaningful evidence.
- [ ] Imbalance does not remove student autonomy.
- [ ] Student receives an understandable balance warning.
- [ ] Authorized faculty/coordinator/admin can receive appropriate alerts.
- [ ] Existing P0-016 early-warning infrastructure is reused.
- [ ] Existing Notification Engine is reused.
- [ ] P0-017 Learning Journey remains the orchestration layer.
- [ ] P0-013 AI Lecturer remains the teaching execution layer.
- [ ] P0-015 remains the mastery source of truth.
- [ ] No duplicate assessment/mastery/remediation/progress facts are created.
- [ ] No Unit table is invented.
- [ ] No opaque AI risk score is introduced.
- [ ] Backend tests pass.
- [ ] Frontend build passes.
- [ ] P0-010–P0-018 regression passes.
- [ ] No secrets or unrelated changes are introduced.

## 22. Non-Negotiable Product Principles

1. **Student chooses the subject.**
2. **SYS recommends the topic order within the chosen subject.**
3. **SYS may strongly advise a prerequisite but should not unnecessarily block learning.**
4. **Each subject has its own independent learning progression.**
5. **Returning to a subject resumes that subject’s state.**
6. **SYS monitors overall course balance without controlling subject order.**
7. **Warnings are explainable and evidence-based.**
8. **Existing platform engines remain the sources of truth.**
9. **Student autonomy must not be confused with absence of guidance.**
10. **The goal is better examination readiness, not rigid LMS sequencing.**

## 23. Implementation Discipline

Before coding:

1. Inspect the current P0-010–P0-018 implementation.
2. Reuse existing services and schemas wherever possible.
3. Do not redesign completed modules.
4. Do not create duplicate engines.
5. Do not add speculative infrastructure.
6. Keep the implementation pilot-focused.
7. Run focused tests first.
8. Run regression tests.
9. Run frontend production build.
10. Report files changed, migration status, APIs, tests, regression, and blockers.
