# Roteiro do Nivus

Este roteiro transforma a visão de [`VISION.md`](VISION.md) numa sequência de entregas pequenas. Cada fase tem um estado atual e critérios verificáveis. Recursos futuros não devem ser descritos como existentes antes de passar esses critérios.

## Visão em uma frase

Construir uma plataforma local-first, modular e de baixo consumo que monitore computadores e dispositivos de uma casa, integre automações com controles explícitos e, no futuro, distribua tarefas de dados/IA entre nós que anunciam suas capacidades.

O alvo de distribuição é Ubuntu Server minimal x86_64/amd64. “Alvo” não é “compatibilidade universal”: a compatibilidade precisa ser medida por versão de Ubuntu, CPU, RAM, armazenamento, rede e periféricos.

## Onde estamos

**Fundação do nó de borda: funcionando numa instalação Ubuntu de teste.** A API modular, o painel, o broker, o worker e o coletor Compose foram instalados em paralelo no notebook CCE U25. Health HTTPS, autenticação, login, persistência SQLite e aumento contínuo de telemetria foram verificados. A instalação systemd/Nginx anterior permaneceu ativa. Veja [`PROJECT_STATUS.md`](PROJECT_STATUS.md) para evidência e limites.

**Instalação portátil: validada por CI hospedada, ainda sem qualificação universal.** O run 43662375766 passou build/smoke Compose e instalação, backup, restauração e rollback em runners Ubuntu descartáveis do GitHub. O operador não usará VMs no computador pessoal. Faltam reboot em hardware, sensores reais adicionais e teste em outras plataformas x86_64; a candidata não é suportada em qualquer computador ainda.

**Multi-nó, Home Assistant, Zigbee, sensores domésticos, vídeo, IA local, P2P e provedores comerciais: planejados.** O painel atual representa o nó instalado; não existe ainda um coordenador multi-nó ou scheduler de IA.

## Fases de software

### Fase 0 — Nó de borda básico

**Estado: funcionando no notebook de teste; não certificado para instalação geral.**

Entregas existentes: API modular, autenticação por senha/JWT, telemetria de host, MQTT com ACL, SQLite persistente, dashboard React e stack Docker Compose com limites de recursos e HTTPS.

Critérios já observados: login funcional; API exige token; health HTTPS responde; o SQLite candidato passa `quick_check` e recebe novas amostras; o coletor não reinicia; os serviços antigos continuam ativos.

**Operação de manutenção (issue #26):** implementação merged no PR #28, com `nivus help` e controle administrativo; CI hospedada aprovada. A pausa interrompe amostragem/publicação de telemetria do host e gravação de novas amostras MQTT, sem desligar API, painel, health ou broker. A publicação e o teste no notebook CCE U25 ainda estão pendentes.

### Fase 1 — Instalação, recuperação e portabilidade

**Estado: em andamento; integração de persistência merged, imagem inicializável pendente.**

**Issue #29 — Ubuntu + Nivus instalado em USB persistente:** a integração inicial de storage foi integrada pelo PR #31. Uma partição ext4 `NIVUS_DATA` é montada em `/var/lib/nivus`; symlinks preservam os caminhos de dados, configuração/segredos, releases e Docker. O guard systemd valida montagem, filesystem, rótulo, marcador e layout antes de Docker/coletor; a ausência do volume bloqueia os serviços. O workflow `Live USB storage` passou em runner Ubuntu hospedado com ext4 em loop device. O operador confirmou uma instalação completa de Ubuntu Server minimal no pendrive, como nó portátil e temporário para outro computador x86_64; o sistema e os dados persistem entre reinicializações, sem instalar no disco interno da máquina hospedeira. **Ainda não há instalador/imagem Nivus pronta para USB.** O instalador deve pedir confirmação explícita do pendrive de destino e não presumir que o maior disco seja o USB. Faltam layout de partições raiz + NIVUS_DATA, artefato reprodutível, smoke de instalação/health/auth, reboot e persistência. Testes físicos UEFI/BIOS e Intel/AMD continuam separados.

Siga [`VM_VALIDATION.md`](VM_VALIDATION.md) como roteiro executável e registre a evidência em [`PROJECT_STATUS.md`](PROJECT_STATUS.md). O script de restauração está implementado; só declare a etapa concluída após teste real em clone descartável com backup, restore, validação e rollback.

1. Implementar um construtor reproduzível de Casper Live x86_64 e escolher uma base LTS no workflow. A raiz do sistema será volátil; SQLite, segredos, configuração e estado Nivus ficarão em NIVUS_DATA separado. Não usar a ISO oficial Ubuntu Server sem convertê-la, pois ela inicia o instalador.
2. Construir a imagem e o primeiro smoke em runner Ubuntu hospedado pelo GitHub a cada pull request para `main` e push em `main`; não iniciar VMs no computador do operador.
3. Registrar RAM livre, CPU, disco, espaço de build, portas, versões do Ubuntu/Docker/Compose e tempo de instalação.
4. Exercitar boot, reinicialização, persistência, instalação, backup, restore e rollback no runner descartável hospedado pelo CI, sem alterar o notebook de teste.
5. Preservar as evidências e logs sanitizados do runner como artefatos da execução; repetir o fluxo após mudança nos scripts operacionais.
6. Qualificar seis máquinas de referência: Intel e AMD, cada fabricante nas faixas de geração antiga, intermediária e recente. Não repetir a suíte inteira por commit; usar a bateria física de compatibilidade documentada em [`TEST_STRATEGY.md`](TEST_STRATEGY.md).
7. Documentar erros recuperáveis, como falta de disco, portas ocupadas, falha APT e interrupção durante o bootstrap.

Critério de saída: uma pessoa que siga o README consegue instalar, autenticar, ver telemetria depois do reboot e restaurar um backup; o procedimento não remove dados ao falhar e não interfere em serviços preexistentes.

CI aprovado comprova o fluxo no runner virtual Ubuntu, não em cada chipset ou periférico. O suporte a plataformas Intel/AMD só será anunciado depois dos seis registros de referência, com CPU, placa-mãe, BIOS, rede, armazenamento e resultado.

### Fase 2 — Identidade e telemetria de vários nós

**Estado: planejada; começar em leitura somente quando o Nó Master estiver operacional.** A telemetria local existe no nó de teste, mas agregá-la entre nós não é requisito para avançar o executor de desenvolvimento ou a biblioteca versionada. Cadastro/heartbeat e atualização coordenada serão entregas distintas. O operador deseja que uma correção, atualização ou função nova possa ser iniciada para todas as máquinas Nivus em rede; o envio automático ainda não existe.

1. Definir identidade estável e cadastro explícito de cada nó; não confiar apenas em nome ou IP.
2. Criar heartbeat, versão do agente, capacidade declarada e estado de conexão.
3. Versionar o envelope de telemetria: nó, timestamp, unidade, origem, qualidade e versão do esquema.
4. Exibir lista de nós, último contato e séries por nó no painel.
5. Tratar duplicatas, atraso, relógios incorretos, perda de rede, revogação e nós desconhecidos.
6. Definir distribuição de releases assinadas: inventário de versão/capacidades, seleção dos nós elegíveis, canário seguido de ondas, health check, manutenção de dados e rollback independente por nó. Offline, baixa bateria ou recursos insuficientes devem adiar a atualização sem bloquear a frota.

Critério de saída: dois dispositivos podem enviar telemetria autenticada; um nó desconectado não derruba os outros; credenciais podem ser revogadas; o painel identifica claramente dados ausentes ou antigos.

Para atualizações de frota, o critério adicional é demonstrar uma correção simulada em um nó canário, ampliar a implantação aos nós elegíveis depois do health check, e reverter somente o nó que falhar. Cada nó valida assinatura e compatibilidade antes de aplicar o artefato.

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
3. Criar uma biblioteca compartilhada de conhecimento curado: PDFs licenciados, documentação técnica e resumos próprios de vídeos/artigos, preservando documento/URL, página ou timestamp, versão, licença, checksum e citação.
4. Separar extração e OCR dos originais; atomizar por conceito e classificar tema, confiança e status de verificação. Não ingerir uma alegação de vídeo como fato sem fonte primária ou teste reproduzível.
5. Começar com índice lexical reproduzível e consulta com citações; avaliar embeddings/RAG somente após medir qualidade, latência, RAM e disco.
6. Versionar catálogo e notas públicas no GitHub para que qualquer IA veja o mesmo conhecimento. Segredos, dados domésticos e transcrições completas sem licença ficam fora do repositório.
7. Definir identidade/ACL, sincronização, retenção e revogação antes de servir dados da biblioteca entre nós.
8. Limitar tamanho de contexto, armazenamento, tempo de inferência e concorrência para não prejudicar monitoramento/automação.
9. Mostrar origem e nível de confiança; permitir revisão humana.

Critério de saída: benchmark reproduzível por hardware; consultas reproduzíveis em catálogo versionado com fontes/timestamps/citações visíveis; sincronização autorizada entre nós; e degradação controlada quando memória, índice ou modelo não estiver disponível.

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

**Em paralelo agora:** concluir a Fase 1 por CI hospedada, manter a biblioteca pública versionada e avançar o executor externo de desenvolvimento. Esse executor não depende da telemetria do nó. **Quando o Nó Master estiver operacional:** iniciar a Fase 2 em leitura somente para agregar dados dos nós. Depois seguem Home Assistant e sensores em leitura, IA local e só então o scheduler de tarefas entre nós. Conectores comerciais entram por último.

Para decidir a próxima entrega física da casa, veja “Decisões em aberto” em [`VISION.md`](VISION.md). Modelos exatos de roteador, switch PoE, câmeras, inversor, medidores e proteção elétrica ainda precisam ser escolhidos e conferidos com documentação de fabricante e profissionais habilitados.
