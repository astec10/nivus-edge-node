# Visão do projeto Nivus — automação local e IA distribuída

Data: 2026-11-13

## Objetivo declarado

Construir uma casa conectada local-first: Home Assistant controla integrações e automações; sensores de energia, ambiente e presença fornecem dados; câmeras geram eventos locais; uma ou mais máquinas executam modelos de IA; nós Nivus anunciam capacidades e recebem tarefas conforme recursos disponíveis. Serviços comerciais podem ser usados quando o operador habilitar e quando orçamento/privacidade permitirem.

Esta visão é contexto e plano. Não significa que os dispositivos, a rede, os sensores, o inversor, a IA local ou o agendamento distribuído já estejam instalados.

## Interface desejada do Nivus

A tela inicial deve funcionar como portal de autenticação local, com apresentação simples semelhante à página de administração de um roteador. Após autenticar, o utilizador acessa um painel HTML5 dinâmico com abas separadas, em uma navegação familiar a abas de navegador: visão geral, nós, telemetria por nó, automações residenciais, usuários e configurações/auditoria. Atualizações de estado devem refletir mudanças sem recarregar a página inteira; o mecanismo (SSE, WebSocket ou polling adaptativo) será escolhido conforme carga e necessidade de latência. O painel deve permanecer leve para hardware antigo.

Esta é a especificação declarada pelo usuário. O painel atual ainda mostra um único nó, tem duas abas e usa polling de cinco segundos; lista distribuída de nós, automações da casa e atualização por eventos ainda não estão implementadas.

## Acesso remoto

Administrar remotamente por VPN privada (por exemplo, Tailscale/WireGuard) com regras de acesso restritas. Não encaminhar SSH ou painel administrativo diretamente pela Internet. A própria sessão/ferramenta que fará SSH também precisa ter rota na VPN; instalar VPN apenas no notebook não concede automaticamente acesso a uma sessão externa.

## Referências de inspiração fornecidas pelo usuário

- [I Build a REAL Holographic AI Assistant!](https://www.youtube.com/watch?v=WgqDaqqto90): ideia opcional de assistente por voz com personagem/visor e controle local de privacidade para câmera e microfone. É uma referência de produto/hardware, não uma dependência do Nivus.
- [Como usar IA sem censura no PC — 100% local (2026)](https://www.youtube.com/watch?v=YC5sG321g0Y): referência para explorar inferência local e escolha de modelos. O conteúdo técnico completo não ficou disponível nesta revisão; não escolher runtime, modelo ou dependências só pelo título do vídeo.

Para o Nivus, runtime/modelo deve ser substituível por adaptador e medido no hardware disponível. A IA permanece uma camada de recomendação/consulta; ações da casa continuam submetidas a regras determinísticas e controles físicos.

## Camadas propostas

1. **Rede e segurança:** ONU da operadora → WAN de roteador/firewall → LAN do roteador → switch PoE gerenciável. O switch alimenta os APs Wi-Fi, hub/bridge e dispositivos compatíveis; o switch de cinco portas conecta-se como extensão da LAN. Câmeras/IoT ficam em segmentos separados dos computadores pessoais. Acesso remoto ocorre por VPN, não por portas administrativas expostas.
2. **Automação residencial:** Home Assistant como fonte de verdade de entidades, áreas, estado e automações. Zigbee entra por coordenador local. Assist pode manter comandos de voz locais; expor somente as entidades necessárias ao agente de IA.
3. **Energia:** medidores e inversor fornecem leituras por interface suportada pelo fabricante (por exemplo Modbus, MQTT ou integração oficial). Começar em leitura e histórico; automatizar cargas só com regras determinísticas, limites físicos e dispositivos de corte apropriados.
4. **Vídeo:** câmeras alimentam NVR local e detecção de eventos. Classificação de pessoa/rosto/placa pode sugerir evento; passagem de pessoas e acionamento de portão ficam sujeitos a barreiras independentes e confirmação segura.
5. **Dados e Nivus:** coletor publica eventos/métricas com unidade, origem, timestamp, qualidade e versão de esquema; broker transporta eventos; armazenamento separa séries temporais, eventos e documentos; serviço Nivus registra nós, capacidades, fila de tarefas, tentativas e artefatos.
6. **IA:** serviços específicos para visão, voz, extração/busca em PDF e LLM conversacional. A regra de automação executável permanece em Home Assistant/serviço determinístico; o LLM interpreta ou recomenda, mas não vira controlador irrestrito.
7. **Conectores comerciais:** adaptadores por provedor/especialidade com limites diários, semanais e mensais, auditoria de tokens/custo e política de quais dados podem sair da LAN.

## Topologia física a validar

O uplink de fibra/ONU deve terminar na porta WAN do roteador/firewall. A porta LAN do roteador liga ao switch gerenciável PoE. Um switch de acesso de cinco portas liga-se a uma porta LAN/uplink do switch principal. Em um switch Ethernet comum de camada 2, as portas “uplink” não fazem roteamento WAN; ligar a ONU diretamente ao switch da LAN mistura domínios e pode expor dispositivos. Dois links entre os mesmos switches podem criar loop se não houver agregação/STP configurados. Confirmar modelos e diagrama do fabricante antes da instalação.

VLANs sugeridas, condicionadas a suporte do roteador, switch e AP: gerenciamento; automação/IoT; câmeras/NVR; clientes domésticos; serviços/servidores. As regras devem permitir apenas os fluxos necessários (por exemplo, Home Assistant até dispositivos IoT e NVR até câmeras), bloqueando a iniciação de conexões de câmeras para computadores pessoais.

## Distribuição de tarefas entre máquinas

- Começar com **orquestração de tarefas**, não com um cluster que promete transformar PCs fracos numa GPU grande. Um nó anuncia CPU, RAM disponível, acelerador, espaço, conectividade e tarefas aceitas. O coordenador escolhe um nó capaz, reserva recursos, atribui prazo/lease e recolhe resultado com checksum/versionamento.
- Categorias de trabalho naturalmente distribuíveis: OCR de PDFs, indexação por lote, transcrição, classificação de clipes, geração de embeddings e pesquisas independentes. Inferência de uma única resposta pode ser encaminhada para um servidor de modelo mais potente.
- Dividir a execução de um único modelo por RAM/VRAM de várias máquinas exige suporte explícito no runtime/modelo e rede apropriada. Compartilhar arquivos de pesos por P2P ajuda em transferência/cache, mas não soma automaticamente a memória nem acelera cada token. O vídeo NetworkChuck/WiCi demonstra uma caixa GPU especializada, streaming de pesos por SSD e scheduler; é um produto/demonstração patrocinada, não evidência de que nós genéricos Nivus se combinem sem esse software e hardware.
- Primeiro usar catálogo/API central de artefatos com hashes e cache local. Adicionar P2P depois, quando medições mostrarem gargalo de distribuição; replicação precisa tratar versões, origem confiável, espaço, revogação e integridade.
- Para uma biblioteca de PDFs, manter originais e metadados; extrair/OCR e indexar por tema com rastreio de página/citação. Embeddings/RAG são para busca semântica nos documentos. Telemetria numérica deve continuar como séries temporais consultáveis, com agregações/features quando necessárias; não “tokenizar” tudo indiscriminadamente.

## Política de segurança e falha segura

- Não permitir que um LLM, reconhecimento facial ou leitura de placa, sozinho, destranque porta, abra portão, desligue carga crítica ou faça corte de bateria/rede elétrica. Começar com notificação e revisão humana; qualquer automação posterior precisa de condições locais verificáveis, sensores independentes, limites e override manual.
- Detecção de queda/imobilidade gera alerta para confirmação; não substituir ligação a serviço de emergência nem assumir que a câmera vê todos os cômodos.
- Detectores certificados de fumaça, CO e gás continuam sendo a proteção primária. A IA recebe estado/alarme e notifica. Desligamento de válvula ou circuito requer equipamento aprovado e projeto/instalação por profissional habilitado.
- Inversor híbrido, baterias 48 V, balanceador, QDC, aterramento, neutro, transferência/islanding e proteção contra corrente exigem dimensionamento, compatibilidade com os manuais e instalação por profissional qualificado. Esta visão não é um projeto elétrico.
- Vídeo, faces, placas e presença são dados pessoais: retenção mínima, acesso restrito, criptografia/backups e informação/consentimento de moradores e visitantes devem ser definidos antes da ativação.

## Requisito prioritário — portabilidade e instalação

O alvo de distribuição é computador **x86_64 (amd64)** com **Ubuntu Server minimal**. Isso é um alvo a validar, não uma garantia de compatibilidade com todo computador: antes da primeira versão instalável, definir CPUs, RAM, armazenamento, versões Ubuntu suportadas e periféricos opcionais.

A instalação deve ser idempotente e guiada: verificar arquitetura, versão do Ubuntu, recursos, espaço e portas; instalar ou validar Docker Engine e Compose; obter configuração sem guardar segredos no repositório; criar volumes persistentes; subir serviços com healthchecks; e oferecer atualização, backup e rollback. Serviços de hardware (GPIO/USB, MQTT, câmeras, inversor) devem ser opcionais e isolados para que o núcleo suba sem esses dispositivos. Validar em instalações limpas de máquinas virtuais x86_64 antes de anunciar compatibilidade.

O host de teste atual comprova somente a execução naquela instalação Ubuntu. A implantação validada ainda usa systemd e Nginx; o pacote Docker/Compose é protótipo e não é o método em produção nesse notebook.

## Fases e critérios de saída

### Fase 0 — Inventário e documentação

Registrar modelo de ONT/roteador, switch(es), orçamento PoE, APs, cabos/pontos, câmeras, interfone, hub Zigbee, Home Assistant, inversor/BMS/medidores, dispositivos de proteção, RAM/CPU/discos e backups. Produzir diagrama L2/L3 e lista de entidades/tópicos. Nenhuma automação de energia ainda.

### Fase 1 — Rede e operação local

Roteador/firewall e VLANs, DNS/NTP local, VPN, UPS e backup configurados. Critério: dispositivos seguem acessíveis dentro de sua zona, mas câmeras/IoT não iniciam conexões para a rede pessoal; documentação permite restaurar configuração.

### Fase 2 — Home Assistant e telemetria

Subir Home Assistant e Zigbee; cadastrar sensores e medidores primeiro em leitura. Normalizar unidades/tempo e verificar dados contra leitura física do medidor. Critério: histórico coerente durante reinício/queda de Internet, sem controle de carga.

### Fase 3 — Automação determinística

Iluminação e alertas de baixo risco. Para cada regra, documentar trigger, condições, ação, timeout, comportamento quando sensores/rede estão indisponíveis e override manual. Depois testar o estado de bateria/energia sem ligar cargas reais.

### Fase 4 — Vídeo local e revisão

Validar câmera por câmera, retenção, detecção, latência, falsos positivos e cobertura. Começar com gravação/alertas; face/placa é etapa opcional. Ação de portão só depois de uma etapa separada de análise de risco e com validações não baseadas só no modelo.

### Fase 5 — Servidor local de IA

Inventariar hardware antes de escolher modelo: RAM disponível, capacidade/banda de memória, CPU, GPU/VRAM, SSD e consumo/ruído. Medir latência e qualidade para cada carga. O notebook CCE de teste pode hospedar serviços leves, mas não deve ser tratado como acelerador de vídeo/LLM sem benchmark real.

### Fase 6 — Rede de nós Nivus

Começar com um coordenador e 2 nós; heartbeat/capacidade, fila com retries/leases, IDs idempotentes, checksum de artefato e limites de CPU/RAM/disco. Distribuir tarefas em lote independentes. Critério: desligar um nó não perde tarefas nem histórico e o nó não consegue executar uma tarefa fora das permissões.

### Fase 7 — Pesquisa documental e IA comercial

Indexar PDFs localmente com citações de páginas. Depois implementar conectores externos com quotas e classificação de dados. Testar fallback local, falha de quota e comportamento quando Internet cai.

## Decisões em aberto antes de comprar/instalar

- Modelo de roteador/firewall, suporte VLAN, mesh e VPN; modelos de switch/AP e orçamento PoE.
- Interfaces e modelos exatos de câmeras/interfone e fluxo de vídeo local suportado.
- Home Assistant appliance/host, coordenador Zigbee e política de backup/restore.
- Marca/modelo de inversor, BMS, medidores de trilho DIN/Modbus e fabricante de proteção elétrica.
- Hardware e consumo-alvo do servidor de IA; tarefas e latência aceitável.
- Bibliotecas de PDFs e direitos/privacidade; espaço e política de retenção de imagens.
- Política de consentimento para imagens de visitantes, acesso a placas/rostos e ação do portão.

## Referências úteis

- [Home Assistant Assist local](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/)
- [Melhores práticas do Assist e exposição mínima de entidades](https://www.home-assistant.io/voice_control/best_practices/)
- [Integração Ollama no Home Assistant e controle de entidades](https://www.home-assistant.io/integrations/ollama/)
- [Frigate: detecção/reconhecimento facial e limitações de CPU](https://docs.frigate.video/configuration/face_recognition/)
- [Frigate: reconhecimento de placas e exigências da imagem](https://docs.frigate.video/configuration/license_plate_recognition/)
- [CISA: microsegmentação e ambientes IoT/legados](https://www.cisa.gov/sites/default/files/2025-07/ZT-Microsegmentation-Guidance-Part-One_508c.pdf)
