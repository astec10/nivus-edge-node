# Pacote de instalação Nivus para USB

O pacote reúne um snapshot público do repositório, o instalador, um manifesto de arquivos com SHA-256 e dois perfis selecionáveis. Ele evita clonar o GitHub no computador de destino. A instalação Master ainda precisa de internet para instalar dependências e construir imagens Docker. O perfil Worker pode instalar o agente sem internet; para parear e enviar telemetria, o Master precisa estar acessível por HTTPS.

Este pacote instala o Nivus num sistema Linux já iniciado. Ele não particiona, formata nem instala a distribuição. Para um USB comercial de 25 GB, use o caminho enxuto Debian 13 em [DEBIAN_USB.md](DEBIAN_USB.md). O fluxo de autoinstall Ubuntu continua documentado em [AUTOINSTALL.md](AUTOINSTALL.md) e mantém o mínimo de 40 GiB.

O código do pacote aceita Ubuntu Server 24.04+ e Debian 13 Trixie, amd64/x86_64. O restante do projeto ainda não foi validado numa instalação física Debian; CI e testes sintéticos não comprovam boot em USB nem compatibilidade de hardware.

## Gerar o pacote

Use uma cópia limpa e commitada do repositório. A saída precisa ficar fora da pasta Git; o gerador recusa árvores modificadas e nomes de arquivos de dados ou credenciais:

```bash
python3 deploy/portable_usb/create_bundle.py build \
  --source-root . \
  --output-dir /caminho/seguro/nivus-bundle-release \
  --version 0.2.0-debian13
```

O gerador cria uma pasta instalável, um arquivo `.tar.gz` e um arquivo lateral `.sha256`. Copie a pasta ou o arquivo para o **volume raiz do Linux instalado no USB**, por exemplo para `/home/USUARIO/`; não coloque o pacote dentro de `/var/lib/nivus` antes da primeira instalação, pois esse volume precisa estar vazio ou já ter um marcador Nivus válido. Se copiar o `.tar.gz`, extraia-o antes de chamar o instalador:

```bash
mkdir -p "$HOME/nivus-package"
tar -xzf /caminho/nivus-install-bundle-0.2.0-debian13.tar.gz -C "$HOME/nivus-package"
```

O SHA-256 detecta corrupção acidental do artefato. Como manifesto e checksum acompanham o pacote, eles não são uma assinatura de autoria; compare o hash com um valor publicado por um canal confiável antes de instalar em produção.

## Instalar com um comando

Na pasta copiada para o sistema Linux, rode:

```bash
sudo bash ./install_nivus.sh
```

O instalador pede o perfil e o modo se houver terminal interativo. Também aceita argumentos diretos:

```bash
sudo bash ./install_nivus.sh --profile master --mode online
sudo bash ./install_nivus.sh --profile worker --mode online
sudo bash ./install_nivus.sh --profile worker --mode offline
sudo bash ./install_nivus.sh --profile master --mode offline --check-only
```

Acrescente `--check-only` a qualquer perfil para validar o pacote e os pré-requisitos sem instalar. O instalador exige confirmação antes de modificar o host.

### Perfil Master

- Ubuntu Server 24.04 ou mais recente, ou Debian 13 Trixie; amd64/x86_64, systemd e Python 3.10+.
- Exige que `/` e `/var/lib/nivus` sejam partições ext4 do mesmo USB, com o rótulo `NIVUS_DATA`, uma entrada `fstab` válida e no mínimo 8 GiB livres no volume de dados.
- Recusa uma instalação Nivus existente, Docker ativo, arquivos conflitantes, volume desconhecido ou armazenamento não comprovado. Não formata discos.
- Configura a persistência já existente do Nivus e chama `deploy/install.sh`, que instala dependências, cria segredos no host e inicia a dashboard/API/MQTT local.
- **Online obrigatório nesta versão.** APT, imagens do Docker Hub, PyPI e npm são usados durante a instalação. `--mode offline` lista os artefatos que faltam e termina antes de alterar o host.

Master significa o servidor local do painel/API nesta versão. Descoberta, classificação de hardware e scheduler de tarefas entre nós ainda não estão implementados só por instalar esse perfil.

### Perfil Worker

- Ubuntu Server 24.04 ou mais recente, ou Debian 13 Trixie; amd64/x86_64, systemd 247+ e Python 3.10+.
- Instala somente o agente em `/opt/nivus/node-agent` e cria o estado privado em `/var/lib/nivus-node-agent`, usando conta de serviço sem login.
- Online, pede URL HTTPS do Master, sugere um nome inicial aleatório editável e solicita o código de pareamento de uso único em entrada oculta. Você pode fornecer a CA pública do Master; ela fica no estado privado do próprio Worker. Depois ativa `nivus-node-agent.service`.
- Offline, prepara o agente sem parear nem iniciar serviço. Quando o Master estiver acessível, rode novamente com `--profile worker --mode online`.
- O agente envia heartbeat e uso de CPU, memória e disco. Ele não executa comandos ou tarefas remotas, não usa MQTT e não transfere arquivos.
- Instalação reexecutável: se o pareamento falhar, o código não substitui uma instalação nem credenciais existentes; execute o mesmo pacote novamente após corrigir a causa.

O token de nó é emitido pelo Master e fica somente em `/var/lib/nivus-node-agent/credentials.json`, com permissões restritas. Não copie esse arquivo entre computadores nem o inclua no pacote ou GitHub. Cada Worker precisa de pareamento próprio. A troca do token/revogação deve ser feita pelo painel Master e por novo pareamento.

## Segurança e suporte

- O snapshot inclui apenas arquivos commitados. O gerador exclui diretórios de dados/desenvolvimento e recusa arquivos versionados com nomes de credenciais, chaves, bancos ou logs.
- SHA-256 detecta alterações desde que o manifesto de origem seja confiável; o manifesto do próprio pacote não autentica quem o publicou.
- O pacote não contém segredos, banco de produção, telemetria real, chave privada, CA privada, credenciais ou estado de nó.
- Não use um clone privado do notebook como imagem de frota. Segredos, hostname, identidade, banco e credenciais devem ser únicos por máquina.
- O fluxo antigo Ubuntu/Subiquity requer pelo menos **40 GiB**; não reduza a verificação. Para um USB comercial de 25 GB, use somente o procedimento Debian 13 em [DEBIAN_USB.md](DEBIAN_USB.md), que não usa o gerador Subiquity.
- O perfil portátil aceita Ubuntu Server 24.04+ e Debian 13 Trixie x86_64. Debian 13 em USB é uma rota candidata ainda sem validação física. Outras distros, ARM/ARM32, Raspberry Pi, Android, tablets, ESP32 e Arduino não são suportados por este pacote.
- Falha do `deploy/install.sh` pode deixar as unidades de persistência do USB configuradas; a instalação Compose tem seu rollback próprio e os dados permanecem. Corrija a causa e execute novamente. Não remova manualmente `/var/lib/nivus`, segredos ou o volume persistente.

## Verificações

Na cópia de desenvolvimento:

```bash
python3 -m unittest deploy.portable_usb.test_bundle -v
python3 -m py_compile deploy/portable_usb/create_bundle.py deploy/portable_usb/test_bundle.py
bash -n deploy/portable_usb/install_nivus.sh
```

Essas verificações validam o artefato e o fluxo de pré-requisitos com dados sintéticos; não formatam USB nem comprovam instalação física, reboot ou hardware. Para critérios de validação no runner hospedado e limites dos testes, veja [VM_VALIDATION.md](../../docs/VM_VALIDATION.md) e o workflow de USB.
