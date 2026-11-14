# Roteiro do Nivus

Este roteiro transforma a visão de [`VISION.md`](VISION.md) numa sequência de entregas pequenas. Cada fase tem um estado atual e critérios verificáveis. Recursos futuros não devem ser descritos como existentes antes de passar esses critérios.

## Visão em uma frase

Construir uma plataforma local-first, modular e de baixo consumo que monitore computadores e dispositivos de uma casa, integre automações com controles explícitos e, no futuro, distribua tarefas de dados/IA entre nós que anunciam suas capacidades.

O alvo de distribuição é Ubuntu Server minimal x86_64/amd64. “Alvo” não é “compatibilidade universal”: a compatibilidade precisa ser medida por versão de Ubuntu, CPU, RAM, armazenamento, rede e periféricos.

## Onde estamos

**Fundação do nó de borda: funcionando numa instalação Ubuntu de teste.** A API modular, o painel, o broker, o worker e o coletor Compose foram instalados em paralelo no notebook CCE U25. Health HTTPS, autenticação, login, persistência SQLite e aumento contínuo de telemetria foram verificados. A instalação systemd/Nginx anterior permaneceu ativa. Veja [`PROJECT_STATUS.md`](PROJECT_STATUS.md) para evidência e limites.

**Instalação portátil: em validação.** O Compose funciona no CCE U25; `deploy/restore.sh` foi implementado, e o comparador de rollback passou quatro fixtures SQLite descartáveis. A VM `nivus-test-clean` está instalada com Ubuntu Server 24.04.5 LTS amd64 e acessível por chave SSH temporária restrita; o clone limpo do repositório está no commit `5edc7e7`, e sintaxe/`--help` dos scripts passou no guest. Docker e Nivus ainda não foram instalados: a instalação aguarda senha sudo inserida pelo operador. Faltam health/login, coleta, reboot e teste integrado de backup, restore e rollback, além de outro hardware x86_64. Não é ainda um release suportado para todos os computadores.

**Multi-nó, Home Assistant, Zigbee, sensores domésticos, vídeo, IA local, P2P e provedores comerciais: planejados.** O painel atual representa o nó instalado; não existe ainda um coordenador multi-nó ou scheduler de IA.

## Fases de software

### Fase 0 — Nó de borda básico

**Estado: funcionando no notebook de teste; não certificado para instalação geral.**

Entregas existentes: API modular, autenticação por senha/JWT, telemetria de host, MQTT com ACL, SQLite persistente, dashboard React e stack Docker Compose com limites de recursos e HTTPS.

Critérios já observados: login funcional; API exige token; health HTTPS responde; o SQLite candidato passa `quick_check` e recebe novas amostras; o coletor não reinicia; os serviços antigos continuam ativos.

### Fase 1 — Instalação, recuperação e portabilidade

**Estado: próxima prioridade.**

Siga [`VM_VALIDATION.md`](VM_VALIDATION.md) como roteiro executável e registre a evidência em [`PROJECT_STATUS.md`](PROJECT_STATUS.md). O script de restauração está implementado; só declare a etapa concluída após teste real em clone descartável com backup, restore, validação e rollback.

1. Validar instalação limpa em VM Ubuntu Server minimal x86_64, sem arquivos de staging ou segredos prévios.
2. Registrar RAM livre, CPU, disco, espaço de build, portas, versões do Ubuntu/Docker/Compose e tempo de instalação.
3. Reiniciar a VM e confirmar que API, painel, MQTT, worker, coletor, dados e endpoint descoberto voltam sozinhos.
4. Criar backup; usar `deploy/test-restore-rollback.sh` numa VM descartável para demonstrar rollback automático e depois testar uma restauração normal.
5. Repetir em uma segunda versão de Ubuntu suportada e, depois, em hardware x86_64 diferente.
6. Documentar erros recuperáveis, como falta de disco, portas ocupadas, falha APT e interrupção durante o bootstrap.

Critério de saída: uma pessoa que siga o README consegue instalar, autenticar, ver telemetria depois do reboot e restaurar um backup; o procedimento não remove dados ao falhar e não interfere em serviços preexistentes.

### Fase 2 — Identidade e telemetria de vários nós

**Estado: planejada; começar em leitura somente.**

1. Definir identidade estável e cadastro explícito de cada nó; não confiar apenas em nome ou IP.
2. Criar heartbeat, versão do agente, capacidade declarada e estado de conexão.
3. Versionar o envelope de telemetria: nó, timestamp, unidade, origem, qualidade e versão do esquema.
4. Exibir lista de nós, último contato e séries por nó no painel.
5. Tratar duplicatas, atraso, relógios incorretos, perda de rede, revogação e nós desconhecidos.

Critério de saída: dois dispositivos podem enviar telemetria autenticada; um nó desconectado não derruba os outros; credenciais podem ser revogadas; o painel identifica claramente dados ausentes ou antigos.

### Fase 3 — Integrações domésticas e energia

**Estado: planejada; primeira etapa somente leitura.**

1. Integrar Home Assistant através de uma interface/adaptador documentado e com escopo mínimo.
2. Ler estados do hub Zigbee, sensores ambientais e de presença sem conceder administração global.
3. Ler medidores gerais, circuito do inversor e bateria com unidade, timestamp e validação contra a leitura física.
4. Importar eventos de câmeras/NVR para notificações; definir retenção, acesso e consentimento.
5. Só depois avaliar automações de baixo risco e comandos, com allowlist, confirmação, timeout, estado seguro e override manual.

Critério de saída: falha de Internet não impede automações locais; sensores ausentes produzem estado explícito; nenhuma previsão de IA pode, sozinha, abrir portão, desligar circuito crítico ou operar bateria/inversor.

### Fase 4 — IA local e biblioteca documental

**Estado: planejada.**

1. Medir CPU, RAM, GPU/VRAM, disco, temperatura e consumo em cada nó antes de escolher modelo.
2. Criar adaptadores substituíveis para runtimes de inferência; manter o core funcional sem acelerador e sem Internet.
3. Indexar PDFs por tema preservando documento, página e citação; separar arquivos originais de índices derivados.
4. Limitar tamanho de contexto, armazenamento, tempo de inferência e concorrência para não prejudicar monitoramento/automação.
5. Mostrar origem e nível de confiança; permitir revisão humana.

Critério de saída: benchmark reproduzível por hardware, fontes/citações visíveis e degradação controlada quando memória ou modelo não estiver disponível.

### Fase 5 — Orquestração de tarefas entre nós

**Estado: planejada; depende da Fase 2 e da Fase 4.**

1. Começar com tarefas de lote naturalmente independentes: OCR, indexação, embeddings e classificação de clipes.
2. Cada nó anuncia recursos e tipos de tarefa aceitos; o coordenador reserva CPU/RAM/disco e define prazo/lease.
3. Usar IDs idempotentes, checksum, versão de modelo/dados, retries limitados, cancelamento e limites de tamanho.
4. Restringir entradas/saídas e executar workers com identidade, permissões mínimas e sem acesso geral ao host.
5. Adicionar cache e distribuição de artefatos por HTTPS com hashes; estudar P2P só se medições demonstrarem necessidade.

Critério de saída: desligar ou comprometer um nó não causa perda silenciosa de tarefas, alteração de resultados aceitos ou execução fora da permissão declarada.

Compartilhar arquivos por P2P não soma automaticamente a RAM/VRAM de máquinas nem acelera um único modelo. Paralelismo de modelo requer suporte do runtime, interconexão e medições próprias.

### Fase 6 — Provedores de IA comerciais

**Estado: planejada; depende da orquestração e de controles de privacidade.**

1. Criar conectores isolados por provedor, com timeout, custo e quota configuráveis.
2. Registrar limites semanais/mensais sem guardar tokens de acesso em logs.
3. Classificar dados e exigir decisão do operador antes de enviar conteúdo da casa para fora.
4. Respeitar quotas e falhas; usar modelo local ou fila pendente como fallback.
5. Comparar respostas, citar fontes e exigir revisão antes de entregar automação ou código crítico.

Critério de saída: limite financeiro não é ultrapassado silenciosamente; dados locais não saem sem política explícita; falha de Internet não interrompe monitoramento local.

## Sequência recomendada

**Agora:** Fase 1. **Depois:** Fase 2 em leitura somente. **Em seguida:** Home Assistant e sensores em leitura, IA local e só então orquestração. Conectores comerciais entram por último. Esse caminho mede a rede e os nós antes de confiar tarefas ou automações a eles.

Para decidir a próxima entrega física da casa, veja “Decisões em aberto” em [`VISION.md`](VISION.md). Modelos exatos de roteador, switch PoE, câmeras, inversor, medidores e proteção elétrica ainda precisam ser escolhidos e conferidos com documentação de fabricante e profissionais habilitados.
