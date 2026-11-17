#!/usr/bin/env bash
set -Eeuo pipefail

CONF_PATH=/etc/nginx/conf.d/nivus-compose-portless.conf
CURRENT=/opt/nivus-compose/current
BACKUP_ROOT=/var/backups/nivus-compose
ACTION=apply

usage() {
  cat <<'USAGE'
Uso:
  sudo bash promote-dashboard-443.sh ENDERECO_IPV4
  sudo bash promote-dashboard-443.sh --rollback
  bash promote-dashboard-443.sh --render PORTA_HTTPS HOST_UPSTREAM PORTA_UPSTREAM ENDERECO_IPV4 CERT KEY

A promoção Nginx adiciona um arquivo próprio e mantém o Compose em sua porta atual.
USAGE
}

valid_port() {
  [[ "$1" =~ ^[0-9]{1,5}$ ]] && (( 10#"$1" >= 1 && 10#"$1" <= 65535 ))
}

valid_ipv4() {
  [[ "$1" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1
  local a b c d octet
  IFS=. read -r a b c d <<< "$1"
  for octet in "$a" "$b" "$c" "$d"; do
    (( 10#"$octet" <= 255 )) || return 1
  done
}

render_config() {
  local listen_port="$1" upstream_host="$2" upstream_port="$3" target="$4" cert="$5" key="$6"
  valid_port "$listen_port" || { echo "Porta HTTPS inválida." >&2; return 2; }
  [[ "$upstream_host" =~ ^[a-z0-9.-]+$ ]] || { echo "Host de upstream inválido." >&2; return 2; }
  valid_port "$upstream_port" || { echo "Porta de upstream inválida." >&2; return 2; }
  valid_ipv4 "$target" || { echo "Informe um endereço IPv4 válido." >&2; return 2; }
  [[ "$cert" =~ ^/[A-Za-z0-9_./-]+$ && "$key" =~ ^/[A-Za-z0-9_./-]+$ ]] || {
    echo "Caminho de certificado inválido." >&2; return 2;
  }
  cat <<NGINX
# Managed by Nivus; remove only with promote-dashboard-443.sh --rollback.
server {
    listen $listen_port ssl;
    server_name $target;
    ssl_certificate $cert;
    ssl_certificate_key $key;
    ssl_protocols TLSv1.2 TLSv1.3;
    location / {
        proxy_pass https://$upstream_host:$upstream_port;
        proxy_http_version 1.1;
        proxy_ssl_server_name on;
        proxy_ssl_name $target;
        proxy_ssl_verify off;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }
}
NGINX
}

if [[ "${1:-}" == "--render" ]]; then
  [[ $# -eq 7 ]] || { usage >&2; exit 2; }
  render_config "$2" "$3" "$4" "$5" "$6" "$7"
  exit
fi
if [[ "${1:-}" == "--rollback" ]]; then
  ACTION=rollback
  shift
fi
if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0 [ENDERECO_IPV4|--rollback]" >&2
  exit 1
fi

if [[ "$ACTION" == rollback ]]; then
  [[ -f "$CONF_PATH" ]] || { echo "Não há promoção Nivus para remover."; exit 0; }
  grep -q '^# Managed by Nivus;' "$CONF_PATH" || {
    echo "Arquivo de configuração não pertence ao Nivus; rollback recusado." >&2
    exit 2
  }
  ROLLBACK_COPY="$BACKUP_ROOT/portless-dashboard/rollback-$(date -u +%Y%m%dT%H%M%SZ).conf"
  install -d -o root -g root -m 700 "$(dirname "$ROLLBACK_COPY")"
  cp -a -- "$CONF_PATH" "$ROLLBACK_COPY"
  rm -- "$CONF_PATH"
  if ! nginx -t || ! systemctl reload nginx; then
    cp -a -- "$ROLLBACK_COPY" "$CONF_PATH"
    nginx -t && systemctl reload nginx || true
    echo "Rollback falhou; a configuração anterior foi restaurada." >&2
    exit 1
  fi
  HTTPS_PORT=$(sed -n 's/^NIVUS_HTTPS_PORT=//p' "$CURRENT/.env")
  curl -kfsS --connect-timeout 2 --max-time 5 "https://127.0.0.1:$HTTPS_PORT/health" >/dev/null
  AUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' \
    "https://127.0.0.1:$HTTPS_PORT/api/telemetry")
  [[ "$AUTH_STATUS" == 401 ]]
  printf 'Promoção removida; Compose permanece disponível na porta %s. Cópia: %s\n' "$HTTPS_PORT" "$ROLLBACK_COPY"
  exit
fi

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
TARGET_IP="$1"
valid_ipv4 "$TARGET_IP" || { echo "Informe o IPv4 do nó, sem protocolo ou porta." >&2; exit 2; }
ip -4 -o addr show | awk '{split($4, a, "/"); print a[1]}' | grep -Fxq "$TARGET_IP" || {
  echo "O endereço informado não pertence a este host." >&2
  exit 2
}

[[ -d "$CURRENT" && -f "$CURRENT/.env" ]] || { echo "Stack Nivus Compose não encontrada." >&2; exit 2; }
HTTPS_PORT=$(sed -n 's/^NIVUS_HTTPS_PORT=//p' "$CURRENT/.env")
valid_port "$HTTPS_PORT" || { echo "NIVUS_HTTPS_PORT inválida." >&2; exit 2; }
(( 10#$HTTPS_PORT != 443 )) || { echo "A stack já usa 443; promoção Nginx recusada." >&2; exit 2; }
SECRET_DIR=$(sed -n 's/^NIVUS_SECRET_DIR=//p' "$CURRENT/.env")
[[ "$SECRET_DIR" =~ ^/[A-Za-z0-9_./-]+$ ]] || { echo "NIVUS_SECRET_DIR inválido." >&2; exit 2; }
CERT="$SECRET_DIR/tls.crt"
KEY="$SECRET_DIR/tls.key"
[[ -r "$CERT" && -r "$KEY" ]] || { echo "Certificado do Nivus não encontrado." >&2; exit 2; }
openssl x509 -in "$CERT" -noout -ext subjectAltName | grep -Fq "IP Address:$TARGET_IP" || {
  echo "O certificado não contém o IP informado; promoção recusada." >&2; exit 2
}
curl -kfsS --connect-timeout 2 --max-time 5 "https://127.0.0.1:$HTTPS_PORT/health" >/dev/null
AUTH_BEFORE=$(curl -k -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' \
  "https://127.0.0.1:$HTTPS_PORT/api/telemetry")
[[ "$AUTH_BEFORE" == 401 ]] || { echo "A API Compose não respondeu 401 sem token." >&2; exit 2; }

NGINX_443=$(ss -H -ltnp 'sport = :443')
if [[ -z "$NGINX_443" ]] || ! grep -q 'nginx' <<< "$NGINX_443" || grep -v 'nginx' <<< "$NGINX_443" | grep -q .; then
  echo "443 precisa estar atendida somente pelo Nginx; serviço observado: ${NGINX_443:-livre}. Nenhuma mudança feita." >&2
  exit 2
fi
nginx -T 2>&1 | grep -Fq 'include /etc/nginx/conf.d/*.conf;' || {
  echo "O Nginx não inclui /etc/nginx/conf.d/*.conf." >&2; exit 2;
}
if nginx -T 2>/dev/null | awk -v target="$TARGET_IP" '
  /^[[:space:]]*server_name[[:space:]]/ {
    line=$0
    sub(/^[[:space:]]*server_name[[:space:]]*/, "", line)
    sub(/;.*/, "", line)
    count=split(line, names, /[[:space:]]+/)
    for (i=1; i<=count; i++) if (names[i] == target) found=1
  }
  END { exit found ? 0 : 1 }
'; then
  if [[ -f "$CONF_PATH" ]] && grep -q '^# Managed by Nivus;' "$CONF_PATH" \
     && grep -Fq "server_name $TARGET_IP;" "$CONF_PATH"; then
    curl -kfsS --connect-timeout 2 --max-time 5 --resolve "$TARGET_IP:443:127.0.0.1" "https://$TARGET_IP/health" >/dev/null
    AUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 --resolve "$TARGET_IP:443:127.0.0.1" \
      -o /dev/null -w '%{http_code}' "https://$TARGET_IP/api/telemetry")
    [[ "$AUTH_STATUS" == 401 ]]
    echo "Dashboard já promovida e validada em https://$TARGET_IP/"
    exit
  fi
  echo "Já existe um server_name exato para $TARGET_IP; configuração preservada." >&2
  exit 2
fi
if [[ -e "$CONF_PATH" || -L "$CONF_PATH" ]]; then
  echo "O caminho $CONF_PATH já existe e não é uma configuração Nivus reconhecida." >&2
  exit 2
fi
systemctl is-active --quiet nginx || { echo "Nginx não está ativo." >&2; exit 2; }

install -d -o root -g root -m 700 "$BACKUP_ROOT/portless-dashboard"
BACKUP_DIR=$(mktemp -d "$BACKUP_ROOT/portless-dashboard/promotion-XXXXXXXX")
chmod 700 "$BACKUP_DIR"
nginx -T > "$BACKUP_DIR/nginx-before.txt" 2>&1
printf 'target=%s\nupstream_port=%s\n' "$TARGET_IP" "$HTTPS_PORT" > "$BACKUP_DIR/promotion.txt"
chmod 600 "$BACKUP_DIR/promotion.txt" "$BACKUP_DIR/nginx-before.txt"

TMP_CONFIG=$(mktemp /etc/nginx/conf.d/.nivus-portless.XXXXXX)
CHANGED=0
cleanup_failed_promotion() {
  rc=$?
  trap - ERR INT TERM
  if [[ "$CHANGED" == 1 ]]; then
    rm -f -- "$CONF_PATH"
    nginx -t && systemctl reload nginx || true
    echo "Promoção falhou; o arquivo aditivo foi removido. Backup: $BACKUP_DIR" >&2
  fi
  rm -f -- "$TMP_CONFIG"
  exit "$rc"
}
trap cleanup_failed_promotion ERR INT TERM

render_config 443 127.0.0.1 "$HTTPS_PORT" "$TARGET_IP" "$CERT" "$KEY" > "$TMP_CONFIG"
install -o root -g root -m 644 "$TMP_CONFIG" "$CONF_PATH"
CHANGED=1
nginx -t
systemctl reload nginx
curl -kfsS --connect-timeout 2 --max-time 5 --resolve "$TARGET_IP:443:127.0.0.1" "https://$TARGET_IP/health" >/dev/null
AUTH_STATUS=$(curl -k -sS --connect-timeout 2 --max-time 5 --resolve "$TARGET_IP:443:127.0.0.1" \
  -o /dev/null -w '%{http_code}' "https://$TARGET_IP/api/telemetry")
[[ "$AUTH_STATUS" == 401 ]]
CHANGED=0
trap - ERR INT TERM
rm -f -- "$TMP_CONFIG"
printf 'Dashboard Compose em https://%s/; porta de retorno HTTPS %s preservada.\n' "$TARGET_IP" "$HTTPS_PORT"
printf 'Backup Nginx: %s\nRollback: sudo bash %s/deploy/promote-dashboard-443.sh --rollback\n' "$BACKUP_DIR" "$CURRENT"
