<!-- Requirement coverage and actual observed results -->
# Testing

Observed on November 17, 2026, using Python 3.12.14 and Node's built-in test
runner. Commands were executed from the extracted `08` assignment directory.

```bash
python3 -m unittest discover -s MySolution/tests -v
node --test MySolution/tests/client.test.mjs
```

**Result: 17 Python tests passed; 8 JavaScript tests passed.** The initial Pythonsuite took 15.173 seconds in this environment. 
It includes two full 8×8 runs (one interpreter trace and one HTTP run). 
An initial separate service run produced 92 solutions across 33,589 events. 
Timings are environment-dependent.

Successful solver tests execute the supplied LAMBDA3 evaluator against the new, type-checked `queens.lam`; there is no substitute Python production solver.
The independent Python oracle appears only inside the test module. 
UI tests use controlled transports and a minimal DOM double; clocks are injected for expiration.

| Requirement | Test names | Observed result |
|---|---|---|
| Same-column collision, both diagonals, safe placement, older-row collision | `SolverTests.test_safety_column_diagonals_and_safe` | Pass |
| Same-row exclusion by one-entry-per-row invariant | `SolverTests.test_four_exact_trace_cps_resumption_and_snapshots` | Pass: every candidate's row equals partial-board length; a placement extends that row exactly once |
| CPS safe/conflict, success, exhaustion, and next-candidate resumption | Both preceding tests, plus full oracle trace comparison | Pass |
| 92 valid solutions, deterministic DFS, uniqueness | `SolverTests.test_eight_all_92_valid_unique_deterministic` | Pass; every event agrees with the independent oracle |
| All six event kinds, coordinates, board snapshots, exactly one done | `SolverTests.test_four_exact_trace_cps_resumption_and_snapshots` | Pass |
| Construct/open performs no search, first force doesn't force tail, bounded prefixes | `SolverTests.test_construct_open_and_bounded_prefix_do_not_run_later_work` | Pass for sizes 4, 8, 9, 10, with actual search/safe body-entry counters |
| Delayed failing tail and memoized force | `SolverTests.test_unrequested_failing_tail_and_final_empty`, preceding counter test | Pass; division by zero occurs only when deliberately forcing the tail |
| HTTP/RPC open and next respect laziness and limits 1 and 32 | `ServiceTests.test_limits_open_no_force_and_independent_streams` | Pass; force-call count equals returned-event count |
| Exhaustion, repeated next, close, unknown IDs | `ServiceTests.test_exhaustion_repeated_next_close_unknown` | Pass |
| Active close, refreshed inactivity, cleanup, active/completed expiration | `ServiceTests.test_close_active_and_expiration_cleanup` | Pass |
| Capacity, exact parameter shapes, type/range errors | `ServiceTests.test_capacity_and_exact_parameter_validation` | Pass |
| Atomic stream advancement under concurrent requests | `ServiceTests.test_concurrent_next_no_duplicate_advancement` | Pass; no events lost or duplicated |
| Request IDs and malformed envelopes | `EnvelopeTests.test_ids`, `test_invalid_envelopes_methods_params` | Pass |
| Valid notifications, hidden internal error details | `EnvelopeTests.test_notifications_and_hidden_internal_error` | Pass |
| Malformed JSON, duplicate keys, non-JSON constants, invalid UTF-8 | `EnvelopeTests.test_strict_json` | Pass |
| End-to-end HTTP open → all 92 solution events → done → repeat → close | `HTTPTests.test_full_eight_flow` | Pass |
| HTTP parse/error status, notifications, client assets | `HTTPTests.test_http_envelopes_notifications_parse_and_assets` | Pass |
| Notification side effects | `HTTPTests.test_http_close_notification_executes` | Pass: close notification actually removes the stream |
| Start/reset, single-event step, no prefetch | JS `start does not prefetch; step requests one; reset closes and clears` | Pass |
| Next solution stops correctly; play distinguishes completion | JS `next solution stops at solution; play distinguishes done` | Pass |
| Pause blocks future requests | JS `pause prevents later requests, including a paused in-flight request` | Pass |
| Reset waits for in-flight work | JS `reset waits for in-flight event then closes old stream` | Pass |
| Network/HTTP/RPC error handling and response IDs | JS `transport detects network, HTTP, RPC errors and mismatched IDs` | Pass |
| Visible error and restart control | JS `visible failure and restart control through mounted DOM handlers` | Pass |
| Actual DOM handler wiring for controls, count, completion, reset, speed | JS `mounted start, step, next solution, completion, reset and speed` | Pass with deterministic DOM double |
| Expired stream recovery | JS `restart recovers when old stream has expired` | Pass |

## Optional browser automation

`tests/browser-smoke.cjs` is provided for actual Chromium testing. See README
for optional Playwright installation and exact run commands. A launch was
attempted in this environment. The Playwright-managed Chromium binary was
unavailable; using the installed `/usr/bin/chromium` was blocked at process
startup with `socket() failed: Operation not permitted`. Therefore no browser
smoke pass or visual review is claimed. The JavaScript controller and DOM
wiring tests above did execute successfully.
