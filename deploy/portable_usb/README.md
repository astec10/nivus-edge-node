# Preparação do alvo USB portátil

Esta etapa **apenas identifica e registra** um disco USB escolhido pelo operador. Ela não instala Ubuntu, não particiona, não formata, não monta e não altera dispositivos de bloco. Ainda não é um instalador Nivus completo nem uma imagem inicializável.

## Uso

Em uma máquina Ubuntu de preparação, conecte o pendrive de destino e execute:

    sudo python3 deploy/portable_usb/select_target.py

O programa lista todos os discos USB que passam pelos critérios de identificação: tipo disco, transporte USB, modelo e número de série presentes e únicos, leitura/gravação habilitada e nenhuma partição montada. Ele também exclui o dispositivo que contém a raiz atual quando consegue mapeá-lo.

Escolha o dispositivo conferindo **caminho, modelo, número de série e capacidade**. Registre a seleção digitando o número de série exato:

    sudo python3 deploy/portable_usb/select_target.py \
      --serial 'NUMERO-DE-SERIE-EXATO' \
      --output /var/tmp/nivus-usb-selection.json

O manifesto é criado com permissão `0600`; um arquivo existente nunca é sobrescrito. A confirmação registra a escolha, mas não autoriza particionamento. Se o modelo não expõe um serial único ou o disco tem sistema de arquivos montado, ele não aparece como elegível.

## Regras de segurança

- Não seleciona o maior disco, não escolhe nenhum alvo automaticamente e não confia apenas no sinal `RM`.
- Ignora discos SATA/NVMe e discos USB somente leitura.
- Recusa números de série ausentes, duplicados ou com caracteres de controle.
- Recusa discos com partições montadas, incluindo mídia do instalador normalmente montada em `/cdrom`.
- O identificador é apenas uma fotografia da seleção: o futuro instalador deve reler o inventário e confirmar serial, modelo, capacidade e caminho imediatamente antes de escrever.
- Se a identidade do alvo mudar, estiver ambígua ou não puder ser verificada, a instalação futura deve parar sem escrever.

## Próximo trabalho necessário

Esta etapa ainda precisa ser integrada a um fluxo Subiquity/autoinstall que mostre a identidade do alvo, confirme novamente antes de particionar e crie EFI, raiz Ubuntu persistente e a partição ext4 `NIVUS_DATA` em `/var/lib/nivus`. Depois serão necessários build da mídia, smoke de instalação no runner hospedado, persistência após reinicialização e testes físicos UEFI/BIOS.

A ISO oficial Ubuntu Server inicia um instalador e a escolha de armazenamento pode sobrescrever o disco escolhido. A referência Subiquity permite casar um disco pelo serial; não se deve usar `size: largest` para este caso:

- [Ubuntu Server: instalação básica](https://ubuntu.com/server/docs/installation/)
- [Subiquity: referência de autoinstall e seleção de discos](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
