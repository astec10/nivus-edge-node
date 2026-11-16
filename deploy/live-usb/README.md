# Ubuntu + Nivus Live USB: persistência

Esta pasta entrega o primeiro componente do issue #29: uma partição ext4 separada para manter os dados e bloquear a inicialização dos serviços Nivus quando o armazenamento não estiver disponível ou íntegro. O formato alvo confirmado é Casper Live verdadeiro, inicializado diretamente do pendrive; a raiz do sistema será volátil/overlay.

## Estado desta entrega

O conteúdo abaixo **não é ainda uma ISO inicializável** e não substitui o instalador Ubuntu. Ele integra uma raiz Ubuntu preparada a um volume de dados. O construtor da imagem Live, o artefato ISO/USB e os testes físicos UEFI/BIOS continuam pendentes.

Uma edição Live verdadeira usa uma raiz temporária/overlay: mudanças no sistema operacional não sobrevivem automaticamente ao reboot. Esta integração faz com que os dados do Nivus, segredos, releases e arquivos do Docker usem o volume persistente. A montagem e o guard devem ser incluídos na raiz do sistema dentro da imagem, antes de produzir a ISO.

## Layout persistente

A partição ext4 com rótulo NIVUS_DATA é montada em /var/lib/nivus. O instalador Compose existente continua usando os caminhos conhecidos por meio de links simbólicos:

- /var/lib/nivus-compose -> /var/lib/nivus/compose (SQLite e estado Mosquitto).
- /etc/nivus-compose -> /var/lib/nivus/config (segredos, TLS e configuração).
- /opt/nivus-compose -> /var/lib/nivus/releases (código e releases).
- /var/lib/docker -> /var/lib/nivus/docker (imagens, metadados e logs de containers).

Backup, restore e atualizações continuam usando os caminhos Nivus já existentes. A imagem precisa estar isolada e sem estado prévio nesses destinos; o integrador recusa substituir diretórios não vazios. A partição deve conter o marcador .nivus-data-volume com a versão nivus-data-volume-v1.

## Preparação do volume

Use uma partição ext4 vazia, já formatada e rotulada NIVUS_DATA. Formatar uma partição apaga o conteúdo; a criação de partições e a formatação ficam deliberadamente fora destes scripts.

No Ubuntu que preparará a mídia, identifique cuidadosamente a partição e confirme o dispositivo antes de continuar:

    lsblk -f

O helper somente aceita uma partição de bloco ext4, não montada, com o rótulo exigido. Ele se recusa a adotar um sistema de arquivos não vazio que não tenha um marcador Nivus reconhecido. Ele cria o marcador e os diretórios necessários, sem formatar, rotular, apagar ou copiar dados.

    sudo bash deploy/live-usb/prepare-data-volume.sh /dev/sdXN

Substitua /dev/sdXN pelo identificador realmente mostrado por lsblk -f. Não execute esse comando antes de identificar com certeza a partição USB correta.

## Integrar durante a montagem da imagem

O processo de imagem precisa montar o root filesystem Ubuntu num diretório de staging e criar nele o arquivo vazio .nivus-live-image-root. Em seguida, execute como root:

    sudo bash deploy/live-usb/install-image-integration.sh /caminho/da/raizfs

O integrador altera somente a raiz de staging marcada. Ele recusa a raiz do sistema em execução, destinos conflitantes ou qualquer diretório de dados não vazio. Ele instala:

- a unidade systemd que monta NIVUS_DATA em /var/lib/nivus;
- o serviço de verificação de volume;
- dependências que fazem Docker e o coletor aguardarem o volume validado;
- links persistentes para dados, configuração, releases e Docker.

Se a montagem falhar, o volume não for ext4, o rótulo ou marcador não corresponder, ou o ponto não for uma montagem real, o guard falha. Docker e o coletor não iniciam, evitando gravar silenciosamente no overlay temporário. O serviço Nivus não apaga, formata nem tenta reparar filesystem automaticamente.

## Validação

O workflow Live USB storage exercita uma partição ext4 criada sobre loop device em runner hospedado Ubuntu 22.04. Ele confere preparação sem formatação, caminho válido, marcador incorreto, partição desmontada e instalação segura em rootfs de teste. Nenhuma VM local é necessária.

Esse teste comprova o componente de persistência em Linux virtualizado pelo runner, não o boot da ISO. Ainda faltam builder de imagem, smoke de login/Compose após boot, reboot e persistência em mídia real, UEFI/BIOS, Secure Boot, desgaste da mídia, interrupção durante atualização e validação Intel/AMD.

## Recuperação

Antes de atualizar uma imagem física, faça backup Nivus e desligue o sistema corretamente. Mantenha uma mídia de recuperação Ubuntu separada. Se o volume não for reconhecido, não formate nem crie um novo marcador sobre dados antigos: preserve a partição e investigue rótulo, sistema de arquivos e conteúdo offline. O guard falha fechado para proteger SQLite, segredos e logs existentes.
