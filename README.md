# Nivus Edge Node — cópia para revisão

Alvo de produto: Ubuntu Server minimal x86_64. Esta árvore foi preparada para revisão técnica; ainda não é um release instalável.

## Estado atual

A API modular passou em verificação isolada e foi ativada em um notebook de teste em 13/11/2026. A ativação usou backup consistente do SQLite e dos fontes, e confirmou compilação Python, health da API, proteção de telemetria sem token e proxy HTTPS. Veja docs/PROJECT_STATUS.md.

O frontend modular está organizado em componentes, compilado e ativado no Nginx do notebook com backup/rollback; health e assets foram conferidos, e o operador confirmou o login. A candidata Compose foi instalada em paralelo sem substituir os serviços antigos; health/HTTPS/401 passaram e a conta inicial foi criada. A verificação encontrou o coletor tentando uma porta localhost que não era publicada pela rede Docker interna. O reparo com backup/rollback e descoberta dinâmica do IP interno foi aplicado; o serviço está estável e as amostras cresceram de 9 para 12 em 15 segundos. Esta árvore continua candidata, não release suportado; instalação limpa, reboot e rollback ainda precisam de validação.

## Licença

AGPL-3.0-only. Consulte [LICENSE](LICENSE). A candidata inclui aviso de licença e links para o código-fonte e a licença na interface. Dependências e assets de terceiros mantêm suas próprias licenças.

## Estrutura

- backend/: API modular FastAPI e serviço MQTT.
- frontend/: extração React/Vite em componentes.
- telemetry/: agente candidato de coleta.
- docs/: visão, arquitetura, decisões, desenvolvimento e estado sem detalhes privados do notebook.
- PROGRESS.html: registro de marcos. Não consome telemetria do notebook.

## Regras

Leia AGENTS.md e docs/PROJECT_STATUS.md antes de alterar. Não copie segredos, banco, logs ou endereços privados para GitHub. Preserve contratos existentes e faça cada alteração com validação/rollback. Não anuncie suporte a Ubuntu, arquitetura x86_64 genérica, multi-nó ou automação real até concluir testes de instalação e hardware.

## Desenvolvimento e execução

Consulte docs/DEVELOPMENT.md e deploy/README.md. Há um instalador candidato para teste; ele instala um stack separado, mas não foi executado em instalação limpa. Não o trate como release de produção. A validação no notebook usou portas/dados de staging e removeu os containers após o teste.

Dependências Python e imagens base estão fixadas nas versões testadas; o frontend usa `package-lock.json` com `npm ci`. Para atualizar versões, faça a alteração deliberada e repita build e smoke test. Licença selecionada: AGPL-3.0-only, conforme decisão do operador. A interface oferece links para o código-fonte e a licença. A instalação limpa em Ubuntu ainda está pendente; veja docs/PROJECT_STATUS.md antes de tratar este pacote como release.
