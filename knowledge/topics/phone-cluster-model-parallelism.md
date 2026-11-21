---
id: phone-cluster-model-parallelism
title: Phone clusters split one model; Nivus workers split independent tasks
topic: distributed-compute
tags: phone-cluster, model-parallelism, inference, local-ai, wifi, latency, memory, openai-compatible, provider, api, task-federation
source: docs/VIDEO_RESEARCH_INDEX.md; orailnoor/cross-platform-llm-client release 1.0.7-cluster
verified_on: 2026-11-21
confidence: primary-project-release-claim-with-unverified-performance
---

## Atomic summary

The PrivateLM phone-cluster demonstration divides one model across several mobile devices and serves it through a LAN API described as OpenAI-compatible. That is model parallelism. Nivus task federation should instead schedule independent, bounded jobs across authenticated nodes. The approaches solve different problems and should remain separate modules.

## Evidence

The video transcript describes choosing a master device, adding workers, assigning portions according to available memory/speed, and passing model data between devices (approximately 1:37–3:14). The maintainer's [1.0.7-cluster release](https://github.com/orailnoor/cross-platform-llm-client/releases/tag/1.0.7-cluster) confirms phone-cluster support, QR pairing, model split by free memory and speed, and a LAN API protected by an API key. The same release states 4–5 tokens/s for a 26B model on four devices; this is a maintainer claim, not an independent benchmark.

## Nivus application

- Keep the existing/future task queue for independent tasks, leases, quotas, cancellation and verified artifacts.
- If exploring this client, treat it as an optional inference backend or a custom OpenAI-compatible LAN provider, not as the task scheduler and not as proof that arbitrary devices pool RAM/VRAM.
- Benchmark end-to-end latency, throughput, memory, thermals, Wi-Fi traffic, worker loss/recovery, API authentication and exposure boundaries before any adoption.
- Do not assume x86_64, AMD/Intel, or generic GPU support from a phone-cluster demonstration.

## Limits

The video and release announce the feature, but the reported speed has not been independently reproduced. The release recommends devices on the same Wi-Fi with screens awake. An OpenAI-compatible label does not prove every client feature or API endpoint is supported. Do not expose a LAN inference server to the public internet without a separately reviewed security design.

## References

- [Video: I Turned My Spare Phones Into a Wireless GPU for AI Agents](https://www.youtube.com/watch?v=reOeczuEzOA)
- [PrivateLM cluster release](https://github.com/orailnoor/cross-platform-llm-client/releases/tag/1.0.7-cluster)
- [Related distinction: networked GPU and task federation](networked-gpu-vs-task-federation.md)
- [Nivus task orchestration plan](../../docs/AI_MODULE_WORKPLAN.md)
