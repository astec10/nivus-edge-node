# Validação em runner remoto, sem VM local

O operador decidiu não usar VirtualBox, Hyper-V ou outras VMs no computador pessoal. A validação de instalação e recuperação deve ocorrer em runners Linux descartáveis hospedados pelo GitHub Actions, sem iniciar VMs no Windows do operador e sem alterar o notebook ativo.

## Fluxo automatizado

O workflow [`ubuntu-ci.yml`](../.github/workflows/ubuntu-ci.yml) executa a validação em Ubuntu amd64 hospedado pelo GitHub. O run `43662375766` passou o smoke Compose e o fluxo de instalação, backup, health-check, rollback induzido e restauração normal. Esse registro é evidência para aquele commit; mudanças posteriores só ficam cobertas depois de uma nova execução verde.

Ao abrir um pull request ou enviar uma alteração para `main`:

1. Confira o resultado de todos os jobs do workflow.
2. Para um job com falha, preserve o log sanitizado e reproduza a falha num runner descartável.
3. Não copie banco, `.env`, tokens, certificados, chaves ou telemetria do notebook para artefatos de CI.
4. Confirme que health HTTPS responde, a API exige autenticação, SQLite passa `quick_check` e a ingestão MQTT aumenta a telemetria.
5. O teste de recuperação deve criar seu próprio estado descartável e demonstrar tanto o rollback forçado quanto o restore normal.

## Testes que não devem rodar no notebook ativo

`deploy/test-restore-rollback.sh` injeta falha para verificar a recuperação. Não rode esse script no notebook de teste nem em qualquer máquina com dados importantes. A rotina deve ser executada somente dentro do workflow remoto que cria um ambiente descartável para cada execução. O notebook permanece disponível para telemetria real e validações de leitura.

## Limites

Runner hospedado valida software e integração com hardware virtualizado. Não certifica sensores, firmware, desempenho ou estabilidade de cada computador. Para anunciar compatibilidade ampla, registre testes físicos em plataformas Intel e AMD de diferentes gerações, sem repetir uma matriz física inteira a cada commit.

Para instalações limpas, o painel tenta usar HTTPS na porta 443 e assim abre em `https://IP/`. Se outro serviço já ocupa 443, o instalador mantém esse serviço e seleciona uma porta alternativa. A instalação paralela atual ainda exige promoção Nginx para colocar a dashboard candidata no endereço sem sufixo de porta.
