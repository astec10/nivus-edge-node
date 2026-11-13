# Roteiro de validação em VM Ubuntu limpa

Este roteiro valida uma instalação independente do Nivus Compose. A VM deve ser descartável e isolada; não execute os passos de instalação em um host com dados importantes.

## 1. Preparar a VM

- Ubuntu Server 22.04 LTS ou posterior, `amd64`/`x86_64`, com `systemd` 247 ou posterior.
- Para o primeiro ciclo: 2 vCPUs, 4 GB de RAM e 30 GB de disco. Registre a configuração real; esses valores são condições de teste, não requisitos mínimos certificados.
- Rede NAT com saída para APT/GitHub/Docker Hub e SSH acessível somente pelo host de virtualização. Não encaminhe as portas da VM para a Internet pública nem para a LAN doméstica.
- Faça um snapshot inicial antes de instalar. Anote versão do Ubuntu, arquitetura, CPU/RAM/disco livres, hipervisor e data.
- Use uma conta Linux de teste com `sudo`. Nunca compartilhe sua senha. Para acesso remoto, autorize uma chave pública temporária e confira a impressão digital SSH da VM por um canal local confiável.

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

## 5. Backup e limite de restauração atual

Crie um backup consistente:

```bash
sudo bash /opt/nivus-compose/current/deploy/backup.sh
sudo ls -lt /var/backups/nivus-compose
```

O backup inclui uma cópia SQLite validada e o `.env` do Compose, mas **não inclui** os segredos JWT/MQTT, credenciais do broker, chave/certificado TLS ou imagens. Portanto, ele serve como ponto de recuperação local da instalação que conserva os mesmos segredos; não é um pacote completo para migrar para outro host.

O repositório ainda não oferece um comando automatizado de restauração. Não sobrescreva o banco ativo manualmente nem marque restauração como validada. Antes de fechar esta etapa, implementar e testar uma restauração que faça backup prévio, pare todos os escritores, preserve os segredos existentes, valide o SQLite restaurado e tenha rollback. Execute esse teste numa cópia da VM, nunca no notebook de uso.

## 6. Relatar o resultado

Anexe ao relatório, sem senhas, JWTs, conteúdo de `.env`, endereços domésticos ou dados pessoais:

- commit Git e versão do Ubuntu, arquitetura, hipervisor e recursos atribuídos;
- resultado e duração da instalação, RAM/disco antes e depois, imagens baixadas e portas ocupadas;
- saída resumida de health, status do serviço/coletor, containers e HTTP 401;
- contagem de telemetria antes/depois da espera e depois do reboot;
- localização e tamanho do backup, resultado de `quick_check` e estado de cada critério;
- erros encontrados e procedimento de rollback usado.

**Critério de saída:** instalação sem staging ou segredos prévios; login e telemetria persistente; recuperação após reboot; backup íntegro; restauração e rollback demonstrados numa cópia descartável. Até esses critérios passarem, o projeto é uma candidata e não declara compatibilidade universal x86_64.
