# Decisões

## Modularização

Separar rotas, schemas, autorização, banco, MQTT e componentes de UI. Preservar contratos durante extração. API modular e frontend React modular ativos no host de teste, com backup/rollback e login confirmado.

## Autenticação inicial

Usar senha e JWT. USB e biometria continuam opcionais. Não conceder admin com base apenas em IP de LAN. Segredo JWT fica fora do Git.

## Persistência

Manter SQLite até plano de backup, migração e restauração testado. Não converter banco de produção sem backup consistente.

## Plataforma

Alvo declarado: Ubuntu Server minimal amd64. Compatibilidade será anunciada somente após instalação limpa e medições em hardware de baixa capacidade.

## Interface

A página PROGRESS.html acompanha o desenvolvimento. O painel Nivus multi-nó é produto separado e ainda não implementado.

## Acesso remoto

Preferir VPN privada com regras restritas. Não expor SSH ou administração diretamente à Internet. A ferramenta remota também precisa participar da VPN.

## Rede do proxy Compose — 2026-11-13

Contexto: a primeira execução de staging mostrou que publicar HTTPS a partir de uma rede Docker `internal` não abria a porta no host.

Decisão: anexar somente o Nginx a `edge_ingress` (bridge normal) e mantê-lo também na rede interna da API. API e broker não publicam portas no host. O agente systemd lê o endereço atual do broker por um helper root de curta duração; a senha MQTT permanece na credencial systemd do processo sem privilégios.

Consequência: a porta HTTPS publicada pode ser acessada no endereço configurado, enquanto API e broker permanecem isolados. Configuração, build e smoke test foram repetidos depois da alteração e passaram. A primeira instalação real mostrou que porta MQTT publicada em rede interna não fica acessível como loopback; o coletor reiniciava e nenhuma amostra chegava à base candidata. O helper dinâmico e o reparo reversível estão preparados; aplicação e medição real ainda pendentes.

## Licença do projeto — 2026-11-13

Decisão do operador: licenciar o Nivus Edge Node sob AGPL-3.0-only para que pessoas possam usar, estudar, modificar e distribuir versões derivadas conforme os termos da AGPL. Interfaces acessíveis pela rede devem oferecer o código-fonte correspondente sem custo e exibir aviso legal apropriado. A licença completa está em LICENSE; dependências e assets de terceiros mantêm as respectivas licenças e avisos.
