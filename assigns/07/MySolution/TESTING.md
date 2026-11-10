# Testing and observed results

Run from the assignment directory, `assigns/07/`:

```bash
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
python3 MySolution/record_examples.py
python3 -m compileall -q MySolution
```

Observed on November 9, 2026 with Python 3.12.14, Flask 3.1.3 and jsonschema
4.26.0: **27 tests passed**, no skipped tests, in 1.810 seconds. Subtests
exercise additional parameter and source combinations. The expected runtime
failure test deliberately logs a server-side ZeroDivisionError; the response
contains only -32603, with no exception detail. This log is expected and does
not indicate a failed test.

The example recorder completed four real HTTP test-client calls: factorial
returned 720, the unbound-variable example returned -32011, and Python and
JavaScript compilation returned complete nonempty code. Exact requests and
responses are in `examples/`. No generated program was executed.

## Required behavior to test mapping

All names below are methods of `RpcTests` in `test_rpc.py`. Tests call Flask's
HTTP test client and assert HTTP status and JSON bodies. Success paths use the
real supplied LAMBDA3 implementation. Only failure paths use test doubles.

| Requirement | Tests | Observed |
| --- | --- | --- |
| 1. Health/version and preserved IDs | `test_health_and_id_types` | pass: strings, integer, fractional number, null, large integer |
| 2. Formatted type checking | `test_typecheck_real_programs` | pass: integer, boolean, function |
| 3. Arithmetic, factorial, tuple, collection | `test_interpret_real_programs` | pass: 42, 720, `(42, true)`, `[1, 2]` |
| 4. Python and JavaScript compilation | `test_compile_both_targets_unchanged` | pass: exact equality with supplied compiler strings |
| 5. Distinct syntax/type errors | `test_syntax_and_type_errors_all_source_methods` | pass: -32010/-32011 for all three source methods |
| 6. Malformed JSON | `test_json_parse_errors` | pass: malformed, empty, trailing content, non-JSON constants, bad UTF-8 |
| 6. Envelope validation | `test_invalid_envelopes` | pass: scalars, missing version, wrong version, invalid IDs |
| 6. Unknown/case-sensitive methods | `test_unknown_method` | pass: -32601 |
| 6. Missing/wrong/extra parameters | `test_missing_and_wrong_params` | pass: -32602 |
| 6. Source validation and limits | `test_bad_sources`, `test_source_size_boundary` | pass: exact byte boundary, multibyte excess, blank, wrong type, invalid Unicode |
| 6. Compile target validation | `test_compile_target_validation` | pass: missing/wrong/unsupported target |
| 7. Function formatting | `test_closures_are_formatted` | pass: `<lam>`/`<fix>`, no captured environment |
| 8. Unexpected backend failure | `test_unexpected_failure_is_logged_and_redacted` | pass: logged, ID preserved, details redacted |
| 8. Timeout error envelope | `test_timeout_rpc_mapping`, `test_actual_timeout_over_http` | pass: -32012, preserved ID |
| 8. Hard deadline cleanup | `test_actual_deadline_terminates_worker` | pass: worker writes readiness marker, is terminated, no remaining child |
| 8. Real runtime failure | `test_real_runtime_failure_redacted` | pass: real division failure becomes safe -32603 |
| 9. Unbound variable | `test_unbound_variable_rejected` | pass: real checker rejects `missing` |
| 10. Mixed batch/IDs/invalid members | `test_batch_mixed` | pass: ID matching, notifications omitted, invalid members return null IDs |
| 10. Notification-only batch | `test_notification_batch` | pass: HTTP 204 and zero bytes |
| 10. Empty batch | `test_empty_batch` | pass: single -32600 object |
| 10. Single notification | `test_single_notifications` | pass: success/unknown method/invalid parameters all produce HTTP 204 |
| 10. Batch response shape | `test_single_call_batch_stays_array` | pass: one-element array |
| HTTP transport contract | `test_transport_status` | pass: 415, 405, 404, 413, JSON charset accepted |
| Response schema | `test_schema_rejects_invalid_response` | pass: schema checks; missing/dual result/error and boolean IDs rejected |
| Large formatted interpretation output | `test_large_formatted_result` | pass: 40,000-element array returned completely |

## Architecture and test boundaries

See the dependency diagram in `README.md`. HTTP transport is in `app.py`,
envelopes and batches in `dispatcher.py`, errors in `errors.py`, and the
language adapter/process lifecycle in `service.py`. Supplied language code
lives in `LAMBDA3/`.

There are no stubs replacing successful parsing, checking, interpreting or
compiling. `patch` is used to inject an unexpected backend failure and an RPC
timeout. A deliberately hanging worker is used to verify real process
termination; a separate HTTP test uses a tiny deadline to exercise the
actual timeout path through the service. The large-output test also checks
that result delivery is not constrained by a pipe buffer.

## Scope and reproducibility

Tests use local HTTP client calls rather than a public deployment. Timeouts
can also occur on a heavily loaded machine; worker startup is included in
the deadline. The service bounds source size and interpretation duration;
it does not impose a memory quota or a separate compiler deadline. A timeout
does not prove nontermination. Recursive programs can reach Python's
recursion limit before the deadline, which is reported as an internal error.
