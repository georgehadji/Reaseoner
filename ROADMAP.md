# Reasoner Roadmap

This document outlines the planned evolution of the **Adaptive Reasoning Architecture (ARA)**.

**Current Status (2026-03-16):** 12 reasoning methods implemented (7 legacy + 3 Sprint 1+2 + 2 Sprint 3)
- Sprint 3 Complete: Analogical Reasoning (B4) & Delphi Method (B5)
- Next: Sprint 4 - Causal Reasoning (B6)

## 🟢 Phase 1: Foundation (Completed)
- [x] Multi-method pipeline (Multi-Perspective, Iterative, Debate, Jury, Research).
- [x] Multi-provider routing (Anthropic, OpenAI, Google, DeepSeek, etc.).
- [x] Web UI with SSE streaming and workspace history.
- [x] Server-side response cache and client-side persistence.
- [x] Scientific and Socratic reasoning methods.
- [x] **Neuro Layer Integration:** Persistent memory (Recall/Learn/Audit).
- [x] **Smart Compression:** Neuro-Squeeze token optimization (Minimal/Aggressive).

## 🟡 Phase 2: Refinement (Short-term)
- [ ] **Multi-Tenant UI:** Allow switching `agent_id` from the web interface.
- [ ] **Compression Control:** Add a UI toggle for compression levels (None, Minimal, Aggressive) in the composer.
- [ ] **Advanced Audit:** Enhance `neuro/audit` to use recalled memory for fact-checking draft responses.
- [ ] **Export Enhancements:** PDF export and direct email sharing.
- [ ] **Performance:** Move embedding computation to a background worker to reduce SSE latency.

## 🟠 Phase 3: Expansion (Medium-term)
- [ ] **Coding Agent Mode:** A specialized method that can read, write, and execute code using Neuro-Squeeze for large files.
- [ ] **Visual Reasoning:** Integrate vision-capable models (Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro) for analyzing diagrams and screenshots.
- [ ] **Local LLM Support:** Native integration with Ollama/LM Studio for private classification and decomposition phases.
- [ ] **Collaborative Workspace:** Real-time shared reasoning sessions (multi-user).

## 🔴 Phase 4: Autonomy (Long-term)
- [ ] **Self-Correcting Pipeline:** Automatically rerunning phases if the `Audit` or `Critique` scores are too low.
- [ ] **Recursive Decomposition:** Automatically breaking complex sub-problems into their own sub-pipelines.
- [ ] **Knowledge Graph:** Evolving Neuro from flat chunks to a structured knowledge graph for better reasoning over time.
- [ ] **Custom Plugin System:** Allow users to add their own phases and tools to the ARA pipeline.

---
*Last Updated: March 2026*
