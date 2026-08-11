# P0-003 — Fix Authentication Password Field Consistency

## Objective

Fix the existing `password` vs `hashed_password` field mismatch in the authentication flow.

## Scope

1. Inspect backend auth models, schemas, CRUD/services, login, registration, and JWT-related code.
2. Identify every inconsistent use of `password` and `hashed_password`.
3. Standardize internal persistence to `hashed_password`.
4. Keep plaintext `password` only where it is required as an input credential; never persist or return it.
5. Preserve the existing API contract unless a change is strictly required.
6. Do not refactor unrelated code.

## Verification

Run targeted authentication tests and relevant existing tests.
Verify:

* registration works
* password is hashed before persistence
* login works with the original password
* incorrect password is rejected
* plaintext password is not returned
* existing application startup still works

## Constraints

* Minimal changes only.
* No new dependencies unless essential.
* Do not modify frontend code unless required by the existing backend contract.
* Do not commit or push.
* Do not generate a long report.

## Output

Return only:

1. Files changed
2. One-line summary
3. Tests run + PASS/FAIL
4. Any remaining blocker
