# Roteiro de validação em VM Ubuntu limpa

Este roteiro valida uma instalação independente do Nivus Compose. A VM deve ser descartável e isolada; não execute os passos de instalação em um host com dados importantes.

## 1. Preparar a VM

- Ubuntu Server 22.04 LTS ou posterior, `amd64`/`x86_64`, com `systemd` 247 ou posterior.
- Para o primeiro ciclo: 2 vCPUs, 4 GB de RAM e 30 GB de disco. Registre a configuração real; esses valores são condições de teste, não requisitos mínimos certificados.
- Rede NAT com saída para APT/GitHub/Docker Hub e SSH acessível somente pelo host de virtualização. No VirtualBox, encaminhe TCP `127.0.0.1:2222` do host para a porta 22 do guest; não encaminhe portas para a Internet pública nem para a LAN doméstica.
- Faça um snapshot inicial antes de instalar. Anote versão do Ubuntu, arquitetura, CPU/RAM/disco livres, hipervisor e data.
- Use uma conta Linux de teste com `sudo`. Nunca compartilhe sua senha. Para acesso remoto, autorize uma chave pública temporária e confira a impressão digital SSH da VM por um canal local confiável.

O operador confirmou uma VM `testev1` com Ubuntu 26.04.1 LTS amd64, 4 vCPUs, 8 GB de RAM, filesystem raiz de cerca de 24,44 GB e 16 MB de memória de vídeo virtual. O vídeo é o adaptador de exibição, não VRAM para inferência. O operador relata que a VM trava ao tentar alterar configurações; numa sessão anterior o console também exibiu mensagens de watchdog/soft-lockup/RCU. Não instale o Nivus nela até resolver a estabilidade. Nenhum Nivus foi instalado nessa VM.

Para repetir o teste num ambiente previsível, o repositório fornece `deploy/windows/New-NivusTestVm.ps1`. Ele cria uma VM separada chamada `nivus-test-clean`, usa Ubuntu Server 24.04.5 LTS amd64, confere o SHA-256 oficial da ISO, atribui no máximo 2 vCPUs e ajusta a RAM conforme o host, cria um VDI dinâmico de 32 GB, mantém 16 MB de vídeo sem aceleração 3D e encaminha SSH somente por `127.0.0.1:2223`. Antes de criar a VM, recusa se outra VM estiver em execução, a porta SSH estiver ocupada ou a RAM livre no Windows for insuficiente. O script não altera nem apaga `testev1` ou outras VMs. Ainda não foi executado no computador do operador.

Baixe [Ubuntu Server 24.04.5 LTS amd64](https://releases.ubuntu.com/24.04/ubuntu-24.04.5-live-server-amd64.iso) e, no PowerShell aberto na raiz do repositório, execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\New-NivusTestVm.ps1 -IsoPath "$env:USERPROFILE\Downloads\ubuntu-24.04.5-live-server-amd64.iso"
```

O `ExecutionPolicy Bypass` vale apenas para essa execução e não altera a política global do Windows. No instalador, escolha o disco virtual de 32 GB, Ubuntu Server minimal e a opção **OpenSSH server**; crie credenciais somente para a VM e não as compartilhe. Depois do primeiro boot, faça um snapshot no VirtualBox antes de instalar o Nivus.

### Se uma VM travar ao alterar configurações

Configurações de hardware como RAM, CPU, armazenamento e rede devem ser ajustadas com a VM completamente desligada. O estado **Salvo** também pode bloquear alterações. Se o guest responder, rode `sudo poweroff` e aguarde o estado **Powered Off**. Se não responder, na janela da VM escolha **Máquina → Fechar → Desligar a máquina**; isso equivale a uma interrupção de energia para o guest e pode perder dados que ainda não foram gravados. Não escolha **Salvar o estado da máquina** para fazer essas alterações. Consulte o [manual oficial do VirtualBox](https://www.virtualbox.org/manual/).

Para a nova VM, mantenha o perfil conservador gerado pelo script. Em servidor sem interface gráfica, 16 MB de vídeo e aceleração 3D desligada são suficientes. O VirtualBox recomenda reservar RAM e no máximo metade das threads lógicas do host para cada VM; memória insuficiente no Windows pode causar paginação e deixar todo o host sem resposta. Se a janela de configurações continuar travando mesmo com a VM desligada, não altere o VDI: mantenha `testev1` intacta e use a nova VM criada pelo script.

Na console da VM, depois do primeiro login:

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

O script configura a regra NAT SSH como `127.0.0.1:2223` no host para a porta `22` do guest. Assim, SSH só fica acessível pelo próprio computador host; a conexão é `ssh -p 2223 usuario@127.0.0.1`. Se a VM for criada manualmente, use **Configurações → Rede → Adaptador 1 (NAT) → Avançado → Encaminhamento de portas** e crie a mesma regra. Autorize apenas uma chave pública temporária entregue para o teste e confira a impressão digital ED25519 da VM.

## 2. Obter e revisar o código

```bash
git clone https://github.com/astec10/nivus-edge-node.git
cd nivus-edge-node
git rev-parse HEAD
git status --short
sed -n '1,240p' deploy/install.sh
```

Registre o commit instalado. O instalador exige Ubuntu x86_64, systemd 247+, Docker Compose e acesso à Internet para dependências. A instalação usa HTTPS com certificado autoassinado e escolhe outra porta se 8443 estiver ocupada.

## 3. Instalar e verificar

```bash
sudo bash deploy/install.sh
```

Crie o primeiro administrador no terminal. Não copie a senha para logs, capturas ou este relatório. Depois:

```bash
sudo systemctl is-enabled docker.service nivus-compose-telemetry.service
sudo systemctl show nivus-compose-telemetry.service -p ActiveState -p SubState -p NRestarts --no-pager
sudo docker ps --filter name=nivus-edge --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
HTTPS_PORT=$(sudo awk -F= '$1 == "NIVUS_HTTPS_PORT" {print $2}' /opt/nivus-compose/current/.env)
curl -kfsS "https://127.0.0.1:${HTTPS_PORT}/health"
curl -ksS -o /dev/null -w '%{http_code}\n' "https://127.0.0.1:${HTTPS_PORT}/api/telemetry"
```

Esperado: serviços habilitados, quatro containers ativos, health com `status: ok`, e `401` para telemetria sem token. Somente o Nginx deve publicar uma porta no host; MQTT e API permanecem em redes Docker privadas. O certificado autoassinado gera um aviso no navegador durante este teste.

Confirme que a coleta persiste novas linhas no SQLite:

```bash
read_count() {
  sudo docker exec nivus-edge-api-1 python -c 'import sqlite3; c=sqlite3.connect("file:/data/nivus.db?mode=ro", uri=True); print(c.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]); c.close()'
}
before=$(read_count)
sleep 12
after=$(read_count)
printf 'telemetry_before=%s telemetry_after=%s\n' "$before" "$after"
test "$after" -gt "$before"
```

Abra `https://IP-DA-VM:PORTA/`, aceite o aviso de certificado apenas nesta VM isolada e confirme o login. Não registre credenciais.

## 4. Verificar reinício

Faça isso somente na VM descartável, após o snapshot e a coleta acima:

```bash
sudo reboot
```

Após a VM voltar, repita health, `401`, `systemctl show`, `docker ps` e a contagem SQLite. Os serviços precisam iniciar sozinhos e a base precisa manter as linhas existentes e continuar crescendo.

## 5. Backup e teste de restauração

Crie um backup consistente:

```bash
sudo bash /opt/nivus-compose/current/deploy/backup.sh
sudo ls -lt /var/backups/nivus-compose
```

O backup inclui uma cópia SQLite validada e o `.env` do Compose, mas **não inclui** os segredos JWT/MQTT, credenciais do broker, chave/certificado TLS ou imagens. Portanto, ele serve como ponto de recuperação local da instalação que conserva os mesmos segredos; não é um pacote completo para migrar para outro host.

O repositório agora inclui `deploy/restore.sh`. Primeiro teste somente a validação:

```bash
sudo ls -lt /var/backups/nivus-compose
BACKUP_DIR=/var/backups/nivus-compose/20261113T000000Z-XXXXXX
sudo bash /opt/nivus-compose/current/deploy/restore.sh --check "$BACKUP_DIR"
```

Substitua o valor de exemplo por um diretório real listado por `backup.sh`; o nome termina com um sufixo aleatório. Para provar o rollback automático, use a VM descartável depois de snapshot, gere um backup, espere a contagem de telemetria avançar e rode:

```bash
sudo bash /opt/nivus-compose/current/deploy/test-restore-rollback.sh --i-understand-this-is-a-disposable-vm "$BACKUP_DIR"
```

O teste só funciona dentro de uma VM, faz um backup de segurança, exige as confirmações `VM-ROLLBACK-TEST` e `RESTORE`, simula uma falha de health por até 45 segundos e verifica o retorno do banco, dos serviços, health 200, `401` sem token e SQLite. O resultado esperado é uma falha de health simulada seguida de mensagem de rollback recuperado; os dados atuais precisam permanecer. Se não houver mais telemetria na base ativa do que no backup escolhido, espere a coleta e tente novamente. Este teste injeta uma falha deliberadamente e nunca deve ser rodado no notebook ativo.

Depois, teste o caminho normal no mesmo ambiente descartável: `sudo bash /opt/nivus-compose/current/deploy/restore.sh "$BACKUP_DIR"`, digite `RESTORE`, confirme que a contagem volta ao ponto salvo e que a telemetria recomeça. O `restore.sh` cria outro backup consistente antes da troca e tenta rollback se a validação posterior falhar. Durante o rollback, verifica o SQLite, os quatro containers, o coletor, health HTTPS 200 e `401` sem token; se não confirmar todos, informa que o rollback não foi totalmente validado e mantém o backup prévio. Ele mantém `.env` e segredos atuais e restaura só o SQLite. Não execute a restauração nem o teste de falha no notebook em uso.

Até passar nesse teste de integração em VM, a restauração automatizada está implementada e revisada, mas não declarada validada.

## 6. Relatar o resultado

Anexe ao relatório, sem senhas, JWTs, conteúdo de `.env`, endereços domésticos ou dados pessoais:

- commit Git e versão do Ubuntu, arquitetura, hipervisor e recursos atribuídos;
- resultado e duração da instalação, RAM/disco antes e depois, imagens baixadas e portas ocupadas;
- saída resumida de health, status do serviço/coletor, containers e HTTP 401;
- contagem de telemetria antes/depois da espera e depois do reboot;
- localização e tamanho do backup, resultado de `quick_check` e estado de cada critério;
- erros encontrados e procedimento de rollback usado.

**Critério de saída:** instalação sem staging ou segredos prévios; login e telemetria persistente; recuperação após reboot; backup íntegro; restauração e rollback demonstrados numa cópia descartável. Até esses critérios passarem, o projeto é uma candidata e não declara compatibilidade universal x86_64.
