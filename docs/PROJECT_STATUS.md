# Estado do projeto Nivus

Atualizado: 2026-11-16 UTC (com base nas saídas do operador)
Licença: AGPL-3.0-only

## Resumo verificado

O projeto tem API modular FastAPI, autenticação por senha/JWT, telemetria MQTT, SQLite persistente, dashboard React e uma instalação candidata Docker Compose. O objetivo de funcionar em Ubuntu Server minimal x86_64 continua em validação; ainda não há certificação para qualquer computador.

A arquitetura, módulos e limites estão descritos em [ARCHITECTURE.md](ARCHITECTURE.md), [HARDWARE_TELEMETRY.md](HARDWARE_TELEMETRY.md) e [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md). Cadastro multi-nó e atualização coordenada de software, Home Assistant, Zigbee, IA local, tarefas distribuídas e provedores comerciais permanecem objetivos futuros.

## CI de instalação e recuperação

O run 43662375766 passou nos dois jobs Ubuntu 22.04 amd64: build/smoke Compose e instalação limpa em runner descartável. A integração cobriu MQTT→SQLite, backup consistente, validação sem mutação, rollback induzido por falha de health, restauração normal, HTTPS 200, API sem token 401, `quick_check` e retomada da telemetria. Isso valida o fluxo de software no runner; não substitui reboot em hardware, sensores físicos ou a matriz Intel/AMD.

O operador decidiu não usar VMs no computador pessoal. Os testes repetíveis usam runners descartáveis hospedados pelo GitHub Actions. CI cobre o fluxo de software; não certifica hardware físico nem sensores.

## Estado do notebook de teste

A saída completa enviada pelo operador confirma que o pacote nivus-update-20261116T000636Z foi aplicado: as imagens da API e do painel foram compiladas, o SQLite passou quick_check, a migração térmica foi concluída e uma nova amostra de telemetria foi gravada. O Nginx passou na validação, health HTTPS respondeu 200 e a API sem token respondeu 401.

A dashboard nova foi promovida para HTTPS padrão, a versão leve foi preservada em 8444 e a página PROGRESS.html permaneceu publicada. A API Compose ficou limitada ao loopback em 8443. O instalador iniciou o reboot; o encerramento da sessão SSH foi esperado. Uma execução posterior informou que a release já estava ativa e parou no preflight, sem alterar serviços ou dados. Essas informações vêm da saída colada pelo operador e não foram reconferidas por uma nova conexão ao host.
## Melhoria térmica e gráficos

O pacote aplicado mantém a coleta térmica identificada pela origem do sensor e registra uma amostra nova durante a validação. Neste notebook, a CPU/APU é a única origem observada; placa-mãe, GPU e hotspot continuam opcionais e dependem do driver e do hardware. Não se publica valor real de telemetria. Os extremos do tooltip descrevem a janela exibida, não máximos históricos nem limites seguros do equipamento.
## Acesso sem sufixo de porta

A saída do update confirma a dashboard principal em HTTPS sem sufixo de porta e preserva a versão leve em 8444. Para a LAN, use reserva DHCP no roteador. DDNS e acesso remoto não foram configurados; o plano é combinar nome DNS com VPN, sem publicar o painel diretamente na Internet.
## Escopo ainda pendente

- Confirmar depois do reboot que a dashboard principal abre em HTTPS padrão, que a versão leve responde em 8444 e que o painel de marcos continua atualizando.
- Conferir a seleção de gráficos, detalhes após três segundos e disponibilidade de sensores no navegador após o update.
- Preparar e instalar o runner auxiliar do notebook somente após a revisão e integração da mudança; o registro exige token temporário digitado no terminal.
- Medir disponibilidade de sensores, consumo e compatibilidade em mais máquinas Intel e AMD.
- Projetar cadastro e atualização coordenada dos nós, com pacotes assinados, implantação gradual, checagens de saúde e rollback individual.
- Preservar autenticação, backup, restore e isolamento; não usar IA sozinha para decisões físicas críticas.
## Orquestração de desenvolvimento com IA

O fluxo persistente com agente, Discord/Jira, roteador de modelos, GitHub PR e aprovação humana está documentado em `docs/AI_DEVELOPMENT_ORCHESTRATION.md`. O cenário completo descrito por um comentarista de vídeo não foi confirmado como uma integração pronta; os componentes são documentados separadamente. `docs/VIDEO_RESEARCH_INDEX.md` cataloga os vídeos e expõe o nível de verificação de cada um. Os metadados, resumos curados e notas atômicas versionados ficam em `knowledge/`; `tools/build_ai_context.py` gera termos lexicais e índice independentes de modelo. A biblioteca consultável e sincronizada dentro do produto continua planejada na Fase 4, não implementada.

O fluxo inicial do executor foi integrado ao main no PR #3. A chave GEMINI_API_KEY e a variável NIVUS_AI_BUDGET_MODE=free-tier foram configuradas no GitHub segundo confirmação do mantenedor; o valor da chave não foi lido. A proposta inicial resultou no PR #16 em rascunho, com CI aprovada. O erro de abertura de PR foi corrigido no PR #17; ainda falta confirmar uma nova execução end-to-end após essa correção. O worker usa background polling limitado, não executa comandos sugeridos pela Issue/modelo e aplica alterações somente aos caminhos autorizados. Ele não aprova, faz merge nem deploy; a revisão humana permanece obrigatória.

GitHub Issues e Actions hospedados continuam sendo a fila e o executor de IA principal, sem depender do PC ou notebook do operador. Esta alteração prepara um runner auxiliar manual no notebook para validar somente a branch padrão depois do merge; ele não executará PRs públicos, tarefas de IA nem terá segredos ou acesso ao Docker. O runner ainda não foi instalado. Telemetria agregada entre nós será útil quando o Nó Master estiver operacional.
