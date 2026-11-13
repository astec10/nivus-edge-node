# Estado do projeto Nivus

Atualizado: 2026-11-13
Licença escolhida: AGPL-3.0-only

## Resumo

- A API modular passou em validação isolada e foi ativada em um notebook de teste x86_64, conforme saída do operador. O deploy confirmou health local e via HTTPS, resposta 401 para telemetria sem token e criou backup com rollback.
- O frontend React modular foi compilado, validado em staging e ativado no Nginx do notebook com backup e rollback rápido.
- Após ativação, HTTPS serviu o index e o bundle JavaScript compilado; health passou e a API continuou respondendo 401 sem token. O operador confirmou que o login com a conta existente funcionou; nenhuma senha foi compartilhada.
- A candidata Docker Compose foi instalada em paralelo em 13/11/2026: API/MQTT/painel/worker estão em execução, health HTTPS passou, telemetria sem token respondeu 401 e o administrador `nivus` foi criado com PBKDF2. Os serviços systemd/Nginx anteriores continuam ativos.
- A primeira execução do instalador parou antes de alterar o host porque chamou `systemd --version`; foi corrigida para consultar `systemctl --version` (systemd 259). A segunda tentativa parou durante o provisionamento do administrador. O código do instalador também foi endurecido para só remover o link `current` se esta execução tiver criado esse link.
- Depois do primeiro rollback, o instalador foi executado novamente e concluiu o provisionamento. A auditoria SSH confirmou `nivus-api`, `nivus-worker`, `nivus-telemetry` e Nginx antigos ativos, além dos quatro containers candidatos ativos; health HTTPS e HTTP 401 passaram. A conta candidata está armazenada com PBKDF2.
- A verificação operacional encontrou uma falha real: o coletor tentava `127.0.0.1:1884`, enquanto o broker está numa rede Docker `internal`, sem porta publicada no host. Um script reversível instalou um resolver dinâmico por `ExecStartPre`, sem publicar MQTT nem expor a senha ao usuário do coletor. O serviço está ativo, com zero reinícios desde a correção; a contagem SQLite aumentou de 9 para 12 em 15 segundos e `quick_check` retornou `ok`.
- O repositório público `astec10/nivus-edge-node` recebeu a candidata sanitizada de 65 arquivos sob AGPL-3.0-only no commit `fda4dfc7d5061c28dcdb6b3a7fe421e719bdef3c`. O README, LICENSE AGPL e o componente LegalNotice foram conferidos no branch `main`.
- O aviso da interface AGPL foi compilado no notebook com `npm ci` e `npm run build`. O bundle contém `AGPL-3.0-only` e o link para o repositório; imagem `nivus-edge-web:agpl-candidate` mede 91.072.305 bytes. O bundler avisou que o JS minificado excede 500 kB. Frontend compilado e painel PROGRESS estão staged para os scripts Nginx de backup/rollback; a ativação ainda aguarda `sudo` no notebook.
- A aplicação ativa continua em systemd/Nginx. O Compose foi validado somente em ambiente temporário isolado, sem alterar serviços ou banco do host.
- O painel PROGRESS.html está publicado no Nginx do notebook e consulta o próprio HTML via HTTPS a cada 20 segundos; isso atualiza o registro após publicação de nova versão, mas não é telemetria remota ao vivo.
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

1. Publicar a build React AGPL e o painel de progresso atualizado no Nginx com os scripts de backup/rollback.
2. Confirmar login na candidata, persistência após reboot e instruções de backup/restauração.
3. Revisar licenças das dependências e validar instalação/rollback numa instalação limpa Ubuntu amd64. O notebook de teste x86_64 não substitui uma instalação limpa independente.

## Depois

- Validar reboot, backup/restauração, instalação limpa e atualização em Ubuntu Server minimal x86_64 e medir consumo no CCE U25.
- Revisar licenças de dependências e repetir a varredura de segredos antes de cada atualização pública.
- Manter decisões críticas de atuadores dependentes de intertravamentos locais, sem permitir que uma IA ou detecção de imagem, sozinha, abra portão ou desligue circuito crítico.

Nenhum suporte universal a hardware, serviço VPN, multi-nó ou automação física é declarado até existir implementação e teste documentados.
