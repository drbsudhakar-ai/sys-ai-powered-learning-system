Implement P0-006 — Frontend API Configuration.

Objective: make frontend API configuration consistent with the project's current environment/configuration approach.

Scope:

* Inspect frontend API/base-URL configuration and all usages of `REACT_APP_API_URL`.
* Identify the actual frontend build system and its supported environment-variable convention.
* Replace incorrect/obsolete configuration only where necessary.
* Preserve the current API behavior and routes.
* Do not modify backend code.
* Do not redesign frontend components.
* Do not introduce new dependencies.
* Do not hardcode production URLs.

Verify:

* frontend starts successfully
* API base URL resolves correctly from environment configuration
* no obsolete `REACT_APP_API_URL` references remain where they should not
* existing frontend tests/build pass

Constraints:

* Minimal changes.
* Do not commit or push.
* Keep output very short.

Return only:
Files changed:
Summary:
Tests:
Remaining blocker:
