# Checkpoint de retomada — Nivus Edge Node

**Data:** 2026-11-21  
**Objetivo ativo:** avançar os marcos do Nivus em entregas pequenas, documentadas e verificáveis. Este checkpoint separa código, CI, revisão, merge e implantação.

## Estado do GitHub

Três PRs seguem abertos e não mesclados. Os resultados abaixo se referem aos heads verificados; CI verde não significa merge, implantação ou validação física.

| PR | Head verificado | Situação | CI hospedada |
| --- | --- | --- | --- |
| [#93 — controlador de tarefas GitHub](https://github.com/astec10/nivus-edge-node/pull/93) | `9806601359460f4a998ac0f971bfd9625602555f` | Aberto, sem merge | Os quatro workflows passaram; CodeQL, Ubuntu Compose/restore, dashboard/sensores e índice concluíram |
| [#96 — lista administrativa de nós](https://github.com/astec10/nivus-edge-node/pull/96) | `2646e83528e23701dcf2b8ccafeb07a89cdd8741` | Aberto, sem merge | Os quatro workflows passaram |
| [#97 — ingestão de telemetria por nó](https://github.com/astec10/nivus-edge-node/pull/97) | `bb28f29fb8ea700bdc1dfaad307a1c517f231367` | Aberto, sem merge | Os quatro workflows passaram |

### PR #93 — controlador GitHub de tarefas

- Observa Issues e exige autorização explícita por tarefa; o Nivus não baixa nem executa código.
- Verifica anonimamente que o repositório configurado é público antes de consultar Issues e autorizar. Repositório privado, inexistente ou visibilidade não verificável falha fechado.
- Se a visibilidade não puder ser confirmada, limpa tarefas antigas em cache; o painel não exibe uma fila que não pode ser revalidada.
- Serializa autorização, alterações de configuração e polls, impedindo que uma consulta em andamento restaure tarefas após troca de repositório ou desativação.
- Token cifrado; controlador opt-in. Propostas são processadas em runners efêmeros do GitHub Actions, não no notebook.
- A primeira CI encontrou uma expectativa de teste desatualizada (6 chamadas esperadas, 4 no fluxo protegido); foi corrigida. Testes cobrem falha de visibilidade com cache antigo, desativação e troca de repositório durante poll.
- Os quatro workflows passaram no head acima. O PR continua aberto para revisão; nenhum merge ou deploy ocorreu.
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

## Documentação e checkout

- O checkpoint e `PROGRESS.html` deste branch refletem o estado atual do PR #93.
- `docs/PROJECT_STATUS.md` e `docs/AI_EXECUTOR_IMPLEMENTATION.md` ainda contêm uma referência histórica que chama o PR #93 de rascunho; corrigir e regenerar o índice antes de merge.
- Última verificação do checkout local: `work/nivus-current`, branch `feat/node-telemetry-main`, HEAD `101f825`, árvore limpa. Não é o branch remoto do PR #97.
- Nenhuma VM foi usada e nenhuma alteração ou implantação foi feita no notebook durante este trabalho.

## Executor e modo offline

GitHub Issues e GitHub Actions podem continuar o fluxo de desenvolvimento em runners hospedados quando o computador do operador está desligado, sujeitos a permissões, quotas e segredos do repositório. O controlador #93 é uma interface opt-in de fila e autorização; ainda não foi mesclado nem instalado no notebook. Ele não é o scheduler runtime distribuído entre nós Nivus. Nenhuma inferência real de modelo foi confirmada; a geração depende de um segredo de API ativo no GitHub Actions.

## Próximos passos

1. Corrigir as referências históricas citadas acima, regenerar o índice lexical e revisar o diff completo de #93.
2. Revisar #96 e #97 e verificar conflitos/documentação compartilhada antes da integração.
3. Aguardar aprovação humana para qualquer merge; nenhum dos três PRs está mesclado.
4. Após merge autorizado do #93, planejar implantação reversível e validar login, leitura da fila e autorização no notebook.
5. Após integração autorizada de #96/#97, validar TLS, replay, revogação, rede interrompida e relógios incorretos em dois dispositivos reais.
6. Qualificar Ubuntu + Nivus persistente em USB, sensores físicos e matriz Intel/AMD em hardware real. Não usar VMs no computador; manter testes repetíveis em runners hospedados e simulações.
7. Confirmar MagicDNS/Tailscale HTTPS no celular. A tentativa de mudar Nginx foi revertida; a checagem isolada do certificado não provou qual cadeia o Nginx serve ao vivo.

## Regra de segurança e relato

Não registrar credenciais, dados domésticos, telemetria real, IPs ou hostnames privados. Código, CI, revisão, merge, implantação e validação física são estados distintos.