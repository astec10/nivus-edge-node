# Estado do projeto Nivus

Atualizado: 2026-11-14 22:48 UTC
Licença escolhida: AGPL-3.0-only

## Organização funcional e árvore de dependências (14/11/2026)

Foi preparado em staging docs/MODULE_MAP.md, com a árvore de responsabilidades existente, o fluxo de dependências em runtime, os módulos futuros e regras para mudanças em paralelo. README, AGENTS, CONTRIBUTING e ARCHITECTURE apontam para esse mapa. O catálogo autenticado de nós está descrito como próximo módulo independente; ainda não foi implementado.

Este conjunto está sendo proposto no GitHub junto das correções do painel e da CI em PR #2. Não foi mesclado nem implantado no notebook. O estado da CI e a publicação do painel só serão atualizados após confirmação do GitHub e do host.

## Cache de contexto e conhecimento técnico (14/11/2026)

Foi preparado em staging o gerador tools/build_ai_context.py: ele reúne contexto oficial, organiza uma nota por conceito em temp/knowledge/notes/, cria JSONL e índice lexical de termos normalizados e monta temp/AI_CONTEXT_BUNDLE.md. /temp/ está ignorado pelo Git. A execução local foi conferida: três notas atômicas foram indexadas e uma busca lexical por `fastapi dependency` encontrou a nota de fronteiras da API. O índice representa termos normalizados, não IDs de tokens de um modelo. As notas são locais, exigem fonte, versão e data, não armazenam segredos e não substituem documentos oficiais. O cache continua fora do GitHub.

## Skills alinhadas ao roadmap (14/11/2026)

Foram criadas em staging onze skills Codex em codex-skills/: uma coordenadora, quatro para módulos e operações da base, cinco para capacidades futuras e uma para um fluxo externo opcional de desenvolvimento com IA. A skill de telemetria de hardware foi acrescentada após a falha observada na seleção de temperatura. docs/SKILL_MAP.md cruza as skills com as fases do projeto. A skill externa de desenvolvimento não é módulo do Nivus e não instala Hermes/OmniRoute no nó de borda. As skills não são módulos do produto. As 11 skills passaram pelo `quick_validate.py` oficial do skill-creator e foram instaladas localmente em `C:/Users/lps93/.codex/skills`. A skill de hardware classifica o Open Hardware Monitor original como legado e o fork como projeto separado. A publicação permanece em revisão no PR #3.

## Avaliação de automação externa com IA (14/11/2026)

docs/AI_DEVELOPMENT_ORCHESTRATION.md registra a checagem das fontes oficiais de Hermes e OmniRoute. Os componentes documentam Discord, webhooks de GitHub/Jira, endpoint compatível com OpenAI e políticas de roteamento de modelos. Não foi confirmada a instalação específica mencionada por um comentarista do YouTube; o ciclo completo requer integração de ferramentas, controles de concorrência, sandbox, orçamento, retry e aprovação humana. Essa automação é uma opção de ferramenta de desenvolvimento externa ao runtime do Nivus e não altera o roadmap do nó de borda.

## CI de recuperação e painel completo de marcos (2026-11-14 23:22:48 UTC)

O [PR #2 passou na execução Ubuntu 22.04 descartável](https://github.com/astec10/nivus-edge-node/actions/runs/43652402829): instalação limpa, MQTT→SQLite, backup validado, falha de health forçada, rollback com preservação dos dados, restauração normal, HTTPS 200, API sem token 401, `PRAGMA quick_check` e telemetria retomada de 1 para 2 registros. O smoke da stack e o teste do painel também passaram. A execução usa runners descartáveis do GitHub e não alterou o notebook.

O painel de staging apresenta 43 marcos até a primeira versão completa: 18 concluídos, um ativo (correção de telemetria térmica no PR #4), um aguardando (teste de instalação limpa na VM Hyper-V local) e 23 planejados. Os cinco filtros, contadores, estados acessíveis, busca e atualização manual foram verificados. O filtro oculto e o estado “Aguardando” foram corrigidos. Esta versão ainda não foi publicada no notebook nem verificada no navegador desse host.

O PR #4 também passou no smoke Compose do [run 43652755033](https://github.com/astec10/nivus-edge-node/actions/runs/43652755033). A correção térmica continua em revisão e não foi implantada no notebook.

## CI Ubuntu 22.04 aprovada (14/11/2026, 15:00 UTC)

O primeiro workflow público do GitHub Actions passou no [PR #1](https://github.com/astec10/nivus-edge-node/actions/runs/43607798466), usando runner Ubuntu 22.04.5 amd64. Sintaxe Bash/Python, validação Compose, build das imagens e smoke isolado passaram: painel/asset e health HTTPS responderam, telemetria sem token retornou 401, uma publicação MQTT chegou ao SQLite e `PRAGMA quick_check` retornou `ok`. Os containers mostraram cerca de 67 MiB agregados numa leitura instantânea (API 40,53; worker 17,36; MQTT 2,89; web 6,17 MiB); isso não é benchmark sustentado nem define RAM mínima.

A CI prova o caminho de software no runner Linux virtual. Não valida BIOS, chipset, NIC, armazenamento, periféricos ou desempenho sustentado. A compatibilidade física planejada é uma amostra de seis computadores: Intel e AMD, cada um em três faixas de geração (antiga, intermediária e recente). A instalação limpa, reboot e teste completo de backup/restore/rollback na VM Hyper-V local continuam pendentes.

## Comparador de rollback exercitado e VM limpa preparada (14/11/2026, 04:46 UTC)

O comparador Python embutido em `deploy/test-restore-rollback.sh` foi executado sem alteração contra quatro fixtures SQLite descartáveis: aceitou uma linha nova de telemetria mantendo todas as linhas anteriores, e rejeitou perda de usuário, alteração de esquema (índice) e alteração de configuração. O processo encerrou com limpeza do diretório temporário confirmada.

Na VM `nivus-test-clean`, a impressão digital SSH do guest foi conferida novamente (`SHA256:l1f0aTbIJrVfJo5pU5DR9KmSJoY6FY5ynopjoPBwiIQ`). A chave temporária entrou por autenticação somente de chave, e a entrada correspondente em `authorized_keys` foi confirmada com a opção `restrict`. O checkout público foi clonado em `/home/nivus/nivus-edge-node`, branch `main`, commit `5edc7e74968017af5731339cf44419830bf924ec`, árvore limpa. No próprio Ubuntu Server 24.04.5 LTS, `bash -n` passou nos três scripts de backup/restore e os modos `--help` de restore e rollback passaram.

A VM reporta x86_64, 4 CPUs online, 4.009.220 kB de memória e 27 GB livres em disco de 32 GB; uma visualização anterior do VirtualBox registrou 2 vCPUs, portanto a contagem de CPU atribuída ainda precisa ser reconciliada antes de qualquer benchmark. Docker e a instalação Nivus ainda estão ausentes. `sudo -n` não está habilitado; a instalação requer que o operador digite a senha administrativa e crie a conta inicial diretamente no terminal. Nenhuma instalação, banco ou serviço do notebook foi alterado.

## Tentativa automatizada de criar VM limpa (14/11/2026, 01:42 UTC)

O operador relata que a VM VirtualBox `testev1` trava ao tentar alterar configurações. Em sessão anterior, o console mostrou mensagens de watchdog, CPU soft-lockup e stalls de RCU. A instalação do Nivus ainda não foi iniciada nessa VM; SSH/NAT também não foram habilitados. O notebook de teste continua separado.

Para facilitar uma tentativa limpa, `deploy/windows/New-NivusTestVm.ps1` cria uma VM adicional, sem apagar ou alterar `testev1`: baixa a ISO oficial Ubuntu Server 24.04.5 amd64 quando necessário e confere o SHA-256, usa até 2 vCPUs, ajusta RAM à memória física do host, cria disco virtual dinâmico de 32 GB, mantém 16 MB de vídeo e limita SSH NAT ao loopback do Windows. O script recusa iniciar com outra VM rodando ou sem RAM/disco livres suficientes. A ISO oficial local foi conferida (4.080.486.400 bytes, SHA-256 correto). A execução do criador nesta sessão parou antes da criação: `VBoxManage list vms` retornou `E_ACCESSDENIED` ao inicializar a interface COM. Nenhuma VM foi criada nem modificada por essa tentativa. Instalação limpa, reboot, backup e restore continuam pendentes.

## VM online; SSH ativo e NAT validado (14/11/2026, 04:18 UTC)

A captura do console confirma `nivus-test-clean` em execução com Ubuntu Server 24.04.5 LTS amd64. A configuração VirtualBox usa NAT e encaminha `127.0.0.1:2223` para a porta 22 do guest. O operador confirmou `systemctl is-active ssh` = `active`. A conexão do Windows ao encaminhamento completou negociação SSH com OpenSSH 9.6p1; a chave de host ED25519 observada foi `SHA256:l1f0aTbIJrVfJo5pU5DR9KmSJoY6FY5ynopjoPBwiIQ`.

A autenticação ainda não foi autorizada: o cliente recebeu `Permission denied (publickey,password)`. Nenhuma senha foi tentada. Para habilitar análise remota, o operador precisa instalar na conta da VM somente a chave pública temporária, marcada com a opção `restrict`; a chave privada permanece no ambiente de desenvolvimento. Depois da autorização, conferir a identidade SSH e o escopo da conta. A instalação do Nivus, reboot e teste integrado de restore/rollback continuam pendentes. Nenhuma alteração foi aplicada ao notebook Nivus.

## Verificação do procedimento de restore (14/11/2026, 04:27 UTC)

O código `deploy/restore.sh` foi revisado para aguardar até 45 segundos e validar o conjunto completo após a troca do banco e após rollback: coletor systemd, quatro containers, HTTPS 200, API 401 sem token e `PRAGMA quick_check`. A mesma verificação agora é usada nos caminhos de sucesso e recuperação, evitando falso erro de rollback por inicialização lenta e evitando declarar uma restauração boa com um serviço faltando. `bash -n` e `--help` passaram numa cópia temporária em Ubuntu do notebook; o scratch foi removido. O hash do `deploy/backup.sh` público coincide com o ativo (`678b3ca...`). Nenhum backup foi criado e nenhum banco ou serviço foi alterado. O teste integrado continua aguardando a VM descartável e a autorização de chave SSH.

## Comparação de dados do teste de rollback fortalecida (14/11/2026, 04:34 UTC)

`deploy/test-restore-rollback.sh` agora compara também as definições de tabelas, índices, triggers e views do SQLite após a recuperação, além de verificar todas as linhas preexistentes, sem exigir que a telemetria pare de crescer. `bash -n` e `--help` passaram no Ubuntu em scratch temporário, removido ao final. Ainda falta exercitar o comparador com fixtures e executar o teste completo na VM descartável. Nenhum arquivo ativo, backup, serviço ou banco do notebook foi alterado por essa mudança.
## Revalidação do host e da rotina de rollback (14/11/2026, 03:40 UTC)

Checagem SSH confirmou `nivus-compose-telemetry.service` ativo, zero reinícios, quatro containers candidatos em execução, health HTTPS 200 e API sem token 401. O `backup.sh` ativo usava caminho somente por segundo (SHA-256 anterior `e5024d7a...`); foi substituído atomicamente pela versão com `mktemp` e sufixo único (SHA-256 `678b3ca086205fd672138e7146ff0cb48fcacab224cb25764c60eb73f8090043`). A versão anterior foi guardada em `/opt/nivus-compose/releases/20261113T203357Z/deploy/backup.sh.pre-20261114T033947Z`; ambos os caminhos foram resolvidos e os dois hashes conferidos. `bash -n` e hash remoto passaram após a troca. Nenhum backup foi criado e nenhum banco ou serviço foi reiniciado. `restore.sh` e `test-restore-rollback.sh` continuam ausentes da pasta `deploy` ativa; backups root não foram inspecionados por exigirem sudo interativo. Os helpers de restore foram copiados somente para `/tmp/nivus-restore-review`; `bash -n` e `--help` passaram após endurecer a verificação de health do rollback. A página PROGRESS atualizada está staged com hash conferido, mas HTTPS ainda serve a versão anterior (`3fc96fb2...`). A integração de restore/rollback ainda depende da nova VM descartável.

## Revalidação ao vivo (13/11/2026, 21:15 UTC)

Checagem somente leitura via SSH no notebook de teste:

- `nivus-compose-telemetry.service` estava `active/running`, com zero reinícios.
- Os quatro containers candidatos (web, API, worker e MQTT) estavam em execução; API e MQTT marcados saudáveis pelo Docker.
- `https://127.0.0.1:8443/health` respondeu HTTP 200 com `status: ok`.
- `/api/telemetry` sem token respondeu HTTP 401.
- O SQLite candidato passou `PRAGMA quick_check` (`ok`); numa amostragem de 12 segundos, o número de linhas de telemetria aumentou de 327 para 329.
- O `docker compose ps` no usuário SSH não conseguiu ler `/opt/nivus-compose/current/.env`; os containers foram conferidos com `docker ps` e `docker inspect`, sem ler nem expor o arquivo de segredos.

A atualização de `/PROGRESS.html` foi publicada em 13/11/2026 às 21:32 UTC. O publicador confirmou sintaxe do Nginx, health HTTPS e `401` sem token; uma checagem SSH confirmou que o SHA-256 servido corresponde ao arquivo staged (`3fc96fb23193e2c48c3db893fb1c0e3dd021dff3af9238dbd6e71aa7a8a38ff3`). O script criou backup antes da publicação. Nenhuma instalação limpa em VM foi iniciada: a compatibilidade Ubuntu amd64 ainda precisa dessa validação.

## Correção do empacotamento do instalador (13/11/2026, 21:18 UTC)

O instalador agora exclui bancos SQLite, logs, chaves privadas, certificados privados e arquivos de credenciais da cópia de release; após extrair o pacote, uma busca fail-closed interrompe a instalação se um desses artefatos ainda aparecer. `bash -n` passou no Ubuntu do notebook e um fixture isolado de tar incluiu somente o `README.md`, excluindo arquivos artificiais `.env`, SQLite, chaves, credenciais e logs. Esta correção foi validada em staging; não reinstala nem modifica os serviços ativos do notebook.

## Recursos observados no CCE U25 (13/11/2026, 21:26 UTC)

A revalidação do host registrou Ubuntu 26.04.1 LTS, x86_64, 2 vCPUs, 3,2 GiB de RAM e 5,7 GiB de swap. Em três amostras, os quatro containers Compose ficaram perto de 71,7 MiB agregados (API ~42,5 MiB, worker ~18,0 MiB, web ~4,6 MiB, MQTT ~6,1 MiB). Os limites configurados somam 512 MiB, sem contar o agente de telemetria, serviços legados, cache do host e pico temporário de build. Leituras instantâneas de CPU variaram de 0,5% a 12,4%; não são um benchmark sustentado. Os serviços legados e Compose estavam ativos; health HTTPS 200 e API sem token 401 passaram. Esse resultado em repouso não define RAM mínima nem comprova compatibilidade com outros computadores.

## Roteiro e VM de teste (13/11/2026, 22:33 UTC)

`docs/VM_VALIDATION.md` define preparação isolada, instalação limpa, login/health/401, crescimento SQLite, reboot e backup. O operador confirmou Ubuntu 26.04.1 LTS amd64 no VirtualBox, com 4 vCPUs, 8 GB RAM, filesystem raiz de cerca de 24,44 GB e 16 MB de memória de vídeo virtual. A configuração oferece margem para a validação; o espaço livre será conferido antes do build. Os 16 MB são memória de exibição, não aceleração de IA. SSH e regra NAT ainda aguardam configuração; foi fornecido um procedimento restrito ao loopback do host.

## Procedimento de restauração implementado (13/11/2026, 22:33 UTC)

`deploy/restore.sh` foi criado para restauração no mesmo host. `--check` valida a origem/SQLite sem parar serviços. A execução interativa exige digitar `RESTORE`, requer a stack ativa, faz backup consistente prévio, para o coletor e os escritores, faz checkpoint/quarentena WAL/SHM, substitui o SQLite atomicamente e confere health/401. O trap tenta restaurar a cópia prévia se a troca ou validação falhar e agora só declara o rollback recuperado depois de validar SQLite, todos os containers, coletor, HTTPS 200 e API 401; `.env` e segredos atuais permanecem intactos.

No Ubuntu do notebook, a checagem de 14/11 repetiu `bash -n` em `backup.sh`, `restore.sh` e `test-restore-rollback.sh`, além de `--help`; uma fixture isolada anterior exercitou snapshot SQLite, troca atômica, quarentena de sidecars e rollback. `backup.sh` cria diretórios exclusivos mesmo quando backups ocorrem no mesmo segundo. Os arquivos continuam somente em staging (`/tmp/nivus-restore-review`): nada foi instalado em `/opt/nivus-compose/current` nem executado contra o banco ativo. Faltam `--check` e o teste integrado de restore/rollback em clone descartável/VM.


## Verificador de rollback para a VM (13/11/2026, 22:47 UTC)

O script deploy/test-restore-rollback.sh foi adicionado para exercitar a recuperação automática sem mexer no notebook: exige detecção de virtualização, argumento explícito e duas confirmações; salva backup de segurança, exige backup escolhido com menos linhas de telemetria e força a falha do health após a troca. Depois confere o retorno dos serviços, health 200, 401, integridade SQLite e preservação do conteúdo anterior. bash -n e --help passaram em staging do notebook; uma fixture SQLite confirmou que o verificador aceita dados preservados com telemetria nova e rejeita dado de usuário alterado. O teste deliberado de 45 segundos ainda não foi executado. A rotina não foi instalada em /opt/nivus-compose/current.
## Resumo

- A API modular passou em validação isolada e foi ativada em um notebook de teste x86_64, conforme saída do operador. O deploy confirmou health local e via HTTPS, resposta 401 para telemetria sem token e criou backup com rollback.
- O frontend React modular foi compilado, validado em staging e ativado no Nginx do notebook com backup e rollback rápido. O bundle servido inclui `AGPL-3.0-only` e o link para o código no GitHub; health HTTPS e 401 foram conferidos após a troca.
- Após ativação, HTTPS serviu o index e o bundle JavaScript compilado; health passou e a API continuou respondendo 401 sem token. O operador confirmou que o login com a conta existente funcionou; nenhuma senha foi compartilhada.
- A candidata Docker Compose foi instalada em paralelo em 13/11/2026: API/MQTT/painel/worker estão em execução, health HTTPS passou, telemetria sem token respondeu 401 e o administrador `nivus` foi criado com PBKDF2. O operador confirmou login na candidata. Os serviços systemd/Nginx anteriores continuam ativos.
- A primeira execução do instalador parou antes de alterar o host porque chamou `systemd --version`; foi corrigida para consultar `systemctl --version` (systemd 259). A segunda tentativa parou durante o provisionamento do administrador. O código do instalador também foi endurecido para só remover o link `current` se esta execução tiver criado esse link.
- Depois do primeiro rollback, o instalador foi executado novamente e concluiu o provisionamento. A auditoria SSH confirmou `nivus-api`, `nivus-worker`, `nivus-telemetry` e Nginx antigos ativos, além dos quatro containers candidatos ativos; health HTTPS e HTTP 401 passaram. A conta candidata está armazenada com PBKDF2.
- A verificação operacional encontrou uma falha real: o coletor tentava `127.0.0.1:1884`, enquanto o broker está numa rede Docker `internal`, sem porta publicada no host. Um script reversível instalou um resolver dinâmico por `ExecStartPre`, sem publicar MQTT nem expor a senha ao usuário do coletor. O serviço está ativo, com zero reinícios desde a correção; a contagem SQLite aumentou de 9 para 12 em 15 segundos e `quick_check` retornou `ok`.
- O repositório público `astec10/nivus-edge-node` recebeu a candidata sanitizada de 65 arquivos sob AGPL-3.0-only no commit `fda4dfc7d5061c28dcdb6b3a7fe421e719bdef3c`. O README, LICENSE AGPL e o componente LegalNotice foram conferidos no branch `main`.
- O aviso AGPL foi compilado no notebook com `npm ci` e `npm run build`; a imagem `nivus-edge-web:agpl-candidate` mede 91.072.305 bytes. O bundle excede o aviso de 500 kB do Vite. Frontend e `/PROGRESS.html` foram publicados com backups e rollback. Os hashes SHA-256 da página e do JavaScript servidos por HTTPS correspondem aos artefatos staged; o bundle servido contém `AGPL-3.0-only` e o link correto para GitHub.
- A aplicação ativa continua em systemd/Nginx. O Compose foi validado somente em ambiente temporário isolado, sem alterar serviços ou banco do host.
- O painel PROGRESS.html está publicado no Nginx do notebook e consulta o próprio HTML via HTTPS a cada 20 segundos; isso atualiza o registro após publicação de nova versão, mas não é telemetria remota ao vivo.
- O README, CONTRIBUTING e roadmap foram reorganizados para explicar objetivo, limites atuais, mapa dos módulos e passo a passo de contribuição. Um inventário de licenças foi gerado a partir dos 141 pacotes npm e 24 distribuições Python do build candidato; todos os registros npm têm licença declarada, mas a compatibilidade e os notices ainda precisam de revisão humana.
- Multi-nó, automação residencial e IA local permanecem objetivos futuros.

## Feito

- Organização do backend FastAPI em routers, schemas, dependências e serviços MQTT.
- Validação isolada com banco SQLite temporário e MQTT simulado; fluxos de autenticação, papéis, PBKDF2, bloqueio, revogação e comandos permitidos passaram.
- Deploy da API modular no notebook de teste com backup prévio do SQLite e fontes, checagem de sintaxe e rollback automático.
- Auditoria pós-deploy: API, worker e coletor ativos; HTTPS/health OK; telemetria sem token retorna 401; SQLite `quick_check: ok` e a coleta continuou durante a observação. Contagens operacionais foram omitidas desta cópia pública.
- Build das imagens Compose com dependências e digests fixados: API 245.737.642 bytes e painel 91.072.058 bytes. O build Vite passou; o Nginx serviu HTML e JavaScript compilado.
- Smoke test Compose isolado, repetido após fixar versões: MQTT saudável, API/painel saudáveis, worker em execução, publicação MQTT gravada no SQLite temporário e telemetria sem token retornou 401. Uso em repouso ~65,3 MiB. Containers/redes temporários foram removidos; os serviços originais continuaram ativos.
- Corrigida a entrada HTTPS do painel: rede interna impedia acesso à porta publicada; o Nginx agora também usa uma rede bridge de entrada separada. API e broker permanecem em redes internas.
- Ativação da UI modular no host: o script fez backup da versão anterior, verificou health e 401 antes/depois da troca, e deixou rollback rápido disponível. O bundle servido corresponde ao hash do artefato compilado.
- Cópia de revisão com instruções para agentes, arquitetura, decisões e configuração sem credenciais.
- Painel dinâmico `/PROGRESS.html` publicado no Nginx; HTML/JavaScript comparados byte a byte após HTTPS, CSP same-origin preservada, health OK e telemetria sem autenticação respondeu 401.

## Em andamento

1. Validar persistência após reboot, backup/restauração e operação prolongada no notebook.
2. Concluir revisão de compatibilidade/notices de dependências e auditoria técnica da candidata.
3. Validar instalação/rollback numa VM Ubuntu Server minimal amd64 limpa; depois repetir em hardware x86_64 diferente.

## Depois

- Validar reboot, backup/restauração, instalação limpa e atualização em Ubuntu Server minimal x86_64 e medir consumo no CCE U25.
- Medir o CCE U25 e outro hardware x86_64; manter a varredura de segredos antes de cada atualização pública.
- Manter decisões críticas de atuadores dependentes de intertravamentos locais, sem permitir que uma IA ou detecção de imagem, sozinha, abra portão ou desligue circuito crítico.

Nenhum suporte universal a hardware, serviço VPN, multi-nó ou automação física é declarado até existir implementação e teste documentados.

