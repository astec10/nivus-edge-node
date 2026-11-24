# Debian 13 enxuto no USB de 25 GB

Este caminho prepara uma instalação persistente para um USB comercial anunciado como 25 GB e depois instala o Nivus pelo pacote. Não é um sistema live nem uma ISO personalizada. O Debian é instalado no próprio pendrive e mantém o sistema, os dados, as imagens Docker e os segredos após desligar.

## Limite do tamanho

Fabricantes anunciam capacidade em GB decimal. Um dispositivo de 25.000.000.000 bytes corresponde a cerca de 23,3 GiB antes de partições e metadados; a capacidade apresentada varia por modelo. O instalador Master exige no mínimo **8 GiB livres** em `NIVUS_DATA` para imagens e builds. Se a verificação mostrar menos, não force a instalação.

O guia oficial do Debian 13 recomenda 4 GB de disco para uma instalação sem ambiente gráfico. Esse valor cobre o sistema operacional, não o Nivus, Docker, imagens, builds ou banco de dados. O projeto ainda não mediu uma instalação completa num USB de 25 GB.

## Preparar a instalação

1. Baixe a mídia oficial Debian 13 amd64 netinst. Use uma mídia de instalação separada do pendrive de destino.
2. Inicie o instalador em modo UEFI e selecione somente **servidor SSH** e **utilitários padrão do sistema**. Desmarque ambiente desktop.
3. Na tela de partições, selecione o USB de destino conferindo modelo, serial e capacidade. Não use particionamento automático se ele puder atingir o disco interno.
4. Crie a tabela GPT no USB e estas partições. Os tamanhos são GiB, não GB:

| Partição | Tamanho sugerido | Formato e montagem |
| --- | ---: | --- |
| EFI System Partition | 1 GiB | FAT32, `/boot/efi` |
| Sistema | 8 GiB | ext4, `/` |
| `NIVUS_DATA` | restante, cerca de 14 GiB | ext4, rótulo `NIVUS_DATA`, `/var/lib/nivus` |

O instalador Nivus valida que `/` e `/var/lib/nivus` são partições ext4 distintas no mesmo dispositivo USB e que `NIVUS_DATA` está registrado uma única vez no `/etc/fstab`. Instale o carregador de boot no USB e interrompa se o instalador indicar o disco interno como destino. O boot em vários computadores, UEFI/BIOS e modelos USB ainda está pendente de validação.

Finalize a instalação, remova a mídia instaladora e faça o primeiro boot pelo pendrive de destino. Conecte a rede antes de instalar o perfil Master.

## Instalar o pacote Nivus

Copie a pasta ou o `.tar.gz` do pacote para `/home/USUARIO/`, que fica na partição raiz do próprio USB. Nesta versão, não coloque o pacote dentro de `/var/lib/nivus`: a verificação de segurança exige que `NIVUS_DATA` esteja vazio antes de inicializar o volume persistente.

Se recebeu o arquivo compactado e o checksum publicado no mesmo diretório, confira o hash antes de extrair:

```bash
cd "$HOME"
sha256sum -c nivus-install-bundle-0.2.0-debian13.tar.gz.sha256
mkdir -p "$HOME/nivus-package"
tar -xzf "$HOME/nivus-install-bundle-0.2.0-debian13.tar.gz" -C "$HOME/nivus-package"
cd "$HOME/nivus-package/nivus-install-bundle-0.2.0-debian13"
sudo bash ./install_nivus.sh --profile master --mode online --check-only
sudo bash ./install_nivus.sh --profile master --mode online
```

O perfil Master pede confirmação antes de alterar o host. Ele instala `docker.io`, `docker-cli` e `docker-compose` dos repositórios Debian, além das dependências do Nivus; depois cria segredos locais e inicia dashboard/API/MQTT. A instalação inicial precisa de Internet para APT, Docker Hub, PyPI e npm. Depois, os serviços locais não exigem um provedor de IA ou serviço de nuvem.

Para instalar um Worker, execute no computador que receberá o agente:

```bash
sudo bash ./install_nivus.sh --profile worker --mode online --check-only
sudo bash ./install_nivus.sh --profile worker --mode online
```

O Worker pede URL HTTPS, nome e código de pareamento do Master. O suporte Debian cobre o agente leve e suas limitações atuais; execução de tarefas remotas ainda não está implementada.

## O que ainda falta validar

- Instalação limpa num USB físico de 25 GB e espaço real após instalar imagens/builds.
- Boot pelo mesmo USB em mais de um computador; BIOS/CSM ainda não qualificado.
- Primeiro login, reboot, SQLite, segredos, Docker e dados persistentes em Debian 13.
- Compatibilidade de hardware, rede, sensores e recuperação/rollback.

Os testes sintéticos locais passaram. A CI hospedada ainda precisa ser executada no GitHub; nenhuma dessas verificações substitui os testes físicos. Se uma partição, unidade de boot ou armazenamento apresentado pelo instalador diferir do esperado, cancele antes de gravar.

## Referências

- [Requisitos de instalação do Debian 13 amd64](https://www.debian.org/releases/trixie/amd64/ch03s04.en.html)
- [Instalador do Debian 13](https://www.debian.org/releases/trixie/amd64/)
- [Pacote Docker Engine do Debian 13](https://packages.debian.org/trixie/admin/docker.io)
- [Pacote Docker Compose do Debian 13](https://packages.debian.org/trixie/admin/docker-compose)
