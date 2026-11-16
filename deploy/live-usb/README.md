# Persistência do Ubuntu instalado em USB

O nome histórico desta pasta é \`live-usb\`, mas a mídia definida para o Nivus é **Ubuntu Server instalado integralmente no pendrive**, não Casper Live. A raiz do sistema e os dados sobrevivem a reinicializações.

## Layout persistente

O instalador Subiquity prepara no mesmo USB uma raiz Ubuntu ext4 e a partição ext4 \`NIVUS_DATA\`, montada em \`/var/lib/nivus\`. O instalador Compose usa os caminhos persistentes por links:

- \`/var/lib/nivus-compose\` → \`/var/lib/nivus/compose\` (SQLite e estado Mosquitto).
- \`/etc/nivus-compose\` → \`/var/lib/nivus/config\` (segredos, TLS e configuração).
- \`/opt/nivus-compose\` → \`/var/lib/nivus\` (releases ficam em \`/var/lib/nivus/releases\`).
- \`/var/lib/docker\` → \`/var/lib/nivus/docker\` (imagens, metadados e logs dos containers).

O marcador \`.nivus-data-volume\` identifica o volume como \`nivus-data-volume-v1\`. O guard systemd verifica a montagem real, ext4, rótulo, marcador e diretórios antes de permitir Docker ou o coletor. Se o volume estiver ausente ou inválido, os serviços que gravam dados não iniciam.

## Instalar Nivus após instalar Ubuntu

A configuração do USB e do seed está em [portable_usb/AUTOINSTALL.md](../portable_usb/AUTOINSTALL.md). A ISO NoCloud é apenas mídia de configuração; use uma mídia Ubuntu Server inicializável separada e mantenha a confirmação de armazenamento do Subiquity ativa. O instalador apaga o USB selecionado. Confira caminho, modelo, serial e capacidade antes de confirmar.

Depois do primeiro boot do Ubuntu instalado no USB, clone o repositório e execute o instalador portátil como root:

    sudo bash deploy/portable_usb/install_nivus.sh

O comando confirma que a raiz e \`NIVUS_DATA\` estão em partições ext4 do mesmo dispositivo USB, que a partição de dados está montada para escrita e registrada uma única vez no \`/etc/fstab\`, e que Docker/Nivus ainda não estão em uso. Ele não particiona nem formata discos. Inicializa somente um volume vazio ou um volume que já tenha o marcador reconhecido, instala as unidades systemd e os links persistentes, e chama o instalador Compose existente.

O instalador Compose pede a criação do primeiro administrador no terminal. Na primeira instalação, internet é necessária para instalar pacotes e construir/baixar componentes. Depois que a instalação termina, os serviços locais iniciam no boot e não precisam de um provedor de IA ou serviço em nuvem para monitorar o nó na rede local. Funcionalidades de IA local, VPN e gerenciamento multi-nó continuam em fases próprias.

Se a etapa Compose falhar depois da integração persistente, corrija a causa e rode o mesmo comando novamente. A configuração dos links e unidades é idempotente e não sobrescreve arquivos conflitantes. O instalador Compose mantém seus próprios procedimentos de rollback e preserva dados/segredos.

## Regras de proteção

- Nunca escolha o maior disco automaticamente.
- Mantenha a mídia Ubuntu, o seed NoCloud e o USB de destino identificáveis e separados.
- Não confirme o armazenamento até conferir a identidade mostrada pelo Subiquity.
- O instalador portátil exige raiz e dados no mesmo dispositivo USB; se não puder provar isso, para sem continuar.
- Não formate ou crie um marcador sobre um volume desconhecido. Faça backup antes de recuperação ou reinstalação.
- Uma remoção acidental do USB pode corromper SQLite e imagens Docker; desligue o Ubuntu corretamente antes de desconectar.

## Validação

A CI hospedada valida o plano de particionamento, o schema do Subiquity, as proteções de seleção e o layout persistente com inventários e arquivos sintéticos. O workflow de storage usa uma partição ext4 em loop device num runner Ubuntu. Esses testes não iniciam um instalador real nem comprovam boot, desligamento ou persistência em hardware físico.

Ainda exigem validação: instalar por Subiquity até o primeiro boot, executar o instalador Nivus, reiniciar e conferir SQLite \`PRAGMA quick_check\`, segredos, configurações, releases e armazenamento Docker. Também faltam recuperação/rollback numa instalação limpa e uma matriz física UEFI/BIOS Intel/AMD. Não anuncie compatibilidade de boot universal antes desses resultados.

## Recuperação

Mantenha uma mídia Ubuntu de recuperação separada. Se \`NIVUS_DATA\` não for reconhecido, não formate nem substitua o marcador. Preserve a partição e investigue rótulo, UUID, sistema de arquivos e conteúdo offline. Use o procedimento de backup/restore documentado em [deploy/README.md](../README.md) somente depois de preservar o estado atual.
