# Estado do projeto Nivus

Atualizado: 2026-11-13
Licença escolhida: AGPL-3.0-only

## Revalidação ao vivo (13/11/2026, 21:15 UTC)

Checagem somente leitura via SSH no notebook de teste:

- `nivus-compose-telemetry.service` estava `active/running`, com zero reinícios.
- Os quatro containers candidatos (web, API, worker e MQTT) estavam em execução; API e MQTT marcados saudáveis pelo Docker.
- `https://127.0.0.1:8443/health` respondeu HTTP 200 com `status: ok`.
- `/api/telemetry` sem token respondeu HTTP 401.
- O SQLite candidato passou `PRAGMA quick_check` (`ok`); numa amostragem de 12 segundos, o número de linhas de telemetria aumentou de 327 para 329.
- O `docker compose ps` no usuário SSH não conseguiu ler `/opt/nivus-compose/current/.env`; os containers foram conferidos com `docker ps` e `docker inspect`, sem ler nem expor o arquivo de segredos.

A página publicada em `/PROGRESS.html` ainda não contém esta revalidação. A versão atual foi copiada para o staging do publicador e o SHA-256 staged/local confere; ainda falta executar o script privilegiado de publicação, que valida Nginx/HTTPS/401 e guarda rollback. Nenhuma instalação limpa em VM foi iniciada: a compatibilidade Ubuntu amd64 ainda precisa dessa validação.

## Correção do empacotamento do instalador (13/11/2026, 21:18 UTC)

O instalador agora exclui bancos SQLite, logs, chaves privadas, certificados privados e arquivos de credenciais da cópia de release; após extrair o pacote, uma busca fail-closed interrompe a instalação se um desses artefatos ainda aparecer. `bash -n` passou no Ubuntu do notebook e um fixture isolado de tar incluiu somente o `README.md`, excluindo arquivos artificiais `.env`, SQLite, chaves, credenciais e logs. Esta correção foi validada em staging; não reinstala nem modifica os serviços ativos do notebook.

## Roteiro da VM preparado (13/11/2026, 21:21 UTC)

`docs/VM_VALIDATION.md` agora define preparação isolada da VM, instalação limpa, login/health/401, crescimento SQLite, reboot e geração de backup. Também deixa explícito que não existe ainda um restaurador automatizado e que o backup omite segredos; restauração permanece um critério pendente e não deve ser improvisada no host em uso. O usuário ainda não informou uma VM disponível ou conexão SSH para esse teste.

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
