# Ubuntu + Nivus USB portátil: sistema e dados persistentes

O operador confirmou uma instalação completa de Ubuntu Server minimal no pendrive de destino, para usar essa máquina como um nó portátil e temporário em outro computador x86_64. O sistema operacional e os dados permanecem no USB após reinicializações. O instalador não pode instalar nem formatar o disco interno do computador hospedeiro.

Este formato é Ubuntu instalado no USB; não é Casper Live com raiz volátil. O PR #31 já entrega a peça de persistência dos dados Nivus. **Ainda não existe um instalador/imagem Nivus pronta para USB.**

## Estado atual

A integração de storage monta uma partição ext4 chamada `NIVUS_DATA` em `/var/lib/nivus` e preserva os caminhos esperados pelo instalador Compose usando links simbólicos:

- `/var/lib/nivus-compose` -> `/var/lib/nivus/compose` (SQLite e estado Mosquitto).
- `/etc/nivus-compose` -> `/var/lib/nivus/config` (segredos, TLS e configuração).
- `/opt/nivus-compose` -> `/var/lib/nivus/releases` (código e releases).
- `/var/lib/docker` -> `/var/lib/nivus/docker` (imagens, metadados e logs de containers).

O guard systemd valida montagem real, ext4, rótulo, marcador e layout antes de Docker/coletor. Se o volume não estiver válido, os serviços não iniciam e não escrevem no lugar errado.

O workflow `Live USB storage` passou em runner Ubuntu hospedado usando ext4 em loop device. Esse teste valida a integração de dados; **não** valida ainda a instalação do Ubuntu no pendrive ou o boot do Nivus.

## Layout planejado

O instalador deve criar no pendrive selecionado:

1. Partição de boot/EFI.
2. Raiz Ubuntu Server minimal persistente.
3. Partição ext4 `NIVUS_DATA` persistente, montada em `/var/lib/nivus`.

O instalador deve identificar e exibir modelo, serial e capacidade do disco de destino e pedir confirmação explícita antes de particionar. Nunca deve presumir que o maior disco é o pendrive. A versão LTS, suporte BIOS/UEFI e Secure Boot serão fixados após os testes de construção.

## Preparação manual do volume atual

Até o instalador USB ficar pronto, use uma partição ext4 vazia, já formatada e rotulada `NIVUS_DATA`. Formatar uma partição apaga seu conteúdo; os helpers abaixo deliberadamente não criam partições nem formatam discos.

No Ubuntu de preparação, identifique cuidadosamente a partição:

    lsblk -f

O helper aceita somente uma partição de bloco ext4 não montada com o rótulo esperado. Ele se recusa a adotar dados sem marcador reconhecido e cria apenas o marcador/diretórios:

    sudo bash deploy/live-usb/prepare-data-volume.sh /dev/sdXN

Substitua `/dev/sdXN` pelo identificador confirmado por `lsblk -f`. Não use um nome de dispositivo presumido.

## Integrar a persistência no Ubuntu instalado

O integrador modifica apenas uma raiz Ubuntu preparada que tenha o marcador `.nivus-live-image-root`. Para um fluxo de instalação completo no USB, o futuro instalador deve aplicar a integração à raiz Ubuntu do pendrive antes do primeiro boot:

    sudo bash deploy/live-usb/install-image-integration.sh /caminho/da/raiz-ubuntu-montada

Ele instala a montagem `NIVUS_DATA`, o guard, dependências de Docker/coletor e os links de dados. Recusa a raiz do sistema em execução, destinos conflitantes e diretórios de dados não vazios.

## Marcos restantes

- Criar instalador/imagem reproduzível de Ubuntu Server minimal x86_64 que instale no USB escolhido.
- Proteger os discos internos com seleção explícita do alvo e confirmação.
- Configurar raiz persistente e partição `NIVUS_DATA`.
- Instalar Nivus no primeiro boot e validar login, HTTPS, API, MQTT e uso sem Internet upstream em runner hospedado.
- Reiniciar o mesmo USB e verificar SQLite com `PRAGMA quick_check`, configuração, segredos, releases e estado Docker.
- Documentar atualização, backup, recuperação e comportamento após remoção do USB.
- Fazer testes físicos UEFI/BIOS e Intel/AMD; CI hospedada não certifica hardware físico.

## Recuperação

Antes de atualizar uma mídia física, faça backup Nivus e desligue o sistema corretamente. Mantenha uma mídia de recuperação Ubuntu separada. Se o volume não for reconhecido, não formate nem crie um novo marcador sobre dados antigos. Preserve a partição e investigue rótulo, sistema de arquivos e conteúdo offline.
