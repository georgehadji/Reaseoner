# /pipeline-run — Run a Quick Pipeline

Test the full reasoning pipeline end-to-end with a simple problem.

**Budget preset (fast, low-cost):**
```bash
cd "E:/Documents/Vibe-Coding/Reasoner" && python main.py --problem "What is the capital of France?" --preset orchestrated-budget 2>&1 | tail -30
```

**Custom problem:**
```bash
python main.py --problem "$ARGUMENTS" --preset orchestrated-budget
```

**With JSON output:**
```bash
python main.py --problem "$ARGUMENTS" --preset debate-budget --output /tmp/ara-result.json && cat /tmp/ara-result.json | python -m json.tool | head -50
```

**Sequential mode (rate-limited envs):**
```bash
python main.py --problem "$ARGUMENTS" --preset orchestrated-budget --sequential
```

**Phases:** Classification → Decomposition → Multi-Perspective Generation → Critique → Stress Test → Synthesis
