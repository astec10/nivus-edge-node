---
id: local-inference-hardware-fit
title: Fit local inference to measured hardware and task
topic: local-inference-hardware
tags: ram, vram, model-size, quantization, latency, benchmark, remote-gpu, bandwidth, ai-gateway, external-provider, arm64, hardware-compatibility
source: docs/VIDEO_RESEARCH_INDEX.md; https://www.youtube.com/watch?v=rPGJhrunbxo; https://www.youtube.com/watch?v=cFdoXn6yvE4; https://www.youtube.com/watch?v=O6_d15v1Zy0; https://github.com/shihabshahrier/freelm; https://armbian.com/boards/aml-s9xx-box; https://github.com/ophub/amlogic-s9xxx-armbian/issues/3676
verified_on: 2026-11-24
confidence: primary-docs-and-source-demonstrations
---

## Atomic summary

Choose a local model only after matching its memory needs, context size, runtime overhead, latency and task quality to measurements on the target device. Keep a no-model path so telemetry and control remain responsive. A gateway that forwards prompts to hosted providers is a different workload: it routes and transports requests but does not perform the model inference locally.

## Distinguish the workloads

- **Local inference:** model weights and inference runtime execute on the node; measure RAM/VRAM use, CPU/GPU support, context size, latency, quality and thermal behavior on that exact device.
- **AI gateway:** a small device exposes or forwards an API request to another provider. It can reduce client setup work, but still depends on network connectivity, provider quotas and provider data policies. It does not pool CPU, RAM or VRAM across nodes.
- **Remote accelerator:** a separate networked GPU may perform inference, but transfer cost, latency, scheduling and failure behavior require independent measurements. A demonstration is not evidence that arbitrary hardware can share memory or accelerate arbitrary jobs.

## Hardware compatibility

Treat hardware reports as specific to the exact board revision, SoC, memory and drivers. The BTV 10 BX report covers an Amlogic S905X p212 unit with 2 GB RAM and 16 GB eMMC; its USB boot, eMMC installation and peripheral results are one upstream user report. Armbian's generic `aml-s9xx-box` listing is not a compatibility guarantee for other TV Boxes. None of these sources establishes Nivus support on ARM TV Boxes.

## Nivus checklist

1. Identify architecture, CPU, RAM, accelerators, storage and sensors on the target node.
2. Benchmark local inference and the monitoring/control services together; record idle and peak resource use.
3. Keep external-provider routing explicit. Explain where prompts go, which provider receives them, and what fallback or parallel routing does.
4. Do not treat a gateway as offline inference. If the network is unavailable, only a separately installed local model can answer locally.
5. Keep thermal safeguards and actuator policy independent of model availability.

## Evidence and limits

The video sources are useful architecture examples, not Nivus compatibility or performance tests. Auto-generated captions may contain recognition errors. No benchmark, board-wide compatibility statement or provider privacy guarantee is inferred from a video.

## References

- [Video research index](../../docs/VIDEO_RESEARCH_INDEX.md)
- [FreeLM upstream README](https://github.com/shihabshahrier/freelm)
- [Armbian aml-s9xx-box board page](https://armbian.com/boards/aml-s9xx-box)
- [Upstream BTV 10 BX report](https://github.com/ophub/amlogic-s9xxx-armbian/issues/3676)
- [Nivus AI and knowledge roadmap](../../docs/PROJECT_ROADMAP.md)
