# Instalação Docker paralela para Ubuntu

Este stack Compose está instalado em paralelo à execução systemd/Nginx preexistente no notebook de teste. A atualização de 17/11/2026 aplicou a release `fff64a68f252f0b1290576e30b39ed78fbc15a7a`; ela confirmou backup SQLite, restart dos containers, health HTTPS 200 e API sem token 401. O instalador e o atualizador não substituem serviços anteriores. O Compose usa HTTPS na porta 8443 por padrão, broker MQTT sem porta publicada no host, diretório de dados persistentes, segredos próprios e serviço de telemetria separado.

## Acesso HTTPS sem sufixo de porta

Em instalação limpa, o instalador usa HTTPS 443 quando a porta está livre. Se algum serviço já escuta nessa porta, identifica o processo e escolhe uma porta livre começando por 8443, sem interromper nem substituir o ocupante. A URL aparece na saída do instalador.

Em um host que já tem Nivus Compose numa porta alternativa e Nginx ativo em 443, publique o painel sem alterar os sites existentes:

```bash
sudo bash /opt/nivus-compose/current/deploy/promote-dashboard-443.sh 192.168.15.110
```

A promoção aceita apenas IPv4 local presente no certificado TLS do Nivus. Confirma que Nginx é o único ocupante de 443 e inclui `/etc/nginx/conf.d/*.conf`, faz cópia da configuração efetiva, cria um arquivo aditivo, valida `nginx -t` e exige HTTPS health 200 e API sem token 401. Em falha, remove somente o arquivo criado e recarrega a configuração anterior. A porta atual do Compose, como 8443, continua disponível como retorno.

Para voltar:

```bash
sudo bash /opt/nivus-compose/current/deploy/promote-dashboard-443.sh --rollback
```

O certificado local é autoassinado; o script confirma que seu SAN contém o IP, mas isso não o transforma numa CA pública. Para evitar avisos no navegador, distribua e confie numa CA local por um canal administrado. API, MQTT e SSH não ganham novas portas. Na migração de `https://IP:8443/` para `https://IP/`, o navegador vê outra origem e pode pedir login uma vez; após isso, o seletor de dashboard atual/legada permanece na mesma sessão.

## Proteção de login e retenção de dados

O Nginx limita `/token` a 10 requisições por minuto por endereço de origem, com rajada limitada. A configuração usa o endereço do peer TCP, não um `X-Forwarded-For` fornecido pelo cliente. Se outro proxy ficar à frente, configure explicitamente a confiança do endereço real antes de publicar o serviço. O backend não bloqueia uma conta globalmente após falhas, evitando que uma pessoa na LAN trave um usuário conhecido.

A API remove telemetria com mais de 30 dias e auditoria de atuadores com mais de 365 dias, em lotes, no início e a cada 24 horas. Ajuste `NIVUS_TELEMETRY_RETENTION_DAYS` e `NIVUS_ACTUATOR_AUDIT_RETENTION_DAYS` no arquivo local de ambiente; ambos precisam ser inteiros entre 1 e 3650. Os prazos são padrões do produto e podem ser ajustados à necessidade de histórico e ao espaço disponível. A limpeza não altera backups já feitos.

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

O instalador cria segredos em /etc/nivus-compose/secrets, um certificado TLS autoassinado e uma conta de serviço para a telemetria. No primeiro uso, escolha um nome de 1–32 caracteres (letras, números, ponto, hífen ou sublinhado) e uma senha temporária de 8–256 caracteres, com pelo menos uma letra e um número, digitada duas vezes sem eco. O primeiro login exige a troca por uma senha definitiva. O broker MQTT não fica exposto à LAN; a API não publica sua porta. Só o Nginx HTTPS publica o painel. A porta web padrão escuta em todas as interfaces, portanto limite o acesso à LAN/VPN confiável com firewall.

O navegador avisará que o certificado é autoassinado. Não exponha a instalação diretamente à Internet.

O instalador também cria a chave mestra de provedores em `/etc/nivus-compose/secrets/provider_encryption_key` com 32 bytes, proprietário root, grupo de runtime e modo 0440. O atualizador a mantém e falha fechado se encontrar credenciais cifradas sem a chave. O backup SQLite padrão não inclui esse arquivo: faça uma cópia de recuperação protegida e separada, fora do repositório, e restaure a mesma chave antes da API ao migrar o banco. Consulte [docs/AI_PROVIDER_CONNECTORS.md](../docs/AI_PROVIDER_CONNECTORS.md).

## Atualizar uma instalação Compose existente

Use um clone limpo da origem oficial e execute o atualizador como administrador:

    git clone --depth 1 https://github.com/astec10/nivus-edge-node.git /tmp/nivus-edge-node-update
    sudo bash /tmp/nivus-edge-node-update/deploy/update.sh

O atualizador aceita somente uma instalação Compose ativa no caminho esperado. Ele valida health e autenticação antes de começar, compila API e dashboard sequencialmente com imagens versionadas, cria backup SQLite consistente, guarda a unidade systemd, troca a release e valida containers, HTTPS, HTTP 401, SQLite, página `/PROGRESS.html` e coleta. A release anterior e o backup são mantidos. Se a validação falhar depois da troca, tenta voltar ao symlink e aos serviços anteriores. O banco não é substituído automaticamente durante rollback; a cópia permanece disponível para recuperação.

O atualizador não altera o Nginx do host, os segredos externos ou o dashboard legado em 8444. Não use `deploy/install.sh` para atualizar uma instalação existente: esse script é somente para a instalação inicial. Este mecanismo é manual, não atualiza outros nós e precisa de Internet e espaço/memória para construir imagens.

A execução do atualizador no CCE U25 foi confirmada em 17/11/2026 na release `fff64a68f252f0b1290576e30b39ed78fbc15a7a`; a saída não comprova reboot completo do Ubuntu nem inspeção visual no navegador. A nova dashboard Compose continua em 8443 e a promoção reversível para a porta 443 está especificada na issue #70. CI hospedada e health checks não substituem a validação visual nem testes em hardware.

O broker e os serviços que o usam ficam numa rede Docker interna. O coletor do host resolve o IP atual do broker por um `ExecStartPre` privilegiado e grava somente esse endereço em `/run`; a senha continua sendo entregue como credencial systemd ao processo sem privilégios. Não altere o agente para conectar a um `localhost`/porta publicada: redes `internal` não publicam a porta MQTT no host. O helper é executado a cada início do coletor para acompanhar a recriação do container.


## Sincronização de hora do Ubuntu

A aba **Configuração → Sincronização de hora do host** mostra se o relógio do Ubuntu está sincronizado. Ela permite ao administrador configurar três hosts NTP e restaurar a configuração anterior. O padrão é `a.ntp.br`, `b.ntp.br` e `c.ntp.br`; são três servidores do projeto NTP.br, não três operadores independentes. O systemd-timesyncd escolhe fontes disponíveis sequencialmente; isso não é votação nem quorum. Consulte [NTP.br](https://www.ntp.br/).

O padrão combina três provedores distintos: `a.ntp.br`, `time.google.com` e `time.cloudflare.com`. São nomes DNS NTP (não URLs HTTPS). O systemd tenta as fontes em sequência como failover; não faz votação nem sincroniza as três simultaneamente.

O administrador pode editar e aplicar a lista se `systemd-timesyncd` estiver instalado. Se o serviço estiver parado, a aplicação inicia/reinicia esse serviço. Se outro cliente (`chrony`, `ntpd` ou semelhante) estiver ativo, o Nivus bloqueia a alteração; não instala pacotes nem substitui outro cliente. A tela informa os estados “parado”, “indisponível” ou “outro cliente ativo”. O drop-in continua pertencendo ao root e recebe ACL POSIX de leitura somente para o usuário `systemd-timesync`; se o sistema de arquivos não oferecer ACL, a aplicação falha antes de trocar o arquivo atual. As preferências de fuso e formato do relógio do painel continuam separadas e não mudam o relógio do Ubuntu.

A API roda sem privilégios e fala com um controlador root por um socket Unix local somente de leitura no container. O controlador aceita apenas consultar estado, aplicar a lista de três nomes DNS ou restaurar o último backup. Ele não executa comandos recebidos da API. Cada alteração salva a configuração Nivus anterior e tenta restaurá-la se o reinício do cliente de hora falhar. Parar o stack para o controlador, mas mantém a fonte NTP aplicada ao Ubuntu; reativá-lo inicia novamente o controlador.

## Modo de manutenção e ajuda da CLI

Após a instalação, `nivus help` mostra os comandos Nivus e sua função resumida; `nivus help maintenance` mostra os detalhes. Para consultar o estado, execute:

    sudo nivus maintenance status

Para pausar somente a leitura/publicação dos sensores do host e a gravação de novas mensagens MQTT no SQLite:

    sudo nivus maintenance enable

Para retomar a operação normal imediatamente, sem reiniciar:

    sudo nivus maintenance disable

API, autenticação, dashboard, health checks, SQLite existente e broker MQTT continuam ativos. A manutenção não desliga serviços alheios nem os processos Nivus; o agente deixa de amostrar/publicar e o worker descarta novas amostras recebidas. O estado ativo fica em `/run/nivus-maintenance`, e o boot retorna automaticamente ao modo normal. O mesmo controle aparece na aba Configuração para administradores. A implementação foi integrada à main pelo PR #28. A release do notebook de teste ainda precisa ser atualizada e validada para disponibilizar os controles nesse host.

## Verificar, backup e parar

    sudo docker compose -f /opt/nivus-compose/current/docker-compose.yml ps
    curl -k https://127.0.0.1:8443/health
    sudo bash /opt/nivus-compose/current/deploy/backup.sh
    sudo bash /opt/nivus-compose/current/deploy/stop-compose.sh

Parar remove os containers e a rede temporária, mas mantém banco, estado do Mosquitto, credenciais e imagens. Para reativar:

    sudo systemctl enable --now nivus-time-sync.service
    sudo systemctl enable --now nivus-compose-telemetry.service
    cd /opt/nivus-compose/current && sudo docker compose up -d

## Restaurar a base SQLite

`backup.sh` cria um diretório exclusivo com sufixo aleatório, uma cópia SQLite consistente validada por `quick_check` e uma cópia do `.env` atual. Segredos JWT/MQTT e certificados ficam no diretório de segredos da instalação e não são sobrescritos pelo restore. O backup é local ao host; não é migração completa para outra máquina. Restrinja o acesso a `/var/backups/nivus-compose` e mantenha cópias externas protegidas se precisar resistir à falha do disco.

Primeiro liste os diretórios de backup e valide a cópia desejada sem parar serviços. Troque o valor de exemplo pelo diretório mostrado pelo comando de backup:

    sudo ls -lt /var/backups/nivus-compose
    BACKUP_DIR=/var/backups/nivus-compose/20261113T000000Z-XXXXXX
    sudo bash /opt/nivus-compose/current/deploy/restore.sh --check "$BACKUP_DIR"

Para restaurar, rode `sudo bash /opt/nivus-compose/current/deploy/restore.sh "$BACKUP_DIR"` e digite `RESTORE` no terminal. O script exige que os quatro containers e o coletor estejam ativos, para antes os escritores da base, cria automaticamente outro backup consistente, preserva os sidecars WAL/SHM, instala a base de forma atômica, reinicia os escritores e verifica SQLite, HTTPS e `401` sem token. Se uma etapa falhar após trocar a base, tenta recuperar a cópia pré-restore e só informa recuperação concluída depois de verificar o banco, os quatro containers, o coletor, health HTTPS e `401`. O diretório pré-restore é mantido para recuperação manual; se a verificação do rollback falhar, o script informa a falha em vez de afirmar que o serviço recuperou.

Para comprovar o caminho de falha e rollback automático, use somente numa VM descartável depois de criar um backup e deixar a telemetria avançar:

    sudo bash /opt/nivus-compose/current/deploy/test-restore-rollback.sh --i-understand-this-is-a-disposable-vm "$BACKUP_DIR"

O teste recusa execução fora de uma VM, cria um backup de segurança e exige confirmações digitadas. Ele provoca uma falha de health após substituir temporariamente o SQLite; o health falso dura até 45 segundos. Resultado esperado: a restauração informa a falha simulada, recupera automaticamente o banco anterior e termina com health 200, telemetria sem token 401, SQLite íntegro e serviços ativos. O comparador verifica o esquema SQLite e os dados: todas as linhas anteriores devem continuar, e telemetria nova pode permanecer. O backup de segurança e o log são mantidos sob `/var/backups/nivus-compose`. Escolha um backup mais antigo cuja contagem de telemetria seja menor que a atual; o teste cancela antes da troca se não houver essa diferença.

Teste restauração apenas numa VM descartável ou clone, depois de snapshot. A rotina ainda requer validação ponta a ponta numa instalação limpa antes de ser considerada pronta para produção.

## Interface modular no host existente

Este pacote descreve a candidata Compose e não inclui detalhes de implantação do host de teste. A UI compilada passou em staging, mas ativá-la numa instalação Nginx existente depende do caminho de release, propriedade dos arquivos e backup/rollback específicos daquele host. Não copie os arquivos diretamente para o root em produção.

## Limites da candidata

- Não importa SQLite nem altera os serviços ativos do host. A base começa vazia e pede a criação de um administrador.
- O agente de telemetria fica no host para ler CPU/memória/disco do host sem montar a raiz do sistema em container.
- O endereço interno do broker é descoberto dinamicamente antes de cada inicialização do coletor; a porta MQTT não é publicada no host.
- Temperatura pode não estar disponível. Potência continua sendo estimativa, não medição elétrica.
- O broker/ACL cobre agente, worker, health check e o tópico de relé existente. Sensores e atuadores externos precisam de usuários/tópicos próprios antes de conexão.
- O painel atual não é ainda o painel multi-nó/domótico planejado.
- O atualizador manual reversível está em `deploy/update.sh`; atualizações automáticas de frota ainda não foram implementadas.
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

