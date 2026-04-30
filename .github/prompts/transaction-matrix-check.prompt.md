---
description: "Run the transaction fetch test matrix: for each bank in .env (active and commented), test 365/100/30-day fetches via both the gateway CLI and the sync client, then compare and report"
name: "Transaction Matrix Check"
agent: "agent"
---

Run the full transaction fetch test matrix against the deployed gateway.
This validates pagination, CAMT/MT940 handling, and the decoupled 2FA flow
across all banks configured in `.env` and across two client paths:

- **Gateway CLI** (`geldstrom-cli`) — uses `FinTS3ClientDecoupled` via the gateway
- **Sync client** (`examples/fetch_transactions.py`) — uses `FinTS3Client` directly

## Prerequisites

Ensure the gateway is deployed and healthy before running this check.
If not already running, follow the deployment-check prompt (steps 1–8) first.

Verify readiness:
```bash
curl -s http://localhost:8000/health/ready
```
Expected: all checks `"ok"`. If not ready, run `docker compose up -d` and wait.

Also verify the `.env` exists and has a `GATEWAY_API_KEY`:
```bash
grep GATEWAY_API_KEY .env
```

## Step 1: Discover All Bank Credential Blocks

Read `.env` and extract **every** bank credential block — both active
(uncommented) and inactive (commented out with `#`).

A bank block is a group of six variables:
```
FINTS_BLZ, FINTS_USER, FINTS_PIN, FINTS_SERVER, FINTS_TAN_MEDIUM, FINTS_TAN_METHOD
```

For each block found, note:
- Which variables are uncommented (active) vs commented
- The BLZ value (strip leading `#` and whitespace)

Then look up each BLZ via the gateway to get the bank name:
```bash
API_KEY=$(grep GATEWAY_API_KEY .env | cut -d= -f2 | tr -d '"')
curl -s -H "Authorization: Bearer $API_KEY" http://localhost:8000/v1/lookup/<BLZ>
```

List all discovered banks before running any tests.

## Step 2: Test Each Bank

Repeat Steps 2a–2d for **every** bank block (active and inactive).

### Step 2a: Activate Bank Credentials

If the block is already active (uncommented), proceed directly.

If the block is **currently commented out**:
1. Save the current active block so you can restore it later.
2. Comment out the currently active block in `.env`.
3. Uncomment the target bank block.
4. Verify the edit looks correct before proceeding — do not mix lines from
   different bank blocks. The `FINTS_PRODUCT_ID`, `FINTS_PRODUCT_VERSION`,
   and `GATEWAY_API_KEY` lines are shared and must remain uncommented.

> Note: The gateway server reads bank credentials from the CLI request body
> at runtime, not from `.env`. Editing `.env` only affects the CLI tools and
> sync example scripts, not the already-running gateway container.

### Step 2b: Get an IBAN

```bash
geldstrom-cli accounts --env-file .env
```

Note the IBAN for the main current account (Girokonto). Use this for all
three fetch tests below.

### Step 2c: Gateway CLI Tests (FinTS3ClientDecoupled)

Run all three tests. For TAN-requiring tests, approve the push notification
when prompted.

```bash
geldstrom-cli transactions <IBAN> --days 365 --env-file .env
geldstrom-cli transactions <IBAN> --days 100 --env-file .env
geldstrom-cli transactions <IBAN> --days 30  --env-file .env
```

After each run, capture:
- Whether 2FA was prompted (`⏳  2FA required` in output)
- Entry count and date range from the table header
- Any errors

Check gateway logs for pagination activity:
```bash
docker compose logs gateway 2>&1 | grep -i "continuation\|merged\|3040" | tail -10
```

### Step 2d: Sync Client Tests (FinTS3Client)

Run the same three tests directly against the bank (bypassing the gateway):

```bash
uv run python examples/fetch_transactions.py --days 365 --env-file .env 2>&1 | tail -5
uv run python examples/fetch_transactions.py --days 100 --env-file .env 2>&1 | tail -5
uv run python examples/fetch_transactions.py --days 30  --env-file .env 2>&1 | tail -5
```

Expected outcomes:

| Days | Expected sync client behavior |
|------|-------------------------------|
| 365 | Raises `DecoupledTANPending` (TAN required, correct behavior) |
| 100 | Raises `DecoupledTANPending` (TAN required, correct behavior) |
| 30  | Returns entries — should match gateway CLI count exactly |

If the bank does **not** require TAN for 100 or 365 days, the sync client
will succeed and return entries — record the count and verify it matches the
gateway CLI.

If the sync client raises any exception **other than** `DecoupledTANPending`
for TAN-requiring tests, that is a bug — investigate and report.

### Step 2e: Restore `.env`

After finishing all tests for a bank block that was activated by editing
`.env`: restore `.env` to its original state (re-comment the tested block,
uncomment the original active block). Verify with:
```bash
grep -v '^#' .env | grep FINTS_BLZ
```
Only one `FINTS_BLZ` line should appear.

## Step 3: Cross-Client Comparison

For the **30-day test** (which both clients can run without TAN for most
banks), compare entry counts and date ranges:

| Bank | Gateway CLI count | Sync client count | Match? |
|------|-------------------|-------------------|--------|
| ...  | ...               | ...               | Yes/No |

If counts differ, investigate by checking the raw entry lists for duplicates
or missing entries. Report any discrepancies.

For TAN-requiring tests (365d, 100d) where the sync client raises
`DecoupledTANPending`, the comparison is not applicable — note this as "N/A
(TAN)".

## Step 4: Investigate Failures

If any test returns an unexpected error:

1. Check gateway logs: `docker compose logs gateway 2>&1 | tail -50`
2. Known error codes:
   - `9370`: Missing HKTAN on continuation — pagination bug
   - `9800`: Dialog aborted — likely clock skew
   - `9931`/`9942`: Wrong PIN
   - `3920`: TAN method not allowed for this operation
3. Podman clock skew check:
   ```bash
   podman machine ssh 'date' && date
   ```
   If the VM clock is more than a few seconds behind, sync it:
   ```bash
   podman machine ssh 'sudo date -s "$(curl -sI google.com | grep -i date | cut -d: -f2-)"'
   ```
4. If `DecoupledTANPending` is raised when TAN is **not** expected (e.g.
   30-day sync client test), check whether HIPINS in the BPD requires TAN
   for HKCAZ/HKKAZ at this bank.

## Step 5: Summary Report

Present a combined summary table covering all banks and both clients:

```
┌───────────────────┬──────┬───────────────────────────┬───────────────────────────┬──────────────┐
│ Bank              │ Days │ Gateway CLI (Decoupled)    │ Sync Client (FinTS3)      │ Match        │
│                   │      │ Count / 2FA / Pages        │ Count / Result            │              │
├───────────────────┼──────┼───────────────────────────┼───────────────────────────┼──────────────┤
│ Triodos (500310)  │ 365  │ 198 / Yes / 2             │ DecoupledTANPending ✓     │ N/A (TAN)    │
│ Triodos (500310)  │ 100  │  80 / Yes / 1             │ DecoupledTANPending ✓     │ N/A (TAN)    │
│ Triodos (500310)  │  30  │  19 / No  / 1             │ 19 entries                │ ✓ Match      │
│ DKB (120300)      │ 365  │ ... / Yes / ...           │ ...                       │ ...          │
│ ...               │      │                           │                           │              │
└───────────────────┴──────┴───────────────────────────┴───────────────────────────┴──────────────┘
```

Then ask the user: "Do these results look correct for each bank? Should I
investigate any counts, date ranges, or discrepancies further?"

## Notes

- The 365-day test is the **critical pagination test**. It should return
  more entries than the 100-day test; if it returns the same or fewer,
  pagination is broken.
- Entry counts change over time as new transactions arrive. Focus on
  relative relationships (365d > 100d > 30d) and date range correctness
  rather than exact numbers.
- For banks that require TAN for all queries (including 30-day), the sync
  client will always raise `DecoupledTANPending`. This is valid
  bank-specific behavior, not a bug.
- Always restore `.env` to its original state after testing each bank block.
  Do not leave a different bank active than the one that was active when
  you started.

