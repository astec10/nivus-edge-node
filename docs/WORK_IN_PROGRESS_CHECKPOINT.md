# Checkpoint de retomada — Nivus Edge Node

**Data:** 2026-11-21  
**Objetivo ativo:** avançar os marcos do Nivus em entregas pequenas, documentadas e verificáveis. Este checkpoint separa código, CI, revisão, merge e implantação.

## Estado do GitHub

Três PRs continuam abertos e não mesclados. As verificações descritas abaixo são as dos heads consultados em 2026-11-21.

| PR | Head | Situação | CI hospedada |
| --- | --- | --- | --- |
| [#93 — controlador de tarefas GitHub no notebook](https://github.com/astec10/nivus-edge-node/pull/93) | `ba3e723` | Aberto, mergeável, sem merge | Quatro workflows passaram |
| [#96 — lista administrativa de nós](https://github.com/astec10/nivus-edge-node/pull/96) | `2646e83` | Aberto, mergeável, sem merge | Quatro workflows passaram |
| [#97 — ingestão de telemetria por nó](https://github.com/astec10/nivus-edge-node/pull/97) | `bb28f29` | Aberto, mergeável, sem merge | Quatro workflows passaram |

### PR #93 — controlador GitHub de tarefas

- Observa Issues e exige autorização explícita por tarefa; o Nivus não baixa nem executa código.
- A execução de propostas fica em runners efêmeros do GitHub Actions, então a etapa hospedada não depende do computador do operador estar ligado.
- O controlador é opt-in, cifra o token e serializa mudanças de configuração com autorizações em andamento.
- Uma lacuna de revisão permanece: ainda não foi verificada a visibilidade pública do repositório configurado no serviço antes de ler ou autorizar Issues. Fechar esse limite e validar os workflows antes de considerar o PR pronto para integração.
- Nenhuma chamada paga/real de modelo foi confirmada nesta etapa.

### PR #96 — painel de nós

- Adiciona uma lista administrativa somente de leitura com presença, último heartbeat, versões e capacidades declaradas.
- Não envia comandos nem apresenta séries agregadas. A telemetria por nó depende do PR #97 e da integração posterior.
- Capacidades são declarações do agente; não comprovam hardware medido.

### PR #97 — telemetria por nó

- Envia telemetria autenticada e tipada, com horários de origem/recepção, sequência, idempotência e limite de cadência.
- Retém 14 dias e remove dados vencidos também quando o nó está offline e o histórico é consultado.
- O agente inicial cobre CPU, memória e disco; sensores não expostos aparecem indisponíveis.
- CI cobre código e smoke em runner Ubuntu; não prova TLS entre dois dispositivos físicos nem compatibilidade com famílias reais de hardware.

## Checkout local

- Árvore: `work/nivus-current`; branch local `feat/node-telemetry-main`; HEAD `101f825`; árvore limpa quando consultada.
- Esse checkout é distinto do head remoto do PR #97. Não tratá-lo como release publicada nem como código instalado.
- Nenhuma VM foi usada. Nenhuma alteração ou deploy foi feito no notebook neste checkpoint.

## Executor e modo offline

O executor de desenvolvimento que pode continuar quando PCs locais estão desligados é o workflow do GitHub Actions, sujeito aos limites e segredos configurados no repositório. O controlador do PR #93 oferece interface de fila e autorização; ele não é, por si só, um executor local persistente nem um scheduler distribuído entre nós Nivus. O scheduler runtime entre nós permanece planejado.

## Próximos passos

1. Corrigir ou documentar a verificação de repositório público no PR #93; conferir os quatro workflows no novo head.
2. Revisar os PRs #93, #96 e #97 e aguardar autorização explícita antes de qualquer merge.
3. Reconciliar documentos compartilhados/roadmap após os merges autorizados.
4. Validar ingestão HTTPS/TLS com dois dispositivos reais, perda de rede, replay, revogação e relógios incorretos; testar painel de séries.
5. Qualificar instalação persistente USB e sensores em hardware físico. O operador não quer VMs no computador; usar runners hospedados e simulações até haver hardware físico disponível.
6. MagicDNS/Tailscale HTTPS ainda requer confirmação do serviço acessado pelo celular; uma tentativa de alteração do Nginx foi revertida, e a verificação isolada da cadeia do certificado não confirmou a configuração servida.

## Regra de segurança e relato

Não registrar credenciais, dados domésticos, telemetria real, endereços privados ou hostnames privados. Não declarar implementação, CI, aprovação, merge, deploy ou validação física como equivalentes entre si.