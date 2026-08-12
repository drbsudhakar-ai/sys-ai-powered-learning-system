# SYS — P0-009

# Assessment Engine, Test Design, Performance Reporting & Notification

**Task ID:** P0-009
**Phase:** Phase 1 — Core Academic Assessment Backbone
**Priority:** P0 — CRITICAL
**Type:** End-to-End Functional Implementation
**Status:** NOT_STARTED

---

# 1. OBJECTIVE

Implement the core SYS Assessment subsystem as the backbone of the academic evaluation platform.

Assessment in SYS is NOT a generic quiz CRUD module.

It must support structured, Course-specific assessment for:

1. Topic-wise assessments
2. Weekly tests
3. Monthly tests
4. Grand tests
5. Final Grand tests

The Assessment subsystem must support:

- Course-specific assessment design
- Multi-subject assessment design
- Topic/subtopic coverage
- Difficulty/complexity distribution
- Assessment blueprints
- Question selection/generation integration
- Assessment lifecycle
- Assessment result data structure
- Student performance sheets
- Individual student report cards
- Downloadable reports
- Admin/Course Coordinator report access
- Configurable official email recipients
- Assessment report notifications
- Notification audit/retry foundation
- Performance Analyzer data contract

The implementation must be production-oriented and must build on the existing SYS architecture.

---

# 2. CRITICAL ARCHITECTURAL PRINCIPLE

The Assessment subsystem must preserve assessment data at sufficient granularity for future Performance Analyzer and Remedial Learning modules.

DO NOT reduce assessment performance to:

student → total score

The system must preserve structured relationships:

Student
    ↓
Course
    ↓
Assessment
    ↓
Assessment Type
    ↓
Subject
    ↓
Topic
    ↓
Subtopic
    ↓
Question
    ↓
Difficulty
    ↓
Response
    ↓
Evaluation
    ↓
Performance Record

The future Performance Analyzer must be able to consume this information.

---

# 3. EXISTING IMPLEMENTATION MUST BE INSPECTED FIRST

Before making changes, inspect the repository and understand:

- Course model
- Course CRUD
- User model
- Student model/representation
- Faculty model/representation
- Subject model
- Topic model
- Assessment model
- Question model/question-related structures
- Existing schemas
- Existing routes
- Existing services
- Existing authorization
- Academic responsibility assignment from P0-008
- Existing authentication
- Existing API client
- Existing frontend structure
- Existing shared components
- Existing SYS Branding Asset family
- Existing database migrations
- Existing testing infrastructure
- Existing email/notification infrastructure, if any

IMPORTANT:

The current repository is the source of truth.

Reuse existing models, schemas, services, authorization and UI components wherever possible.

Do NOT create duplicate Course, Subject, Topic, Student, Faculty, or User structures.

Do NOT recreate already-working P0-007/P0-008 functionality.

---

# 4. ASSESSMENT MODEL

Assessment must belong to a Course.

Conceptually:

Course
    │
    ├── Subjects
    │      ├── Subject A
    │      ├── Subject B
    │      └── Subject C
    │
    └── Assessments
           ├── Topic Assessment
           ├── Weekly Test
           ├── Monthly Test
           ├── Grand Test
           └── Final Grand Test

Every Assessment must have a valid Course association.

Backend must enforce this.

---

# 5. ASSESSMENT CATEGORIES

Do NOT model Weekly/Monthly/Grand/Final Grand as the only conceptual categories.

The system must distinguish the purpose/scope of an assessment.

At minimum support:

## TOPIC_MASTERY

Assessment conducted after completion of a specific topic.

Purpose:

Determine whether the student has mastered the completed topic.

---

## PERIODIC_EVALUATION

Assessment conducted periodically to evaluate recently completed syllabus across multiple subjects.

Examples:

- Weekly Test
- Monthly Test

---

## CUMULATIVE_EVALUATION

Assessment covering a broader portion of the Course syllabus across multiple subjects.

Example:

- Grand Test

---

## FINAL_READINESS

Assessment intended to measure overall readiness for the target entrance/competitive examination.

Example:

- Final Grand Test

Use appropriate enums/constants following repository conventions.

Do not hardcode category strings throughout the application.

---

# 6. ASSESSMENT TYPES

At minimum support:

TOPIC_TEST
WEEKLY_TEST
MONTHLY_TEST
GRAND_TEST
FINAL_GRAND_TEST

The architecture must permit future assessment types without redesign.

---

# 7. IMPORTANT DISTINCTION

Topic tests are fundamentally different from periodic/cumulative tests.

## Topic Assessment

Example:

Course:
    JEE Preparation

Subject:
    Mathematics

Topic:
    Quadratic Equations

Assessment:
    Quadratic Equations — Topic Test

Purpose:
    Topic mastery

Coverage:
    Single topic

---

## Weekly Test

Example:

Course:
    JEE Preparation

Subjects:

    Mathematics
    Physics
    Chemistry

Coverage:

    Topics completed during the week

Purpose:

    Periodic evaluation

---

## Monthly Test

Example:

Course:
    JEE Preparation

Subjects:

    Mathematics
    Physics
    Chemistry

Coverage:

    Topics/units completed during the month

Purpose:

    Cumulative/periodic evaluation

---

## Grand Test

Example:

Course:
    JEE Preparation

Subjects:

    Mathematics
    Physics
    Chemistry

Coverage:

    Broad Course syllabus

Purpose:

    Cumulative evaluation / competitive-exam simulation

---

## Final Grand Test

Example:

Course:
    JEE Preparation

Subjects:

    Mathematics
    Physics
    Chemistry

Coverage:

    Full or prescribed final syllabus

Purpose:

    Final readiness

---

# 8. MULTI-SUBJECT ASSESSMENT — MANDATORY

Weekly, Monthly, Grand and Final Grand assessments MUST support multiple Subjects belonging to the selected Course.

Example:

Course:
    Competitive Exam Preparation

Subjects:

    Mathematics
    Physics
    Chemistry

Assessment:

    Grand Test 01

Distribution:

    Mathematics → 30 questions
    Physics     → 30 questions
    Chemistry   → 30 questions

The system must NOT restrict these assessments to a single Subject.

---

# 9. SUBJECT-WISE DISTRIBUTION

Authorized Assessment Designers must be able to configure question distribution by Subject.

Example:

Grand Test:

Mathematics:
    30 questions

Physics:
    30 questions

Chemistry:
    40 questions

Total:
    100 questions

The system must validate:

30 + 30 + 40 = 100

If the configured values do not match the required total:

Prevent publication.

---

# 10. TOPIC-WISE ASSESSMENT

Topic assessments must be associated with a specific:

Course
Subject
Topic

Example:

Course:
    EAMCET Mathematics

Subject:
    Mathematics

Topic:
    Probability

Assessment:
    Probability Topic Test

The system must not allow a Topic Assessment to silently cover unrelated Topics.

---

# 11. MULTI-SUBJECT TOPIC COVERAGE FOR PERIODIC TESTS

For Weekly/Monthly/Grand/Final Grand tests, the assessment designer must be able to select:

Subject
    ↓
Topic
    ↓
Subtopic where available

Example:

Mathematics
    Algebra
        Quadratic Equations
        Progressions

Physics
    Mechanics
        Laws of Motion
        Work and Energy

Chemistry
    Organic Chemistry
        Hydrocarbons

The exact hierarchy must follow the existing repository model.

---

# 12. ASSESSMENT BLUEPRINT

Implement an Assessment Blueprint.

The blueprint defines what the assessment should contain.

Example:

Assessment:

    Grand Test 01

Blueprint:

Mathematics
    Algebra
        Easy     = 3
        Medium   = 5
        Hard     = 2

    Geometry
        Easy     = 2
        Medium   = 4
        Hard     = 2

Physics
    Mechanics
        Easy     = 3
        Medium   = 5
        Hard     = 2

Chemistry
    Organic Chemistry
        Easy     = 4
        Medium   = 4
        Hard     = 2

The blueprint must be stored in a structured way.

Do not store the entire blueprint as an opaque unvalidated text blob.

---

# 13. DIFFICULTY / COMPLEXITY

Support multiple difficulty levels.

At minimum:

EASY
MEDIUM
HARD
ADVANCED

Reuse an existing Difficulty representation if already available.

Do not create duplicate difficulty models.

---

# 14. DIFFICULTY DISTRIBUTION

Assessment designer must be able to configure difficulty.

Example:

100 questions:

Easy:
    20

Medium:
    50

Hard:
    25

Advanced:
    5

The system must validate the total.

It should also support subject/topic-specific difficulty requirements where appropriate.

Example:

Physics → Mechanics:

Easy:
    5

Medium:
    8

Hard:
    5

---

# 15. COUNT AND PERCENTAGE CONFIGURATION

Where useful, support:

- absolute question count
- percentage distribution

Example:

Easy:
    20%

Medium:
    50%

Hard:
    25%

Advanced:
    5%

The implementation may normalize this to question counts before test generation.

Avoid duplicate representations in persistent storage unless necessary.

---

# 16. MARKING SCHEME

Assessment must support configurable marking.

Example:

Correct:
    +4

Incorrect:
    -1

Unanswered:
    0

Another assessment may use:

Correct:
    +1

Incorrect:
    0

Unanswered:
    0

Do NOT hardcode one universal marking scheme.

Store the marking configuration with the Assessment/Test Version.

---

# 17. DURATION

Assessment must support configurable duration.

Example:

Topic Test:
    30 minutes

Weekly Test:
    60 minutes

Grand Test:
    180 minutes

Duration must be validated.

Do not allow zero or negative durations.

---

# 18. TOTAL MARKS

Assessment must support:

- total questions
- total marks
- marks per question where applicable
- section marks where applicable
- negative marks

The system must validate internal consistency.

---

# 19. ASSESSMENT DESIGNER — ADMIN

Admin must be able to:

- select Course
- create Assessment
- choose Assessment Category
- choose Assessment Type
- configure Subjects
- configure Topics
- configure difficulty
- configure question counts
- configure marks
- configure duration
- configure marking scheme
- review blueprint
- generate/assemble test
- save draft
- publish
- archive

Admin has unrestricted access within the system's academic scope.

---

# 20. ASSESSMENT DESIGNER — COURSE COORDINATOR

Course Coordinator must be able to design Assessments for Course(s) assigned to them, according to the authorization architecture established by P0-008.

Backend must verify the Course assignment.

A Course Coordinator must NOT be able to manipulate assessments belonging to unrelated Courses.

Do not rely on frontend filtering.

---

# 21. SUBJECT EXPERT

Where P0-008 has established Subject Expert responsibility:

Subject Experts may access/manage assessment content within their permitted Subject scope.

Do not automatically give Subject Experts unrestricted assessment management.

Use existing academic responsibility/authorization architecture.

Do not create a second permission framework.

---

# 22. STUDENT ACCESS

Students must NOT be able to:

- create Assessments
- edit Assessments
- delete Assessments
- configure blueprints
- publish Assessments
- modify marking schemes

Future tasks will allow students to:

- view assigned assessments
- attempt assessments
- submit responses
- view permitted results

---

# 23. ASSESSMENT LIFECYCLE

Reuse the existing Assessment status architecture if available.

At minimum the system should distinguish:

DRAFT
PUBLISHED/ACTIVE
ARCHIVED/INACTIVE

Where more detailed states already exist, preserve them.

Do not create a competing state machine.

---

# 24. ASSESSMENT REVIEW

Before publication, authorized users must be able to review:

- Course
- Assessment Category
- Assessment Type
- duration
- total questions
- total marks
- marking scheme
- Subject distribution
- Topic distribution
- difficulty distribution
- question availability
- selected/generated questions

The review page must clearly identify configuration problems.

---

# 25. PUBLISH VALIDATION

Before publication, validate:

1. Course exists.
2. Course is accessible to the designer.
3. Assessment Category is valid.
4. Assessment Type is valid.
5. Duration is valid.
6. Total question count is valid.
7. Total marks are valid.
8. Subject distribution is valid.
9. Topic distribution is valid.
10. Difficulty distribution is valid.
11. Required questions exist.
12. Questions belong to the permitted Course.
13. Questions satisfy Subject constraints.
14. Questions satisfy Topic constraints.
15. Questions satisfy difficulty constraints.
16. Marking scheme is valid.

If any critical validation fails:

DO NOT publish.

Return actionable validation errors.

---

# 26. QUESTION BANK INTEGRATION

P0-009 must establish the Assessment → Question integration boundary.

The complete Question Bank management module will be implemented in P0-010.

P0-009 should nevertheless be capable of:

- identifying eligible questions
- selecting questions
- associating questions with an Assessment
- validating question metadata
- storing the actual question set used by a published Assessment

Question eligibility may depend on:

- Course
- Subject
- Topic
- Subtopic
- Difficulty
- Question Type
- status

Reuse existing question structures if available.

---

# 27. TEST GENERATION / ASSEMBLY

Implement the mechanism necessary to assemble a test from the Assessment Blueprint where the existing Question Bank permits it.

Example:

Blueprint:

Physics
    Mechanics
        Easy = 5
        Medium = 5
        Hard = 2

The system must select questions satisfying those requirements.

If only:

Easy = 5
Medium = 5
Hard = 3 available

and Hard = 2 required:

selection succeeds.

If:

Hard = 1 available
Hard = 2 required

selection must fail with a meaningful error.

Do NOT silently produce an invalid test.

---

# 28. RANDOM QUESTION SELECTION

Where random selection is used:

- randomize eligible question selection
- preserve the final selected question set

Do not regenerate a different test every time an existing Assessment is viewed.

---

# 29. TEST VERSION / SNAPSHOT

Once an Assessment is published or used, the actual question set must be preserved.

Example:

Assessment:
    Weekly Test 05

Version:
    v1

Questions:
    Q12
    Q35
    Q47
    Q51
    ...

Historical student results must continue to refer to this exact version.

If the underlying Question Bank later changes, historical assessment data must remain reproducible.

---

# 30. VERSIONING

If an already-published Assessment needs substantial modification:

Do not silently mutate the historical version if students have already attempted it.

Create a new Assessment Version where necessary.

At minimum preserve:

- Assessment ID
- Version ID
- question set
- marking configuration
- blueprint
- total marks
- duration
- publication state

---

# 31. TOPIC TEST WORKFLOW

Support:

Course
    ↓
Subject
    ↓
Topic completed
    ↓
Topic Assessment created
    ↓
Blueprint
    ↓
Questions
    ↓
Publish
    ↓
Student later attempts
    ↓
Result later generated

The system must maintain the Topic relationship.

---

# 32. WEEKLY TEST WORKFLOW

Support:

Course
    ↓
Subjects
    ↓
Topics completed during week
    ↓
Weekly Assessment
    ↓
Multi-subject blueprint
    ↓
Questions
    ↓
Review
    ↓
Publish

A Weekly Test must be an independent Assessment record.

Do not overwrite previous Weekly Tests.

---

# 33. MONTHLY TEST WORKFLOW

Support:

Course
    ↓
Multiple Subjects
    ↓
Topics/units completed during month
    ↓
Monthly Assessment
    ↓
Multi-subject blueprint
    ↓
Questions
    ↓
Review
    ↓
Publish

Previous Monthly Tests must remain historically available.

---

# 34. GRAND TEST WORKFLOW

Support:

Course
    ↓
Multiple Subjects
    ↓
Broad syllabus coverage
    ↓
Grand Test
    ↓
Difficulty distribution
    ↓
Question generation/selection
    ↓
Review
    ↓
Publish

Grand Tests should support competitive-examination simulation.

---

# 35. FINAL GRAND TEST WORKFLOW

Support:

Course
    ↓
Multiple Subjects
    ↓
Full/prescribed syllabus
    ↓
Final Grand Test
    ↓
Blueprint
    ↓
Questions
    ↓
Review
    ↓
Publish

Final Grand Tests must remain independently identifiable for final readiness analysis.

---

# 36. STUDENT RESULT DATA MODEL — FOUNDATION

P0-009 must establish the data contract needed for future Student Attempt and Evaluation modules.

The system must eventually be able to represent:

Student
Assessment
Assessment Version
Course
Subject
Topic
Subtopic
Question
Difficulty
Response
Correctness
Marks
Time

Do not implement a score-only result structure.

---

# 37. PERFORMANCE RECORD GRANULARITY

The future evaluation layer must be able to produce records equivalent to:

student_id
course_id
assessment_id
assessment_version_id
assessment_category
assessment_type
assessment_date

subject_id
topic_id
subtopic_id

question_id
question_type
difficulty

marks_available
marks_obtained

correct
incorrect
unanswered

response_time
negative_marks

attempt_number

The exact database implementation may differ, but these dimensions must remain available.

---

# 38. PERFORMANCE ANALYZER CONTRACT

Assessment data must be structured so the future Performance Analyzer can answer:

- What Course?
- What Assessment?
- What Assessment Category?
- What Assessment Type?
- Which Subject?
- Which Topic?
- Which Subtopic?
- Which Question?
- What difficulty?
- Was the answer correct?
- Was it unanswered?
- How many marks?
- How much time?
- What was the accuracy?
- How is performance changing?

The Performance Analyzer implementation is NOT part of P0-009.

The data contract is.

---

# 39. STUDENT PERFORMANCE SHEET

Implement an Admin/Course Coordinator performance sheet for an individual student.

Workflow:

Admin/Course Coordinator
    ↓
Select Course
    ↓
Select Student
    ↓
Performance Sheet

The sheet must consolidate assessment results across:

- Topic Tests
- Weekly Tests
- Monthly Tests
- Grand Tests
- Final Grand Tests

---

# 40. PERFORMANCE SHEET — STUDENT INFORMATION

Display:

- Student Name
- Student ID
- Course
- academic period/session where supported

Do not expose unrelated student information.

---

# 41. PERFORMANCE SHEET — TOPIC TESTS

Display topic-wise results including, where available:

- Subject
- Topic
- Test name
- Test date
- marks obtained
- maximum marks
- percentage
- accuracy
- result/status

Example:

| Subject | Topic | Test | Marks | % |
|---|---|---|---:|---:|
| Mathematics | Probability | Topic Test | 17/20 | 85% |
| Physics | Laws of Motion | Topic Test | 14/20 | 70% |

---

# 42. PERFORMANCE SHEET — WEEKLY TESTS

Display:

| Test | Mathematics | Physics | Chemistry | Total | % |
|---|---:|---:|---:|---:|---:|
| Weekly 01 | 32/40 | 28/40 | 30/40 | 90/120 | 75% |
| Weekly 02 | 35/40 | 25/40 | 32/40 | 92/120 | 76.7% |

Use the actual Subjects belonging to the Course.

Do not hardcode Mathematics/Physics/Chemistry.

---

# 43. PERFORMANCE SHEET — MONTHLY TESTS

Provide monthly assessment results.

Include:

- total marks
- percentage
- subject-wise marks
- subject-wise percentage where available
- test date
- assessment status

---

# 44. PERFORMANCE SHEET — GRAND TESTS

Provide Grand Test results including:

- total score
- percentage
- subject-wise performance
- test date
- rank where a valid ranking system exists
- accuracy where available

Do not invent rank if ranking is not implemented.

---

# 45. PERFORMANCE SHEET — FINAL GRAND TEST

Provide:

- Final Grand Test score
- percentage
- subject-wise performance
- assessment date
- overall status
- progression against previous tests where data permits

---

# 46. PERFORMANCE TREND

Where sufficient result data exists, provide a basic progression view:

Topic Mastery
    ↓
Weekly
    ↓
Monthly
    ↓
Grand
    ↓
Final Grand

The goal is to make progression visible.

Do NOT implement the full Performance Analyzer here.

Do not invent predictive analytics.

---

# 47. SUBJECT-WISE PERFORMANCE

The performance sheet should allow Admin/Course Coordinator to inspect performance by Subject.

Example:

Mathematics:
    Topic Tests Average
    Weekly Average
    Monthly Average
    Grand Test Average
    Final Grand Score

Physics:
    ...

Chemistry:
    ...

This data will later feed the Performance Analyzer.

---

# 48. REPORT CARD

Implement an individual Student Report Card.

Workflow:

Select Student
    ↓
Performance Sheet
    ↓
Generate Report Card
    ↓
Preview
    ↓
Download PDF

---

# 49. REPORT CARD CONTENT

The report card should include:

## Student Information

- Student Name
- Student ID
- Course
- Academic Session/Period where available

## Assessment Summary

- Topic-wise assessments
- Weekly Tests
- Monthly Tests
- Grand Tests
- Final Grand Tests

## Subject Performance

For each Subject:

- marks
- percentage
- assessment-level performance where available

## Overall Performance

- total assessments
- completed assessments
- average performance
- latest performance
- final grand performance where available

Do not invent statistics when insufficient data exists.

---

# 50. REPORT CARD PDF

Generate a professional PDF report card.

Use the existing project PDF/reporting architecture if available.

If no suitable reporting architecture exists, implement the smallest appropriate PDF generation mechanism.

The PDF should be:

- readable
- professional
- printable
- branded with SYS
- structured
- suitable for institutional use

Do not expose internal database IDs unnecessarily in the report.

---

# 51. REPORT CARD DOWNLOAD

Admin and authorized Course Coordinators must be able to download the report card.

The downloaded report must correspond to the selected Student and Course.

Do not allow Course Coordinators to download reports for unrelated Courses.

---

# 52. REPORT CARD HISTORICAL ACCURACY

A generated report must reflect the assessment results available at generation time.

Historical assessment versions must remain stable.

Changing future Question Bank content must not alter historical marks.

---

# 53. ADMIN REPORT ACCESS

Admin:

- can view student performance sheets
- can generate report cards
- can download report cards
- can access all applicable Courses/students

subject to the overall system authorization architecture.

---

# 54. COURSE COORDINATOR REPORT ACCESS

Course Coordinator:

- can view performance of students in assigned Course(s)
- can generate report cards for those students
- can download report cards for those students

Backend must enforce Course scope.

---

# 55. STUDENT REPORT ACCESS

Student report access is NOT the primary scope of P0-009.

Do not expose Admin reporting functionality to students.

Future student portal tasks may provide students with their own performance report.

---

# 56. NOTIFICATION MODULE — CORE REQUIREMENT

Assessment reporting must integrate with a Notification subsystem.

When assessment results/reporting events occur, the system must be capable of notifying:

- Admin
- Course Coordinator
- Other configured higher officials

The email notification architecture must be reusable by future Performance Analyzer alerts.

---

# 57. NOTIFICATION RECIPIENT CONFIGURATION

Do NOT hardcode official email addresses in source code.

Admin must be able to configure notification recipients.

A recipient configuration should support, where appropriate:

- name
- designation
- email
- active/inactive
- notification event types
- Course scope where applicable

Example:

Academic Director
    academic.director@example.edu

Principal
    principal@example.edu

Assessment Coordinator
    assessment@example.edu

---

# 58. NOTIFICATION RECIPIENT TYPES

Support conceptual recipient types:

SYSTEM_ADMIN
COURSE_COORDINATOR
HIGHER_OFFICIAL
CUSTOM_RECIPIENT

Use the actual repository naming conventions.

Do not create unnecessary duplicate User roles.

---

# 59. NOTIFICATION EVENTS

The architecture should support at least:

ASSESSMENT_PUBLISHED
ASSESSMENT_COMPLETED
RESULTS_PUBLISHED
REPORT_GENERATED
REPORT_CARD_GENERATED

Future modules may add:

LOW_PERFORMANCE_ALERT
PERFORMANCE_DECLINE_ALERT
REMEDIAL_REQUIRED

Do not implement Performance Analyzer alerts now.

Prepare the notification architecture for them.

---

# 60. RESULT NOTIFICATION

When results are finalized/published, the notification system should be capable of sending a summary.

Example:

Student:
    Student Name

Course:
    JEE Preparation

Assessment:
    Weekly Test 05

Date:
    12-Aug-2026

Overall:
    78/100
    78%

Subject Performance:

Mathematics:
    82%

Physics:
    74%

Chemistry:
    78%

The actual content must use available data.

Do not fabricate missing fields.

---

# 61. REPORT CARD EMAIL

Where configured, notification should be able to include:

- report summary
- report card attachment OR secure report link

Use the safest architecture available in the repository.

Do not expose sensitive student information through insecure public URLs.

---

# 62. CONSOLIDATED NOTIFICATION

The architecture should support both:

INDIVIDUAL NOTIFICATION

and:

CONSOLIDATED NOTIFICATION

Example:

Instead of sending 500 individual emails for a weekly assessment, the Course Coordinator may receive:

Weekly Assessment Performance Report
    Course: JEE Preparation
    Assessment: Weekly Test 05

    Students: 500

    Average: 72.4%
    Highest: 98%
    Lowest: 31%

    Report attachment/link

The full aggregate analytics implementation can be expanded later.

---

# 63. NOTIFICATION FREQUENCY

Where practical, support configurable policies such as:

IMMEDIATE
DAILY_SUMMARY
WEEKLY_SUMMARY
MONTHLY_SUMMARY

Do not over-engineer scheduling if the existing infrastructure does not support it.

At minimum, design the Notification model so future scheduling is possible.

---

# 64. EMAIL RECIPIENT EXAMPLE

For a Course Assessment:

TO:

admin@institution.edu

CC:

course.coordinator@institution.edu
academic.director@institution.edu
principal@institution.edu

Recipient lists must be configurable.

Do not hardcode these addresses.

---

# 65. NOTIFICATION AUDIT

Every notification attempt must be auditable.

Store information equivalent to:

Notification ID
Event
Assessment
Course
Student/report reference where applicable
Recipients
Created timestamp
Sent timestamp
Status
Failure reason
Retry count

---

# 66. NOTIFICATION STATUS

Support statuses such as:

PENDING
PROCESSING
SENT
FAILED
RETRYING

Use repository conventions if an existing notification model exists.

---

# 67. EMAIL FAILURE ISOLATION

Email failure must NOT cause assessment result persistence to fail.

Correct architecture:

Assessment Result
    ↓
Persist Result
    ↓
Generate Report Data
    ↓
Create Notification Job
    ↓
Email Delivery

If email fails:

Result remains stored.

Notification can be retried independently.

Do NOT wrap database result persistence and external email delivery into one fragile transaction.

---

# 68. EMAIL RETRY FOUNDATION

If email delivery fails:

- record failure
- increment retry count
- allow retry
- preserve failure reason

Do not implement a complex distributed queue unless the existing project already requires it.

---

# 69. NOTIFICATION SECURITY

Do not expose:

- passwords
- authentication tokens
- internal secrets
- database credentials

Do not place sensitive report data into URLs.

Use secure report access if links are used.

---

# 70. EMAIL SERVICE CONFIGURATION

Inspect the existing configuration system.

If email infrastructure exists:

Reuse it.

If it does not:

Implement configuration placeholders through environment variables.

Do not hardcode:

- SMTP passwords
- API keys
- credentials

Use environment configuration.

Update `.env.example` only with safe placeholder names.

---

# 71. FRONTEND ASSESSMENT MANAGEMENT ROUTES

Use existing Next.js routing conventions.

Potential routes:

/assessments
/assessments/new
/assessments/[id]
/assessments/[id]/edit

Potential course integration:

/courses/[id]/assessments

Potential reporting:

/students/[id]/performance

or the equivalent route structure already used by the project.

Do not create duplicate routing patterns.

---

# 72. ASSESSMENT DESIGN UI

Implement a functional Assessment Designer.

Recommended stages:

1. Course
2. Assessment Information
3. Assessment Category
4. Assessment Type
5. Subjects
6. Topics/Subtopics
7. Difficulty
8. Question Distribution
9. Marks/Duration
10. Blueprint Review
11. Question Selection/Generation
12. Final Review
13. Save Draft / Publish

Use the existing SYS UI architecture.

A wizard/stepper is recommended if already supported by the design system.

---

# 73. ASSESSMENT LIST UI

Provide:

- Course filter
- Assessment Category filter
- Assessment Type filter
- Status filter
- search where appropriate
- assessment list
- create action
- view action
- edit action
- publish/archive actions according to permissions

---

# 74. COURSE → ASSESSMENT INTEGRATION

From Course Details:

Course
    ↓
Assessments
    ↓
View Tests
    ↓
Create Assessment

When creating from a Course page:

The Course should already be known.

Do not require the user to re-enter the Course.

---

# 75. PERFORMANCE SHEET UI

Implement:

Student selector
Course selector where appropriate
Assessment summary
Topic Test section
Weekly Test section
Monthly Test section
Grand Test section
Final Grand section
Subject performance
Trend/progression where available
Generate Report Card
Download Report Card

Use tables/cards consistent with existing SYS UI.

---

# 76. NOTIFICATION ADMIN UI

If no existing Notification configuration UI exists, provide an Admin configuration area for:

- recipients
- designation
- email
- active/inactive
- notification event selection

Do not allow ordinary students to modify notification recipients.

---

# 77. SYS BRANDING — MANDATORY

All Assessment, Performance Sheet, Report Card preview and Notification Configuration screens MUST use the established SYS Branding Asset family.

Inspect and reuse:

- SYS logo
- colors
- typography
- theme
- navigation
- cards
- tables
- forms
- buttons
- dialogs
- badges
- status indicators
- loading states
- empty states
- error states

Do NOT invent a new design language.

Assessment pages must look like a natural extension of:

- Dashboard
- Course Management
- Student Management
- Faculty Management

---

# 78. RESPONSIVE DESIGN

Assessment Designer and Performance Sheet should work on:

- desktop
- tablet
- mobile

Complex tables may use responsive scrolling or appropriate stacked layouts.

---

# 79. ACCESSIBILITY

Ensure:

- labels for form fields
- keyboard-accessible controls
- accessible dialogs
- meaningful buttons
- readable validation messages
- semantic tables where appropriate

Reuse existing accessibility patterns.

---

# 80. BACKEND API

Implement or complete APIs according to existing backend conventions.

Potential operations:

GET assessments
GET assessment
GET assessments by Course
POST assessment
PUT/PATCH assessment
DELETE/archive assessment
POST publish
POST generate/assemble
GET assessment blueprint
POST/PUT blueprint
GET student performance
GET student assessment history
GET report card
POST/generate report card
GET notification configuration
POST/PUT notification configuration

IMPORTANT:

Do not create endpoints that already exist.

Inspect first and extend existing APIs.

---

# 81. BACKEND VALIDATION

Backend must validate:

- Course
- Subject
- Topic
- Assessment Category
- Assessment Type
- Difficulty
- Question count
- Marks
- Duration
- Blueprint consistency
- Question eligibility
- Academic responsibility
- publication state

Frontend validation is not sufficient.

---

# 82. AUTHORIZATION MATRIX

At minimum verify:

Unauthenticated:
    Assessment management → 401
    Student performance → 401

Student:
    Assessment management → 403
    Other students' reports → 403

Faculty without applicable responsibility:
    Access according to existing authorization rules

Course Coordinator:
    Assessment management for assigned Course(s)
    Student performance for assigned Course(s)

Subject Expert:
    Access according to assigned Subject responsibility

Admin:
    Full applicable Assessment management
    Full applicable performance reporting
    Notification recipient management

Do not introduce system roles merely to represent academic responsibilities.

---

# 83. DATABASE DESIGN

Reuse existing models where possible.

Potential entities include:

Assessment
AssessmentBlueprint
AssessmentBlueprintItem
AssessmentVersion
AssessmentQuestion
PerformanceRecord/AssessmentResult
Report
NotificationRecipient
Notification

BUT:

Do NOT create all of these automatically.

First inspect the current repository.

If equivalent models already exist, reuse them.

Only introduce genuinely missing structures.

---

# 84. DATABASE MIGRATION

If database changes are necessary:

- create Alembic migration
- preserve existing data
- follow repository naming conventions
- test migration
- avoid destructive operations

If no migration is necessary:

Do NOT create an unnecessary migration.

---

# 85. REPORT DATA ARCHITECTURE

The report generation layer should consume structured result data.

Do not calculate everything directly from frontend state.

Backend should be authoritative for:

- marks
- percentages
- subject totals
- assessment totals
- report data

Frontend should display the authoritative backend result.

---

# 86. PERFORMANCE SHEET DATA API

Provide a backend representation capable of returning something conceptually like:

StudentPerformanceSheet:

    student
    course

    topic_assessments[]
    weekly_tests[]
    monthly_tests[]
    grand_tests[]
    final_grand_tests[]

    subject_summary[]
    overall_summary

The exact schema should follow project conventions.

---

# 87. REPORT CARD DATA API

Provide a backend representation capable of generating:

StudentReportCard:

    student
    course
    academic_period

    assessment_summary
    topic_summary
    weekly_summary
    monthly_summary
    grand_summary
    final_grand_summary

    subject_performance
    overall_performance

Do not calculate institutional analytics in the frontend.

---

# 88. PERFORMANCE ANALYZER INTEGRATION BOUNDARY

P0-009 must expose structured assessment data for the future Performance Analyzer.

The future module must be able to consume:

Course
Student
Assessment
Assessment Category
Assessment Type
Assessment Version
Assessment Date
Subject
Topic
Subtopic
Question
Difficulty
Marks
Correctness
Response Time
Unanswered
Negative Marks

Do not implement Performance Analyzer algorithms in this task.

---

# 89. FUTURE REMEDIAL LEARNING

Assessment data must eventually allow the system to identify:

Weak Subject
Weak Topic
Weak Subtopic
Difficulty-specific weakness
Accuracy problems
Speed problems
Repeated mistakes

P0-009 only establishes the data foundation.

Do not implement remedial recommendations yet.

---

# 90. TESTING — BACKEND

Add tests for:

## Assessment CRUD

- list
- detail
- create
- update
- delete/archive

## Assessment Types

- Topic Test
- Weekly
- Monthly
- Grand
- Final Grand

## Categories

- Topic Mastery
- Periodic Evaluation
- Cumulative Evaluation
- Final Readiness

## Course association

- valid Course
- invalid Course
- unauthorized Course

## Multi-subject

- multiple Subjects
- subject distribution
- invalid totals

## Topic coverage

- valid topic
- invalid topic
- topic belonging to wrong Subject/Course

## Difficulty

- Easy
- Medium
- Hard
- Advanced
- invalid distribution

## Blueprint

- valid blueprint
- inconsistent question count
- insufficient questions
- invalid difficulty requirements

## Authorization

- unauthenticated
- Student
- Faculty
- Course Coordinator
- Subject Expert
- Admin

## Versioning

- published Assessment snapshot
- historical question set preservation where implemented

---

# 91. TESTING — PERFORMANCE REPORTING

Test:

- Student performance retrieval
- Topic assessment history
- Weekly test history
- Monthly test history
- Grand test history
- Final Grand history
- subject summaries
- overall summary
- Course Coordinator scope
- Admin access
- unauthorized access

---

# 92. TESTING — REPORT CARD

Verify:

- report generated for correct Student
- correct Course
- correct assessments included
- correct marks
- correct percentages
- subject summary
- PDF generation
- PDF download
- unauthorized Course access rejected

---

# 93. TESTING — NOTIFICATIONS

Test:

- recipient configuration
- event configuration
- notification creation
- email dispatch where infrastructure is available
- successful notification status
- failed notification status
- retry state
- multiple recipients
- Course Coordinator recipient
- configured higher official recipient
- result persistence when email fails

---

# 94. FRONTEND VERIFICATION

Verify:

Assessment list
Assessment creation
Assessment editing
Blueprint configuration
Difficulty configuration
Subject/topic configuration
Question selection/generation integration
Review
Publish
Archive
Course → Assessment workflow
Student performance sheet
Report card preview
Report card download
Notification configuration

---

# 95. END-TO-END ACCEPTANCE WORKFLOW

Perform the following workflow where the repository supports the required downstream data:

ADMIN / COURSE COORDINATOR
        ↓
Select Course
        ↓
Create Assessment
        ↓
Choose Category
        ↓
Choose Type
        ↓
Configure Subjects
        ↓
Configure Topics
        ↓
Configure Difficulty
        ↓
Configure Questions
        ↓
Configure Marks
        ↓
Configure Duration
        ↓
Validate Blueprint
        ↓
Generate/Assemble Test
        ↓
Review
        ↓
Publish
        ↓
Verify Assessment under Course
        ↓
Verify result/report data path
        ↓
Open Student Performance
        ↓
Generate Report Card
        ↓
Download PDF
        ↓
Verify Notification Event/Configuration

If Student Attempt/Evaluation is not yet implemented in the repository:

Do NOT fake the final result.

Verify the reporting architecture using available data/fixtures and clearly report the boundary.

---

# 96. IMPORTANT: DO NOT FAKE DOWNSTREAM FUNCTIONALITY

If Student Attempt, Evaluation, or Question Bank functionality does not yet exist:

Do NOT create fake/mock production functionality simply to claim the entire workflow passes.

Implement the Assessment interfaces and contracts required by future tasks.

Use test fixtures only inside tests where necessary.

Clearly identify actual remaining downstream dependencies.

---

# 97. NO UNRELATED REFACTORING

Do not redesign:

- authentication
- authorization
- Course Management
- Student Management
- Faculty Management
- global UI
- deployment
- unrelated AI modules

unless directly required.

---

# 98. DEPENDENCY POLICY

Do not add dependencies unless genuinely necessary.

Reuse existing:

- FastAPI
- SQLAlchemy
- Pydantic
- Next.js
- API client
- testing framework
- authentication
- authorization
- PDF/reporting infrastructure
- email infrastructure

Do not perform major framework upgrades.

---

# 99. TOKEN EFFICIENCY

This is a major implementation task.

Prioritize:

1. Functional backend code
2. Database integration
3. API integration
4. Assessment Designer UI
5. Performance reporting
6. Report generation
7. Notification integration
8. Tests
9. Verification
10. Short final report

Do NOT spend excessive Cursor tokens on:

- long explanations
- architecture essays
- repeated summaries
- speculative future designs
- unnecessary documentation
- explaining obvious code

MAXIMIZE ACTUAL CODED FUNCTIONALITY.

---

# 100. GIT SAFETY

DO NOT execute:

git reset --hard
git rebase
git filter-repo
git filter-branch
git push --force

Do not rewrite existing history.

Do not automatically commit unless explicitly instructed.

Before completion:

git status

Do not modify unrelated uncommitted work.

---

# 101. ACCEPTANCE CRITERIA — ASSESSMENT

- [ ] Course-specific Assessment works.
- [ ] Topic Test works.
- [ ] Weekly Test works.
- [ ] Monthly Test works.
- [ ] Grand Test works.
- [ ] Final Grand Test works.
- [ ] Assessment Category is represented.
- [ ] Assessment Type is represented.
- [ ] Multi-subject assessments work.
- [ ] Topic/subtopic coverage works.
- [ ] Difficulty levels work.
- [ ] Marking scheme works.
- [ ] Duration works.
- [ ] Blueprint works.
- [ ] Blueprint validation works.
- [ ] Assessment lifecycle works.
- [ ] Test generation/assembly works where Question Bank permits.

---

# 102. ACCEPTANCE CRITERIA — QUESTION INTEGRATION

- [ ] Eligible questions can be identified.
- [ ] Course boundary is enforced.
- [ ] Subject boundary is enforced.
- [ ] Topic boundary is enforced.
- [ ] Difficulty constraints are enforced.
- [ ] Insufficient question availability is detected.
- [ ] Published test question set is preserved.
- [ ] Historical version is reconstructable.

---

# 103. ACCEPTANCE CRITERIA — PERFORMANCE SHEET

- [ ] Admin can select a Student.
- [ ] Admin can view Student performance.
- [ ] Course Coordinator can view assigned Course students.
- [ ] Topic Tests appear.
- [ ] Weekly Tests appear.
- [ ] Monthly Tests appear.
- [ ] Grand Tests appear.
- [ ] Final Grand Tests appear.
- [ ] Subject-wise performance appears.
- [ ] Overall performance appears.
- [ ] Historical results remain available.

---

# 104. ACCEPTANCE CRITERIA — REPORT CARD

- [ ] Individual report card can be generated.
- [ ] Correct Student is represented.
- [ ] Correct Course is represented.
- [ ] Assessment history is included.
- [ ] Subject performance is included.
- [ ] Overall performance is included.
- [ ] PDF is generated.
- [ ] PDF is downloadable.
- [ ] SYS branding is applied.
- [ ] Unauthorized Course Coordinator access is rejected.

---

# 105. ACCEPTANCE CRITERIA — NOTIFICATION

- [ ] Admin recipients can be configured.
- [ ] Course Coordinator recipients can be resolved.
- [ ] Higher official recipients can be configured.
- [ ] Multiple recipients are supported.
- [ ] Assessment result notification event is supported.
- [ ] Report generation notification event is supported.
- [ ] Notification status is recorded.
- [ ] Failed notifications are recorded.
- [ ] Retry foundation exists.
- [ ] Email failure does not destroy assessment result data.
- [ ] Credentials are environment-configured.
- [ ] No email credentials are hardcoded.

---

# 106. ACCEPTANCE CRITERIA — PERFORMANCE ANALYZER CONTRACT

The implementation must preserve sufficient structured information for future Performance Analyzer integration.

The system must be able to associate performance with:

- [ ] Student
- [ ] Course
- [ ] Assessment
- [ ] Assessment Category
- [ ] Assessment Type
- [ ] Assessment Version
- [ ] Date
- [ ] Subject
- [ ] Topic
- [ ] Subtopic
- [ ] Question
- [ ] Difficulty
- [ ] Marks
- [ ] Correctness
- [ ] Unanswered
- [ ] Response Time
- [ ] Negative Marks

The Performance Analyzer itself is NOT implemented in P0-009.

---

# 107. ACCEPTANCE CRITERIA — SYS BRANDING

- [ ] Existing SYS Branding Asset family inspected.
- [ ] Existing SYS assets reused.
- [ ] Existing theme reused.
- [ ] Existing typography reused.
- [ ] Existing shared components reused.
- [ ] Assessment screens match Course Management.
- [ ] Performance screens match existing SYS UI.
- [ ] Report Card uses SYS branding.
- [ ] No parallel design system created.

---

# 108. ACCEPTANCE CRITERIA — TESTING

- [ ] Backend tests pass.
- [ ] Authorization tests pass.
- [ ] Blueprint tests pass.
- [ ] Multi-subject tests pass.
- [ ] Difficulty tests pass.
- [ ] Reporting tests pass.
- [ ] Report-card tests pass.
- [ ] Notification tests pass.
- [ ] Frontend verification passes.
- [ ] End-to-end verification passes for implemented boundaries.

---

# 109. DATABASE MIGRATION POLICY

If changes to the existing schema are necessary:

- create proper Alembic migration
- preserve existing data
- verify upgrade
- verify downgrade where appropriate
- do not perform destructive changes without necessity

If no schema migration is required:

State:

Database migration:
NO

---

# 110. FINAL RESPONSE TO PROJECT OWNER

Return ONLY:

Files changed:
<list>

Assessment CRUD:
PASS / FAIL

Topic-wise Assessment:
PASS / FAIL

Weekly Assessment:
PASS / FAIL

Monthly Assessment:
PASS / FAIL

Grand Assessment:
PASS / FAIL

Final Grand Assessment:
PASS / FAIL

Multi-subject Assessment:
PASS / FAIL

Assessment Blueprint:
PASS / FAIL

Difficulty Configuration:
PASS / FAIL

Question Integration:
PASS / FAIL / PARTIAL

Test Generation/Assembly:
PASS / FAIL / PARTIAL

Assessment Versioning:
PASS / FAIL / PARTIAL

Student Performance Sheet:
PASS / FAIL / PARTIAL

Individual Report Card:
PASS / FAIL / PARTIAL

PDF Download:
PASS / FAIL

Notification Configuration:
PASS / FAIL

Assessment Report Notification:
PASS / FAIL / PARTIAL

Notification Audit/Retry:
PASS / FAIL / PARTIAL

Performance Analyzer Data Contract:
PASS / FAIL

Academic Authorization:
PASS / FAIL

SYS Branding Verification:
PASS / FAIL

Backend Tests:
PASS / FAIL

Frontend Verification:
PASS / FAIL

End-to-End Verification:
PASS / FAIL / PARTIAL

Database Migration:
YES / NO

Remaining blocker:
<None or concise description>

Do not provide a long explanation.

---

# 111. FINAL IMPLEMENTATION INSTRUCTION

Treat Assessment as one of the CORE BACKBONES of SYS.

The target architecture is:

COURSE
    ↓
ASSESSMENT DESIGN
    │
    ├── TOPIC MASTERY
    │      └── Topic Test
    │
    └── MULTI-SUBJECT EVALUATION
           ├── Weekly Test
           ├── Monthly Test
           ├── Grand Test
           └── Final Grand Test
                    │
                    ▼
             ASSESSMENT BLUEPRINT
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       SUBJECT    TOPIC    DIFFICULTY
          │         │         │
          └─────────┼─────────┘
                    ▼
              QUESTION BANK
                    │
                    ▼
              TEST VERSION
                    │
                    ▼
              STUDENT ATTEMPT
                    │
                    ▼
                EVALUATION
                    │
                    ▼
             STRUCTURED RESULTS
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
     PERFORMANCE  REPORT    NOTIFICATION
       SHEET       CARD        ENGINE
          │         │             │
          │         ▼             ├── Admin
          │        PDF             ├── Coordinator
          │                        └── Higher Officials
          ▼
   PERFORMANCE ANALYZER
          │
          ▼
   LEARNING GAP ANALYSIS
          │
          ▼
    REMEDIAL LEARNING

DO NOT implement this as a generic quiz CRUD module.

DO NOT reduce results to total score.

DO NOT restrict Weekly/Monthly/Grand/Final Grand tests to one Subject.

Weekly, Monthly, Grand and Final Grand assessments MUST be capable of covering multiple Subjects belonging to the selected Course.

Topic Tests are different: they are normally conducted after completion of an individual Topic and primarily measure Topic Mastery.

Admin and authorized Course Coordinators MUST be able to view an individual student's consolidated performance sheet covering all assessment categories.

Admin and authorized Course Coordinators MUST be able to generate and download an individual Student Report Card.

Assessment reporting MUST provide a structured data foundation for the future Performance Analyzer.

Assessment reporting MUST integrate with a configurable Notification system capable of notifying Admin, Course Coordinator and specified higher officials through email.

Notification failure MUST NOT cause assessment result data loss.

Historical published assessment versions MUST remain reproducible.

Use the existing SYS architecture.

Reuse the existing SYS Branding Asset family.

Reuse existing authentication, authorization, Course Management, Student Management and Faculty Management.

Do not recreate existing functionality.

MAXIMIZE ACTUAL CODED FUNCTIONALITY.

MINIMIZE EXPLANATION, DOCUMENTATION AND UNNECESSARY REFACTORING.