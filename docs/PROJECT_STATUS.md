# Estado do projeto Nivus

Atualizado: 2026-11-16 02:57 UTC
Licença: AGPL-3.0-only

## Resumo verificado

O projeto tem API modular FastAPI, autenticação por senha/JWT, telemetria MQTT, SQLite persistente, dashboard React e uma instalação candidata Docker Compose. O objetivo de funcionar em Ubuntu Server minimal x86_64 continua em validação; ainda não há certificação para qualquer computador.

A arquitetura, módulos e limites estão descritos em [ARCHITECTURE.md](ARCHITECTURE.md), [HARDWARE_TELEMETRY.md](HARDWARE_TELEMETRY.md) e [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md). Cadastro multi-nó e atualização coordenada de software, Home Assistant, Zigbee, IA local, tarefas distribuídas e provedores comerciais permanecem objetivos futuros.

## CI de instalação e recuperação

O run 43662375766 passou nos dois jobs Ubuntu 22.04 amd64: build/smoke Compose e instalação limpa em runner descartável. A integração cobriu MQTT→SQLite, backup consistente, validação sem mutação, rollback induzido por falha de health, restauração normal, HTTPS 200, API sem token 401, `quick_check` e retomada da telemetria. Isso valida o fluxo de software no runner; não substitui reboot em hardware, sensores físicos ou a matriz Intel/AMD.

O operador decidiu não usar VMs no computador pessoal. Os testes repetíveis usam runners descartáveis hospedados pelo GitHub Actions. CI cobre o fluxo de software; não certifica hardware físico nem sensores.

## Estado do notebook de teste

O operador aplicou a release do PR #20 em 16/11/2026. O script reconstruiu API e dashboard, validou a migração SQLite com `quick_check=ok`, confirmou uma nova amostra do coletor e promoveu o Nginx antes de reiniciar o Ubuntu.

Após o reboot, a inspeção SSH somente de leitura confirmou a release `/opt/nivus-compose/releases/20261116T015555Z-969a1bd062b138cba9d1286930ca7779ffbde6ff`; containers web, API, worker e MQTT ativos; API/MQTT saudáveis; `nivus-compose-telemetry.service` ativo; HTTPS principal sem sufixo de porta e a versão leve em 8444 respondendo HTTP 200; `/health` respondendo `{"status":"ok","node":"nivus-edge-node"}`; e API de telemetria sem token retornando 401. Esses checks confirmam serviço e autorização, não substituem o teste visual da troca entre versões.

O rollback da release está em `/home/nivus/nivus-backups/nivus-update-20261116T015555Z`. O painel `/PROGRESS.html` e seu script também respondem HTTP 200, mas o HTML ainda contém o status antigo de promoção pendente. A correção da fonte e a republicação estão em andamento; não publicar valores ou contagens reais de sensores.

## Melhoria térmica e gráficos

O PR #20 foi integrado ao main e aplicado no notebook. A build confirmou os componentes API/web e a migração SQLite; a saída de implantação e a leitura pós-reboot confirmaram coleta contínua com origem térmica coretemp. Valores reais não são publicados. Placa-mãe, GPU e hotspot continuam dependentes dos sensores expostos pelo sistema e driver do equipamento.

A dashboard contém os cartões térmicos, períodos e seleção conjunta de séries, detalhes após três segundos e aviso sonoro opcional pelo navegador. O seletor atual/leve é implementado no mesmo estado React e guarda apenas a preferência de versão em `localStorage`; o backend mantém a sessão/token na aplicação. Os dois endereços respondem 200, mas a alternância real em ambas as direções, logout e expiração ainda aguardam conferência no navegador. O painel leve foi preservado em HTTPS 8444.

## Regra automática do relé por bateria

O comportamento solicitado é desligar `nivus/edge/relay1` quando a bateria do dispositivo móvel associado estiver em 20% ou menos. O contrato de telemetria MQTT e a tabela SQLite atuais não incluem nível de bateria nem identificam o aparelho associado ao relé. Portanto, o modo automático ainda não está ativo; o painel mantém os comandos manuais até haver uma fonte de bateria identificada, leitura recente e associação segura. A interface informa essa pendência e não envia comandos automáticos com dados ausentes.

## Acesso sem sufixo de porta

A dashboard principal está disponível em HTTPS na porta 443, portanto `https://IP/` não exige porta explícita. A versão leve continua em HTTPS 8444 para preservar compatibilidade e rollback. O IP da LAN pode ser reservado no roteador. DDNS e VPN de acesso remoto não foram configurados; o plano continua sendo combinar um nome DNS com VPN e não encaminhar painel ou SSH diretamente à Internet.

## Modo de manutenção e comando de ajuda

A issue #26 está sendo implementada nesta branch. A proposta oferece `nivus help`, `nivus help maintenance` e `sudo nivus maintenance status`; `sudo nivus maintenance enable` pausa a amostragem/publicação do agente do host e a gravação de novas amostras MQTT; `sudo nivus maintenance disable` retoma o trabalho sem relogar ou reiniciar. O painel traz o mesmo controle na aba Configuração para administradores. API, autenticação, painel, health, broker e dados já gravados permanecem disponíveis. Os processos Nivus continuam iniciados; apenas esses workloads são pausados. O marcador é volátil em `/run`, então reboot retorna ao funcionamento normal. Testes unitários de estado/CLI já passaram localmente; integração Compose, CI e publicação no notebook ainda estão pendentes. Não execute os comandos no notebook até a release ser atualizada.

## Escopo ainda pendente

- Issue #25: corrigir e republicar `PROGRESS.html`, que ainda mostra a promoção como pendente, e validar a troca de dashboard sem novo login, logout e expiração.
- Issue #21 e #23: aba Configuração com relógio Brasília, formatos 12/24h e data, fuso/GMT, servidores NTP redundantes sem mostrar a fonte no relógio e temas selecionáveis.
- Issue #26: concluir integração e CI do modo de manutenção e publicar a release; validação de implantação no notebook ainda não realizada.
- Issue #22: integrar fonte identificada e recente da bateria do dispositivo móvel e associá-la ao relé; manter comandos manuais até então.
- Fase 1: instalação limpa, recuperação e medição em mais hardware; a CI hospedada não substitui a matriz física Intel/AMD de três faixas de geração.
- Fase 2: identidade/cadastro/heartbeat multi-nó, telemetria agregada e rollout de releases assinadas com canário, saúde e rollback por nó.
- Fase 3: Home Assistant, Zigbee, energia e câmeras em leitura antes de automação física.
- Fase 4: inferência local e biblioteca documental consultável com fonte, licença, citações e limites de recursos.
- Fase 5: fila de tarefas entre nós com quotas, leases, cancelamento, isolamento e artefatos verificados.
- Fase 6: conectores comerciais com quotas, custos e aprovação explícita para dados que saem da rede local.
- Executor de desenvolvimento: concluir uma proposta end-to-end e manter CI/revisão humana antes de merge/deploy.

Nenhuma compatibilidade universal x86_64, automação doméstica, coordenador multi-nó ou execução distribuída de IA é declarada até existir implementação e evidência específicas.

## Orquestração de desenvolvimento com IA

O fluxo persistente com agente, Discord/Jira, roteador de modelos, GitHub PR e aprovação humana está documentado em `docs/AI_DEVELOPMENT_ORCHESTRATION.md`. O cenário completo descrito por um comentarista de vídeo não foi confirmado como uma integração pronta; os componentes são documentados separadamente. `docs/VIDEO_RESEARCH_INDEX.md` cataloga os vídeos e expõe o nível de verificação de cada um. Os metadados, resumos curados e notas atômicas versionados ficam em `knowledge/`; `tools/build_ai_context.py` gera termos lexicais e índice independentes de modelo. A biblioteca consultável e sincronizada dentro do produto continua planejada na Fase 4, não implementada.

O fluxo inicial do executor foi integrado ao `main` no PR #3. A chave `GEMINI_API_KEY` e a variável `NIVUS_AI_BUDGET_MODE=free-tier` foram configuradas no GitHub segundo confirmação do mantenedor; o valor da chave não foi lido. Duas tentativas com a API não produziram proposta: HTTP 503 e timeout após 75 segundos da chamada síncrona. Esta branch corrige o timeout com background polling limitado, códigos de falha úteis, limpeza da interação e remoção da segunda via de disparo que poderia duplicar uma chamada. Os testes offline desta branch passaram; a chamada end-to-end com esta correção ainda não foi observada. O worker continua restrito a caminhos exatos e não executa comandos, não modifica workflows, não aprova, não faz merge nem deploy. A revisão humana permanece obrigatória.

GitHub Issues e Actions são a fila e execução principais, sem depender do PC ou notebook do operador. O notebook é suporte opcional para painel, inspeção e agregação de relatórios quando estiver online. Telemetria do host não é requisito; agregação de telemetria entre nós será útil quando o Nó Master estiver operacional.
