# /models — List Available Models

Show the model whitelist and routing registry.

```bash
python main.py --list-models 2>/dev/null || python -c "
from src.reasoner.infrastructure.llm.registry import _MODEL_WHITELIST
by_provider = {}
for model in sorted(_MODEL_WHITELIST):
    provider = model.split('/')[0] if '/' in model else 'direct'
    by_provider.setdefault(provider, []).append(model)
print(f'Total: {len(_MODEL_WHITELIST)} models\n')
for p, models in sorted(by_provider.items()):
    print(f'{p} ({len(models)}):')
    for m in models:
        print(f'  {m}')
"
```

**Provider count:** 12 direct adapters + OpenRouter (350+ models)
**Routing philosophy:** Cross-lab diversity — Phase 2 uses ≥3 different labs (budget) or ≥4 (premium).
