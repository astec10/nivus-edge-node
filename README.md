# Nivus Edge Node

O Nivus é uma plataforma local-first, modular e de baixo consumo para nós de borda. A base atual combina FastAPI, React, SQLite, MQTT e Docker Compose. O alvo de implantação é Ubuntu Server minimal x86_64/amd64; compatibilidade universal ainda não foi comprovada.

## Estado atual

A stack Compose está instalada no notebook CCE U25 de teste. Em 20/11/2026, o operador informou que a release `ecca6adde473593d91e23255bf64f397c890be36` está ativa, que o sistema funciona normalmente e que a nova aba de provedores de IA aparece. A saída do atualizador confirmou HTTPS health `200` e telemetria sem token `401`. Consulte [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) para distinguir implantação reportada, testes de CI e validações ainda pendentes.

O sistema continua sendo um nó único. Testes com dois computadores reais, instalação e reboot por USB físico, recuperação em hardware, compatibilidade Intel/AMD e automações domésticas ainda não foram concluídos. A CI hospedada valida fluxos de software; não certifica sensores, firmware ou todos os computadores x86_64.

## Começar

- Preparar o ambiente de desenvolvimento: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- Instalar ou atualizar Ubuntu/Compose: [deploy/README.md](deploy/README.md)
- Regras para agentes e contribuidores: [AGENTS.md](AGENTS.md) e [CONTRIBUTING.md](CONTRIBUTING.md)
- Ver estado e fases: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) e [docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md)

Antes de uma mudança, leia [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md) e os documentos da área afetada. Consulte o [mapa de módulos](docs/MODULE_MAP.md), a [arquitetura](docs/ARCHITECTURE.md) e as [decisões](docs/DECISIONS.md) para mudanças que cruzem fronteiras de módulos.

## Escopo

A versão atual oferece autenticação por senha, painel de telemetria local, gestão de usuários, Configuração, catálogo de provedores de IA e executor runtime com limites de dados e orçamento. O catálogo inclui OpenAI, Anthropic, Google Gemini e Ollama local; outros serviços podem usar cadastro manual. Credenciais do runtime Nivus são cifradas no host e independentes do segredo `GEMINI_API_KEY` do GitHub Actions. Nenhuma inferência comercial real foi confirmada nesta instalação.

Home Assistant, Zigbee, medidores e câmeras, IA local com biblioteca citável, agregação multi-nó, distribuição de tarefas e atualização de frota são fases futuras. O executor de propostas do GitHub Actions é ferramenta de desenvolvimento; não é o scheduler dos nós Nivus.

## Segurança e contribuição

Não exponha o painel, SSH ou broker diretamente à Internet. Não versione senhas, chaves, tokens, bancos de produção, logs ou telemetria privada. A licença do projeto é **AGPL-3.0-only**; preserve os avisos e as licenças de terceiros.

Escolha uma tarefa pequena, valide o comportamento na área afetada e registre o que foi testado. Não descreva recursos planejados como implementados, nem considere CI equivalente a teste em hardware real.

## Documentação

- [Visão e arquitetura](docs/ARCHITECTURE.md)
- [Mapa de módulos e dependências](docs/MODULE_MAP.md)
- [Decisões](docs/DECISIONS.md) · [Roadmap](docs/PROJECT_ROADMAP.md) · [Estado verificado](docs/PROJECT_STATUS.md)
- [Contexto para IAs](docs/AI_CONTEXT.md) · [Mapa de skills](docs/SKILL_MAP.md)
- [Provedores de IA](docs/AI_PROVIDER_CONNECTORS.md)
- [Validação e testes](docs/TEST_STRATEGY.md) · [Validação física de hardware](docs/HARDWARE_VALIDATION.md)
- [Ubuntu instalado em USB](deploy/portable_usb/README.md)

