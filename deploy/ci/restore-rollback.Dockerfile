FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl openssl python3 util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/nivus-compose/current/deploy /usr/local/sbin
COPY deploy/backup.sh /opt/nivus-compose/current/deploy/backup.sh
COPY deploy/restore.sh /opt/nivus-compose/current/deploy/restore.sh
COPY deploy/test-restore-rollback.sh /opt/nivus-compose/current/deploy/test-restore-rollback.sh
COPY deploy/test-restore-rollback-sandbox.sh /usr/local/sbin/nivus-test-restore-rollback-sandbox

RUN chmod 0755 /opt/nivus-compose/current/deploy/*.sh /usr/local/sbin/nivus-test-restore-rollback-sandbox

ENTRYPOINT ["/usr/local/sbin/nivus-test-restore-rollback-sandbox"]
