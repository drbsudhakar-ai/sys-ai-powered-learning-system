Implement P0-004 — Authorization / Role Enforcement.

Objective: verify and fix backend role-based access control so protected endpoints enforce the user's role correctly.

Scope:

* Inspect existing auth dependencies, current-user logic, role checks, and protected routes.
* Identify missing or inconsistent role enforcement.
* Fix only confirmed authorization defects.
* Preserve existing API contracts.
* Do not redesign authentication or authorization.
* Do not modify frontend code.
* Do not refactor unrelated code.
* No new dependencies unless essential.

Verify:

* unauthenticated access to protected endpoints is rejected
* authenticated users can access permitted endpoints
* users with insufficient roles are rejected
* admin/faculty/student role restrictions match the existing application design
* existing authentication tests still pass
* application startup still works

Constraints:

* Minimal changes.
* Do not commit or push.
* Keep output very short.

Final response only:

1. Files changed
2. One-line summary
3. Tests: PASS/FAIL
4. Remaining blocker, if any
