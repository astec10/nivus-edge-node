# Roteiro do Nivus

Este roteiro transforma a visão de [`VISION.md`](VISION.md) numa sequência de entregas pequenas. Cada fase tem um estado atual e critérios verificáveis. Recursos futuros não devem ser descritos como existentes antes de passar esses critérios.

## Visão em uma frase

Construir uma plataforma local-first, modular e de baixo consumo que monitore computadores e dispositivos de uma casa, integre automações com controles explícitos e, no futuro, distribua tarefas de dados/IA entre nós que anunciam suas capacidades.

O alvo de distribuição é Ubuntu Server minimal x86_64/amd64. “Alvo” não é “compatibilidade universal”: a compatibilidade precisa ser medida por versão de Ubuntu, CPU, RAM, armazenamento, rede e periféricos.

## Onde estamos

**Fundação do nó de borda: funcionando numa instalação Ubuntu de teste.** A API modular, painel, broker, worker, coletor Compose e registro inicial de nós foram instalados em paralelo no notebook CCE U25. Em 17/11/2026, a release `fff64a68f252f0b1290576e30b39ed78fbc15a7a` foi aplicada; build, backup SQLite, restart dos serviços, HTTPS 200 e telemetria sem token 401 foram confirmados. Isso não comprova reboot completo ou compatibilidade universal. Veja [`PROJECT_STATUS.md`](PROJECT_STATUS.md) para evidências e limites.

**Instalação portátil: código integrado, validação física pendente.** Ubuntu Server completo instalado no USB, com raiz e NIVUS_DATA persistentes. O PR #34 foi integrado à `main` (`703efa4128f60460910b05ab344b60b082006a7e`); todos os checks hospedados passaram no head `3a1621dc11d2532853ef83b9ab5ea47f64cfaca5`, incluindo schema Subiquity, bootstrap, ext4 em loop, smoke Compose, índice e CodeQL. Essa evidência não substitui instalação/reinicialização em USB físico nem teste de compatibilidade. O operador não usará VMs no computador pessoal.

**Multi-nó operacional, Home Assistant, Zigbee, sensores domésticos, vídeo, IA local e P2P continuam futuros.** O cadastro administrativo de provedores (#68/#72) e o executor limitado de inferência (#74/#82) estão integrados à `main`; o cadastro está na release `f896de8` do notebook, mas a implantação do executor runtime ainda não foi confirmada. Nenhuma inferência real foi chamada. A primeira camada de identidade/pareamento/heartbeat está integrada pelo PR #66 e implantada em `fff64a68f252f0b1290576e30b39ed78fbc15a7a`; ela não agrega telemetria, executa comandos nem atualiza frota. O agente mínimo de nó foi implementado no PR #69; falta validar dois dispositivos reais e avançar com a telemetria agregada.

## Fases de software

### Fase 0 — Nó de borda básico

**Estado: funcionando no notebook de teste; não certificado para instalação geral.**

Entregas existentes: API modular, autenticação por senha/JWT, telemetria de host, MQTT com ACL, SQLite persistente, dashboard React e stack Docker Compose com limites de recursos e HTTPS.

Critérios já observados: login funcional; API exige token; health HTTPS responde; o SQLite candidato passa `quick_check` e recebe novas amostras; o coletor não reinicia; os serviços antigos continuam ativos.

**Operação de manutenção (issue #26):** implementação integrada no PR #28 e presente no update `fff64a68` informado em 17/11; o último estado reportado depois é `f896de8`, sem sondagem nesta revisão. A CI hospedada passou. A pausa interrompe amostragem/publicação de telemetria do host e gravação de novas amostras MQTT, sem desligar API, painel, health ou broker. Ainda falta executar `nivus help`, exercitar pausa/retomada e reinício normal no notebook.

**Relógio, interface e sensores (issues #21/#23):** PRs #37–#50 implementaram preferências, controle NTP, temas, gráficos, bateria interna e regra móvel. Em 17/11/2026, a release `fff64a68f252f0b1290576e30b39ed78fbc15a7a` foi aplicada com health HTTPS 200 e 401 sem token. Depois o operador informou `f896de8` e promoção reversível para HTTPS 443; reboot e conferência visual continuam pendentes e o host não foi sondado nesta revisão. PR #67 compactou medidores Glass e moveu as dicas dos cartões para os detalhes após 3 segundos. O operador não usará VMs locais; CI hospedada valida software, não hardware físico.

**Perfil de desempenho condicionado à alimentação (issue #62):** PR #87 integrado em 21/11/2026, com 12 testes simulados locais e quatro workflows hospedados aprovados. Sinal confirmado de alimentação permite somente mudar para um governor disponível, dentro dos limites térmicos. Sem sinal válido, perfil conservador; atuadores mantêm regras e overclock é manual. Linux Mains só vale com AC direta; para a entrada AC do UPS, requer NUT local com estado `OL`/`OB`. Erro ou estado ambíguo mantém o modo conservador. A política e o timer estão desligados por padrão. Instalação e validação em hardware continuam pendentes.

### Fase 1 — Instalação, recuperação e portabilidade

**Estado: em andamento; instalação física e recuperação ainda não validadas.**

**Issue #29 — Ubuntu instalado em USB com dados persistentes:** Ubuntu Server completo, não Casper Live. O PR #31 integrou `NIVUS_DATA` ext4 em `/var/lib/nivus` e guard antes do Docker/coletor. O PR #34 foi integrado à `main` e acrescenta seleção/revalidação do USB, seed Subiquity com confirmação humana de armazenamento e instalação pós-boot do Compose. Os checks hospedados passaram no head `3a1621dc11d2532853ef83b9ab5ea47f64cfaca5`. Ainda não existe ISO customizada ou validação física; faltam instalação interativa até o primeiro boot, primeiro login, reboot e verificação de persistência/recuperação, além da matriz UEFI/BIOS Intel/AMD.

Siga [`VM_VALIDATION.md`](VM_VALIDATION.md) como roteiro executável e registre a evidência em [`PROJECT_STATUS.md`](PROJECT_STATUS.md). O script de restauração está implementado; só declare a etapa concluída após teste real em clone descartável com backup, restore, validação e rollback.

1. Formato decidido: Ubuntu Server completo instalado no USB, com raiz e dados persistentes; usar mídia Ubuntu inicializável separada, seed NoCloud privado e confirmação humana do destino. Não é Casper Live.
2. [x] CI hospedada aprovada no head `3a1621dc11d2532853ef83b9ab5ea47f64cfaca5` para seletor, seed/schema Subiquity, bootstrap, guard ext4, smoke Compose, workflows gerais e CodeQL.
3. Registrar RAM livre, CPU, disco, espaço de build, portas, versões do Ubuntu/Docker/Compose e tempo de instalação.
4. Exercitar boot, reinicialização, persistência, instalação, backup, restore e rollback no runner descartável hospedado pelo CI, sem alterar o notebook de teste.
5. Preservar as evidências e logs sanitizados do runner como artefatos da execução; repetir o fluxo após mudança nos scripts operacionais.
6. Qualificar seis máquinas de referência: Intel e AMD, cada fabricante nas faixas de geração antiga, intermediária e recente. Não repetir a suíte inteira por commit; usar a bateria física de compatibilidade documentada em [`TEST_STRATEGY.md`](TEST_STRATEGY.md).
7. Documentar erros recuperáveis, como falta de disco, portas ocupadas, falha APT e interrupção durante o bootstrap.

Critério de saída: uma pessoa que siga o README consegue instalar, autenticar, ver telemetria depois do reboot e restaurar um backup; o procedimento não remove dados ao falhar e não interfere em serviços preexistentes.

CI aprovado comprova o fluxo no runner virtual Ubuntu, não em cada chipset ou periférico. O suporte a plataformas Intel/AMD só será anunciado depois dos seis registros de referência, com CPU, placa-mãe, BIOS, rede, armazenamento e resultado.

### Fase 2 — Identidade e telemetria de vários nós

**Estado: registro inicial implantado; agente mínimo implementado no PR #69; ingestão autenticada em revisão no PR #97; multi-nó operacional ainda incompleto.** A release `fff64a68f252f0b1290576e30b39ed78fbc15a7a` contém o cadastro seguro da issue #65 / PR #66. O PR #69 acrescenta pareamento e heartbeat; seus testes com dois nós simulados não substituem HTTPS end-to-end. O PR #97 adiciona envio HTTPS, persistência por nó, envelope estrito, sequência compartilhada, retry idempotente, intervalo mínimo de 30 segundos e retenção de 14 dias. A revisão corrigiu a consulta de histórico para também expirar os dados de nós offline e apagar as amostras filhas; a nova cobertura e o estado dos quatro workflows devem ser conferidos na aba Checks do PR. A suíte unittest completa requer FastAPI e é executada na CI hospedada. PR #93 e #96 continuam separados; reconcilie os arquivos compartilhados antes de integrar. Pareamento/TLS em dispositivos reais, painel de séries, perda de rede e atualização coordenada ainda não foram validados.

1. [x] Identidade criada pelo servidor e cadastro administrativo por código de uso único — PR #66.
2. [x] Heartbeat autenticado, sequência contra replay e presença baseada no relógio do servidor — PR #66.
3. [x] Implementar agente mínimo de pareamento/heartbeat (PR #69; CI hospedada aprovada).
4. [ ] Testar pareamento e heartbeat em dois dispositivos reais, incluindo TLS confiável, reinício e revogação.
5. [ ] Revisar e integrar o envelope versionado com timestamp de origem, unidade, qualidade, schema, idempotência, retenção e limite de taxa por nó; PR #97 também separa horário de origem e recebimento pelo servidor.
6. [ ] Exibir lista de nós, último contato e séries por nó no painel (PR #96 está aberto para lista read-only; a série aguarda ingestão integrada).
7. [ ] Validar duplicatas, atraso, relógios incorretos, perda de rede, revogação e nós desconhecidos na candidata e em dois dispositivos reais.
8. [ ] Definir distribuição de releases assinadas: inventário de versão/capacidades, seleção dos nós elegíveis, canário seguido de ondas, health check, manutenção de dados e rollback independente por nó. Offline, baixa bateria ou recursos insuficientes devem adiar a atualização sem bloquear a frota.

Critério de saída: dois dispositivos podem enviar telemetria autenticada; um nó desconectado não derruba os outros; credenciais podem ser revogadas; o painel identifica claramente dados ausentes ou antigos.

Para atualizações de frota, o critério adicional é demonstrar uma correção simulada em um nó canário, ampliar a implantação aos nós elegíveis depois do health check, e reverter somente o nó que falhar. Cada nó valida assinatura e compatibilidade antes de aplicar o artefato.

### Fase 3 — Integrações domésticas e energia

**Estado: parcialmente em andamento.** A primeira regra limitada de atuador (issue #22: bateria móvel → somente OFF no relé) foi integrada pelo PR #50 no commit `ba6e0c824fe1b62dd44c7d924a6a2d1074f26e23`; os quatro workflows hospedados passaram. A regra só opera após cadastro do dispositivo e envio de relatórios válidos pela integração Home Assistant, ainda não configurada ou validada em hardware. As demais integrações começam em leitura somente; nenhuma ação física foi testada.

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

**Estado: cadastro administrativo integrado no PR #72; o executor runtime da issue #74 foi integrado no PR #82 e os checks hospedados passaram na main.** A release `f896de8` do notebook contém o cadastro, não há confirmação de implantação do PR #82. Nenhuma inferência real foi chamada. Consulte [AI_PROVIDER_CONNECTORS.md](AI_PROVIDER_CONNECTORS.md).

1. [x] Cadastro administrativo com credenciais cifradas, classificação de dados e perfis explicitamente habilitados (PR #72).
2. [x] Implementar conectores isolados por protocolo, timeout, preço configurável e reserva de orçamento/quota antes da chamada (PR #82; CI hospedada aprovada).
3. Não guardar prompt, saída nem token de acesso no banco/auditoria; manter chave mestra fora do SQLite e do repositório.
4. Classificar dados e exigir solicitação explícita; a nuvem só recebe conteúdo público/sintético.
5. Manter fallback automático desligado até política, orçamento e provedor alternativo receberem validação própria.
6. Exigir revisão humana antes de usar a saída para automação ou código crítico.

Critério de saída: limite financeiro não é ultrapassado silenciosamente; dados locais não saem sem política explícita; falha de Internet não interrompe monitoramento local.

## Sequência recomendada

**Próximos trabalhos:** atualizar o notebook para a `main` atual pelo fluxo reversível e confirmar health, autenticação, Configuração/provedores e dashboard após reboot; a última release informada é `f896de8`, anterior aos PRs #82 e #87. A política AC/UPS deve continuar desabilitada até verificar a fonte e o governor conservador no hardware. Depois, retomar instalação USB física, smoke do agente em dois nós e validações Intel/AMD. O registro multi-nó inicial está integrado; agregação de dados e atualização de frota não existem.

Para decidir a próxima entrega física da casa, veja “Decisões em aberto” em [`VISION.md`](VISION.md). Modelos exatos de roteador, switch PoE, câmeras, inversor, medidores e proteção elétrica ainda precisam ser escolhidos e conferidos com documentação de fabricante e profissionais habilitados.
