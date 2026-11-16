# Configuração revisável do Ubuntu instalado em USB

Esta etapa gera um seed NoCloud para o instalador Subiquity. Com `--build-seed-iso`, também cria uma ISO NoCloud de configuração usando `cloud-localds`; essa ISO não inicia o instalador Ubuntu. A etapa não cria mídia Ubuntu inicializável, não instala o Nivus e não grava em discos. O Subiquity fará a gravação após a revisão da tela de armazenamento.

O fluxo requer Ubuntu Server 24.04 LTS ou mais recente. A configuração mantém a seleção de armazenamento interativa; Subiquity mostra a tela para revisão antes de executar o plano. O instalador também roda uma validação antecipada do dispositivo selecionado.

## Pré-requisitos

- Um computador Ubuntu de preparação com python3, lsblk, findmnt e openssl. Para gerar a ISO de configuração, instale também `cloud-image-utils` (`sudo apt install cloud-image-utils`).
- Uma mídia instaladora Ubuntu Server separada do pendrive de destino.
- Um pendrive de destino identificado com modelo e número de série únicos, USB, gravável e sem partições montadas.
- Capacidade mínima de 40 GiB. O plano reserva 1 MiB para BIOS/GRUB, 1 GiB para EFI e 24 GiB para o Ubuntu; o espaço restante forma NIVUS_DATA.

Não selecione a própria mídia do instalador como destino. O helper exclui discos com partições montadas, inclusive /cdrom, e também tenta excluir o disco que contém /.

## Gerar o seed

Na raiz do repositório, primeiro registre o USB escolhido. O manifesto deve ficar fora do repositório:

    sudo python3 deploy/portable_usb/select_target.py \
      --serial 'SERIAL-EXATO-DO-USB' \
      --output /var/tmp/nivus-usb-selection.json

Em seguida gere o seed. O comando relê o inventário atual e exige que caminho, modelo, serial e capacidade ainda correspondam ao manifesto:

    sudo python3 deploy/portable_usb/generate_autoinstall.py \
      --selection /var/tmp/nivus-usb-selection.json \
      --output /var/tmp/nivus-usb-seed\n\nPara gerar também uma ISO privada de configuração NoCloud, use uma pasta nova e acrescente `--build-seed-iso`:\n\n    sudo python3 deploy/portable_usb/generate_autoinstall.py \\\n      --selection /var/tmp/nivus-usb-selection.json \\\n      --output /var/tmp/nivus-usb-seed-with-iso \\\n      --build-seed-iso\n\nA ISO `nivus-autoinstall-seed.iso` e seu checksum `.sha256` ficam dentro dessa pasta. A ISO contém a configuração e o hash da senha; mantenha-a privada.

O gerador pergunta usuário, hostname e senha do Ubuntu. A senha é digitada sem aparecer e transformada localmente com openssl; apenas o hash entra no arquivo user-data. O diretório de saída usa modo 0700, os arquivos usam 0600, e uma pasta existente nunca é sobrescrita.

O seed contém:

- user-data: configuração autoinstall com identidade inicial, verificação antecipada e plano de armazenamento.
- meta-data: identificador da instância NoCloud.
- TARGET-IDENTITY.txt: caminho, modelo, serial e capacidade que devem aparecer na revisão.
- SHA256SUMS: hashes para conferir os arquivos do seed.

Trate o diretório como privado porque user-data contém o hash da senha do Ubuntu. Não o publique nem o envie para chats.

## Instalar

Disponibilize `user-data` e `meta-data` ao instalador Subiquity como datasource NoCloud. A ISO de configuração gerada pode ser anexada como mídia separada (por exemplo, como CD virtual) ou gravada em uma terceira mídia; a mídia instaladora Ubuntu e o USB de destino também precisam ser separados. A ISO seed não é inicializável e não substitui o instalador Ubuntu.

Inicie o instalador Ubuntu Server 24.04 ou mais recente. Antes de confirmar a gravação, confira o caminho, modelo, serial e capacidade na tela de armazenamento e compare com TARGET-IDENTITY.txt. Cancele se a tela mostrar outro disco ou qualquer divergência. O plano formata o USB selecionado e remove seus dados.

A configuração usa o serial exato em vez de selecionar o maior disco. Um comando early-commands confere novamente serial único, caminho, modelo, capacidade, transporte USB, estado gravável e ausência de partições montadas. Se uma checagem falhar, o instalador para.

## Layout resultante

| Partição | Tipo | Uso |
| --- | --- | --- |
| BIOS boot | sem sistema de arquivos | GRUB em firmware BIOS com GPT |
| EFI | FAT32, 1 GiB | /boot/efi em firmware UEFI |
| Ubuntu | ext4, 24 GiB | Sistema operacional persistente em / |
| NIVUS_DATA | ext4, restante do USB | Montagem persistente em /var/lib/nivus |

O plano prepara a persistência para banco, segredos, configurações, releases e armazenamento Nivus nesse ponto de montagem. A instalação do Nivus e seu guard de inicialização ainda são etapas seguintes.

## Limites e validação pendente

A CI usa inventários de discos sintéticos em runner Ubuntu hospedado, não particiona discos e valida um seed representativo pelo validador/schema oficial da linha Subiquity Ubuntu 24.04, fixado a um commit. Isso não executa o instalador nem substitui validação no runtime de cada ISO. Ainda faltam integrar o seed a mídia inicializável reprodutível, instalar o Nivus no primeiro boot, testar reinício e persistência, verificar recuperação/rollback e validar firmware UEFI/BIOS em hardware físico Intel/AMD. Não há declaração de compatibilidade de boot universal até essa matriz passar.

Referências oficiais:

- [Subiquity: referência de autoinstall](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
- [Subiquity: validação do autoinstall](https://canonical-subiquity.readthedocs-hosted.com/en/latest/howto/autoinstall-validation.html)
- [Subiquity: fornecimento do arquivo autoinstall](https://canonical-subiquity.readthedocs-hosted.com/en/latest/tutorial/providing-autoinstall.html)
- [Curtin: armazenamento, partições e montagem](https://curtin.readthedocs-hosted.com/en/latest/topics/storage.html)
