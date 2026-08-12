# P0-012 — Performance Analyzer, Learning Gap Detection & Unified Notification Engine

**Priority:** P0 — Critical  
**Dependencies:** P0-009 Assessment Management & Reporting, P0-010 Intelligent Question Knowledge Base, P0-011 Student Assessment Attempt & Evaluation

## 1. Objective

Implement the production-ready **Performance Analyzer and Learning Gap Detection Engine** for SYS and establish a reusable **Unified Notification Engine**.

P0-011 provides real evaluated student assessment data. P0-010 provides question intelligence including historical frequency, weightage, topic priority, question importance, difficulty, concepts, shortcuts, traps, quality and novelty.

P0-012 must transform those inputs into an explainable student learning profile and actionable performance analysis, then distribute appropriate reports/alerts through **Email** and **In-App notifications**, with an architecture ready for **future SMS**.

The Notification Engine is a cross-cutting SYS platform service. Future modules must reuse it rather than implement their own notification systems.

## 2. Architecture

```text
P0-010 Question Intelligence
          +
P0-011 Evaluated Attempts
          ↓
   P0-012 Performance Analyzer
          │
          ├── Overall Analysis
          ├── Subject Analysis
          ├── Topic/Subtopic Analysis
          ├── Concept Analysis
          ├── Difficulty Analysis
          ├── Error Analysis
          ├── Time Analysis
          ├── Trend Analysis
          ├── Learning Gap Detection
          ├── Exam Readiness
          └── Student Learning Profile
                    ↓
             Performance Report
                    ↓
          Unified Notification Engine
             ┌──────┼──────┐
             ↓      ↓      ↓
           Email  In-App  SMS (future)
             ↓      ↓
          Audit / Retry / Delivery Status
```

## 3. Core Principle

The analyzer must **explain performance, not merely display marks**.

For example:

```text
Physics = 61%
```

is reporting.

A useful analysis is:

```text
Mechanics
  Basic concepts: 81%
  Medium: 68%
  Hard: 39%
  Time/question: high
  Repeated errors: Newton's Laws

Possible learning gap:
Application of Newton's Laws in multi-step problems.
```

Clearly distinguish **observed evidence** from **system inference**. Never present an inference as a confirmed diagnosis.

## 4. Analysis Dimensions

Analyze where data exists at:

- Course
- Subject
- Topic/Subtopic
- Concept
- Question
- Difficulty
- Marks/negative marks
- Question type
- Historical importance
- Topic priority
- Question importance
- Time spent
- Shortcut/trap metadata

## 5. Assessment-Type Analysis

Analyze separately:

- Topic-wise tests
- Weekly tests
- Monthly tests
- Grand tests
- Final Grand tests

Identify patterns such as:

```text
Topic Tests       86%
Weekly Tests      82%
Monthly Tests     74%
Grand Tests       61%
Final Grand       57%
```

A possible interpretation is that topic knowledge exists but cumulative retrieval/application is weaker. Treat this as an analytical signal, not a certainty.

## 6. Overall Performance

Calculate and expose:

- total/completed assessments
- average marks/percentage
- accuracy
- attempted/correct/incorrect/unanswered
- average time
- recent performance
- cumulative performance
- improvement/decline
- readiness estimate

Use appropriate weighting rather than blindly averaging percentages.

## 7. Subject / Topic / Concept Analysis

For each relevant subject, topic and concept calculate:

- attempts
- correct
- incorrect
- unanswered
- marks
- percentage
- accuracy
- average time
- recent trend
- difficulty performance
- repeated mistakes
- assessment coverage
- importance/priority context from P0-010

Identify strong, developing and weak concepts.

## 8. Difficulty Analysis

Analyze:

- Easy
- Medium
- Hard
- Advanced

Example:

```text
Easy        92%
Medium      77%
Hard        46%
Advanced    21%
```

Use this to identify whether the student struggles mainly with complex/application questions.

## 9. Time Analysis

Use question-level timing from P0-011.

Detect signals such as:

```text
High accuracy + low time
→ strong fluency signal

High accuracy + excessive time
→ knowledge may exist but fluency may need improvement

Low accuracy + excessive time
→ possible conceptual/application difficulty

Low accuracy + very low time
→ possible guessing/careless-attempt signal
```

These are signals, not definitive diagnoses.

## 10. Repeated Error Detection

Identify repeated errors across assessments.

Example:

```text
Mechanics → Newton's Laws → Hard questions
incorrect across 4 assessments
```

Repeated errors should increase learning-gap confidence.

## 11. Error Taxonomy

Where evidence permits, classify or infer:

- conceptual error
- formula error
- calculation error
- interpretation error
- careless-error signal
- time-pressure signal
- question-selection signal
- incomplete-knowledge signal
- repeated misconception signal

Clearly label observed versus inferred information.

## 12. Learning Gap Classification

Support a consistent classification such as:

```text
MASTERED
STRONG
ADEQUATE
DEVELOPING
WEAK
CRITICAL_GAP
```

Classification should consider multiple signals:

```text
Accuracy
+ Recent performance
+ Historical performance
+ Difficulty
+ Repeated mistakes
+ Time
+ Assessment type
+ Topic importance
+ Question importance
```

Do not determine a significant learning gap from one percentage alone.

## 13. P0-010 Question Intelligence Integration

Use P0-010 intelligence when interpreting performance.

A repeated mistake on a high-frequency/high-priority exam concept should have greater analytical significance than an isolated mistake on a low-priority question.

Every important learning-gap classification should have traceable evidence, for example:

```text
Learning Gap: Mechanics

Evidence:
- 4 assessments
- 11 relevant questions
- 36% accuracy
- repeated high-priority-question errors
- hard-question weakness
```

## 14. Trend Analysis

Identify:

- improving
- declining
- stable
- fluctuating
- recovering
- stagnating

Track trends at course, subject, topic, assessment type and difficulty levels.

## 15. Exam Readiness

For relevant Entrance/Competitive Test courses calculate a readiness **estimate**:

- overall readiness
- subject readiness
- topic readiness
- difficulty readiness
- cumulative-test readiness
- final-exam readiness

Example:

```text
Final Readiness: 68%

Mathematics      81%
Physics          59%
Chemistry        64%
English          72%
```

Clearly label readiness as an estimate, not a guarantee.

## 16. Student Learning Profile

Generate a machine-readable profile containing:

```text
Overall performance
Strengths
Developing areas
Learning gaps
High-priority gaps
Topic performance
Difficulty performance
Assessment-type performance
Trends
Readiness
Evidence
Recommended focus
```

Example:

```text
Overall: 72%

Strengths:
- Probability
- Algebra

Developing:
- Calculus

Critical Gaps:
- Advanced Mechanics

Trend: Improving

Priority:
1. Mechanics
2. Calculus Applications
```

## 17. Performance Analyzer Contract

Reuse the existing P0-009 Performance Analyzer data contract where available.

Do not create a second incompatible performance-data model.

P0-011 evaluated attempts are the source of truth.

Expose a clean machine-readable output for future modules, including:

```text
student_id
course_id
strengths
developing_areas
learning_gaps
high_priority_gaps
topic_performance
difficulty_performance
assessment_type_performance
trends
readiness
evidence
recommended_focus
```

## 18. AI Lecturer Integration

P0-012 must expose data that allows the future AI Lecturer to combine:

```text
P0-010 Topic Intelligence
+
P0-012 Student Learning Profile
```

This should allow future behavior such as:

- emphasize weak/high-priority concepts
- stress probable exam questions
- teach shortcuts
- warn about traps
- generate targeted practice

Do not implement the full AI Lecturer in P0-012.

## 19. Remedial Learning Boundary

P0-012 determines:

```text
WHAT is weak?
WHY does it appear weak?
HOW strong is the evidence?
HOW important is the gap?
```

A future Remedial Learning Engine determines:

```text
WHAT should the student do next?
```

Do not implement the complete remedial-content engine here.

# 20. Performance Reports

Generate a structured SYS-branded performance report containing:

### Summary
- overall performance
- percentage
- accuracy
- trend
- readiness

### Strengths
Strong areas.

### Learning Gaps
Weak/critical areas with evidence.

### Subject Analysis
Subject-level performance.

### Topic Analysis
Topic/subtopic performance.

### Difficulty Analysis
Easy/Medium/Hard/Advanced.

### Assessment-Type Analysis
Topic/Weekly/Monthly/Grand/Final.

### Time Analysis
Where reliable data exists.

### Priority Recommendations
Areas requiring further learning.

Reuse the existing P0-009 PDF/report infrastructure where possible.

## 21. Admin / Course Coordinator / Subject Expert Views

Authorized users should be able to view:

- student performance
- course performance
- subject performance
- topic gaps
- assessment trends
- readiness
- improvement
- declining performance
- students requiring attention
- high-performing students

Authorization must follow existing SYS academic scope:

```text
Subject Expert → assigned subject scope
Course Coordinator → assigned course scope
Admin → authorized institutional scope
```

## 22. Student Dashboard

Provide an understandable student-facing view:

```text
My Performance
Overall: 72%
Status: Improving

Strong Areas
✓ Probability
✓ Algebra

Needs Attention
⚠ Mechanics
⚠ Calculus Applications

Exam Readiness
68%

Priority Focus
1. Mechanics
2. Calculus
```

Do not expose unnecessary internal scoring details.

# 23. Unified Notification Engine

This is a **mandatory cross-cutting P0-012 deliverable**.

Do not implement notification logic only inside Performance Analyzer.

Architecture:

```text
Any SYS Module
      ↓
Notification Event
      ↓
Unified Notification Engine
      ↓
Recipient Resolution
      ↓
Authorization / Academic Scope
      ↓
User Preferences / Policy
      ↓
Channel Selection
      ↓
Email / In-App / Future SMS
      ↓
Audit / Retry / Delivery Status
```

Future modules must call this engine.

## 24. Notification Channels

### Email

Use the existing SMTP configuration and notification foundation.

### In-App

Persist notifications and support:

- unread notifications
- read notifications
- timestamp
- notification type
- severity
- source module
- related entity/report

### Future SMS

Do not implement SMS delivery now.

Provide a channel abstraction so SMS can later be added without changing the core notification/event architecture.

Suggested abstraction:

```text
NotificationChannel
├── EmailChannel
├── InAppChannel
└── SMSChannel (future)
```

## 25. Generic Notification Event

Support a reusable event model containing appropriate fields such as:

```text
event_type
source_module
source_entity
recipient
priority
severity
title
message
payload
channel
status
created_at
sent_at
read_at
retry_count
error
```

Reuse existing P0-009 notification structures where equivalent functionality already exists.

## 26. Performance Notification Events

At minimum support:

### Assessment
- Assessment Evaluated
- Result Available
- Performance Analysis Available

### Periodic
- Weekly Performance Report
- Monthly Performance Report
- Grand Assessment Analysis
- Final Grand Assessment Analysis

### Alerts
- Significant Performance Decline
- Critical Learning Gap
- Repeated Weakness
- Significant Improvement
- Exam Readiness Updated

Do not notify on every individual answer.

## 27. Notifications Across SYS

The engine must be reusable for:

```text
Assessment Published
Assessment Reminder
Assessment Completed
Result Available
Answer Key Available

Performance Report Generated
Learning Gap Detected
Performance Improved
Performance Declined

Learning Recommendation
Remedial Plan Available

Administrative Event
Academic Announcement
System Alert
```

Future modules must use the Unified Notification Engine instead of implementing separate email/in-app systems.

## 28. Recipient Resolution

Notifications must reach **all appropriate users for the scenario**, but never indiscriminately.

Consider:

- role
- course assignment
- subject assignment
- student relationship
- institutional scope
- event type
- configured higher officials
- explicit recipient configuration
- authorization

Examples:

```text
Student
→ own performance/report

Subject Expert
→ assigned subject/student scope

Course Coordinator
→ assigned course/student scope

Admin
→ authorized institutional scope

Higher Official
→ explicitly configured events/reports
```

## 29. Notification Preferences

Provide a foundation for user preferences:

```text
Email
☑ Assessment Results
☑ Performance Reports
☑ Important Academic Alerts

In-App
☑ Academic Notifications

SMS
Future
```

Users may control non-mandatory notification categories.

Mandatory/system-critical notifications follow system policy.

## 30. Notification Severity

Support:

```text
INFO
SUCCESS
WARNING
IMPORTANT
CRITICAL
```

Example:

```text
INFO:
Assessment result available

WARNING:
Performance declined

IMPORTANT:
Repeated weakness detected

CRITICAL:
Configured critical academic alert
```

## 31. Notification Delivery

Support delivery states such as:

```text
PENDING
PROCESSING
SENT
DELIVERED
READ
FAILED
RETRYING
```

Do not claim successful delivery merely because an SMTP request was attempted.

## 32. Retry / Failure Handling

Support:

- retry count
- last error
- next retry time where applicable
- terminal failure
- audit history
- controlled retries

Do not retry indefinitely.

Reuse/enhance P0-009 notification audit/retry functionality where possible.

## 33. In-App Notification UI

Provide:

```text
Notification Bell
      ↓
Unread Count
      ↓
Notification List
      ↓
Open Notification
      ↓
Mark Read
      ↓
Open Authorized Report/Assessment
```

Maintain SYS Branding Asset family and frontend consistency.

## 34. Notification Security

A user must never access another user's private performance report by changing an ID in a URL/API request.

Every notification and related report must re-check authorization.

## 35. Notification Audit

Maintain auditable records for:

- event created
- recipient resolved
- channel selected
- send attempted
- sent
- failed
- retried
- read
- related report/entity

## 36. Database / Migration

Create Alembic migrations only for genuinely new structures.

Potential structures:

```text
PerformanceAnalysis
LearningGap
StudentLearningProfile
Notification
NotificationRecipient
NotificationDelivery
NotificationPreference
```

Before creating any structure, inspect P0-009 and reuse existing equivalent models.

Migration must be deterministic, tested and reversible.

## 37. Backend APIs

Implement clean APIs as required for:

```text
Performance
GET /performance/me
GET /performance/students/{student_id}
GET /performance/courses/{course_id}
GET /performance/subjects/{subject_id}
GET /performance/topics/{topic_id}
GET /performance/trends
GET /performance/learning-gaps
GET /performance/readiness
GET /performance/report

Notifications
GET /notifications
GET /notifications/unread-count
PATCH /notifications/{id}/read
PATCH /notifications/read-all
GET /notifications/preferences
PUT /notifications/preferences
```

Follow existing route/authentication conventions. Do not create unnecessary endpoints.

## 38. Authorization Matrix

At minimum verify:

| Capability | Student | Subject Expert | Coordinator | Admin |
|---|---:|---:|---:|---:|
| Own performance | ✅ | — | — | — |
| Assigned subject performance | — | ✅ | — | ✅ |
| Assigned course performance | — | Limited | ✅ | ✅ |
| Institutional performance | — | — | Limited | ✅ |
| Own notifications | ✅ | ✅ | ✅ | ✅ |
| Own notification preferences | ✅ | ✅ | ✅ | ✅ |
| Higher-official configuration | ❌ | ❌ | Authorized scope | ✅ |

Adapt to the existing SYS authorization implementation.

## 39. Testing

### Performance Analyzer
Test:

- overall analysis
- subject analysis
- topic analysis
- concept analysis
- difficulty analysis
- assessment-type analysis
- time analysis
- trend analysis
- repeated errors
- learning-gap classification
- readiness
- learning profile
- evidence/explainability
- P0-010 integration
- P0-011 integration

### Notification Engine
Test:

- notification creation
- recipient resolution
- academic authorization
- email channel
- in-app channel
- future SMS abstraction
- preferences
- severity/priority
- audit
- retry
- failure
- duplicate prevention where appropriate
- unread/read
- report navigation

### Security
Verify:

- student cannot access another student's performance
- faculty/Subject Expert cannot access unrelated subject data
- Coordinator cannot access unrelated course data
- unauthorized users cannot read another user's notifications
- notification links cannot bypass report authorization

## 40. End-to-End Verification

Use **real database-backed data**.

Required flow:

```text
Student completes P0-011 assessment
        ↓
Server evaluates attempt
        ↓
P0-012 analyzes performance
        ↓
Subject/topic/concept analysis
        ↓
Difficulty/time/error analysis
        ↓
Trend analysis
        ↓
Learning gaps
        ↓
Exam readiness
        ↓
Student Learning Profile
        ↓
Performance Report
        ↓
Notification Event
        ↓
Recipient Resolution
        ↓
Email + In-App notification
        ↓
Authorized user opens notification
        ↓
Authorized performance report
```

Also verify the notification system across:

```text
Student
Faculty / Subject Expert
Course Coordinator
Admin
Configured Higher Official
```

where appropriate.

Do not claim complete E2E success using fixture-only performance data.

# 41. Frontend Requirements

Implement:

```text
Student
├── Performance Dashboard
├── Learning Gaps
├── Trends
├── Readiness
└── Report Access

Admin
├── Performance Dashboard
├── Student Performance
└── Authorized Reports

Course Coordinator
└── Assigned Course Performance

Subject Expert
└── Assigned Subject Performance

All Users
├── Notification Bell
├── Notification List
├── Unread Count
└── Notification Preferences
```

Reuse existing Header, API client, authentication, layout and SYS branding assets.

# 42. Scope Boundary

P0-012 MUST implement:

- Performance Analyzer
- Learning Gap Detection
- Trend Analysis
- Exam Readiness
- Student Learning Profile
- Performance Reports
- Unified Notification Engine
- Email notifications
- In-App notifications
- Notification preferences foundation
- Recipient resolution
- Notification audit
- Retry/failure handling
- Performance-report notifications

P0-012 MUST NOT implement:

- full AI Lecturer
- full Remedial Learning Engine
- SMS delivery
- AI proctoring
- webcam monitoring
- advanced anti-cheating

# 43. Cursor Execution Rules

Before coding:

1. Inspect P0-009 assessment/reporting/notification implementation.
2. Inspect P0-010 Question Intelligence.
3. Inspect P0-011 student attempt/evaluation implementation.
4. Inspect the existing Performance Analyzer data contract.
5. Inspect existing notification audit/retry mechanisms.
6. Inspect existing PDF/report infrastructure.
7. Inspect authentication and academic authorization.
8. Reuse existing structures rather than creating duplicates.

**Prioritize actual implementation and working functionality over lengthy explanations or progress reports.**

Do not modify unrelated modules.

# 44. Deliverables

```text
Backend
├── Performance Analyzer
├── Learning Gap Engine
├── Trend Engine
├── Readiness Engine
├── Student Learning Profile
├── Performance Report Service
├── Unified Notification Engine
├── Recipient Resolution
├── Email Channel
├── In-App Channel
├── Future SMS abstraction
├── Notification Preferences
├── Notification Audit
├── Retry/Failure handling
└── APIs

Frontend
├── Student Performance Dashboard
├── Admin Performance Dashboard
├── Coordinator Performance View
├── Subject Expert Performance View
├── Notification Bell
├── Notification List
├── Notification Preferences
└── Performance Report access

Database
├── Required performance structures
├── Learning gap structures
├── Notification structures
└── Alembic migration(s)

Tests
├── Performance analysis
├── Learning gaps
├── Trends
├── Readiness
├── P0-010 integration
├── P0-011 integration
├── Notification creation
├── Recipient resolution
├── Email
├── In-app
├── Audit
├── Retry
├── Preferences
├── Authorization
└── End-to-end
```

# 45. Definition of Done

P0-012 is complete only when:

```text
Student completes assessment
        ↓
P0-011 evaluates
        ↓
P0-012 analyzes
        ↓
Subject/topic/concept analysis
        ↓
Difficulty/time/error analysis
        ↓
Trend analysis
        ↓
Learning gap detection
        ↓
Exam readiness
        ↓
Student Learning Profile
        ↓
Performance Report
        ↓
Notification Event
        ↓
Recipient Resolution
        ↓
Email + In-App Notification
        ↓
Authorized User opens report
```

And the notification architecture is reusable:

```text
Assessment ───────────┐
Performance Analyzer ─┤
AI Lecturer (future) ─┤
Remedial (future) ────┤
Administration ───────┤
                      ▼
            Unified Notification Engine
                      │
                 ┌────┼────┐
                 ▼    ▼    ▼
               Email In-App SMS (future)
```

Historical integrity:

```text
Historical evaluated attempt
        ↓
Performance analysis
        ↓
Must remain reproducible from
historical evaluated data/snapshot.
```

Security:

```text
Notification opened
      ↓
Authorization checked again
      ↓
Only authorized data returned
```

**P0-012 establishes the adaptive intelligence and notification foundation of SYS: assessment results become explainable learning intelligence, and important academic events become actionable notifications for every appropriate user.**
