# Preparação do alvo USB portátil

Esta etapa começa a preparar a instalação persistente do Ubuntu Server + Nivus em um pendrive. Os scripts não gravam, particionam, formatam, montam ou alteram dispositivos de bloco.

## Etapas disponíveis

### 1. Selecionar o pendrive

Em uma máquina Ubuntu de preparação, conecte o pendrive de destino e execute:

    sudo python3 deploy/portable_usb/select_target.py

O programa lista discos USB elegíveis mostrando caminho, modelo, número de série e capacidade. Exige serial único, disco gravável e partições desmontadas; também exclui o dispositivo que contém a raiz atual quando consegue mapeá-lo. Não escolhe automaticamente o maior disco.

Registre a escolha digitando o número de série exato:

    sudo python3 deploy/portable_usb/select_target.py \
      --serial 'SERIAL-EXATO-DO-USB' \
      --output /var/tmp/nivus-usb-selection.json

### 2. Gerar seed revisável do instalador

Com o manifesto ainda na máquina Ubuntu de preparação:

    sudo python3 deploy/portable_usb/generate_autoinstall.py \
      --selection /var/tmp/nivus-usb-selection.json \
      --output /var/tmp/nivus-usb-seed\n\nOpcionalmente, instale `cloud-image-utils` e acrescente `--build-seed-iso` ao comando para criar `nivus-autoinstall-seed.iso` e um checksum. Essa ISO é apenas a mídia de configuração NoCloud; não inicia o Ubuntu nem substitui a mídia instaladora. Ela contém configuração privada e o hash da senha, portanto não a publique.

O gerador relê o inventário atual e exige correspondência de caminho, modelo, serial e capacidade. Pede usuário, hostname e senha do Ubuntu; a senha não aparece no terminal e somente um hash entra no arquivo privado. A pasta de saída deve ser nova e fica protegida em modo 0700; os arquivos usam modo 0600.

A configuração gerada mantém a seleção de armazenamento interativa e verifica novamente a identidade antes de abrir a tela do Subiquity. Consulte [AUTOINSTALL.md](AUTOINSTALL.md) para preparar o seed e revisar a instalação.

## Layout proposto

O seed planeja BIOS/GRUB, EFI FAT32, raiz Ubuntu ext4 e uma partição ext4 rotulada NIVUS_DATA montada em /var/lib/nivus. A mídia de instalação e o pendrive de destino precisam ser diferentes.

O disco precisa ter pelo menos 40 GiB; o plano usa 1 MiB para BIOS/GRUB, 1 GiB para EFI, 24 GiB para Ubuntu e o restante para NIVUS_DATA. O instalador formata o USB escolhido e apaga os dados existentes nele.

## Limites atuais

Esta branch cria opcionalmente uma ISO NoCloud de configuração, mas ainda não cria a mídia inicializável do Ubuntu, não instala os serviços Nivus e não prova reinício/persistência em equipamento físico. A CI usa inventários sintéticos e não grava em discos; valida um seed pelo schema oficial Subiquity da linha Ubuntu 24.04 e testa a geração da ISO com uma saída sintética. Ainda faltam executar o instalador Subiquity, integrar ou documentar a mídia inicializável completa, instalar Nivus e testar persistência/boot UEFI/BIOS em hardware físico.

A ISO Ubuntu Server inicia um instalador e a tela de armazenamento pode formatar o disco escolhido. O Subiquity permite identificar o disco pelo serial; a configuração não usa a seleção por maior capacidade:

- [Ubuntu Server: instalação](https://ubuntu.com/server/docs/installation/)
- [Subiquity: referência de autoinstall](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
- [Curtin: armazenamento](https://curtin.readthedocs.io/en/latest/topics/storage.html)
