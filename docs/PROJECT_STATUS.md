# Estado do projeto Nivus

Atualizado: 2026-11-15 01:39 UTC
Licença: AGPL-3.0-only

## Resumo verificado

O projeto tem API modular FastAPI, autenticação por senha/JWT, telemetria MQTT, SQLite persistente, dashboard React e uma instalação candidata Docker Compose. O objetivo de funcionar em Ubuntu Server minimal x86_64 continua em validação; ainda não há certificação para qualquer computador.

A arquitetura, módulos e limites estão descritos em [ARCHITECTURE.md](ARCHITECTURE.md), [HARDWARE_TELEMETRY.md](HARDWARE_TELEMETRY.md) e [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md). Multi-nó, Home Assistant, Zigbee, IA local, tarefas distribuídas e provedores comerciais permanecem objetivos futuros.

## CI de instalação e recuperação

O run 43662375766 passou nos dois jobs Ubuntu 22.04 amd64: build/smoke Compose e instalação limpa em runner descartável. A integração cobriu MQTT→SQLite, backup consistente, validação sem mutação, rollback induzido por falha de health, restauração normal, HTTPS 200, API sem token 401, `quick_check` e retomada da telemetria. Isso valida o fluxo de software no runner; não substitui reboot em hardware, sensores físicos ou a matriz Intel/AMD.

A VM local instável foi retirada dos testes de rotina. Os testes repetíveis usam runners descartáveis do GitHub Actions. Não é necessário alterar a VM local para contribuir ou validar a CI.

## Estado do notebook de teste

A candidata Docker Compose está em execução paralela à instalação systemd/Nginx anterior. Na porta HTTPS 8443, o pacote térmico `20261115T004156Z` compilou API e interface, fez migração aditiva SQLite, reiniciou coletor/API/worker/dashboard, confirmou `coretemp` e preservou backup e imagens para rollback. Em checagem SSH somente de leitura posterior, o coletor estava ativo sem reinícios, os quatro containers candidatos estavam em execução, health respondeu 200, telemetria sem token respondeu 401 e a coleta avançou. Os serviços legados não foram alterados.

A captura do dashboard enviada pelo operador corresponde ao layout legado atualmente servido na porta 443. A candidata em 8443 usa outro bundle. Por isso a tela antiga ainda pode mostrar a leitura ACPI fixa de 29,8 °C; a correção já aplicada no Compose não substituiu a interface/API legada.

## Melhoria térmica e gráficos

O agente classifica CPU/APU por fonte/label, prioriza o pacote `coretemp` no CCE e mantém placa-mãe/GPU como opcionais. Leituras ausentes não reaproveitam valor antigo. A origem `coretemp` foi observada em amostra nova na candidata Compose. Neste notebook, placa-mãe, GPU e hotspot continuam indisponíveis quando o sistema/driver não os expõe.

Esta branch prepara a extensão de hotspot com origem, migração SQLite aditiva, gráficos separados de temperatura/uso/energia, períodos de 5/15/30/60 minutos e até 1000 amostras, além de detalhes de mínimo/máximo após 3 segundos de hover/foco. Os extremos são da janela exibida, não máximos históricos nem limites seguros do hardware. A nova interface ainda aguarda build de CI e publicação na candidata; a porta 443 permanece na versão anterior.

## Escopo ainda pendente

- Integrar a melhoria térmica após CI e revisar o dashboard candidato em uso.
- Confirmar reboot/persistência e instalação/recuperação em clone descartável quando houver laboratório apropriado.
- Medir disponibilidade de sensores, consumo e compatibilidade em mais máquinas Intel e AMD.
- Preservar autenticação, backup, restore e isolamento; não usar IA sozinha para decisões físicas críticas.

Nenhum suporte universal x86_64, automação doméstica, coordenador multi-nó ou execução distribuída de IA é declarado até implementação e evidência específicas.
