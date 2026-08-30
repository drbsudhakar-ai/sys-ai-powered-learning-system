# P0-018 — Course & Programme Foundation Alignment

## Objective

Align the existing SYS implementation with the clarified product vision without redesigning or destabilizing the working P0-010–P0-017 foundation.

SYS is a unified AI-powered platform for:

- Higher-education entrance examination preparation
- Government/employment examination preparation
- Independent English Communication learning
- Universal student Motivation & Support
- Future career/technical skill development

For SYS, **Course means a goal-oriented preparation/learning programme**, not necessarily a conventional academic degree course.

The existing learning hierarchy remains:

**Course → Subject → Unit → Topic**

This task is a targeted foundation-alignment task. Do not rebuild working modules.

---

# 1. Core Product Model

## 1.1 Course definition

Treat a SYS Course as a structured programme directed toward a defined learning, examination, admission, employment, or skill-development goal.

Examples:

- NEET
- JEE
- CUET
- GATE CSE
- PGCET
- LAWCET
- ICET
- SSC
- Banking
- State Government Group examinations
- Police recruitment examinations
- Future technical skill programmes

A course may contain:

```text
Course
  └── Subject
       └── Unit
            └── Topic
```

Do not introduce an additional Exam → Course hierarchy unless the existing implementation proves it is necessary.

---

# 2. Course Classification

Inspect the existing Course model/API/UI and add the minimum metadata necessary to distinguish programme categories.

Preferred classification values:

- `HIGHER_EDUCATION_ENTRANCE`
- `EMPLOYMENT_EXAM`
- `INDEPENDENT_LEARNING`
- `SKILL_DEVELOPMENT`

If the repository already has an equivalent classification mechanism, reuse it instead of creating a duplicate.

The classification must not break existing course records or APIs.

For exam-oriented courses, allow useful metadata such as:

- examination name
- examination authority/organization where applicable
- target purpose
- active/inactive state

Do not over-model external examination authorities unless required by the existing implementation.

---

# 3. Enrollment Model

Verify and align enrollment behavior so that:

### Supported

1. Student enrolled in one preparation course.
2. Student enrolled in multiple courses.
3. Student enrolled only in an independent programme.
4. Authorized student with no course enrollment.
5. Student enrolled in an examination course plus English Communication.
6. Student enrolled in multiple examination/learning programmes.

### Important rule

**Course enrollment must not be required for a student to exist as an authorized SYS student or to access universal student services.**

Do not break existing authorization or academic-scope boundaries.

---

# 4. English Communication

Treat English Communication as an independent SYS learning programme.

It must be possible for an authorized student to enroll in English Communication without enrolling in:

- NEET
- JEE
- CUET
- GATE
- SSC
- Banking
- or any other examination course.

Do not implement the complete English Communication Agent in this task.

Only ensure that the platform foundation can represent English Communication correctly as an independent programme.

The future English Communication MVP will be implemented separately.

---

# 5. Motivation & Support

Confirm that the platform-wide Motivation & Support capability is not dependent on course enrollment.

An authorized student should be able to access it when:

- enrolled in a course;
- enrolled only in English Communication;
- enrolled in another independent programme;
- or currently enrolled in no course.

The service must continue to respect authentication, authorization, student privacy, and existing notification/security rules.

Do not implement a new Motivation Agent in this task.

---

# 6. Existing Learning Intelligence Compatibility

P0-018 must preserve reuse of the existing SYS learning intelligence stack:

- P0-010 Question Intelligence & Assessment
- P0-011 Answer Key / Explanation
- P0-012 Performance Analyzer & Notification Engine
- P0-013 Learning Sessions & AI Lecturer
- P0-014 Remedial Learning
- P0-015 Adaptive Practice & Mastery
- P0-016 Learning Intelligence & Early Warning Analytics
- P0-017 Personalized Learning Journey & Orchestration

Do not duplicate:

- assessment facts
- question-bank facts
- performance facts
- learning gaps
- remedial status
- mastery states/events
- learning-session state
- analytics aggregates
- learning-journey actions

Existing services remain the authoritative source of their respective data.

---

# 7. Terminology Alignment

Inspect user-facing terminology and correct only terminology that incorrectly implies a conventional college-degree LMS.

Preferred concepts:

- Course / Preparation Course
- Learning Programme
- Subject
- Unit
- Topic
- Learning Session
- Learning Journey
- English Communication
- Motivation & Support

Avoid introducing unnecessary terminology changes throughout the application.

Do not perform a broad UI redesign.

---

# 8. Dashboard / Navigation Alignment

Review existing student and admin navigation.

Where practical, ensure the information architecture can distinguish:

### Student

- My Courses / Preparation
- My Learning Programmes
- English Communication
- Learning Journey
- My Performance / Insights
- Motivation & Support

Do not create empty pages merely to satisfy navigation.

If a feature is not yet implemented, preserve existing working navigation and add only the minimum foundation required.

---

# 9. Data Migration / Backward Compatibility

Inspect existing Course records and migrations.

Requirements:

- Existing courses must remain valid.
- Existing course → subject → unit → topic relationships must remain valid.
- Existing enrollments must remain valid.
- Existing assessment/session/mastery/remedial references must remain valid.
- No destructive migration.
- Provide sensible defaults for any newly required course metadata.
- No duplicated tables representing the same concepts.

If no schema change is actually necessary, do not create a migration.

---

# 10. Authorization

Preserve existing authorization rules.

Course classification must never weaken:

- role authorization
- academic scope
- student enrollment boundaries
- faculty responsibility boundaries
- admin permissions

Students must only access their own authorized course/programme data.

Faculty/managers must only access students/programmes within their authorized scope.

---

# 11. Future Extensibility

The implementation should allow future programmes such as:

```text
MS Office
MS Excel
Advanced Excel
Data Analysis
Interview Skills
Digital Skills
```

but **do not implement these programmes now**.

Do not create sample production data for future programmes unless required by tests.

---

# 12. Pilot Scope Boundary

This task is explicitly NOT intended to implement:

- full conventional LMS functionality
- MS Office/Excel courses
- complete English Communication Agent
- complete Motivation & Support Agent
- career marketplace
- prerequisite graph
- ML-based course recommendation
- new assessment engine
- new mastery engine
- new learning-session engine
- new notification engine
- new analytics engine

Reuse existing infrastructure.

---

# 13. Required Investigation Before Modification

Before changing code:

1. Inspect the current Course model.
2. Inspect Course CRUD APIs.
3. Inspect course enrollment/relationship implementation.
4. Inspect course-related authorization.
5. Inspect existing student dashboards.
6. Inspect P0-017 learning journey assumptions about courses.
7. Inspect English/learning-programme related existing structures.
8. Identify the minimum set of changes required.

Do not make speculative architectural changes.

---

# 14. Implementation Requirements

Implement only changes justified by the investigation.

Potential changes may include:

- Course classification field/enum
- Minimal course metadata
- API/schema support
- validation
- backward-compatible migration if required
- student programme visibility
- terminology adjustments
- authorization corrections
- tests

If the current implementation already satisfies a requirement, leave it unchanged.

---

# 15. Tests

Add or update backend tests covering at minimum:

### Course classification

- Create supported course categories.
- Retrieve classification.
- Update classification where permitted.
- Invalid classification rejected.

### Enrollment

- Student can have multiple courses/programmes.
- Student can have no course enrollment.
- Existing enrollment behavior remains valid.

### English Communication

- Independent programme can exist.
- Student can access it without an examination course.

### Universal Support

- Authorized student without course enrollment can access the existing universal support entry point, if such an entry point already exists.
- Do not create the full support agent here.

### Authorization

- Unauthorized student cannot access another student's programme data.
- Faculty scope remains enforced.
- Existing admin/faculty permissions remain intact.

### Regression

Run relevant existing suites from P0-010 through P0-017.

---

# 16. Frontend Verification

Run:

```text
npm run build
```

Verify that existing routes continue to compile.

Do not introduce unnecessary frontend dependencies.

Do not perform a visual redesign.

---

# 17. Database

If schema changes are required:

1. Create one focused Alembic migration.
2. Preserve all existing data.
3. Use backward-compatible defaults.
4. Verify `alembic upgrade head`.
5. Verify existing course/enrollment records.

If no database change is necessary, explicitly report:

**No migration required.**

---

# 18. Acceptance Criteria

P0-018 is complete when:

- [ ] SYS Course is clearly represented as a goal-oriented programme.
- [ ] Higher-education entrance courses are supported.
- [ ] Employment examination courses are supported.
- [ ] Independent learning programmes are supported.
- [ ] Future skill-development programmes are structurally supported.
- [ ] Existing Course → Subject → Unit → Topic hierarchy remains intact.
- [ ] Students may have zero, one, or multiple programme enrollments.
- [ ] English Communication can exist independently of exam courses.
- [ ] Universal student support does not depend on course enrollment.
- [ ] Existing authorization boundaries remain intact.
- [ ] Existing P0-010–P0-017 data/services are reused.
- [ ] No duplicate learning intelligence or assessment systems are introduced.
- [ ] Existing data remains backward compatible.
- [ ] Backend tests pass.
- [ ] Relevant regression tests pass.
- [ ] Frontend production build passes.
- [ ] No pilot-critical existing feature is broken.

---

# 19. Expected Implementation Report

After implementation, report:

1. Files changed
2. Course/programme model changes
3. Enrollment changes
4. English Communication foundation changes
5. Universal support access changes
6. Authorization changes
7. Database/migration status
8. APIs added/changed
9. Frontend changes
10. Tests executed and results
11. P0-010–P0-017 regression results
12. Blockers
13. Any requirements intentionally deferred

Do not claim completion of English Communication Agent or Motivation & Support Agent unless those features were actually implemented.

---

# 20. Critical Instruction to Cursor

**Do not redesign SYS.**

The purpose of P0-018 is to align the existing implementation with the clarified SYS product model using the smallest safe set of changes.

Preserve the working P0-010–P0-017 architecture.

Prefer reuse over new abstractions.

Prefer migration-free changes when the existing schema can already represent the requirement.

Do not invent prerequisites, academic structures, examination relationships, or future features that are not present in the repository.

Keep the pilot as the immediate priority.
