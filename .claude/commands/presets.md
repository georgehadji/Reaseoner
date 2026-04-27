# /presets — List All Pipeline Presets

List all 42 available presets grouped by method and tier.

```bash
python main.py --list-presets 2>/dev/null || python -c "
from src.reasoner.domain.preset_registry import PRESET_REGISTRY
methods = {}
for name, preset in PRESET_REGISTRY.items():
    m = getattr(preset, 'method', 'unknown')
    methods.setdefault(m, []).append(name)
for method, names in sorted(methods.items()):
    print(f'\n{method}:')
    for n in sorted(names):
        print(f'  - {n}')
"
```

**Tiers per method:**
- `*-budget` — ~$0.02/run, cross-lab 3 providers
- `*-balanced` — mid-cost
- `*-premium` — ~$0.15–$0.30/run, ≥4 labs

**Key methods:** orchestrated, debate, jury, research, scientific, socratic, pre-mortem, bayesian, dialectical, analogical, delphi, cove, sot, tot, pot, self-discover, writing
