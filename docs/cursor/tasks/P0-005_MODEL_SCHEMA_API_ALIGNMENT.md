Implement P0-005 — Model/Schema/API Contract Alignment.

Objective: fix confirmed backend model/schema mismatches causing API 500 errors.

Scope:

* Inspect Course and Assessment models, schemas, routes, and existing migrations.
* Align schemas/routes with the fields actually supported by the models.
* Resolve `Assessment.created_at` mismatch.
* Resolve Course `duration`/`category` mismatch.
* Resolve Assessment `description`/`duration`/`difficulty`/`status` mismatch.
* Preserve existing intended API behavior where the model already supports it.
* Add a database migration only if a missing model field is clearly required by the existing application contract.
* Do not redesign models or APIs.
* Do not modify frontend code.
* Do not refactor unrelated code.
* No new dependencies.

Verify:

* course create/update works
* assessment create/update works
* course/assessment responses serialize correctly
* existing authentication/authorization tests still pass
* application startup works
* relevant tests pass

Constraints:

* Minimal changes.
* Do not commit or push.
* Keep output very short.

Return only:
Files changed:
Summary:
Tests:
Remaining blocker:
