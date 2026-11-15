---
name: nivus-local-ai-knowledge
description: "Design Nivus local inference and searchable technical-document libraries with provenance, resource limits, and offline behavior."
---

# Nivus Local AI Knowledge

Use for the planned document library, local retrieval, and local inference in Nivus.

## Respect the roadmap
Read docs/PROJECT_ROADMAP.md Phase 4, docs/MODULE_MAP.md, and docs/AI_WORKFLOW.md. Do not assume a GPU or sufficient RAM from VM video memory. Measure CPU, RAM, storage, temperature, model size, latency, and impact on monitoring before choosing a runtime/model.

## Knowledge and retrieval
- Preserve source document, page/section, edition/version, license, and extraction date for each chunk.
- Keep source files immutable; treat OCR, text extraction, token/term indexes, and embeddings as derived artifacts that can be rebuilt.
- Atomize by coherent concept/section and retain citations so answers can point to exact sources.
- Start with local lexical search; add a vector index only when measured quality justifies storage and memory costs.
- Distinguish lexical tokens used by a local search index from model tokenizer IDs.
- Do not place credentials, household telemetry, private camera material, or complete copyrighted books in a public repository.

Keep the system useful offline and without an accelerator. Show sources and uncertainty, cap context and concurrency, and fail gracefully under memory pressure. Any external sharing must follow an explicit privacy decision by the operator.
