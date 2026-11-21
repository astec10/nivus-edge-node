# Checkpoint de retomada — Nivus Edge Node

**Data:** 2026-11-21  
**Objetivo ativo:** avançar os marcos do Nivus em entregas pequenas, documentadas e verificáveis. Este checkpoint separa código, CI, revisão, merge e implantação.

## Estado do GitHub

Três PRs seguem abertos e não mesclados. Os resultados abaixo se referem aos heads de código verificados; CI verde não significa merge, implantação ou validação física.

| PR | Head de código verificado | Situação | CI hospedada |
| --- | --- | --- | --- |
| [#93 — controlador de tarefas GitHub](https://github.com/astec10/nivus-edge-node/pull/93) | `218a09a45aa804b5b0a0afc797f1825f0e41a22c` | Aberto, sem merge | Os quatro workflows passaram; check runs incluem CodeQL, Ubuntu Compose/restore, dashboard/sensores e índice |
| [#96 — lista administrativa de nós](https://github.com/astec10/nivus-edge-node/pull/96) | `2646e83528e23701dcf2b8ccafeb07a89cdd8741` | Aberto, sem merge | Os quatro workflows passaram |
| [#97 — ingestão de telemetria por nó](https://github.com/astec10/nivus-edge-node/pull/97) | `bb28f29fb8ea700bdc1dfaad307a1c517f231367` | Aberto, sem merge | Os quatro workflows passaram |

### PR #93 — controlador GitHub de tarefas

- Observa Issues e exige autorização explícita por tarefa; o Nivus não baixa nem executa código.
- Verifica anonimamente que o repositório configurado é público antes de consultar Issues e antes de autorizar. Repositório privado/inexistente ou visibilidade não verificável falha fechado.
- Serializa autorização, alterações de configuração e polls. Isso impede que uma consulta já iniciada restaure tarefas de um repositório anterior após troca ou desativação.
- Token cifrado; controlador opt-in. Propostas são processadas em runners efêmeros do GitHub Actions, não no notebook.
- O primeiro head com a checagem pública revelou um teste que esperava seis chamadas, embora o caminho de sucesso faça quatro. A expectativa foi corrigida e foram adicionados testes de corrida para desativação e troca de repositório durante um poll.
- Todos os workflows passaram no head de código acima. A revisão final do PR e qualquer merge aguardam decisão humana.
- Nenhuma chamada real/paga de modelo foi confirmada.

### PR #96 — painel de nós

- Lista estado, heartbeat, versões e capacidades declaradas em modo somente leitura.
- Não envia comandos nem apresenta séries agregadas; essa integração depende do PR #97.
- Capacidades autodeclaradas não comprovam hardware medido.

### PR #97 — telemetria por nó

- Envio autenticado e tipado, horários de origem/recepção, sequência, idempotência e limite de cadência.
- Retenção de 14 dias também aplicada à consulta de nós offline.
- Agente inicial lê CPU, memória e disco; fonte ausente aparece indisponível.
- CI e smoke em runner Ubuntu não comprovam TLS entre dispositivos reais nem compatibilidade física por família de hardware.

## Checkout local

- Última verificação: checkout `work/nivus-current`, branch `feat/node-telemetry-main`, HEAD `101f825`, árvore limpa.
- É diferente do branch remoto do PR #97; não equivale a release publicada nem instalada.
- Nenhuma VM foi usada e nenhuma alteração ou implantação foi feita no notebook durante este trabalho.

## Executor e modo offline

GitHub Issues e GitHub Actions podem continuar o fluxo de desenvolvimento em runners hospedados quando o computador do operador está desligado, sujeitos a permissões, quotas e segredos do repositório. O controlador #93 é uma interface opt-in de fila e autorização; ainda não foi mesclado nem instalado no notebook. Ele não é o scheduler runtime distribuído entre nós Nivus. Nenhuma inferência real de modelo foi confirmada.

## Próximos passos

1. Conferir a CI acionada por esta atualização documental e revisar o diff final do PR #93.
2. Solicitar aprovação humana antes de mesclar #93, #96 ou #97; nenhum deles está mesclado.
3. Após merge autorizado do #93, planejar implantação reversível e validar login, leitura da fila e autorização no notebook. Nenhuma implantação foi feita nesta etapa.
4. Integrar a lista de nós (#96) e a telemetria (#97) somente depois da revisão/merge autorizados; validar TLS, replay, revogação, rede interrompida e relógios incorretos em dois dispositivos reais.
5. Qualificar o USB instalado persistente, sensores físicos e matriz Intel/AMD em hardware real. Não usar VM no computador; manter testes repetíveis em runners hospedados e simulações.
6. MagicDNS/Tailscale HTTPS ainda precisa confirmação de acesso pelo celular. A tentativa de mudar Nginx foi revertida; a checagem isolada validou a cadeia do certificado temporário, mas não provou qual cadeia o Nginx serve ao vivo.

## Regra de segurança e relato

Não registrar credenciais, dados domésticos, telemetria real, IPs ou hostnames privados. Código, CI, revisão, merge, implantação e validação física são estados distintos.