from parsing import extract_json

json_data = extract_json("""
[SOLUTION]
Test solution.
[/SOLUTION]
```json
{
  "action_blueprint": [{"?": ""}, {"step": "", "action": ""}, {"step": "2", "action": "Act"}]
}
```
""")

raw_bp = json_data.get("action_blueprint", [])
clean_bp = []
for step in (raw_bp if isinstance(raw_bp, list) else []):
    if isinstance(step, dict):
        if not any(k in step for k in ("step", "action", "time_horizon", "go_criteria", "fallback")):
            print("skip missing keys:", step)
            continue
        step_val = (step.get("step", "") or "").strip()
        action_val = (step.get("action", "") or "").strip()
        print("check", step, "step_val", repr(step_val), "action_val", repr(action_val))
        if not step_val and not action_val:
            print("skip empty")
            continue
        clean_bp.append(step)
    elif step is not None and str(step).strip():
        clean_bp.append({"step": "", "action": str(step).strip(), "time_horizon": "", "go_criteria": "", "fallback": ""})

print("clean_bp:", clean_bp)
