# Desenvolvimento local

## Backend

    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r backend/requirements.txt
    export NIVUS_DB_PATH="$PWD/work/dev.sqlite3"
    export NIVUS_JWT_SECRET_FILE="$HOME/.config/nivus-edge/jwt_secret"
    uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000

Crie o primeiro usuário administrador com PYTHONPATH=backend python3 -m create_admin. O fluxo pede senha interativamente.

O broker MQTT é externo. Configure o endereço, usuário e senha antes de iniciar worker/agente. Não inicie instâncias duplicadas.

As dependências Python e as imagens base do Docker estão fixadas nas versões usadas na validação. O frontend deve ser instalado com `npm ci` usando `package-lock.json`. Atualize versões de forma deliberada e repita build e smoke test; não troque tags/digests automaticamente durante uma instalação.

## Frontend

    cd frontend
    npm ci
    npm run dev

O Dockerfile do frontend executa `npm ci` e `npm run build`; o build passou no notebook de teste, foi servido em smoke test Compose isolado e depois ativado no Nginx do host com backup/rollback. A verificação de health, assets e HTTP 401 foi aprovada; o operador também confirmou o login com a conta existente. Nunca envie a senha ao chat.

## Verificação Compose isolada

No notebook de teste, a candidata passou por `docker compose config`, build das imagens e smoke test com projeto/portas/dados temporários. O teste verificou HTTPS, asset do painel, HTTP 401 sem token e uma mensagem MQTT inserida no SQLite de staging. O script `deploy/verify-compose-staging.sh` exige `NIVUS_ALLOW_STAGING_SMOKE=1`, apaga apenas arquivos de segredo de staging, para apenas seu próprio projeto Compose e preserva a pasta para diagnóstico. Ele não substitui a verificação numa instalação limpa.

## Licenciamento

O código deste projeto é AGPL-3.0-only (LICENSE). Preserve a licença de cada dependência e asset de terceiros. Se a interface for servida pela rede, mantenha os avisos legais e os links para obter o código-fonte correspondente e a licença.
