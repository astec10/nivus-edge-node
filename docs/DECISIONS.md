# Decisões

## Modularização

Separar rotas, schemas, autorização, banco, MQTT e componentes de UI. Preservar contratos durante extração. API modular e frontend React modular ativos no host de teste, com backup/rollback e login confirmado.

## Autenticação inicial

Usar senha e JWT. USB e biometria continuam opcionais. Não conceder admin com base apenas em IP de LAN. Segredo JWT fica fora do Git.

## Ubuntu instalado em USB — 2026-11-16

Decisão do operador: instalar Ubuntu Server completo no pendrive, não usar Casper Live. A raiz do sistema e os dados do Nivus devem persistir após reboot. O layout usa NIVUS_DATA ext4 separado em /var/lib/nivus no mesmo dispositivo USB da raiz. A mídia do instalador é separada, e Subiquity mantém a confirmação manual do alvo. O instalador pós-boot valida que raiz e dados estão no mesmo USB e recusa formatar ou mover dados. O fluxo de instalação inicial requer Internet; operação local após instalação não deve depender de serviços de nuvem.

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

Consequência: a porta HTTPS publicada pode ser acessada no endereço configurado, enquanto API e broker permanecem isolados. Configuração, build e smoke test foram repetidos depois da alteração e passaram. A primeira instalação real mostrou que porta MQTT publicada em rede interna não fica acessível como loopback; o coletor reiniciava e nenhuma amostra chegava à base candidata. O reparo reversível instalou um helper dinâmico que foi validado: o coletor não reiniciou e publicou amostras na base candidata.

## Licença do projeto — 2026-11-13

Decisão do operador: licenciar o Nivus Edge Node sob AGPL-3.0-only para que pessoas possam usar, estudar, modificar e distribuir versões derivadas conforme os termos da AGPL. Interfaces acessíveis pela rede devem oferecer o código-fonte correspondente sem custo e exibir aviso legal apropriado. A licença completa está em LICENSE; dependências e assets de terceiros mantêm as respectivas licenças e avisos.


## Perfil de desempenho com alimentação AC/UPS — 2026-11-16

Decisão do operador: usar presença confirmada de alimentação AC no nó ou na entrada do UPS como sinal para selecionar automaticamente um governor de desempenho suportado. A ausência, falha ou ambiguidade mantém o governor conservador. O perfil não habilita overclock: overclock permanece manual. O sinal de alimentação não altera nem libera atuadores; eles continuam sujeitos às suas regras determinísticas e intertravamentos. Dados de bateria do UPS/nobreak pertencem ao futuro Nó Master e à automação, não ao sensor de bateria interna do nó.

Desdobramento implementado nesta branch: a fonte Linux `Mains/online` só é aceita para AC direta; ela não indica a entrada elétrica do UPS quando o computador está conectado à saída do UPS. Para esse arranjo, o controlador pode ler NUT local e falha para o perfil conservador quando a resposta está indisponível, stale ou ambígua. O serviço systemd opcional muda somente `scaling_governor`, usa governors suportados e deixa o timer desabilitado por padrão. Não altera limites térmicos, frequência/voltagem manual, atuadores ou overclock. A validação física ainda está pendente.

## Semântica da telemetria térmica — 2026-11-14

A temperatura principal representa CPU/APU identificada por driver e label, e a origem é armazenada junto da amostra. Temperaturas de placa-mãe e GPU são campos opcionais separados. Sensores indisponíveis ou ambíguos permanecem nulos; zonas ACPI genéricas não substituem a leitura da CPU. Usar a interface Linux hwmon/psutil no runtime Ubuntu. lm-sensors é ferramenta opcional de diagnóstico. Open Hardware Monitor original é referência Windows legada; não é dependência do Nivus. Validar cada driver e família de hardware antes de declarar suporte.

## Gráficos e detalhes de sensores — 2026-11-15

Separar gráficos de temperatura, uso e potência para manter unidades e escalas legíveis. Permitir janelas de 5, 15, 30 e 60 minutos, além do conjunto carregado limitado a 1000 amostras. Os tooltips de métricas aparecem após 3 segundos de hover ou foco; mínimo e máximo referem-se somente à janela visível. GPU, hotspot e placa-mãe sem fonte identificada permanecem N/D. O hotspot é coletado apenas quando o driver o rotula explicitamente como `hotspot` ou `junction`.

## Acesso HTTPS sem sufixo de porta — 2026-11-15

Instalações novas devem preferir a porta padrão HTTPS 443 e mostrar `https://IP/`. Se 443 já estiver em uso, o instalador mantém o serviço atual e escolhe uma porta livre; uma promoção Nginx separada e reversível é necessária para integrar a candidata a um host existente. A versão anterior permanece preservada e pode ser aberta pelo controle do cabeçalho quando o build configura `NIVUS_LEGACY_DASHBOARD_PORT`. Para acesso na LAN, usar IP reservado no roteador; DDNS pode ser avaliado para uso remoto junto com VPN. Não encaminhar o painel diretamente à Internet.

## Atualizações coordenadas de nós — planejado em 2026-11-15

Quando houver cadastro multi-nó, o coordenador poderá iniciar atualizações, correções e funções novas em todos os nós elegíveis. O desenho deverá usar artefatos e manifestos assinados, rollout gradual, compatibilidade declarada, verificação de saúde e rollback individual. Nós offline ou incompatíveis aguardam; a distribuição não executará scripts arbitrários por SSH nem sobreporá mudanças locais sem política explícita. Esta capacidade ainda não está implementada.

## Conhecimento comum para agentes e biblioteca compartilhada — 2026-11-15

O GitHub é a fonte pública versionada de decisões, mapas de módulos, resumos técnicos curados e registros de procedência, para que agentes de IA diferentes usem o mesmo contexto. Fontes de vídeo recebem estado de verificação, tema, timestamp/link e termos lexicais normalizados; não se publicam transcrições completas sem licença. O índice lexical é derivado e independente de modelo, não uma sequência de IDs de tokenizer.

A pasta `knowledge/` contém catálogo e notas próprias para contribuição pública. A biblioteca consultável dentro do produto e sincronizada entre nós é parte planejada da Fase 4; ainda não está implementada. Dados domésticos privados, credenciais e bases do notebook permanecem fora do GitHub.

## Separação do executor e telemetria do Nó Master — 2026-11-15

Telemetria agregada entre nós não é pré-requisito para o executor de desenvolvimento; será mais útil quando o Nó Master estiver operacional. O notebook CCE pode ser avaliado como controlador leve que despacha workflows para runners GitHub-hosted; não será runner self-hosted de código público nem sandbox paralela sem comprovar recursos e isolamento. Issues e Actions são o estado durável quando o notebook fica offline.

## Chamadas Gemini em segundo plano — 2026-11-15

O worker usa background polling limitado porque chamadas síncronas anteriores excederam o timeout de conexão. A API exige `store=true` nesse modo; o cliente deve recuperar a resposta e apagar a interação assim que puder, registrar `interaction_deleted` e tratar falha de exclusão como possível retenção temporária no provedor. Tarefas continuam limitadas a dados públicos/sintéticos e a uma autorização explícita por tentativa. O intake usa somente o evento `ai:ready` para iniciar o worker e não dispara também `workflow_dispatch`.

## Modo de manutenção reversível — 2026-11-15

Decisão do operador: oferecer um controle explícito na configuração e comandos `nivus maintenance enable|disable|status`, com `nivus help` para explicar os comandos. A manutenção pausa somente a coleta local do host e a gravação de novas mensagens de telemetria MQTT. API, login, dashboard, health, banco existente e broker continuam disponíveis; serviços não relacionados não são parados. `disable` retoma a operação sem reboot. O marcador temporário fica em `/run`, portanto um reboot também volta ao modo normal. Transições são registradas em SQLite, sem persistir o estado ativo entre boots. A implementação aguarda CI e publicação; ainda não está no notebook.


## Sincronização NTP do host — 2026-11-16

A preferência de fuso/formato da dashboard permanece no navegador e separada do relógio do Ubuntu. A integração de host consulta e altera somente o \`systemd-timesyncd\` já ativo. Se outro cliente de hora estiver ativo, ou timesyncd estiver indisponível, a configuração é recusada sem instalar, habilitar ou substituir serviços de hora.

A API sem privilégios usa um socket Unix para um controlador root com operações fechadas: estado, aplicar exatamente três hosts DNS e rollback. O socket é exposto ao container API em montagem somente leitura; o controlador valida UID/GID do peer e não aceita shell, caminhos nem comandos fornecidos pela API. A configuração pertence ao Nivus em \`/etc/systemd/timesyncd.conf.d/90-nivus.conf\`, com backup e recuperação em falha. A interface não mostra fonte no relógio; a lista de hosts aparece somente na aba Configuração.

Padrão: \`a.ntp.br\`, \`b.ntp.br\`, \`c.ntp.br\`. São três servidores do projeto NTP.br, não três operadores independentes. O systemd-timesyncd utiliza fontes disponíveis sequencialmente, não por quorum. Nenhuma consulta externa é feita pelo navegador.

## Automação do relé por bateria móvel — 2026-11-16

- Fonte inicial: sensor de bateria do Home Assistant Companion App; bateria móvel permanece distinta da bateria interna do nó e do banco de 48 V do inversor.
- Cada fonte é cadastrada explicitamente por administrador e recebe token aleatório, mostrado uma vez e armazenado no SQLite somente como SHA-256. Relatórios usam HTTPS com validação TLS, percentual inteiro 0–100 e timestamp com fuso.
- Só uma leitura nova, autenticada e com até 60 minutos pode acionar a regra. Em 20% ou menos, enviar somente OFF para o tópico fixo `nivus/edge/relay1`, no máximo uma vez por ciclo baixo. Acima de 20%, apenas rearmar; nunca enviar ON automaticamente, inclusive no boot ou na recuperação.
- Relatório ausente, expirado, repetido, fora de ordem, token revogado ou broker indisponível não autoriza ON. Falha do broker limita novas tentativas de OFF a uma por cinco minutos.
- Se houver mais de um celular ativo, qualquer leitura recente em 20% ou menos pode acionar OFF; a interface deve deixar essa regra explícita.
- Registrar auditoria e distinguir aceitação MQTT de confirmação do relé físico. Manter comando manual de administrador. Validar primeiro com SQLite temporário e publisher MQTT simulado; não enviar comando a relé físico sem etapa de validação autorizada.


## Registro de identidade de nós — 2026-11-16

A primeira entrega multi-nó começa por cadastro autenticado e heartbeat somente de metadados. O administrador cria um código aleatório de uso único, válido por 10 minutos; o nó não escolhe sua própria identidade. O servidor gera o ID estável e um token aleatório; banco guarda somente SHA-256 do código e do token. A credencial do nó é mostrada uma vez. Perda do token requer revogação e novo pareamento.

O agente obtém uma sessão que rotaciona e invalida a sessão anterior. Heartbeats usam sequência crescente; o servidor registra o horário recebido, sem aceitar ID, IP, horário ou capacidade como permissão escolhidos pelo cliente. Estado online é derivado de heartbeat recebido nos últimos 90 segundos; agentes devem enviar a cada 30 segundos. No cadastro, o nó permanece offline até o primeiro heartbeat.

Capacidades são declarações informativas numa allowlist, não grants de autorização. A primeira versão não habilita shell remoto, execução de tarefas, comandos MQTT, transferência P2P, upload de telemetria ou atualização de software. Cada função exige contrato, autorização e revisão separados.

O registro seguro da API foi integrado pelo PR #66 e está na release aplicada ao notebook. O agente mínimo de pareamento/heartbeat foi implementado no PR #69; a CI hospedada passou, mas o smoke de dois dispositivos e TLS real ainda está pendente. O agente salva o token local em arquivo `0600` dentro de diretório `0700`, sem criptografia; proteger disco e backups. Ele não envia telemetria, executa comandos ou controla atuadores. A amostragem de telemetria agregada, o painel multi-nó e as atualizações de frota continuam planejados.


## Cadastro de provedores de IA do runtime — 2026-11-17

Na issue #68, a interface será uma seção própria em **Configuração → Provedores de IA**: lista de conexões, catálogo predefinido e cadastro manual. O formulário abre sob demanda; edição de metadados não pede a chave de novo, e substituição da credencial tem ação separada. Perfil criado começa desabilitado e só pode ser ativado após teste explícito. Salvar não faz chamada externa.

Chave de API não pode ser guardada apenas como hash, pois o processo precisa recuperá-la para autenticar chamadas. O backend usa AES-GCM com nonce aleatório de 96 bits e identificador do perfil como dado autenticado; chave mestra binária de 32 bytes fica fora do repositório e do SQLite. A resposta da API contém apenas `credential_configured`, nunca cifra ou chave. Backup SQLite sozinho não recupera o segredo; a chave mestra precisa de cópia protegida separada.

Nuvem exige HTTPS público e aceita somente dados públicos/sintéticos. Endpoint local é separado, limitado a endereços privados e portas conhecidas, e não recebe chave em HTTP. O teste é GET da lista de modelos, sem prompt, redirecionamento, com timeout. Orçamento e máximo de pedidos são campos de política e permanecem informativos enquanto não existir executor de inferência; habilitar um perfil não significa que o runtime já faz chamadas. Isso continua separado de `GEMINI_API_KEY` do GitHub Actions.

## Canal SSH de manutenção — registro de evidência — 2026-11-23

O operador relata que uma consulta de diagnóstico `status` respondeu por um canal SSH restrito. Uma tentativa independente nesta sessão não autenticou; a disponibilidade e a configuração atuais não foram verificadas independentemente. Este registro não contém dados de conexão ou credenciais e não concede autorização para conectar ou operar. Toda tarefa futura exige autorização específica, validação da identidade/chave de host e confirmação das operações permitidas. Não presumir shell, sudo, acesso Docker, atualização ou deploy. A issue #130 continua aberta e cobre o desenho mais amplo, incluindo ciclo de vida das credenciais, auditoria e ações de manutenção.


## Credencial SSH temporária por sessão — direção preferida — 2026-11-23

O operador prefere substituir, no desenho futuro, a chave cliente persistente por um par de chaves efêmero e um certificado de usuário OpenSSH de curta validade para cada sessão de manutenção autenticada e aprovada. O certificado deve ser vinculado ao usuário/sessão, a um nó e a operações em allowlist; os nós devem confiar na chave pública de uma CA protegida fora do repositório e dos próprios nós. Um serviço de autorização deve controlar emissão, uso único quando exigido, auditoria, revogação e encerramento das conexões abertas no logout. A expiração do certificado, por si só, não encerra uma conexão já autenticada.

Esta é uma direção de arquitetura, não implementação. O canal diagnóstico atualmente relatado continua usando credencial cliente persistente, não foi convertido e não foi auditado independentemente. Não alterar o SSH do notebook sem tarefa específica, backup e validação. A issue #130 permanece aberta.

Referências: [OpenBSD sshd_config(5)](https://man.openbsd.org/sshd_config) e [OpenBSD ssh-keygen(1)](https://man.openbsd.org/ssh-keygen).


## Política configurável de sessões SSH — requisito futuro — 2026-11-23

O operador solicita que a Gestão de usuários permita configurar a duração máxima da credencial/sessão (padrão inicial de 2 horas), a redução do prazo por nova sessão (15 minutos) e o intervalo de reset (24 horas). A janela fixa começando na primeira emissão e o bloqueio de nova emissão quando o prazo calculado chega a zero são propostas para implementação segura; confirmar antes de codificar. O cálculo e as faixas permitidas devem ser aplicados e auditados no servidor, com controle contra sessões paralelas.

A interface deve permitir logout, revogação da credencial e encerramento de sessões remotas abertas. Revogação impede reautenticação e encerra também conexões existentes; o logout web precisa chamar esse mecanismo explicitamente. Logs de acesso detalhados ficam locais, persistentes e disponíveis para leitura somente a administradores autorizados, com retenção/rotação definidas. Registrar ator, nó, horário, sessão/certificado, ação, resultado, motivo e validade; não registrar chaves privadas, passphrases, tokens nem dados secretos. O servidor da API valida e autoriza, e mudanças de política também geram auditoria.

Requisitos planejados, ainda sem implementação ou teste no notebook. Consulte a issue #130 para critérios e decisões pendentes.
