# Codebase Introspection Report

**Generated:** 2026-03-25T00:54:21.554084

## Summary

- **Total Modules:** 81
- **Total Functions:** 843
- **Total Classes:** 274
- **Average Coverage:** 2.6%

## Complexity Distribution

- **LOW:** 784
- **MEDIUM:** 59
- **HIGH:** 0
- **CRITICAL:** 0

## Severity Summary

- **P1:** 19
- **P2:** 8
- **P3:** 782

## Error Handling Gaps

**Total Gaps:** 19

### Top 20 Gaps

| Function | File | Gap Type | Recommendation |
|----------|------|----------|----------------|
| save | models.py | no_handling | Add try/except block around I/O operations |
| load | models.py | no_handling | Add try/except block around I/O operations |
| export_to_json | renderer.py | no_handling | Add try/except block around I/O operations |
| save_events | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| get_events | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| list_pipelines | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| get_aggregate_state | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| save_snapshot | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| get_snapshot | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| count_events | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| delete_aggregate | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| get_stats | infrastructure\persistence\event_store.py | no_handling | Add try/except block around I/O operations |
| save_events | infrastructure\persistence\postgres_store.py | no_handling | Add try/except block around I/O operations |
| save_snapshot | infrastructure\persistence\postgres_store.py | no_handling | Add try/except block around I/O operations |
| save_read_model | infrastructure\persistence\postgres_store.py | no_handling | Add try/except block around I/O operations |
| delete_aggregate | infrastructure\persistence\postgres_store.py | no_handling | Add try/except block around I/O operations |
| execute_widget | infrastructure\widgets\registry.py | no_handling | Add try/except block around I/O operations |
| load_config | neuro\config.py | no_handling | Add try/except block around I/O operations |
| ingest | neuro\sessions.py | no_handling | Add try/except block around I/O operations |

## Type Annotation Gaps

**Total Gaps:** 8

### Top 20 Gaps

| Function | File | Missing Annotations |
|----------|------|---------------------|
| dispatch | api.py | self, request, call_next |
| run_pipeline | api.py | request, req, authenticated, rate_limit_checked |
| dispatch | api.py | self, request, call_next |
| dispatch | api.py | self, request, call_next |
| check_component | server_check.py | name, func |
| start | neuro\cli.py | host, port |
| archive_hot_sessions | neuro\sessions.py | self, summarize_fn |
| pytest_configure | tests\conftest.py | config |

## Dead Code

**Total Items:** 782

### Top 20 Items

| Type | Name | File | Reason |
|------|------|------|--------|
| function | add_rule | alerts.py | Public function not called anywhere in codebase |
| function | check_and_alert | alerts.py | Public function not called anywhere in codebase |
| function | get_alert_history | alerts.py | Public function not called anywhere in codebase |
| function | get_active_alerts | alerts.py | Public function not called anywhere in codebase |
| function | get_memory_usage_percent | alerts.py | Public function not called anywhere in codebase |
| function | get_circuit_breaker_open_count | alerts.py | Public function not called anywhere in codebase |
| function | get_health_check_success | alerts.py | Public function not called anywhere in codebase |
| function | get_alert_manager | alerts.py | Public function not called anywhere in codebase |
| function | dispatch | api.py | Public function not called anywhere in codebase |
| function | validate_problem | api.py | Public function not called anywhere in codebase |
| function | validate_preset | api.py | Public function not called anywhere in codebase |
| function | validate_source_type | api.py | Public function not called anywhere in codebase |
| function | validate_domain | api.py | Public function not called anywhere in codebase |
| function | run_stream | api.py | Public function not called anywhere in codebase |
| function | check_rate_limit | api.py | Public function not called anywhere in codebase |
| function | require_auth | api.py | Public function not called anywhere in codebase |
| function | optional_auth | api.py | Public function not called anywhere in codebase |
| function | run_pipeline | api.py | Public function not called anywhere in codebase |
| function | clear_cache | api.py | Public function not called anywhere in codebase |
| function | stop_pipeline | api.py | Public function not called anywhere in codebase |
