# Gateway Review Findings

This document captures the implementation review against:

- `docs/developer/api_architecture.md`
- `docs/developer/implementation_plan.md`
- `docs/developer/implementation_tasks.md`

It is intended as a durable follow-up list, not as a release gate checklist.

## Overall Status

The current gateway implementation covers most of the core domain, application, persistence, cache, and Geldstrom anti-corruption-layer slices.

The implementation is not complete against the documented target architecture.

The largest missing areas are still:

- Milestone `C10`: health evaluation use case
- Milestone `C11`: administration use cases
- Milestone `G1` to `G3`: bootstrap, lifecycle, and logging
- Milestone `H1` to `H5`: FastAPI presentation layer
- Milestone `I1` to `I3`: Typer admin CLI
- Milestone `J1` to `J2`: security regression and end-to-end smoke coverage

That means the backend core is present, but the documented runtime composition and public surfaces are still not delivered.

## High Severity Findings

### 1. Pending operation state retains the raw bank password

Status:

- open

Where:

- `apps/gateway/gateway/infrastructure/banking/geldstrom/serialization.py`
- `apps/gateway/gateway/infrastructure/banking/geldstrom/connector.py`

Why it matters:

- The gateway currently serializes the presented bank password into pending-operation session state.
- This is explicitly at odds with the intended secret-minimization direction.
- A compromise of in-memory pending operation state would expose reusable bank credentials.

Evidence:

- `serialize_pending_operation(...)` persists the `password` field.
- `_serialize_pending_state(...)` passes `credentials.password.value.get_secret_value()` into that payload.
- `resume_operation(...)` reconstructs credentials from the stored password.

Fixability assessment:

- not an easy gateway-only fix

Reasoning:

- The serialized `FinTSSessionState` itself does not include the PIN/password.
- However, resumed Geldstrom flows still rebuild the client from full `GatewayCredentials` and the FinTS adapter constructs authentication mechanisms with `pin=str(creds.pin)` during resumed dialog work.
- In practice this means the current resumed-session design still depends on the bank PIN.
- Removing the password from gateway pending state would therefore require either:
  - changing Geldstrom so resumed operations can continue from session state without a PIN, or
  - redesigning the gateway pending flow so resumed polling reacquires credentials through another mechanism.

Recommended next step:

- treat this as a design task spanning gateway and Geldstrom, not as a local cleanup

### 2. Error vocabulary is behind the documented API contract

Status:

- open

Where:

- `apps/gateway/gateway/application/common/errors.py`
- Geldstrom connector exception mapping paths

Why it matters:

- The current application error set is small and generic.
- The documented HTTP contract expects clearer, stable failure categories for presentation-layer mapping.
- If the HTTP layer is added on top of the current vocabulary, it will either invent transport-specific logic or collapse distinct bank failures into the same response shape.

Examples:

- authentication failures and temporary upstream failures are not separated cleanly
- unsupported bank capabilities are not modeled separately
- pending-operation-specific failure causes are still free-form strings

Fixability assessment:

- moderate effort, but local to the gateway codebase

Reasoning:

- This does not appear to require upstream Geldstrom redesign.
- It does require deliberate expansion of the application error model and a review of connector exception translation.

Recommended next step:

- define the target gateway error taxonomy before starting Milestone `H`

## Medium Severity Findings

### 3. Failed pending sessions retain opaque session blobs

Where:

- `apps/gateway/gateway/application/operation_sessions/resume_pending_operations.py`
- `apps/gateway/gateway/application/banking_gateway/get_operation_status.py`

Why it matters:

- Completed sessions are deleted on read.
- Failed sessions are returned but kept in the in-memory session store together with their opaque `session_state`.
- This retains more sensitive runtime material than needed after the operation can no longer progress.

Fixability assessment:

- easy

Recommended direction:

- clear `session_state` when a session transitions to `FAILED`
- consider deleting failed sessions after the first status read, mirroring completed sessions

### 4. Transaction date ranges are not validated

Where:

- `apps/gateway/gateway/application/banking_gateway/fetch_transactions.py`

Why it matters:

- `_resolve_date_range(...)` fills defaults but does not reject `start_date > end_date`.
- Invalid ranges can flow into the connector and fail later in a less controlled way.

Fixability assessment:

- easy

Recommended direction:

- reject invalid ranges in the application layer with a stable validation error before the connector is called

### 5. In-memory current product key provider has no synchronization

Where:

- `apps/gateway/gateway/infrastructure/cache/memory/current_product_key_provider.py`

Why it matters:

- The provider is a mutable shared runtime component.
- Reads and writes are unsynchronized.
- This is unlikely to corrupt Python memory, but it does make concurrent visibility semantics unclear in an async multi-task process.

Fixability assessment:

- easy

Recommended direction:

- protect load/read operations with an `asyncio.Lock` or replace the mutable slot with a small synchronized holder

### 6. Application use cases still depend on the current product key provider

Where:

- `apps/gateway/gateway/application/banking_gateway/list_accounts.py`
- `apps/gateway/gateway/application/banking_gateway/fetch_transactions.py`
- `apps/gateway/gateway/application/banking_gateway/get_tan_methods.py`

Why it matters:

- Task `F2` explicitly notes that product key access should be internal to the connector.
- The application layer currently calls `require_current()` before invoking the connector.
- This duplicates connector responsibilities and slightly weakens the anti-corruption boundary.

Fixability assessment:

- moderate

Recommended direction:

- remove this dependency from the use cases and let connector construction and connector execution own product-key availability fully

### 7. Schema drifts from the documented `CITEXT` email storage

Where:

- `apps/gateway/gateway/infrastructure/persistence/postgres/schema.py`

Why it matters:

- `api_consumers.email` is currently stored as `String(320)`.
- The architecture docs call for case-insensitive email handling in PostgreSQL.
- If this is left as-is, unique-email semantics will depend on application normalization rather than DB guarantees.

Fixability assessment:

- moderate

Recommended direction:

- either adopt `CITEXT` in schema/bootstrap or explicitly update the docs if normalized `VARCHAR` is the intended design

## Low Severity Findings

### 8. `_raise_for_unsupported_pending` appears to be dead code

Where:

- `apps/gateway/gateway/infrastructure/banking/geldstrom/connector.py`

Why it matters:

- The helper currently returns immediately when `client.session_state is not None` and otherwise does nothing.
- It does not raise, log, or enforce any condition.

Fixability assessment:

- easy

Recommended direction:

- remove it or replace it with an actual invariant check

### 9. Some failure reasons are still stringly typed

Where:

- pending-operation failure paths in the connector and application envelopes

Why it matters:

- This makes downstream mapping and future API stability harder.

Fixability assessment:

- moderate

Recommended direction:

- introduce structured failure categories before the HTTP layer is implemented

## Architectural Completeness Gaps

The following documented milestones are still missing entirely or effectively missing:

- `C10` health use case implementation
- `C11` administration use cases for consumer, institute, and product-key operations
- `G1` settings and composition root
- `G2` startup and shutdown orchestration
- `G3` structured logging bootstrap
- `H1` to `H5` FastAPI app, schemas, middleware, dependencies, and routers
- `I1` to `I3` Typer CLI app and commands
- `J1` secret-regression suite
- `J2` end-to-end smoke integration slice

These are not code smells so much as remaining delivery scope.

## Suggested Remediation Order

1. Decide how pending-session secret handling should work across gateway and Geldstrom.
2. Expand and stabilize the application error taxonomy before starting the HTTP layer.
3. Apply the easy runtime cleanups: failed-session scrubbing, date-range validation, product-key provider synchronization, dead-code removal.
4. Resolve the email storage contract by either implementing `CITEXT` or updating the docs.
5. Start Milestone `G` only after the above boundary decisions are settled.

## High Severity Summary

Can the high-severity issues be fixed easily?

- Pending-session password retention: no, not with a small gateway-only patch. It appears to require a resumed-session design change in Geldstrom or a broader gateway flow redesign.
- Error vocabulary gap: yes, relative to the first issue. It is a contained gateway refactor, but it should be designed intentionally before the HTTP layer is built.