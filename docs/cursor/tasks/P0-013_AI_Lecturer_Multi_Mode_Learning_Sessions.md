# P0-013 — AI Lecturer & Multi-Mode Learning Sessions

**Project:** SYS — AI-Powered Learning System
**Priority:** P0
**Status:** Planned
**Parent Architecture:** SYS Learning Platform
**Dependencies:** P0-010 Assessment Infrastructure, P0-011 Attempt Engine, P0-012 Performance Analysis & Unified Notification Engine

---

## 1. Objective

Build the common learning-session infrastructure that supports:

1. Common/class-level lectures
2. Individual student learning sessions
3. Hybrid lectures combining common instruction with individualized learning
4. AI Lecturer orchestration
5. Learning objectives and session activities
6. Student participation and interaction tracking
7. Learning evidence generation
8. Session completion and outcome tracking
9. Academic-scope and role-based authorization
10. Integration with the existing assessment, attempt, performance-analysis, and notification infrastructure

P0-013 must establish a reusable **Learning Session** foundation that P0-014 Intelligent Remedial Learning and P0-015 Adaptive Practice & Mastery Engine can consume.

The implementation must avoid creating separate lecture systems for class, individual, and remedial learning.

---

# 2. Architectural Principle

The fundamental abstraction is:

```text
LearningSession
    ├── SessionParticipants
    ├── LearningMode
    ├── LearningObjectives
    ├── LearningActivities
    ├── LearningResources
    ├── Interactions
    ├── LearningEvidence
    └── SessionOutcome
```

The system must support three modes using the same infrastructure:

```text
COMMON
INDIVIDUAL
HYBRID
```

Do not create separate persistence or service architectures for each mode.

---

# 3. Relationship With Existing SYS Architecture

P0-013 must build on the infrastructure already implemented in P0-010, P0-011, and P0-012.

The intended architecture is:

```text
                    SYS Learning Platform
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
      P0-013            P0-014            P0-015
   AI Lecturer       Remediation        Adaptive
   & Sessions        & Grouping          Mastery
          │                │                │
          └────────────────┼────────────────┘
                           │
                    Learning Evidence
                           │
                           ▼
                Performance Analysis
                       (P0-012)
                           │
                           ▼
                 Student Learning Profile
```

P0-013 must reuse existing:

* authentication
* authorization
* academic scope
* student/user models
* assessment infrastructure
* attempt engine
* performance analyzer
* learning-gap detection
* student learning profile
* notification engine
* reporting infrastructure

Do not duplicate these capabilities.

---

# 4. Supported Learning Modes

## 4.1 Common Learning Session

A lecturer/AI Lecturer conducts a learning session for multiple students.

Example:

```text
Teacher/Class
      │
      ▼
Common Lecture
      │
      ├── Topic explanation
      ├── Examples
      ├── Questions
      ├── Activities
      └── Practice
```

The session may target:

* a class
* section
* course
* subject
* academic group
* authorized student cohort

---

## 4.2 Individual Learning Session

A session is created for one student.

Example:

```text
Student
   │
   ▼
Individual AI Lecture
   │
   ├── Personalized explanation
   ├── Examples
   ├── Questions
   ├── Practice
   └── Feedback
```

The content may eventually be personalized using:

* learning profile
* previous performance
* learning gaps
* mastery
* preferred learning pace
* previous session evidence

The initial P0-013 implementation should provide the infrastructure for personalization without attempting to implement the full adaptive engine.

---

## 4.3 Hybrid Learning Session

A hybrid session combines common instruction and individualized learning.

Example:

```text
                 Hybrid Session
                       │
              ┌────────┴────────┐
              │                 │
       Common Instruction   Individual Path
              │                 │
              ├── Lecture       ├── Remediation
              ├── Explanation   ├── Extra examples
              └── Activity      └── Practice
```

The infrastructure must allow the session to contain both:

* common activities
* participant-specific activities

This is important for future classroom personalization.

---

# 5. Core Domain Concepts

P0-013 should introduce the following domain concepts where they do not already exist.

## 5.1 LearningSession

Represents a single learning interaction/session.

Expected conceptual attributes:

* id
* title
* description
* session type/mode
* course/subject reference
* academic context
* learning objectives
* facilitator/lecturer
* status
* scheduled start
* scheduled end
* actual start
* actual end
* created by
* created timestamp
* updated timestamp

Possible lifecycle:

```text
DRAFT
SCHEDULED
READY
IN_PROGRESS
PAUSED
COMPLETED
CANCELLED
ARCHIVED
```

Only implement states that are consistent with the existing SYS conventions.

---

# 6. Session Mode

Use a controlled value for:

```text
COMMON
INDIVIDUAL
HYBRID
```

Do not represent these modes using arbitrary strings throughout the codebase.

Use the existing SYS constants/enumeration conventions.

---

# 7. Session Participants

A session must support participants independently of the session creator.

Conceptually:

```text
LearningSession
      │
      └── SessionParticipant
              ├── student
              ├── role
              ├── status
              ├── joined_at
              ├── left_at
              └── participation evidence
```

Possible participant roles include:

* STUDENT
* FACILITATOR
* TEACHER
* AI_LECTURER

Use only roles that fit the existing SYS authorization model.

---

# 8. Session Activities

A session should consist of activities.

Examples:

```text
INTRODUCTION
LECTURE
EXPLANATION
EXAMPLE
QUESTION
DISCUSSION
PRACTICE
ASSESSMENT
REFLECTION
SUMMARY
```

The initial implementation should establish an extensible activity model.

Do not hard-code activity-specific behavior into the LearningSession entity.

---

# 9. Learning Objectives

Each session should be associated with one or more learning objectives.

Conceptually:

```text
LearningSession
      │
      ├── Objective 1
      ├── Objective 2
      └── Objective 3
```

Objectives should be linked to the appropriate academic scope where existing SYS models support it.

Examples:

* course
* subject
* unit
* topic
* concept
* competency

The implementation must reuse existing curriculum/academic entities instead of creating duplicate topic/course structures.

---

# 10. Learning Resources

A session may reference learning resources such as:

* lecture notes
* documents
* examples
* questions
* assessment items
* multimedia references
* AI-generated explanations

P0-013 should establish references/interfaces where required but should not attempt to implement a complete content-management system unless one already exists.

---

# 11. AI Lecturer

P0-013 introduces the AI Lecturer as a learning-session facilitator.

The AI Lecturer should eventually support:

* topic explanation
* structured lecture delivery
* student questions
* examples
* clarification
* guided practice
* session summaries
* contextual feedback
* transition between activities
* personalized interaction

The AI Lecturer must be implemented as an orchestration/service layer rather than embedding LLM-specific logic directly inside database models or API routes.

Conceptually:

```text
LearningSession
       │
       ▼
AI Lecturer Orchestrator
       │
       ├── Session Context
       ├── Learning Objectives
       ├── Student Context
       ├── Learning Activities
       ├── AI/LLM Provider
       └── Learning Evidence
```

The architecture must allow future replacement or expansion of the underlying LLM provider.

---

# 12. AI Lecturer Context

The AI Lecturer should receive a controlled session context.

Potential context:

```text
Session
Course
Subject
Topic
Learning Objectives
Current Activity
Participant Context
Previous Learning Evidence
Relevant Performance Data
Available Learning Resources
```

Only authorized information may be supplied to the AI layer.

Student data must not be exposed outside the student's authorized academic scope.

---

# 13. Learning Evidence

P0-013 must establish a common mechanism for recording evidence generated during learning sessions.

Examples:

* session started
* activity completed
* question asked
* answer submitted
* explanation viewed
* practice completed
* participation recorded
* objective completed
* session completed

Conceptually:

```text
LearningSession
      │
      ▼
LearningEvidence
      │
      ├── participant
      ├── activity
      ├── objective
      ├── event type
      ├── timestamp
      └── evidence payload
```

Learning evidence must be designed so that P0-012 can consume relevant evidence for future performance analysis.

---

# 14. Integration With Assessment

P0-013 must reuse the existing assessment and attempt infrastructure.

A learning session may invoke an existing assessment or practice activity.

The flow should be:

```text
Learning Session
      ↓
Assessment/Practice
      ↓
Existing Attempt Engine
      ↓
Assessment Result
      ↓
Performance Analysis
```

Do not create a second attempt mechanism inside P0-013.

---

# 15. Integration With Performance Analysis

P0-013 should provide learning evidence to the existing performance infrastructure.

The intended future flow is:

```text
Learning Session
      ↓
Learning Evidence
      ↓
Performance Analyzer
      ↓
Learning Profile
      ↓
Learning Gap
```

P0-013 must not duplicate:

* learning-gap detection
* trend analysis
* exam-readiness calculations
* student learning profile calculations

Those belong to the existing performance-analysis infrastructure.

---

# 16. Integration With Notifications

P0-013 must use the existing Unified Notification Engine.

Possible notifications include:

* session scheduled
* session updated
* session cancelled
* session starting
* student invited
* session available
* session completed
* follow-up activity available

Notifications must respect the existing:

* role authorization
* academic scope
* recipient preferences
* delivery audit
* retry mechanism

Do not create a separate lecture notification system.

---

# 17. Authorization

All P0-013 endpoints and services must enforce existing SYS authorization.

Authorization must consider:

```text
User Role
Academic Scope
Course/Subject Scope
Class/Section Scope
Student Ownership
Session Participation
```

Examples:

* A student can access only sessions they are authorized to attend.
* A teacher can manage sessions within their authorized academic scope.
* An administrator may access sessions according to existing administrative permissions.
* A user must not access another student's individual session without authorization.

Do not bypass existing authorization middleware/services.

---

# 18. API Layer

The API should expose the minimum required operations for the session foundation.

Expected conceptual operations:

```text
Create session
Get session
List sessions
Update session
Change session status
Add participant
Remove participant
Get participants
Add activity
Get activities
Record learning evidence
Complete session
```

Use existing SYS API conventions.

Do not create unnecessary endpoints before their corresponding domain behavior exists.

---

# 19. Database Design

Database changes must use Alembic migrations.

Potential tables:

```text
learning_sessions
learning_session_participants
learning_session_activities
learning_session_objectives
learning_evidence
```

Actual table names must follow the repository's established naming conventions.

Database requirements:

* foreign keys
* appropriate indexes
* timestamps
* uniqueness constraints
* status constraints where appropriate
* academic-scope relationships
* participant uniqueness
* referential integrity

Avoid storing arbitrary duplicated student/course information when foreign-key references are available.

---

# 20. P0-013 Persistence Requirements

The persistence model must support:

### Common

```text
One session
Many students
Common activities
```

### Individual

```text
One session
One student
Individual activities
```

### Hybrid

```text
One session
Many participants
Common activities
Participant-specific activities
```

The schema must therefore not assume:

```text
one session = one student
```

nor:

```text
one session = one class
```

---

# 21. Session Lifecycle

The lifecycle should prevent invalid state transitions.

Example:

```text
DRAFT
  ↓
SCHEDULED
  ↓
READY
  ↓
IN_PROGRESS
  ↓
COMPLETED
```

Alternative paths may include:

```text
DRAFT → CANCELLED
SCHEDULED → CANCELLED
READY → CANCELLED
IN_PROGRESS → PAUSED
PAUSED → IN_PROGRESS
```

The exact state machine should follow existing project conventions.

Invalid transitions must be rejected.

---

# 22. Frontend Requirements

P0-013 should eventually provide a common learning-session UI.

The frontend should not implement three separate lecture pages.

Use a common session experience:

```text
LearningSessionPage
       │
       ├── Session Header
       ├── Objective Panel
       ├── Activity Area
       ├── AI Lecturer Interaction
       ├── Participant Context
       ├── Progress
       └── Session Summary
```

The experience should adapt based on:

```text
session.mode
```

rather than duplicating entire pages.

Initial backend/domain work may be completed before the complete learner-facing UI.

---

# 23. Hybrid Session UI

For HYBRID mode, the UI should conceptually support:

```text
Common Content
      │
      ├── Shared Lecture
      ├── Shared Activity
      │
      └── Individual Path
             ├── Student A activity
             ├── Student B activity
             └── Student C activity
```

The infrastructure should allow this without creating separate sessions for every participant unless explicitly required.

---

# 24. AI Provider Abstraction

Do not tightly couple the AI Lecturer to a single model/provider.

Use an abstraction such as:

```text
AI Lecturer Service
       ↓
LLM Provider Interface
       ↓
Provider Implementation
```

The actual project naming should follow the existing SYS AI/LLM architecture.

The design should allow future support for:

* cloud LLMs
* local models
* institution-hosted models
* different models for different workloads

---

# 25. Error Handling

P0-013 must use the existing SYS error-handling conventions.

Handle at minimum:

* unauthorized session access
* invalid session state transition
* invalid participant
* duplicate participant
* invalid academic scope
* missing learning objective
* invalid activity
* session not found
* invalid evidence
* AI provider failure

AI provider failure must not corrupt session state.

---

# 26. Auditability

Important session actions should be auditable.

At minimum:

* session creation
* session modification
* participant changes
* status transitions
* activity creation/modification
* session completion

Use existing audit infrastructure where available.

Do not introduce a second audit architecture.

---

# 27. Observability

Where the existing project supports logging/monitoring, record useful operational information for:

* session creation
* session lifecycle transitions
* AI Lecturer requests
* AI Lecturer failures
* activity execution
* evidence creation
* session completion

Do not log sensitive student information unnecessarily.

---

# 28. Testing Requirements

P0-013 must include backend tests for:

### Domain

* session creation
* session retrieval
* session update
* lifecycle transitions
* invalid lifecycle transitions

### Modes

* common session
* individual session
* hybrid session

### Participants

* adding participants
* duplicate participant prevention
* participant authorization
* participant removal where supported

### Activities

* activity creation
* activity ordering
* activity authorization

### Evidence

* evidence creation
* participant ownership
* invalid evidence rejection

### Authorization

* student access
* teacher access
* administrative access
* cross-scope access rejection

### Integration

* assessment integration
* attempt-engine integration
* performance-analysis integration
* notification integration

Tests must use the existing test infrastructure.

---

# 29. Frontend Verification

Where frontend implementation is included in a specific P0-013 task, verify:

* session list
* session details
* correct session mode
* participant visibility
* activity rendering
* session status
* authorization behavior
* responsive behavior
* SYS branding

Do not replace existing global UI components unnecessarily.

---

# 30. End-to-End Verification

At least one real end-to-end flow should eventually verify:

```text
Authorized User
      ↓
Create Learning Session
      ↓
Add Student(s)
      ↓
Start Session
      ↓
Execute Activity
      ↓
Record Learning Evidence
      ↓
Complete Session
      ↓
Evidence Available for Analysis
      ↓
Notification Where Applicable
```

For individual sessions:

```text
Student
  ↓
Individual Session
  ↓
AI Lecturer Interaction
  ↓
Evidence
  ↓
Completion
```

For hybrid sessions:

```text
Class
  ↓
Common Instruction
  ↓
Individual Activity
  ↓
Evidence
  ↓
Completion
```

---

# 31. P0-013 Implementation Breakdown

P0-013 must be implemented incrementally.

## P0-013.1 — Learning Session Domain & Persistence Foundation

Build:

* LearningSession model
* session mode
* lifecycle/status
* participants
* objectives
* activities
* learning evidence foundation
* Alembic migration
* schemas
* repositories/services as appropriate
* authorization foundation
* backend tests

Do not implement the full AI Lecturer experience.

---

## P0-013.2 — Session Management APIs

Build:

* create session
* retrieve session
* list sessions
* update session
* lifecycle operations
* participant management
* objective/activity management
* authorization enforcement
* API tests

---

## P0-013.3 — Common, Individual & Hybrid Session Behavior

Implement:

* COMMON behavior
* INDIVIDUAL behavior
* HYBRID behavior
* common activities
* participant-specific activities
* session evidence

Add backend integration tests.

---

## P0-013.4 — AI Lecturer Orchestration

Build:

* AI Lecturer service
* session context
* activity context
* LLM provider abstraction
* AI response handling
* error handling
* learning evidence generation
* AI Lecturer tests

Do not embed provider-specific logic into domain models.

---

## P0-013.5 — Frontend Learning Session Experience

Build:

* session list
* session details
* common session UI
* individual session UI
* hybrid session UI
* activity interface
* AI Lecturer interaction
* progress
* session completion

Reuse existing SYS frontend architecture and components.

---

## P0-013.6 — Cross-Module Integration

Integrate:

* P0-010 assessment
* P0-011 attempt engine
* P0-012 performance analyzer
* student learning profile
* learning-gap detection
* unified notification engine

Verify the complete flow.

---

## P0-013.7 — End-to-End Verification

Perform:

* backend tests
* frontend verification
* authorization verification
* migration verification
* real E2E verification
* regression testing

Confirm no existing P0 functionality has been broken.

---

# 32. Explicit Non-Goals

P0-013 must NOT implement the complete functionality of:

### P0-014

Do not implement:

* learning-gap clustering
* similarity-based grouping
* remedial group formation
* intervention optimization
* group evolution
* remedial recommendation engine

These belong to P0-014.

### P0-015

Do not implement:

* adaptive practice selection
* mastery engine
* mastery prediction
* adaptive sequencing
* continuous mastery loop

These belong to P0-015.

### Existing Infrastructure

Do not rebuild:

* assessment engine
* attempt engine
* performance analyzer
* reporting engine
* notification engine
* authorization system
* authentication system

Reuse the existing implementations.

---

# 33. Architectural Constraints

The implementation must follow these rules:

1. Reuse existing SYS infrastructure.
2. Do not duplicate existing domain concepts.
3. Do not create parallel authorization logic.
4. Do not create a second notification system.
5. Do not create a second assessment/attempt engine.
6. Do not duplicate performance-analysis calculations.
7. Do not hard-code AI provider dependencies into domain models.
8. Do not create separate architectures for common, individual, and hybrid learning.
9. Keep domain logic out of API route handlers where existing service architecture is used.
10. Follow existing project naming and folder conventions.
11. Add migrations for all schema changes.
12. Add tests with each backend capability.
13. Avoid unrelated refactoring.
14. Avoid modifying unrelated files.
15. Preserve existing P0-010/P0-011/P0-012 behavior.

---

# 34. Cursor Implementation Rules

Each P0-013 task must begin by inspecting the existing repository.

Before modifying code:

1. Identify relevant existing models.
2. Identify existing schemas.
3. Identify existing services.
4. Identify existing authorization mechanisms.
5. Identify existing assessment/attempt integration points.
6. Identify existing performance-analysis integration points.
7. Identify existing notification interfaces.
8. Identify existing frontend patterns.
9. Reuse existing conventions.

Do not invent new architecture when an existing implementation already provides the required capability.

### Scope control

Cursor must:

* modify only files necessary for the requested task
* avoid broad refactoring
* avoid speculative features
* avoid creating unnecessary abstractions
* avoid rewriting working P0-010/P0-011/P0-012 code
* run the relevant tests
* report only implementation-relevant results

---

# 35. Definition of Done

P0-013 is complete only when all applicable criteria below are satisfied.

## Backend

* [ ] Learning Session domain implemented
* [ ] COMMON mode supported
* [ ] INDIVIDUAL mode supported
* [ ] HYBRID mode supported
* [ ] Session lifecycle implemented
* [ ] Participant management implemented
* [ ] Learning objectives supported
* [ ] Learning activities supported
* [ ] Learning evidence supported
* [ ] Authorization enforced
* [ ] Database migration created and applied
* [ ] Backend tests pass

## AI Lecturer

* [ ] AI Lecturer service implemented
* [ ] Session context implemented
* [ ] Provider abstraction implemented
* [ ] AI failures handled safely
* [ ] AI interactions produce learning evidence
* [ ] Relevant tests pass

## Integration

* [ ] P0-010 integration verified
* [ ] P0-011 integration verified
* [ ] P0-012 integration verified
* [ ] Student Learning Profile integration verified
* [ ] Learning Gap integration verified where applicable
* [ ] Unified Notification Engine integration verified

## Frontend

* [ ] Learning session UI implemented
* [ ] Common mode supported
* [ ] Individual mode supported
* [ ] Hybrid mode supported
* [ ] Session progress displayed
* [ ] Activity interaction supported
* [ ] Session completion supported
* [ ] Authorization respected
* [ ] SYS branding preserved

## Quality

* [ ] Backend tests pass
* [ ] Frontend verification passes
* [ ] Authorization tests pass
* [ ] Database migration passes
* [ ] Real E2E flow passes
* [ ] No regression in previous P0 functionality
* [ ] No unrelated files/features modified

---

# 36. Target Architecture After P0-013

After completion, SYS should conceptually have:

```text
                         SYS
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
   AI Lecturer       Assessment       Performance
   & Sessions          Engine           Analysis
          │               │                │
          │               ▼                ▼
          │          Attempt Engine    Learning Profile
          │                                │
          └───────────────┬────────────────┘
                          │
                   Learning Evidence
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
       P0-014 Remedial            P0-015 Adaptive
       Learning & Groups          Practice & Mastery
```

The long-term learning cycle becomes:

```text
             ┌───────────────────────┐
             │                       │
             ▼                       │
           LEARN                     │
             │                       │
             ▼                       │
         PRACTICE                    │
             │                       │
             ▼                       │
          ASSESS                     │
             │                       │
             ▼                       │
          ANALYZE                    │
             │                       │
             ▼                       │
        REMEDIATE                    │
             │                       │
             ▼                       │
        REASSESS                     │
             │                       │
             ▼                       │
          MASTER ────────────────────┘
```

P0-013 provides the **learning delivery/session foundation** for this loop.

P0-014 provides the **intelligent remediation and grouping layer**.

P0-015 provides the **adaptive practice and mastery-control layer**.

---

# 37. Success Criterion

The ultimate success criterion for P0-013 is not merely that an AI chatbot can explain a topic.

SYS must have a reusable learning-session infrastructure in which:

> **A common classroom, an individual student, and a hybrid personalized classroom can all use the same Learning Session architecture, generate structured learning evidence, integrate with assessment and performance analysis, and provide the foundation required for intelligent remediation and adaptive mastery.**

This architecture must remain extensible for future SYS capabilities including:

* remedial learning
* adaptive practice
* mastery learning
* English communication learning
* motivation/counselling workflows
* future learning agents
* additional AI teaching modes
* future notification channels
* future learning analytics
