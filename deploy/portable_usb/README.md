# Ubuntu + Nivus persistentes no USB

Este pacote prepara um Ubuntu Server instalado integralmente no pendrive. A raiz do Ubuntu e os dados Nivus persistem após reinicializações. Não é uma edição Casper Live nem uma ISO Ubuntu personalizada pronta.

## Etapas disponíveis

### 1. Selecionar o pendrive de destino

Em um Ubuntu de preparação, conecte o pendrive e execute:

    sudo python3 deploy/portable_usb/select_target.py

O helper lista modelo, caminho, serial e capacidade. Exige serial único, USB gravável e partições desmontadas; também exclui o disco que contém a raiz quando consegue identificá-lo. Não seleciona discos automaticamente.

Registre o serial exato:

    sudo python3 deploy/portable_usb/select_target.py \
      --serial 'SERIAL-EXATO-DO-USB' \
      --output /var/tmp/nivus-usb-selection.json

### 2. Gerar a configuração privada do instalador

    sudo python3 deploy/portable_usb/generate_autoinstall.py \
      --selection /var/tmp/nivus-usb-selection.json \
      --output /var/tmp/nivus-usb-seed \
      --build-seed-iso

A geração pede usuário, hostname e senha do Ubuntu, sem exibir a senha; somente o hash entra no seed. A pasta e os arquivos são privados. Não publique nem envie esses arquivos para chats. Para criar a ISO NoCloud, instale \`cloud-image-utils\` (\`sudo apt install cloud-image-utils\`).

A ISO \`nivus-autoinstall-seed.iso\` é mídia de configuração; não contém o instalador Ubuntu e não inicia o computador. Use três mídias ou dispositivos identificáveis: uma mídia Ubuntu Server inicializável, o USB de destino e a ISO/USB do seed NoCloud. A mídia instaladora e o alvo precisam ser diferentes.

### 3. Instalar Ubuntu no USB

Inicie a mídia oficial Ubuntu Server 24.04 LTS ou mais recente sem adicionar o parâmetro de kernel \`autoinstall\`. Disponibilize \`user-data\` e \`meta-data\` ao Subiquity pela ISO seed e mantenha a tela de armazenamento interativa. Confira o caminho, modelo, serial e capacidade do USB comparando com \`TARGET-IDENTITY.txt\`. Cancele se houver qualquer divergência. A instalação formata o USB de destino e apaga o conteúdo existente nele.

O layout usa BIOS/GRUB, EFI FAT32, uma raiz Ubuntu ext4 e a partição ext4 \`NIVUS_DATA\` no restante do USB, montada em \`/var/lib/nivus\`. O dispositivo precisa ter pelo menos 40 GiB. O instalador revalida a identidade do alvo antes de apresentar a confirmação do armazenamento.

### 4. Instalar Nivus após o primeiro boot

Após iniciar no Ubuntu instalado no próprio USB, obtenha uma cópia do repositório e execute:

    sudo apt update
    sudo apt install -y git python3
    git clone https://github.com/astec10/nivus-edge-node.git
    cd nivus-edge-node
    sudo bash deploy/portable_usb/install_nivus.sh

O comando recusa continuar se raiz e dados não forem partições ext4 do mesmo USB, se \`NIVUS_DATA\` não estiver montado com escrita e registrado uma única vez no \`/etc/fstab\`, se o rótulo estiver duplicado, se Docker já estiver ativo ou se houver uma instalação Nivus existente. Ele não formata discos nem move diretórios com dados. Em seguida prepara a persistência e chama o instalador Compose existente, que pede o primeiro administrador no terminal.

A instalação inicial precisa de internet para APT e construção/obtenção das dependências. Depois de concluída, o Nivus pode operar na LAN sem depender de serviços na nuvem; os módulos de IA local, VPN e coordenação de vários nós continuam separados no roadmap.

## Limites de validação

A CI valida os seletores com inventários sintéticos e o seed contra o schema oficial Subiquity fixado no workflow. A integração ext4 é exercitada em loop device no runner hospedado. A CI não formata um pendrive físico nem executa o instalador interativamente.

Ainda não há ISO bootável customizada. O processo usa a mídia oficial do Ubuntu Server e um seed em mídia separada. Boot real UEFI/BIOS, primeiro login, Compose, reboot com verificação do SQLite/segredos/containers, recuperação e a matriz física Intel/AMD ainda precisam de validação.

Veja [AUTOINSTALL.md](AUTOINSTALL.md) para parâmetros do seed e [../live-usb/README.md](../live-usb/README.md) para o guard e detalhes do volume persistente.
