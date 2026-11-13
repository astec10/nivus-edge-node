# Instalação Docker paralela para Ubuntu

Este stack é uma instalação candidata separada da execução systemd/Nginx já existente. O instalador não para nem substitui serviços anteriores. Ele usa HTTPS na porta 8443, broker MQTT sem porta publicada no host, outro diretório de dados, segredos próprios e um serviço de telemetria com nome próprio.

## Pré-requisitos e alvo

- Ubuntu Server 22.04 ou posterior, systemd 247+ e arquitetura x86_64/amd64.
- Acesso à Internet no primeiro build para APT, imagens e pacotes Python/npm.
- Containers limitados a 512 MiB agregados por padrão, mais o processo leve de telemetria do host e memória temporária do build do frontend. Confira a RAM disponível antes de construir no notebook antigo.
- Quando Docker/Compose faltarem, o instalador tenta instalar docker.io e docker-compose-v2 pelos repositórios Ubuntu.

## Validar configuração sem iniciar serviços

A verificação `docker compose config --quiet` valida YAML, variáveis e caminhos de secrets. No notebook de teste, `ComposeConfig`, o build das imagens e `deploy/verify-compose-staging.sh` passaram numa cópia sanitizada em staging privado. O smoke test iniciou somente um projeto Compose temporário, validou HTTPS, o asset do painel, HTTP 401 sem token e ingestão MQTT no SQLite de teste; depois removeu os containers/redes temporários. A API/worker/telemetria systemd e o banco de produção permaneceram ativos.

## Instalar

Na raiz clonada do projeto:

    sudo bash deploy/install.sh

O instalador cria segredos em /etc/nivus-compose/secrets, um certificado TLS autoassinado e uma conta de serviço para a telemetria. No primeiro uso, escolha um nome de 1–32 caracteres (letras, números, ponto, hífen ou sublinhado) e uma senha de 12–256 caracteres, digitada duas vezes sem eco. O broker MQTT não fica exposto à LAN; a API não publica sua porta. Só o Nginx HTTPS publica o painel. A porta web padrão escuta em todas as interfaces, portanto limite o acesso à LAN/VPN confiável com firewall.

O navegador avisará que o certificado é autoassinado. Não exponha a instalação diretamente à Internet.

O broker e os serviços que o usam ficam numa rede Docker interna. O coletor do host resolve o IP atual do broker por um `ExecStartPre` privilegiado e grava somente esse endereço em `/run`; a senha continua sendo entregue como credencial systemd ao processo sem privilégios. Não altere o agente para conectar a um `localhost`/porta publicada: redes `internal` não publicam a porta MQTT no host. O helper é executado a cada início do coletor para acompanhar a recriação do container.

## Verificar, backup e parar

    sudo docker compose -f /opt/nivus-compose/current/docker-compose.yml ps
    curl -k https://127.0.0.1:8443/health
    sudo bash /opt/nivus-compose/current/deploy/backup.sh
    sudo bash /opt/nivus-compose/current/deploy/stop-compose.sh

Parar remove os containers e a rede temporária, mas mantém banco, estado do Mosquitto, credenciais e imagens. Para reativar:

    sudo systemctl enable --now nivus-compose-telemetry.service
    cd /opt/nivus-compose/current && sudo docker compose up -d

## Interface modular no host existente

Este pacote descreve a candidata Compose e não inclui detalhes de implantação do host de teste. A UI compilada passou em staging, mas ativá-la numa instalação Nginx existente depende do caminho de release, propriedade dos arquivos e backup/rollback específicos daquele host. Não copie os arquivos diretamente para o root em produção.

## Limites da candidata

- Não importa SQLite nem altera os serviços ativos do host. A base começa vazia e pede a criação de um administrador.
- O agente de telemetria fica no host para ler CPU/memória/disco do host sem montar a raiz do sistema em container.
- O endereço interno do broker é descoberto dinamicamente antes de cada inicialização do coletor; a porta MQTT não é publicada no host.
- Temperatura pode não estar disponível. Potência continua sendo estimativa, não medição elétrica.
- O broker/ACL cobre agente, worker, health check e o tópico de relé existente. Sensores e atuadores externos precisam de usuários/tópicos próprios antes de conexão.
- O painel atual não é ainda o painel multi-nó/domótico planejado.
- Atualização automática com rollback de versão ainda não foi implementada; faça backup e preserve a release atual antes de atualizar.
- Controlar Docker equivale a poder administrativo alto no host; não adicione usuários ao grupo docker sem compreender esse privilégio.

## Medição ao vivo no CCE U25

Em 13/11/2026, no Ubuntu 26.04.1 LTS x86_64 com 2 vCPUs e 3,2 GiB de RAM, três leituras do Docker mostraram aproximadamente 71,7 MiB agregados para os quatro containers da candidata (API ~42,5 MiB, worker ~18,0 MiB, web ~4,6 MiB e MQTT ~6,1 MiB). Os limites de memória do Compose totalizam 512 MiB; isso é um teto configurado, não o consumo observado. CPU instantânea variou de 0,5% a 12,4%, portanto não se apresenta como média de carga nem teste de estresse. O host também executa os serviços systemd/Nginx anteriores; build e pico de memória não foram medidos nesta leitura. Uma VM limpa ainda deve registrar seus próprios recursos e consumo.

## Validação e limitações atuais

- Build e smoke test foram repetidos com imagens base por digest e dependências Python fixadas. O último teste mediu 65,3 MiB agregados em repouso: API 40,6 MiB, worker 17,4 MiB, Mosquitto 2,9 MiB e Nginx 4,3 MiB. O uso varia com carga e não inclui memória temporária do build.
- O primeiro smoke test revelou que uma rede Docker `internal` impede a publicação da porta HTTPS. A candidata foi corrigida com a rede bridge `edge_ingress`; somente o Nginx participa dela.
- A primeira instalação paralela revelou que o broker MQTT em rede `internal` não aceita a porta publicada para o host. O coletor systemd reiniciava ao tentar `127.0.0.1:1884`. O reparo reversível com descoberta dinâmica do IP interno foi aplicado: o serviço permaneceu ativo sem reinícios e o SQLite aumentou de 9 para 12 amostras em 15 segundos.
- O instalador gera senhas MQTT com a mesma imagem Mosquitto fixada por digest no Compose e exclui qualquer `.env` da pasta de staging ao criar a release, gerando uma configuração própria. O smoke test reutilizável prepara propriedade recursiva dos volumes de staging e usa um identificador por execução.
- O smoke test passou após a correção, mas não valida criação interativa do administrador, login com credencial real, persistência após reboot, backup/restauração nem migração de dados existentes.
- O instalador não foi executado numa instalação limpa nem ativado como stack permanente no notebook de teste. Não declare suporte a qualquer computador x86_64 até testar mais hardware e Ubuntu Server minimal.
- A versão React modular passou em smoke test e foi ativada no Nginx do host de teste usando um script privado de backup/rollback. A troca da interface de outra instalação precisa de procedimento próprio para os caminhos daquele host.

Esta árvore continua sendo uma candidata para revisão, não um release de produção.
