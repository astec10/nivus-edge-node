# Nivus Edge Node

Nivus é uma plataforma local-first para monitoramento e automação de borda. A base atual usa FastAPI, React, SQLite, MQTT e Docker Compose. O alvo é Ubuntu Server minimal x86_64; suporte universal a hardware ainda não foi comprovado.

## Estado atual

A instalação candidata Compose está em operação paralela num notebook CCE U25. O registro inicial de nós e o agente de pareamento/heartbeat passaram pela CI; telemetria multi-nó, inventário de capacidades, scheduler e validação entre computadores reais ainda estão pendentes. Consulte [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) para evidências atuais e limitações.

## Começar

- Preparar o ambiente de desenvolvimento: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- Instalar ou atualizar a candidata Ubuntu/Compose: [deploy/README.md](deploy/README.md)
- Regras para agentes e contribuidores: [AGENTS.md](AGENTS.md) e [CONTRIBUTING.md](CONTRIBUTING.md)

Antes de uma mudança, leia [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md) e os documentos da área afetada. Consulte arquitetura e decisões quando alterar contratos entre módulos.

## Escopo e segurança

Home Assistant, Zigbee, inferência local e execução distribuída são fases futuras. A fila do GitHub Actions para propostas de código é uma ferramenta de desenvolvimento, separada do scheduler futuro entre nós Nivus.

Não exponha painel, SSH ou broker diretamente à Internet. O certificado local é autoassinado. Não publique segredos, banco real, telemetria doméstica ou dados pessoais. A licença é AGPL-3.0-only; preserve avisos e licenças de terceiros.

## Documentação

- [Visão e arquitetura](docs/ARCHITECTURE.md)
- [Estado e roadmap](docs/PROJECT_STATUS.md) · [docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md)
- [Mapa de módulos](docs/MODULE_MAP.md) · [decisões](docs/DECISIONS.md)
- [Contexto e fluxo de IA](docs/AI_CONTEXT.md) · [skills](docs/SKILL_MAP.md)
- [Estratégia de validação](docs/TEST_STRATEGY.md)

