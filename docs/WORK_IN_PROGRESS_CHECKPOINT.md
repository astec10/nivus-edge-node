# Checkpoint de retomada — Nivus Edge Node

**Data:** 2026-11-21  
**Objetivo ativo:** avançar os marcos do Nivus em entregas pequenas, documentadas e verificáveis. Este checkpoint separa código, CI, revisão, merge e implantação.

## Estado do GitHub

Três PRs seguem abertos e não mesclados. O controlador (#93) recebeu commits de documentação após seu último commit de código. Os resultados de CI abaixo são associados ao commit de código verificado, sem tratar um commit documental posterior como validação nova do código.

| PR | Revisão de código | Situação | CI hospedada |
| --- | --- | --- | --- |
| [#93 — controlador de tarefas GitHub](https://github.com/astec10/nivus-edge-node/pull/93) | código em `ba3e723`; checkpoint salvo no branch do PR | Aberto, sem merge | Quatro workflows passaram em `ba3e723`; revalidar o status do branch antes de integrar |
| [#96 — lista administrativa de nós](https://github.com/astec10/nivus-edge-node/pull/96) | `2646e83` | Aberto, sem merge | Quatro workflows passaram |
| [#97 — ingestão de telemetria por nó](https://github.com/astec10/nivus-edge-node/pull/97) | `bb28f29` | Aberto, sem merge | Quatro workflows passaram |

### PR #93 — controlador GitHub de tarefas

- Observa Issues e exige autorização explícita por tarefa; o Nivus não baixa nem executa código.
- A execução das propostas fica em runners efêmeros do GitHub Actions e pode continuar sem o computador do operador ligado.
- O controlador é opt-in, cifra o token e serializa alterações de configuração com autorizações em andamento.
- Permanece uma lacuna de revisão: a visibilidade pública do repositório configurado ainda não é verificada pelo serviço antes de ler ou autorizar Issues. Fechar esse limite antes da integração.
- Nenhuma chamada paga ou real de modelo foi confirmada.

### PR #96 — painel de nós

- Mostra em modo somente leitura estado, heartbeat, versões e capacidades declaradas.
- Não envia comandos nem apresenta séries agregadas; essa integração depende do PR #97.
- Capacidades são autodeclaradas e não comprovam hardware medido.

### PR #97 — telemetria por nó

- Envio autenticado e tipado, horários de origem/recepção, sequência, idempotência e limite de cadência.
- Retenção de 14 dias aplicada também à consulta de nós offline.
- Agente inicial lê CPU, memória e disco; fonte ausente aparece indisponível.
- CI e smoke em runner Ubuntu não comprovam TLS entre dispositivos reais nem compatibilidade física por família de hardware.

## Checkout local

- Checkout: `work/nivus-current`; branch `feat/node-telemetry-main`; HEAD `101f825`; árvore limpa quando consultada.
- É diferente do branch remoto do PR #97; não equivale a release publicada nem instalada.
- Nenhuma VM foi usada e nenhuma alteração ou implantação foi feita no notebook neste checkpoint.

## Executor e modo offline

O workflow de desenvolvimento do GitHub Actions pode continuar em runners hospedados quando os PCs locais estão desligados, sujeito à configuração, permissões, cotas e segredos do repositório. O controlador #93 é uma interface de fila e autorização, não um executor local persistente. O scheduler runtime distribuído entre nós Nivus permanece planejado.

## Próximos passos

1. Corrigir a verificação de visibilidade pública do repositório no serviço do PR #93 e revalidar CI.
2. Revisar #93, #96 e #97; fazer merge apenas após autorização explícita.
3. Reconciliar documentos compartilhados/roadmap depois dos merges autorizados.
4. Validar telemetria TLS com dois dispositivos reais, incluindo perda de rede, replay, revogação e relógios incorretos; conferir séries no painel.
5. Qualificar instalação persistente USB e sensores em hardware físico. Não usar VMs no computador; manter testes em runners e simulações até haver hardware físico.
6. MagicDNS/Tailscale HTTPS ainda precisa confirmação de acesso pelo celular. A tentativa anterior de alterar Nginx foi revertida; a verificação isolada do certificado não provou qual cadeia está sendo servida.

## Regra de segurança e relato

Não registrar credenciais, dados domésticos, telemetria real, IPs ou hostnames privados. Código, CI, revisão, merge, implantação e validação física são estados distintos.