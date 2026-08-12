# P0-011 — Student Assessment Attempt, Evaluation & Universal Answer Key Engine

**Priority:** P0 — Critical  
**Type:** End-to-End Feature  
**Dependencies:** P0-009 Assessment Management & Reporting, P0-010 Intelligent Academic Question Knowledge Base  
**Primary consumers:** Students, Performance Analyzer, Report Card, Remedial Learning, AI Lecturer

## 1. Objective

Implement the production-ready **Student Assessment Attempt and Evaluation Engine** for SYS.

P0-009 already provides assessment creation, blueprints, question integration, test generation/assembly, assessment versioning, performance sheets, report cards, PDF reporting, and notification infrastructure.

P0-011 must complete the live student assessment lifecycle:

```text
Published Assessment
        ↓
Eligible Student
        ↓
Start Assessment
        ↓
Live Attempt
        ↓
Question Navigation
        ↓
Answer / Review / Auto-save
        ↓
Submit / Auto-submit
        ↓
Server-side Evaluation
        ↓
Result
        ↓
Performance Records
        ├── Performance Sheet
        ├── Report Card
        ├── Performance Analyzer
        └── Answer Key + Explanation PDF
```

Do not rebuild functionality that already exists in P0-009. Integrate with it.

## 2. Core Requirements

Support real student attempts for:

- Topic-wise Tests
- Weekly Tests
- Monthly Tests
- Grand Tests
- Final Grand Tests
- Multi-subject assessments
- Other assessment types supported by P0-009

The student must receive the **exact assessment version/question set** intended for that attempt.

## 3. Assessment Attempt Model

Create a durable assessment-attempt model linked to the student, assessment, and exact assessment version.

At minimum support:

```text
AssessmentAttempt
├── id
├── student_id
├── assessment_id
├── assessment_version_id
├── attempt_number
├── status
├── started_at
├── submitted_at
├── auto_submitted
├── time_spent
├── score
├── percentage
└── timestamps
```

Possible statuses:

```text
NOT_STARTED
IN_PROGRESS
SUBMITTED
AUTO_SUBMITTED
EVALUATED
CANCELLED
```

Do not permit submitted/evaluated attempts to be modified.

## 4. Attempt Response Model

Store individual student responses:

```text
AttemptResponse
├── id
├── attempt_id
├── question_id
├── question_sequence
├── selected_answer
├── answered
├── marked_for_review
├── time_spent
├── submitted_answer_snapshot
└── timestamps
```

Preserve enough information to reproduce what the student actually saw and submitted. Do not rely solely on the current Question Bank record.

## 5. Assessment Version Integrity

Once a student starts:

```text
Assessment Version
        ↓
Question Snapshot
        ↓
Student Attempt
```

Later Question Bank changes must not alter historical attempts, evaluation, results, or answer keys.

## 6. Student Eligibility & Access

Allow access only when:

- authenticated
- authorized for the course
- assessment is published/available
- within configured availability window
- attempt limit is not exceeded
- assessment is not invalidated

Prevent:

- another student's attempt access
- unpublished assessment access
- another student's submission
- modification of submitted attempts
- answer-key access while assessment is active

Reuse existing SYS academic authorization.

## 7. Student Assessment Dashboard

Provide:

### Available
- assessment name
- course
- assessment type
- number of questions
- total marks
- duration
- start/end availability
- attempt information

### Upcoming
Scheduled assessments not yet available.

### In Progress
Attempts that can be resumed.

### Completed
Completed assessments with score, percentage, status, report availability and answer-key availability.

Use existing SYS frontend layout and branding.

## 8. Live Assessment UI

Implement:

- question display
- options
- previous/next
- question palette
- answer selection
- clear answer
- mark for review
- answered/unanswered/reviewed/current states
- timer
- submission

Example:

```text
┌─────────────────────────────────────────────┐
│ Assessment Name                  42:18       │
├─────────────────────────────────────────────┤
│ Question 12                                 │
│ Question text...                            │
│                                             │
│ ○ Option A                                  │
│ ○ Option B                                  │
│ ○ Option C                                  │
│ ○ Option D                                  │
│                                             │
│ [Clear] [Mark Review] [Previous] [Next]    │
└─────────────────────────────────────────────┘
```

## 9. Timer

Assessment duration must be enforced server-side. The frontend timer is only a display.

Support:

- configured duration
- remaining time
- synchronization
- automatic submission on expiry
- protection against client-side timer manipulation

## 10. Auto-save

Persist answers during the attempt.

Tolerate reasonable interruptions such as browser refresh and temporary network failure where possible.

Do not create excessive API traffic. The server remains authoritative.

## 11. Navigation & State

Support:

- Previous
- Next
- Direct question selection
- Clear answer
- Mark/unmark review

On resume, restore selected answers, review flags, remaining time and appropriate question state.

## 12. Submission

Before submission show:

```text
Answered:        78
Unanswered:      12
Marked Review:    5
Total Questions: 90
```

Require confirmation.

Manual:

```text
IN_PROGRESS → SUBMITTED → EVALUATED
```

Timeout:

```text
IN_PROGRESS → AUTO_SUBMITTED → EVALUATED
```

After submission, no student-side modification.

## 13. Server-side Evaluation Engine

Evaluation must occur on the backend.

Never trust client-calculated:

- score
- correctness
- marks
- completion time

Evaluate using the exact assessment version/question snapshot.

Classify:

```text
CORRECT
INCORRECT
UNANSWERED
```

Apply configured positive/negative/zero marking and existing question-type rules.

## 14. Overall Result

Calculate:

- total questions
- attempted
- correct
- incorrect
- unanswered
- total marks
- obtained marks
- percentage
- accuracy
- negative marks
- time spent
- completion status

Example:

```text
Score:          72 / 100
Percentage:     72%
Attempted:      90
Correct:        72
Incorrect:      18
Unanswered:     10
Accuracy:       80%
```

## 15. Subject-level Performance

For multi-subject assessments calculate machine-readable subject results, e.g.:

```text
Mathematics     82%
Physics         64%
Chemistry       71%
```

## 16. Topic-level Performance

Calculate per topic/subtopic where metadata permits:

- attempted
- correct
- incorrect
- unanswered
- marks
- accuracy
- percentage

Example:

```text
Calculus       88%
Algebra        76%
Mechanics      52%
Organic Chem   69%
```

This data must feed the future Performance Analyzer.

## 17. Difficulty-level Performance

Calculate performance across:

- Easy
- Medium
- Hard
- Advanced

Example:

```text
Easy        94%
Medium      78%
Hard        51%
Advanced    32%
```

## 18. Question-level Performance

Persist data sufficient to determine:

- wrong questions
- weak topics
- difficult levels causing problems
- repeated concept errors
- time spent per question
- skipped questions
- review behavior

This must be structured for P0-012 Performance Analyzer.

## 19. Performance Analyzer Contract

P0-009 already defines the Performance Analyzer data contract.

P0-011 must populate that contract with real evaluated attempt data.

Do not create a second incompatible performance-data model.

```text
Student Attempt
      ↓
Evaluation
      ↓
Performance Data Contract
      ↓
Performance Analyzer
```

## 20. Result Page

Provide:

### Summary
- score
- percentage
- accuracy
- attempted
- correct
- incorrect
- unanswered
- time spent

### Subject performance
### Topic performance
### Difficulty performance

Where release policy permits, allow question review with question, selected answer, correct answer and explanation.

## 21. Universal Answer Key & Explanation Document

This is a **mandatory P0-011 feature**.

For every completed/released assessment, generate a downloadable **Answer Key & Explanation document**.

It must be available to **all eligible authenticated users**, including:

- Student
- Faculty
- Course Coordinator
- Admin
- Other authorized users

Do not restrict answer-key downloads to administrative roles.

## 22. Answer Key Availability

Do not expose the answer key while an assessment is active.

Recommended lifecycle:

```text
Assessment Active
      ↓
Answer Key Hidden
      ↓
Assessment Completed / Released
      ↓
Answer Key Available
      ↓
All eligible users can download
```

Respect any existing release policy from P0-009.

## 23. Answer Key Content

Include:

### Header
- SYS branding
- course
- assessment name
- assessment type
- assessment date
- assessment version
- total questions
- total marks

### Every question
- question number
- question text
- options
- correct answer
- explanation
- marks
- negative marks where relevant
- subject
- topic/subtopic
- shortcut/alternative solution where available

Where P0-010 provides Question Intelligence, include useful academic guidance where appropriate:

- important concept
- shortcut
- common trap
- exam tip

Do not expose internal ranking/probability scores unless explicitly intended for the audience.

## 24. Answer Key Version Integrity

The Answer Key must be generated from the **exact assessment version/question snapshot** administered.

```text
Final Grand Test — Version 3
       ↓
Question Snapshot
       ↓
Answer Key — Version 3
```

Later Question Bank edits must not alter historical answer keys.

## 25. Answer Key Format

At minimum provide a **PDF download**.

Reuse existing SYS PDF/report infrastructure where possible.

The document must be:

- readable
- correctly paginated
- printable
- consistently branded
- complete
- deterministic for the same assessment version

## 26. Answer Key Access

Expose appropriate authenticated routes, following existing route conventions, such as:

```text
GET /assessments/{assessment_id}/answer-key
GET /assessment-versions/{version_id}/answer-key
```

Do not expose raw file paths or sensitive server details.

## 27. Answer Key UI

For completed assessments show:

```text
[View Result]
[Download Report Card]
[Download Answer Key & Explanations]
```

The answer-key action should be visible to all eligible authenticated users after release.

## 28. Assessment Integrity

Implement:

- attempt ownership validation
- assessment availability validation
- attempt count enforcement
- server-side timing
- server-side evaluation
- immutable submitted attempts
- assessment-version integrity
- authorization on every attempt endpoint

Do not implement full online proctoring in P0-011.

## 29. Notification Integration

P0-009 already contains notification/report infrastructure.

Integrate where configured for events such as:

```text
Assessment Completed
Assessment Evaluated
Result Available
Answer Key Available
```

Do not duplicate the notification engine.

## 30. Frontend Requirements

Implement:

```text
Student
├── Assessment Dashboard
├── Assessment Instructions
├── Live Assessment
├── Attempt Resume
├── Submission Confirmation
├── Result
└── Answer Key Download

Existing Admin/Faculty
├── Assessment results
├── Student performance
└── Answer Key Download
```

Maintain SYS Branding Asset family and existing frontend consistency.

Reuse existing Header, navigation, API client, authentication, layout, typography, components and branding assets.

## 31. Backend APIs

Implement clean APIs for:

```text
List available assessments
Get assessment instructions
Start attempt
Get attempt
Get attempt questions
Save response
Mark/unmark review
Clear answer
Get attempt status
Submit attempt
Auto-submit
Evaluate attempt
Get result
Get subject performance
Get topic performance
Get difficulty performance
Download answer key
```

Follow existing authentication/authorization conventions.

## 32. Database Migration

Create an Alembic migration for genuinely new attempt/response structures.

Migration must be:

- deterministic
- reversible
- compatible with existing database
- tested

Do not unnecessarily modify P0-009 structures.

## 33. Testing Requirements

Backend tests must cover:

### Authorization
```text
Unauthenticated
Student
Faculty
Subject Expert
Course Coordinator
Admin
```

### Assessment access
- eligible student
- ineligible student
- unpublished assessment
- expired assessment
- future assessment
- attempt limit

### Attempt lifecycle
```text
Start
Resume
Save
Submit
Auto-submit
Evaluate
```

### Attempt isolation
Verify one student cannot access another student's attempt.

### Assessment version integrity
Verify historical attempts remain tied to the original question/version snapshot.

### Evaluation
Test correct, incorrect, unanswered, positive marks, negative marks and zero marks.

### Multi-subject
Verify subject-level results.

### Topic analysis
Verify topic-level performance.

### Difficulty analysis
Verify difficulty-level performance.

### Performance contract
Verify evaluated results populate the P0-009 Performance Analyzer data contract.

### Answer key
Verify:
- generated after completion/release
- unavailable while active
- available to all eligible authenticated users
- exact assessment version used
- correct answers
- explanations
- PDF generation
- PDF content
- historical key immutability

### Security
Verify students cannot:
- alter scores
- submit another user's attempt
- modify submitted attempts
- access active answer keys
- change assessment timing through client payloads

## 34. Frontend Verification

Verify:

- student assessment dashboard
- instructions
- live test
- timer
- navigation
- answer selection
- mark for review
- auto-save
- resume
- submission
- result page
- answer-key download
- report-card access

Test responsive behavior for normal desktop and mobile-sized layouts where practical.

## 35. End-to-End Verification

The complete flow must work with real database-backed data:

```text
Admin/Course Coordinator
        ↓
Published Assessment
        ↓
Student Login
        ↓
Assessment Dashboard
        ↓
Start Assessment
        ↓
Answer Questions
        ↓
Auto-save
        ↓
Submit
        ↓
Server Evaluation
        ↓
Result
        ↓
Performance Data
        ↓
Report Card
        ↓
Answer Key + Explanation PDF
```

Also verify:

```text
Completed Assessment
        ↓
All eligible authenticated users
        ↓
Download Answer Key
```

## 36. Important Scope Boundary

Do NOT implement:

- complete Performance Analyzer
- complete Remedial Learning
- complete AI Lecturer
- AI proctoring
- webcam monitoring
- advanced anti-cheating system

P0-011 must provide the real attempt/evaluation data required by those future modules.

## 37. Deliverables

```text
Backend
├── Assessment Attempt model
├── Attempt Response model
├── Version/snapshot integrity
├── Attempt APIs
├── Evaluation service
├── Performance data integration
├── Answer Key generator
├── Answer Key APIs
└── Alembic migration

Frontend
├── Student Assessment Dashboard
├── Assessment Instructions
├── Live Assessment UI
├── Attempt Resume
├── Submission Flow
├── Result Page
└── Answer Key Download

Tests
├── Authorization
├── Attempt lifecycle
├── Evaluation
├── Version integrity
├── Multi-subject results
├── Topic performance
├── Difficulty performance
├── Performance contract
├── Answer key generation
├── Answer key access
└── Security
```

## 38. Cursor Execution Rule

**Prioritize implementation and working functionality over lengthy explanations.**

Before changing code:

1. Inspect P0-009 assessment models/routes/services.
2. Inspect the P0-009 Performance Analyzer data contract.
3. Inspect existing report/PDF generation.
4. Inspect existing authentication/academic authorization.
5. Reuse existing assessment versioning and question integration.
6. Do not create duplicate assessment/report/PDF infrastructure.

At completion report only:

```text
Files changed:
...

Assessment attempt:
PASS/FAIL

Student assessment UI:
PASS/FAIL

Auto-save:
PASS/FAIL

Timer:
PASS/FAIL

Submission:
PASS/FAIL

Evaluation:
PASS/FAIL

Subject/topic/difficulty performance:
PASS/FAIL

Performance Analyzer contract:
PASS/FAIL

Answer Key + Explanation PDF:
PASS/FAIL

Universal Answer Key access:
PASS/FAIL

Assessment version integrity:
PASS/FAIL

Security/authorization:
PASS/FAIL

Backend tests:
PASS/FAIL

Frontend verification:
PASS/FAIL

SYS branding verification:
PASS/FAIL

End-to-end verification:
PASS/FAIL

Database migration:
YES/NO

Remaining blockers:
...
```

Do not modify unrelated modules.

Do not rewrite working P0-007, P0-008, P0-009 or P0-010 functionality unless required for integration.

## Definition of Done

P0-011 is complete only when the following works with real database-backed data:

```text
Published Assessment
       ↓
Eligible Student
       ↓
Start
       ↓
Live Attempt
       ↓
Answer / Review / Auto-save
       ↓
Submit / Auto-submit
       ↓
Server-side Evaluation
       ↓
Overall Result
       ↓
Subject Result
       ↓
Topic Result
       ↓
Difficulty Result
       ↓
Performance Analyzer Data
       ↓
Report Card
       ↓
Answer Key + Explanation PDF
       ↓
Available to all eligible authenticated users
```

Historical integrity rule:

```text
Question Bank changes
       ↓
Existing completed attempt
       ↓
NO change to:
- administered question
- correct answer
- evaluation
- result
- answer key
```

**P0-011 is the bridge between SYS's assessment-generation infrastructure and its actual student learning/performance intelligence.**
