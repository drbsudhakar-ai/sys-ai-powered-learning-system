# P0-010 — Intelligent Academic Question Knowledge Base & Question Intelligence Engine

**Priority:** P0 — Critical  
**Type:** End-to-End Feature  
**Dependencies:** P0-007 Course Management, P0-008 Academic Responsibility Management, P0-009 Assessment Management  
**Primary consumers:** AI Lecturer, Assessment Engine, Performance Analyzer, Remedial Learning

---

## 1. Objective

Implement a production-ready **Intelligent Academic Question Knowledge Base and Question Intelligence Engine** for SYS.

This must **not** be implemented as simple Question CRUD.

The system must maintain structured question knowledge and derive examination intelligence from:

- Course
- Subject
- Topic
- Subtopic
- Syllabus
- Real examination pattern
- Subject marks weightage
- Topic marks/question weightage
- Previous question papers
- Historical question frequency
- Historical concept frequency
- Recent examination trends
- Topic priority
- Difficulty distribution
- Question type distribution
- Question quality
- Question reuse/history
- Question similarity
- Common question patterns
- Shortcuts/alternative solving methods
- Common mistakes/traps

The resulting intelligence must be usable by:

```text
                Question Intelligence
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
   AI Lecturer     Assessment Engine   Analytics
        │               │                │
        ▼               ▼                ▼
 Important Topics   Test Generation   Performance
 Question Patterns  Grand/Final Paper   Analysis
 Shortcuts                              │
                                        ▼
                                Remedial Learning
```

---

## 2. Core Design Principle

The Question Intelligence Engine should answer four major questions:

### A. What should students learn?

Based on:

- syllabus
- topic importance
- examination weightage
- historical relevance

### B. What questions are students likely to encounter?

Based on:

- historical question patterns
- frequency
- concept recurrence
- recent trends
- examination blueprint

### C. How should students solve them?

Based on:

- formulas
- shortcuts
- alternative methods
- elimination strategies
- time-saving techniques
- common traps

### D. Which questions should be selected for an assessment?

Based on:

- assessment blueprint
- subject/topic weightage
- difficulty
- question type
- historical relevance
- novelty/reuse policy
- syllabus coverage
- quality
- duplication/similarity

---

## 3. Question Bank Data Model

Extend the existing backend model architecture without breaking existing functionality.

Each question should support at least:

```text
Question
├── id
├── course_id
├── subject_id
├── topic_id
├── subtopic_id
├── question_type
├── question_text
├── options
├── correct_answer
├── explanation
├── marks
├── negative_marks
├── difficulty
├── status
├── source
├── source_year
├── exam_name
├── concept_tags
├── learning_objective
├── shortcut
├── alternative_solution
├── common_traps
├── estimated_time
├── quality_score
├── created_by
├── created_at
└── updated_at
```

Use the existing SYS Course/Subject/Faculty responsibility relationships.

Do not create duplicate representations of existing academic entities.

---

## 4. Question Types

Implement an extensible architecture supporting at minimum:

- Single-answer MCQ
- Multiple-answer MCQ
- True/False
- Fill-in-the-blank

The schema should permit future types without requiring a major database redesign.

---

## 5. Question Lifecycle

Implement:

```text
DRAFT
   ↓
REVIEW
   ↓
APPROVED
   ↓
ACTIVE
   ↓
ARCHIVED
```

Permissions:

### Admin

Full access.

### Course Coordinator

Manage questions belonging to assigned courses.

### Subject Expert

Create/review/manage questions belonging to assigned subject responsibility.

### Student

No question authoring or question-bank administration access.

Reuse P0-008 authorization rather than creating a second permission system.

---

## 6. Question Authoring UI

Implement a usable frontend for authorized academic staff.

The authoring workflow:

```text
Course
 ↓
Subject
 ↓
Topic
 ↓
Subtopic
 ↓
Question Type
 ↓
Question
 ↓
Options
 ↓
Correct Answer
 ↓
Explanation
 ↓
Difficulty
 ↓
Marks / Negative Marks
 ↓
Shortcut
 ↓
Common Trap
 ↓
Preview
 ↓
Save
```

Include:

- create
- edit
- preview
- duplicate
- archive
- search
- filter
- pagination

Do not build only backend APIs.

---

## 7. Historical Question Paper Repository

Implement support for storing/analyzing previous examination questions.

Historical records must preserve:

```text
Exam
Exam Year
Course/Exam Type
Subject
Topic
Subtopic
Question
Question Type
Marks
Difficulty
Concept
Source
```

The system should distinguish:

### Exact previous question

Same/sufficiently identical question.

### Similar question

Different wording/numbers but substantially similar structure.

### Concept variant

Same underlying concept with a different problem formulation.

### Novel question

New question targeting the same syllabus/concept.

This distinction will later control question reuse in Grand/Final assessments.

---

## 8. Historical Examination Analysis

Implement backend logic to calculate statistics such as:

```text
Topic Frequency
Concept Frequency
Question Frequency
Subject Weightage
Topic Weightage
Difficulty Distribution
Question-Type Distribution
Year-over-Year Trend
Recent Trend
```

Example:

```text
Topic: Probability

Historical frequency: 8/10 exams
Average marks weightage: 7.5%
Recent trend: Increasing
Priority: HIGH
```

The implementation must store derived values where appropriate so that they can be efficiently consumed by other modules.

---

## 9. Topic Priority Engine

Implement a configurable **Topic Priority Score**.

The score should consider factors such as:

```text
Historical Exam Weightage
+
Historical Frequency
+
Concept Frequency
+
Recent Trend
+
Current Syllabus Importance
+
Exam Pattern Relevance
```

Do **not** hard-code arbitrary weights without making the weighting mechanism configurable.

The system should produce categories such as:

```text
VERY_HIGH
HIGH
MEDIUM
LOW
```

The calculation should be deterministic and explainable.

For every priority score, retain the contributing factors so the Admin/Course Coordinator can understand **why** a topic received that priority.

---

## 10. Examination Weightage Engine

Support configuration at multiple levels:

```text
Course
 ├── Subject Weightage
 │
 └── Subject
      ├── Topic Weightage
      │
      └── Topic
           └── Subtopic Weightage
```

Example:

```text
Mathematics       40%
Physics           30%
Chemistry         30%
```

and:

```text
Mathematics
 ├── Calculus              30%
 ├── Algebra               25%
 ├── Coordinate Geometry   20%
 └── Other                 25%
```

The Assessment Engine must eventually be able to use this information when generating tests.

---

## 11. Question Importance Score

Implement a question-level ranking mechanism.

Question importance should consider factors such as:

```text
Topic Priority
Historical Concept Frequency
Question Pattern Frequency
Exam Relevance
Difficulty Fit
Question Quality
Recency
Novelty
```

Return an explainable score.

For example:

```text
Question Importance: 0.87

Contributing factors:
Topic Priority       HIGH
Historical Frequency HIGH
Recent Trend         HIGH
Quality              0.92
Difficulty Fit       GOOD
```

Do not make this an opaque AI score.

---

## 12. Question Similarity / Duplicate Protection

Implement protection against:

- exact duplicate questions
- near duplicates
- repeated question variants

The initial implementation may use deterministic/text-based similarity techniques where appropriate.

The architecture should later support embedding/semantic similarity without requiring a database redesign.

The objective is to prevent Grand/Final papers from accidentally containing excessive duplicates.

---

## 13. Question Selection Engine

This is the most important functional component of P0-010.

Create a backend service/API capable of receiving requirements such as:

```text
Course
Subject(s)
Topic(s)
Question count
Difficulty distribution
Question-type distribution
Marks distribution
Historical relevance
Novelty requirement
Previous-question reuse policy
```

and return ranked eligible questions.

Example request conceptually:

```text
Course: Entrance Exam Preparation
Questions: 100

Physics: 30%
Chemistry: 30%
Mathematics: 40%

Difficulty:
Easy: 20%
Medium: 50%
Hard: 25%
Advanced: 5%

Historical relevance: HIGH
Exact previous questions: 0%
Concept variants: allowed
Novel questions: preferred
```

The engine should produce a candidate pool and ranked selections.

---

## 14. Scientifically/Evidence-Based Grand & Final Question Selection

This is a **critical requirement**.

For Grand Tests and Final Grand Tests, the system must select questions using an evidence-based ranking/probability approach.

The engine should consider:

```text
Official/Configured Exam Blueprint
        +
Historical Weightage
        +
Historical Frequency
        +
Recent Trends
        +
Topic Priority
        +
Concept Importance
        +
Difficulty Distribution
        +
Question Quality
        +
Novelty
        +
Syllabus Coverage
        +
Question Diversity
```

Then:

```text
Candidate Pool
      ↓
Eligibility Filtering
      ↓
Weighted Ranking
      ↓
Constraint Satisfaction
      ↓
Duplicate/Semantic Similarity Check
      ↓
Coverage Check
      ↓
Difficulty Check
      ↓
Final Paper
```

### Important

Do **not** claim that SYS can predict exact future exam questions.

The system should describe results as:

- historically high-priority
- highly exam-relevant
- frequently tested
- statistically important
- high-probability based on available historical evidence

This distinction must be reflected in the UI and API documentation.

---

## 15. AI Lecturer Integration

Expose an API/service that allows the AI Lecturer to request topic intelligence.

For a topic, it should be able to retrieve:

```text
Topic Priority
Exam Weightage
Historical Frequency
Recent Trend
Frequently Tested Concepts
Important Question Patterns
Representative Questions
Shortcuts
Alternative Solutions
Common Traps
Typical Difficulty
Estimated Solving Time
```

Example conceptual endpoint:

```text
GET /academic-intelligence/topics/{topic_id}
```

The response should contain enough structured information for the AI Lecturer to say:

> "This is a high-priority concept based on historical examination patterns."

and then emphasize:

- likely question patterns
- important formulas
- shortcuts
- elimination techniques
- common mistakes
- time-saving approaches

The AI Lecturer should **not blindly expose internal scores** to students unless explicitly designed for student-facing presentation.

---

## 16. Lecture-to-Question Intelligence

The intelligence layer must support this workflow:

```text
AI Lecturer explains Topic
        ↓
Retrieve Topic Intelligence
        ↓
Identify high-priority concepts
        ↓
Explain important question patterns
        ↓
Demonstrate representative questions
        ↓
Teach shortcut/fast solving method
        ↓
Highlight common trap
        ↓
Give practice question
```

This must be treated as a core SYS requirement, not a future afterthought.

---

## 17. Assessment Integration

P0-009 should be able to consume the Question Intelligence Engine.

Do not duplicate question-selection logic inside the Assessment module.

The architecture should be:

```text
Assessment Blueprint
        ↓
Question Intelligence Engine
        ↓
Eligible Question Pool
        ↓
Ranked Questions
        ↓
Assessment Paper
```

Support:

- Topic Tests
- Weekly Tests
- Monthly Tests
- Grand Tests
- Final Grand Tests

The periodic/cumulative/final assessments may span **multiple subjects within a course**.

---

## 18. Question Reuse Policy

Support configurable policies:

```text
EXACT_PREVIOUS
CONCEPT_VARIANT
NOVEL
MIXED
```

For example:

```text
Grand Test:
Exact previous questions     10%
Concept variants              40%
Novel questions               50%
```

These are examples only; the percentages must be configurable.

---

## 19. Question Quality Controls

Implement validation for:

- missing answer
- invalid options
- inconsistent marks
- invalid difficulty
- incomplete explanation
- duplicate question
- duplicate options
- invalid topic/course relationship
- unauthorized author
- archived question selected for active assessment

Where possible, reject invalid data before it enters the active question pool.

---

## 20. Admin/Coordinator Intelligence Dashboard

Provide a basic UI showing:

### Topic intelligence

```text
Topic
Priority
Historical Frequency
Weightage
Trend
Question Count
```

### Question bank

```text
Total Questions
By Subject
By Topic
By Difficulty
By Status
By Type
```

### Historical analysis

```text
Exam Year
Subject Distribution
Topic Distribution
Difficulty Distribution
```

Keep this dashboard functional and concise. Do not spend excessive time on visual polish.

---

## 21. API Requirements

Implement clean APIs for:

```text
Question CRUD
Question Search
Question Filtering

Historical Paper CRUD
Historical Analysis

Topic Intelligence
Topic Priority
Topic Weightage

Question Importance
Question Similarity

Question Candidate Selection
Assessment Question Generation

AI Lecturer Topic Intelligence
```

Follow existing SYS authentication and authorization patterns.

---

## 22. Database Migration

Create an Alembic migration for all genuinely new database structures.

Do not modify existing tables unnecessarily.

Migration must be:

- reversible
- deterministic
- compatible with existing database
- tested

---

## 23. Testing Requirements

Backend tests must cover at minimum:

### Authorization

```text
Unauthenticated
Student
Faculty
Subject Expert
Course Coordinator
Admin
```

### Question lifecycle

```text
Create
Read
Update
Archive
Duplicate
```

### Academic ownership

Verify Subject Expert/Course Coordinator restrictions.

### Weightage

Verify subject/topic weightage calculations.

### Historical analysis

Verify frequency and trend calculations using deterministic test fixtures.

### Topic priority

Verify priority calculation.

### Question ranking

Verify deterministic ranking for known test data.

### Duplicate detection

Verify exact and near duplicate handling.

### Selection constraints

Verify:

- subject distribution
- topic distribution
- difficulty distribution
- question-type distribution
- novelty/reuse policy
- syllabus coverage

### Grand/Final selection

Create a realistic fixture representing historical papers and verify that the generated candidate set respects the configured blueprint and evidence-based ranking.

---

## 24. Frontend Verification

Verify:

- Question Bank
- Question creation
- Question editing
- Question preview
- Question filtering
- Historical question management
- Topic intelligence
- Weightage configuration
- Question-selection preview
- authorization behavior

---

## 25. SYS Branding

All new frontend pages must follow the existing **SYS Branding Asset family and frontend consistency** already established in previous tasks.

Do not introduce a separate visual language.

Reuse:

- existing Header
- existing navigation
- existing layout
- existing typography
- existing components
- existing branding assets

---

## 26. Important Scope Boundary

Do **not** implement the complete Student Assessment Attempt Engine in P0-010.

Do **not** implement the complete Performance Analyzer.

Do **not** implement the complete AI Lecturer.

Instead, create the **stable APIs/data contracts** that allow those modules to consume Question Intelligence.

P0-010 is responsible for building the **academic question intelligence foundation**.

---

## 27. Deliverables

```text
Backend
├── Question models
├── Historical question models
├── Intelligence services
├── Weightage engine
├── Priority engine
├── Ranking engine
├── Selection engine
├── APIs
└── Alembic migration

Frontend
├── Question Bank
├── Question Authoring
├── Historical Questions
├── Topic Intelligence
├── Weightage Management
└── Question Selection Preview

Tests
├── Authorization
├── CRUD
├── Historical analysis
├── Priority
├── Ranking
├── Duplicate detection
├── Selection constraints
└── Grand/Final generation scenarios
```

---

## 28. Cursor Execution Rule

**Prioritize implementation over explanation.**

Do not spend large token budgets generating lengthy implementation reports.

At the end provide only:

```text
Files changed:
...

Features completed:
...

Backend tests:
PASS/FAIL

Frontend verification:
PASS/FAIL

Question intelligence verification:
PASS/FAIL

Historical analysis verification:
PASS/FAIL

Grand/Final selection verification:
PASS/FAIL

Database migration:
YES/NO

Remaining blockers:
...
```

Do not modify unrelated modules.

Do not rewrite working P0-007/P0-008 functionality unless required for integration.

---

## Definition of Done

P0-010 is complete only when this complete flow works:

```text
Course
  ↓
Subject
  ↓
Topic
  ↓
Question Bank
  ↓
Historical Question Papers
  ↓
Historical Analysis
  ↓
Topic Weightage
  ↓
Topic Priority
  ↓
Question Importance
  ↓
Question Ranking
  ↓
Assessment Blueprint
  ↓
Question Selection
  ↓
Grand/Final Paper Candidate Set
```

And independently:

```text
Topic
  ↓
Academic Intelligence
  ↓
AI Lecturer API
  ↓
Important Concepts
  ↓
Important Question Patterns
  ↓
Shortcuts
  ↓
Common Traps
```

**This P0-010 establishes the intelligence foundation that makes SYS different from a conventional LMS + online examination system.**
