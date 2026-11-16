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

Consequência: a porta HTTPS publicada pode ser acessada no endereço configurado, enquanto API e broker permanecem isolados. Configuração, build e smoke test foram repetidos depois da alteração e passaram. A primeira instalação real mostrou que porta MQTT publicada em rede interna não fica acessível como loopback; o coletor reiniciava e nenhuma amostra chegava à base candidata. O reparo reversível instalou um helper dinâmico que foi validado: o coletor não reiniciou e publicou amostras na base candidata.

## Licença do projeto — 2026-11-13

Decisão do operador: licenciar o Nivus Edge Node sob AGPL-3.0-only para que pessoas possam usar, estudar, modificar e distribuir versões derivadas conforme os termos da AGPL. Interfaces acessíveis pela rede devem oferecer o código-fonte correspondente sem custo e exibir aviso legal apropriado. A licença completa está em LICENSE; dependências e assets de terceiros mantêm as respectivas licenças e avisos.


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

## Ubuntu + Nivus USB portátil — 2026-11-16

Contexto: o operador quer usar uma instalação Ubuntu + Nivus em um pendrive como nó portátil e temporário em outro computador x86_64, sem instalar no disco interno desse computador. O sistema operacional e os dados devem persistir entre reinicializações.

Decisão: instalar Ubuntu Server minimal diretamente no pendrive de destino. O sistema e o estado Nivus persistem no USB após reboot. Manter uma partição ext4 separada, com rótulo `NIVUS_DATA`, montada em `/var/lib/nivus`, para banco SQLite, configuração, segredos e estado do Docker. A integração de persistência e o guard do PR #31 continuam válidos. Este formato é Ubuntu instalado no USB; não usa raiz volátil Casper Live.

Consequência: o instalador deve exigir seleção e confirmação explícita do pendrive de destino, nunca presumir que o maior disco seja o USB nem formatar o disco interno. O particionamento, a versão LTS e a construção reproduzível do instalador ainda serão definidos. Validar boot e persistência após reboot em runners hospedados; compatibilidade física UEFI/BIOS e Intel/AMD continua separada.
