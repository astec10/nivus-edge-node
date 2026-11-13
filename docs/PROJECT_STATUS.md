# Estado do projeto Nivus

Atualizado: 2026-11-13
Licença escolhida: AGPL-3.0-only

## Resumo

- A API modular passou em validação isolada e foi ativada em um notebook de teste x86_64, conforme saída do operador. O deploy confirmou health local e via HTTPS, resposta 401 para telemetria sem token e criou backup com rollback.
- O frontend React modular foi compilado, validado em staging e ativado no Nginx do notebook com backup e rollback rápido.
- Após ativação, HTTPS serviu o index e o bundle JavaScript compilado; health passou e a API continuou respondendo 401 sem token. O operador confirmou que o login com a conta existente funcionou; nenhuma senha foi compartilhada.
- A candidata Docker Compose passou por configuração, build e smoke test em staging. A tentativa de instalação paralela iniciou API/MQTT/painel e passou health HTTPS/401, mas foi revertida antes de concluir a criação do administrador; ainda não é um release suportado.
- A primeira execução do instalador parou antes de alterar o host porque chamou `systemd --version`; foi corrigida para consultar `systemctl --version` (systemd 259). A segunda tentativa parou durante o provisionamento do administrador. O código do instalador também foi endurecido para só remover o link `current` se esta execução tiver criado esse link.
- Auditoria após rollback: `nivus-api`, `nivus-worker` e `nivus-telemetry` continuam ativos; somente Mosquitto original permanece no Docker. Containers e redes da candidata foram removidos, `current` está ausente, e o banco candidato está íntegro, com zero usuários e zero telemetrias. Segredos e diretório de dados da candidata foram preservados. O instalador corrigido passou `bash -n` remotamente; nova tentativa está pendente.
- O repositório público `astec10/nivus-edge-node` foi criado com AGPL-3.0. O operador confirmou alinhar a candidata local para AGPL-3.0-only; nenhum código candidato foi enviado ainda.
- O texto AGPL oficial e os metadados foram alinhados. Foi adicionado `frontend/src/components/LegalNotice.jsx` com aviso de ausência de garantia e links para o código-fonte/licença; ainda falta compilar e publicar essa versão do frontend e do painel PROGRESS.
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

1. Compilar/publicar os avisos de interface AGPL-3.0-only, revisar dependências/licenças e enviar a candidata sanitizada para `astec10/nivus-edge-node`, já criado como público.
2. Repetir a instalação paralela, completar a criação inicial do administrador e verificar HTTPS/401, coleta, recursos e preservação da instalação atual.
3. Validar instalação e rollback numa instalação limpa Ubuntu amd64. O notebook de teste x86_64 não substitui uma instalação limpa independente.

## Depois

- Validar instalação limpa e atualização em Ubuntu Server minimal x86_64 e medir consumo no CCE U25.
- Revisar licenças de dependências e concluir a varredura final antes do primeiro push público.
- Manter decisões críticas de atuadores dependentes de intertravamentos locais, sem permitir que uma IA ou detecção de imagem, sozinha, abra portão ou desligue circuito crítico.

Nenhum suporte universal a hardware, serviço VPN, multi-nó ou automação física é declarado até existir implementação e teste documentados.
