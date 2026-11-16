# Estado do projeto Nivus

Atualizado: 2026-11-16 23:28 UTC
Licença: AGPL-3.0-only

## Resumo verificado

O projeto tem API modular FastAPI, autenticação por senha/JWT, telemetria MQTT, SQLite persistente, dashboard React e uma instalação candidata Docker Compose. O objetivo de funcionar em Ubuntu Server minimal x86_64 continua em validação; ainda não há certificação para qualquer computador.

A arquitetura, módulos e limites estão descritos em [ARCHITECTURE.md](ARCHITECTURE.md), [HARDWARE_TELEMETRY.md](HARDWARE_TELEMETRY.md) e [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md). Cadastro multi-nó e atualização coordenada de software, Home Assistant, Zigbee, IA local, tarefas distribuídas e provedores comerciais permanecem objetivos futuros.

## CI de instalação e recuperação

O run 43662375766 passou nos dois jobs Ubuntu 22.04 amd64: build/smoke Compose e instalação limpa em runner descartável. A integração cobriu MQTT→SQLite, backup consistente, validação sem mutação, rollback induzido por falha de health, restauração normal, HTTPS 200, API sem token 401, `quick_check` e retomada da telemetria. Isso valida o fluxo de software no runner; não substitui reboot em hardware, sensores físicos ou a matriz Intel/AMD.

O operador decidiu não usar VMs no computador pessoal. Os testes repetíveis usam runners descartáveis hospedados pelo GitHub Actions. CI cobre o fluxo de software; não certifica hardware físico nem sensores.

## Ubuntu instalado em USB

A decisão da issue #29 está fechada: Ubuntu Server completo instalado no pendrive, com raiz ext4 e uma partição ext4 separada \`NIVUS_DATA\` para dados persistentes. O objetivo é iniciar outro computador x86_64 sem alterar o disco interno. Não é Casper Live.

O PR #34 foi integrado à `main` no commit `703efa4128f60460910b05ab344b60b082006a7e`. Todos os checks hospedados passaram no head `3a1621dc11d2532853ef83b9ab5ea47f64cfaca5`: seletor USB, seed/schema Subiquity, bootstrap pós-boot, integração ext4, smoke Compose, workflows gerais, índice e CodeQL. `deploy/portable_usb/install_nivus.sh` valida raiz e `NIVUS_DATA` no mesmo dispositivo USB, verifica ext4/rótulo/fstab/montagem e configura caminhos e guard persistentes antes de chamar o instalador Compose.

O fluxo continua usando a mídia oficial inicializável do Ubuntu e um seed NoCloud separado. A tela de armazenamento do Subiquity permanece interativa; a pessoa confere caminho, modelo, serial e capacidade antes de confirmar, porque o instalador apaga o USB escolhido. A primeira instalação do Compose precisa de Internet para instalar pacotes e construir/obter componentes. Depois de instalado, o Nivus local pode operar na LAN sem serviço de nuvem; inferência local e coordenação multi-nó são fases separadas.

Ainda faltam executar uma instalação real do Subiquity até o primeiro boot, instalar Nivus, autenticar no painel, reiniciar e verificar SQLite (`quick_check`), configurações, segredos e Docker persistidos, testar recuperação/rollback e fazer a matriz física UEFI/BIOS Intel/AMD. A CI hospedada e o loop ext4 validam software, não boot em USB físico nem compatibilidade universal. Consulte [deploy/portable_usb/README.md](../deploy/portable_usb/README.md) para o procedimento e seus limites.

## Configuração visual, NTP e atualização

O PR #36 corrigiu filtros e acessibilidade do quadro de marcos; o PR #37 integrou relógio digital, formatos de hora/data, fuso IANA/GMT e temas. O PR #38 adicionou atualização manual reversível; os PRs #40/#41 instalaram o controlador NTP restrito e corrigiram o staging do atualizador.

Os temas completos do PR #43 adicionam layouts Bento, Glass, SCADA, Cupertino e E-Ink, selecionáveis em Configuração. O PR #44 restaurou o valor atual do ponto imediatamente. Após o relato de atraso, o PR #48 passou a exibir sem espera também mínimos/máximos, origem e hotspots disponíveis no tooltip; a pausa de 3 segundos vale apenas para os detalhes ampliados dos cartões de métricas. O mesmo PR aplica alto contraste e movimento reduzido. Os PRs #44 e #45 passaram pelos checks hospedados; o PR #46 também passou em frontend/sensores, Python, JavaScript/TypeScript, CodeQL, índice e smoke Compose Ubuntu 22.04 amd64.

O PR #45 define três fontes de provedores distintos (a.ntp.br, time.google.com, time.cloudflare.com) e permite edição quando systemd-timesyncd está instalado, mesmo parado. Se outro cliente NTP estiver ativo, a alteração é bloqueada. O controlador mantém backup e rollback. A sincronização é failover, não votação.

O PR #46 coleta a bateria interna do nó por psutil no agente de telemetria do host. O cartão e o gráfico mostram N/D quando o sistema não expõe leitura. Esse valor não é a bateria de celular nem a do inversor e não controla o relé.

- O atualizador está em deploy/update.sh; exige clone Git limpo e sudo, cria backup consistente do SQLite, constrói as imagens sequencialmente e preserva a release anterior para rollback. A última release confirmada por SSH no notebook é `/opt/nivus-compose/releases/20261116T015555Z-969a1bd062b138cba9d1286930ca7779ffbde6ff` (PR #20); não há confirmação de instalação dos PRs #43-50. A captura enviada em 2026-11-16 ainda mostra o texto antigo sobre esperar 3 segundos no gráfico, enquanto o código atual mostra o tooltip imediatamente. A publicação e a validação visual das mudanças mais recentes continuam pendentes.

## Estado do notebook de teste

O operador aplicou a release do PR #20 em 16/11/2026. O script reconstruiu API e dashboard, validou a migração SQLite com `quick_check=ok`, confirmou uma nova amostra do coletor e promoveu o Nginx antes de reiniciar o Ubuntu.

Após o reboot, a inspeção SSH somente de leitura confirmou a release `/opt/nivus-compose/releases/20261116T015555Z-969a1bd062b138cba9d1286930ca7779ffbde6ff`; containers web, API, worker e MQTT ativos; API/MQTT saudáveis; `nivus-compose-telemetry.service` ativo; HTTPS principal sem sufixo de porta e a versão leve em 8444 respondendo HTTP 200; `/health` respondendo `{"status":"ok","node":"nivus-edge-node"}`; e API de telemetria sem token retornando 401. Esses checks confirmam serviço e autorização, não substituem o teste visual da troca entre versões.

O rollback da release está em `/home/nivus/nivus-backups/nivus-update-20261116T015555Z`. A fonte versionada de `/PROGRESS.html` foi alinhada ao merge do PR #34; a cópia servida no notebook não foi reconfirmada nesta rodada. Não publicar valores ou contagens reais de sensores.

## Melhoria térmica e gráficos

O PR #20 foi integrado ao main e aplicado no notebook. A build confirmou os componentes API/web e a migração SQLite; a saída de implantação e a leitura pós-reboot confirmaram coleta contínua com origem térmica coretemp. Valores reais não são publicados. Placa-mãe, GPU e hotspot continuam dependentes dos sensores expostos pelo sistema e driver do equipamento.

A dashboard contém cartões térmicos, períodos e seleção conjunta de séries. O PR #48, integrado à main, mostra imediatamente valor, mínimos/máximos, origem e hotspots disponíveis no tooltip do gráfico; a pausa de três segundos vale apenas para detalhes ampliados dos cartões. A legenda antiga ainda vista na captura do notebook indica que a nova build não foi confirmada visualmente nesse host. O aviso sonoro usa o navegador, não um buzzer físico. A bateria interna do nó ganhou cartão e modo de gráfico no PR #46. A implementação da regra da issue #22 foi integrada no PR #50, com quatro checks hospedados aprovados, mas ainda falta validar a implantação e configurar uma fonte Home Assistant; a regra de bateria interna do nó não é a bateria móvel. O seletor atual/leve guarda apenas a preferência de versão em `localStorage`; o backend mantém sessão/token na aplicação. Os dois endereços responderam 200 na última inspeção, mas a alternância real em ambas as direções, logout e expiração ainda aguardam conferência no navegador. O painel leve foi preservado em HTTPS 8444.

## Regra automática do relé por bateria

O PR #50 integrou a implementação da regra solicitada: qualquer dispositivo móvel ativo e cadastrado que envie relatório autenticado, ordenado e com até 60 minutos de idade pode provocar somente `OFF` para o tópico fixo `nivus/edge/relay1` quando a bateria estiver em 20% ou menos. Há trava por ciclo baixo e limite de tentativas em falha do broker; nenhuma leitura ausente, vencida, duplicada ou fora de ordem provoca comando, e a recuperação da carga ou inicialização não envia `ON`. O token aleatório é mostrado uma vez e armazenado como SHA-256. A implementação ainda não está confirmada no notebook, não tem integração real do Home Assistant configurada e não foi testada em relé físico. A aceitação pelo broker não comprova a ação elétrica do relé.

## Acesso sem sufixo de porta

A dashboard principal está disponível em HTTPS na porta 443, portanto `https://IP/` não exige porta explícita. A versão leve continua em HTTPS 8444 para preservar compatibilidade e rollback. O IP da LAN pode ser reservado no roteador. DDNS e VPN de acesso remoto não foram configurados; o plano continua sendo combinar um nome DNS com VPN e não encaminhar painel ou SSH diretamente à Internet.

## Modo de manutenção e comando de ajuda

A implementação de manutenção reversível e `nivus help` foi integrada à `main` pelo PR #28 em 16/11/2026. A CI hospedada aprovou o smoke Compose Ubuntu, o índice de conhecimento, a dashboard/sensores e o CodeQL. O recurso pausa a amostragem/publicação do agente de telemetria do host e a gravação de novas amostras MQTT; API, autenticação, painel, health, broker e dados existentes continuam ativos. `sudo nivus maintenance disable` retoma a coleta sem reboot; reiniciar o host retorna ao modo normal. O código está no GitHub, mas a release ainda não foi aplicada nem validada visualmente no notebook CCE U25; não considere a função ativa nesse host até essa etapa.

## Escopo ainda pendente

- Issue #25: as correções do quadro de marcos estão na main pelo PR #36; a página atualizada e a troca da dashboard sem novo login ainda aguardam atualização do notebook e validação visual.
- Issue #21: preferências/relógio do painel estão nos PRs #37 e #45; a lista NTP usa NTP.br, Google e Cloudflare, permite edição com systemd-timesyncd instalado/parado e preserva outro cliente ativo. Falta aplicar e validar essa versão no host; o navegador não configura o relógio do Ubuntu.
- Issue #23: os seis temas (Atual, Bento, Glass, SCADA, Cupertino e E-Ink), seleção imediata e preferências locais por conta estão no PR #37. A confirmação visual comparativa no notebook ainda aguarda a atualização e teste no navegador.
- Issue #26: implementação integrada no PR #28; resta aplicar a release no notebook e confirmar CLI/dashboard e retorno ao modo normal após reboot. A CI hospedada passou, mas não substitui a validação do host.
- Issue #22: a implementação de bateria móvel foi integrada pelo PR #50 no commit `ba6e0c824fe1b62dd44c7d924a6a2d1074f26e23`; API, persistência, painel administrativo, integração documentada e simulações estão no repositório, e os quatro workflows hospedados passaram. A implantação no notebook, configuração real do Home Assistant e validação do relé físico continuam pendentes; a issue permanece aberta.
- Fase 1: instalação limpa, recuperação e medição em mais hardware; a CI hospedada não substitui a matriz física Intel/AMD de três faixas de geração.
- Issue #29: PR #34 integrado com seleção explícita do USB, seed Subiquity revisável e bootstrap pós-boot de Nivus. Pendem instalação e reboot em USB físico, verificação de persistência e recuperação, e matriz UEFI/BIOS Intel/AMD; a CI não substitui essas provas.
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
