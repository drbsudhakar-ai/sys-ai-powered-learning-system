# P0-023 — SYS Course Master and Academic Setup Phases

## Terminology and boundaries

Use **Course** for a SYS learning or examination-preparation offering. Preserve the student's `academic_program` as the separate institutional degree programme. Existing database and API field names such as `programme_code` and `programme_category` remain unchanged for compatibility.

## Phase 1 — Course foundation

Provide an administrator-only, SYS-branded Course Master with a course list, search, filters, genuine readiness counts, unique course codes, category-specific examination information, draft/active publication state, course creation, editing, and a detailed course profile. Preserve the existing student and faculty `/courses` catalogue.

## Phase 2 — Structured syllabus

Introduce the full academic hierarchy **Course → Subject → Unit → Topic → Subtopic**. Add the missing Unit database model through a compatible migration, provide administrator syllabus authoring, enable structured Excel import, validate duplicate/order relationships, and preserve existing Subject → Topic → Subtopic data during migration.

## Phase 3 — Academic ownership

Assign course coordinators and subject experts from authenticated faculty master records. Define ownership scope, reassignment, responsibility visibility, and a controlled handoff from administrator setup to academic experts.

## Phase 4 — Weightages and approval

Allow authorized coordinators and subject experts to propose subject, unit, topic, and subtopic weightages. Validate sibling totals, support review and approval, preserve audit history, and publish only approved academic priorities.

## Phase 5 — Academic integration

Connect the approved course structure and priorities to student enrollment, learning sessions, assessments, question intelligence, mastery, performance analytics, early warnings, personalized learning journeys, and remedial support. Display honest empty states until real pilot data exists.
