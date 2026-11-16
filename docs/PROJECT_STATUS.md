# Estado do projeto Nivus

Atualizado: 2026-11-16 01:25 UTC
Licença: AGPL-3.0-only

## Resumo verificado

O projeto tem API modular FastAPI, autenticação por senha/JWT, telemetria MQTT, SQLite persistente, dashboard React e uma instalação candidata Docker Compose. O objetivo de funcionar em Ubuntu Server minimal x86_64 continua em validação; ainda não há certificação para qualquer computador.

A arquitetura, módulos e limites estão descritos em [ARCHITECTURE.md](ARCHITECTURE.md), [HARDWARE_TELEMETRY.md](HARDWARE_TELEMETRY.md) e [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md). Cadastro multi-nó e atualização coordenada de software, Home Assistant, Zigbee, IA local, tarefas distribuídas e provedores comerciais permanecem objetivos futuros.

## CI de instalação e recuperação

O run 43662375766 passou nos dois jobs Ubuntu 22.04 amd64: build/smoke Compose e instalação limpa em runner descartável. A integração cobriu MQTT→SQLite, backup consistente, validação sem mutação, rollback induzido por falha de health, restauração normal, HTTPS 200, API sem token 401, `quick_check` e retomada da telemetria. Isso valida o fluxo de software no runner; não substitui reboot em hardware, sensores físicos ou a matriz Intel/AMD.

O operador decidiu não usar VMs no computador pessoal. Os testes repetíveis usam runners descartáveis hospedados pelo GitHub Actions. CI cobre o fluxo de software; não certifica hardware físico nem sensores.

## Estado do notebook de teste

A candidata Docker Compose continua paralela à instalação systemd/Nginx anterior. Segundo a saída enviada pelo operador, o pacote térmico `20261115T015200Z` compilou API e interface, migrou o SQLite, reiniciou os serviços candidatos, passou `quick_check`, preservou imagens de rollback e recebeu nova amostra com origem `coretemp: Package id 0`. Health HTTPS e API sem token 401 também passaram. Valores e contagens reais de telemetria não são publicados. A candidata continua publicada na porta 8443; o Nginx legado permanece como padrão na porta 443.

A candidata ainda está em 8443 e a interface antiga em 443; por isso o endereço sem porta ainda mostra a versão antiga. Um pacote reversível de promoção está em staging remoto e passou verificações somente de leitura: hash, sintaxe Bash, arquivos de backup, porta 8444 livre, health 200 e 401. A execução exige sudo interativo do operador. Ele recompila somente o painel, promove a nova dashboard a 443, preserva a leve em 8444 e mantém `/PROGRESS.html` e `/progress.js` no mesmo endereço. Ainda não está ativa em 443.

## Melhoria térmica e gráficos

O agente classifica CPU/APU por fonte/label, prioriza o pacote `coretemp` no CCE e mantém placa-mãe/GPU como opcionais. Leituras ausentes não reaproveitam valor antigo. A origem `coretemp` foi observada em amostra nova na candidata Compose. Neste notebook, placa-mãe, GPU e hotspot continuam indisponíveis quando o sistema/driver não os expõe.

O update aplicado contém cartões térmicos, gráficos com períodos múltiplos e detalhes após três segundos. A CPU/APU foi observada por `coretemp`; placa-mãe, GPU e hotspot dependem de sensores expostos pelo equipamento. Os extremos do tooltip descrevem a janela exibida, não máximos históricos nem limites seguros do hardware. Esta branch acrescenta no cabeçalho um link discreto para a versão leve, ativado apenas quando `NIVUS_LEGACY_DASHBOARD_PORT` é configurado; o build e a publicação desta nova opção ainda não foram confirmados no notebook.

O PR #20, ainda em revisão, agrupa os controles do gráfico e adiciona um aviso sonoro opcional pelo navegador. O som não aciona hardware físico e ainda não foi publicado no notebook.

## Regra automática do relé por bateria

O comportamento solicitado é desligar `nivus/edge/relay1` quando a bateria do dispositivo móvel associado estiver em 20% ou menos. O contrato de telemetria MQTT e a tabela SQLite atuais não incluem nível de bateria nem identificam o aparelho associado ao relé. Portanto, o modo automático ainda não está ativo; o painel mantém os comandos manuais até haver uma fonte de bateria identificada, leitura recente e associação segura. A interface informa essa pendência e não envia comandos automáticos com dados ausentes.

## Acesso sem sufixo de porta

Instalações limpas passam a preferir HTTPS 443 quando livre; quando a porta já está ocupada, o instalador preserva o serviço existente e escolhe uma alternativa. No notebook, a candidata ainda depende da promoção Nginx para aparecer em `https://IP/`. A LAN pode usar IP reservado no roteador. DDNS e acesso remoto não foram configurados; o plano é combinar nome DNS com VPN, sem publicar o painel diretamente na Internet.

## Escopo ainda pendente

- Executar a promoção reversível do dashboard candidato para HTTPS 443, confirmar o acesso ao endereço sem porta e o link para a versão leve em 8444.
- Confirmar a nova mudança de porta e o controle visual por CI hospedada; o operador não usará VMs no computador pessoal.
- Issue #22: integrar uma fonte identificada e recente de bateria e associá-la ao relé; manter a automação inativa até validação.
- Issue #23: comparar as cinco propostas de interface e as melhorias comuns; escolher o tema antes de substituir o layout.
- Issue #21: relógio digital de Brasília em 24 horas, ao lado da gestão de usuários, sincronizado por três fontes com fallback identificado.
- Medir disponibilidade de sensores, consumo e compatibilidade em mais máquinas Intel e AMD.
- Projetar cadastro e atualização coordenada dos nós, com pacotes assinados, implantação gradual, checagens de saúde e rollback por nó.
- Preservar autenticação, backup, restore e isolamento; não usar IA sozinha para decisões físicas críticas.

Nenhum suporte universal x86_64, automação doméstica, coordenador multi-nó ou execução distribuída de IA é declarado até implementação e evidência específicas.

## Orquestração de desenvolvimento com IA

O fluxo persistente com agente, Discord/Jira, roteador de modelos, GitHub PR e aprovação humana está documentado em `docs/AI_DEVELOPMENT_ORCHESTRATION.md`. O cenário completo descrito por um comentarista de vídeo não foi confirmado como uma integração pronta; os componentes são documentados separadamente. `docs/VIDEO_RESEARCH_INDEX.md` cataloga os vídeos e expõe o nível de verificação de cada um. Os metadados, resumos curados e notas atômicas versionados ficam em `knowledge/`; `tools/build_ai_context.py` gera termos lexicais e índice independentes de modelo. A biblioteca consultável e sincronizada dentro do produto continua planejada na Fase 4, não implementada.

O fluxo inicial do executor foi integrado ao `main` no PR #3. A chave `GEMINI_API_KEY` e a variável `NIVUS_AI_BUDGET_MODE=free-tier` foram configuradas no GitHub segundo confirmação do mantenedor; o valor da chave não foi lido. Duas tentativas com a API não produziram proposta: HTTP 503 e timeout após 75 segundos da chamada síncrona. Esta branch corrige o timeout com background polling limitado, códigos de falha úteis, limpeza da interação e remoção da segunda via de disparo que poderia duplicar uma chamada. Os testes offline desta branch passaram; a chamada end-to-end com esta correção ainda não foi observada. O worker continua restrito a caminhos exatos e não executa comandos, não modifica workflows, não aprova, não faz merge nem deploy. A revisão humana permanece obrigatória.

GitHub Issues e Actions são a fila e execução principais, sem depender do PC ou notebook do operador. O notebook é suporte opcional para painel, inspeção e agregação de relatórios quando estiver online. Telemetria do host não é requisito; agregação de telemetria entre nós será útil quando o Nó Master estiver operacional.
