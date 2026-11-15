# Validação reproduzível de instalação e recuperação

Use runners Ubuntu descartáveis para repetir a validação funcional em cada mudança de software. Não execute instalação, restore ou rollback na instalação ativa do notebook.

## Evidência mais recente

O workflow Ubuntu VM validation passou no run 43662375766, associado ao commit ba242268786c838626c6f76907e6e64eba158d94, em Ubuntu 22.04 amd64. Os jobs de instalação/backup/rollback e de smoke Compose concluíram com sucesso. Ele executou build e smoke Compose, instalação limpa, coleta MQTT para SQLite, backup consistente, validação somente leitura, rollback por falha de health, restauração normal, health HTTPS 200, API 401 sem token, quick_check e retomada da telemetria.

A CI fornece um ambiente virtual efêmero, com execução reproduzível e sem exigir que o operador monte uma VM local para cada computador. O resultado não testa BIOS, rede física, controladores de disco, sensores ou desempenho sustentado de cada modelo.

O operador decidiu não usar a VM local instável. Nenhum nome de VM, endereço, impressão digital SSH ou chave temporária é necessário para reproduzir os testes; esses dados ficam fora da documentação pública.

## Rodar a validação automatizada

1. Abra um pull request para o repositório Nivus ou atualize uma branch já aberta.
2. Aguarde o workflow Ubuntu VM validation terminar; revise os dois jobs e os logs em caso de falha.
3. Confirme a execução MQTT→SQLite e a integridade do banco temporário.
4. No job de recuperação, confirme backup, modo de verificação, falha de health induzida, recuperação dos dados e restauração normal.
5. Registre o número do run, Ubuntu, arquitetura, conclusão de cada job e limites do runner em PROJECT_STATUS.md.

O job instala a candidata somente no runner descartável. Ele não conecta ao notebook, não usa o banco da casa e não aplica alterações a hosts externos.

## Teste manual opcional em laboratório separado

Se uma pessoa contribuinte precisar depurar um comportamento que a CI não reproduz, use uma VM descartável própria com Ubuntu Server 22.04 ou posterior, arquitetura amd64, systemd, snapshot inicial e acesso de rede limitado. Uma configuração inicial de 2 vCPUs, 4 GB de RAM e 30 GB de disco é apenas um perfil de ensaio, não requisito mínimo certificado.

- Clone a branch em teste para a VM descartável; crie credenciais somente para ela.
- Registre versão Ubuntu, CPU/RAM/disco, Docker/Compose e portas livres.
- Siga deploy/README.md para instalar e confirmar health, autenticação e coleta.
- Crie um backup e rode restore.sh --check antes de qualquer restauração.
- Para o teste destrutivo de rollback, use test-restore-rollback.sh somente nessa VM, leia as confirmações e preserve o backup de segurança.
- Reinicie a VM somente depois de salvar um snapshot; confirme os serviços e a telemetria antes de aceitar o resultado.
- Descarte a VM e suas credenciais ao terminar; não as reutilize em produção.

Esse laboratório manual é opcional e não altera a escolha de usar runners descartáveis para a CI de rotina.

## Limites do restore

O procedimento atual restaura SQLite no mesmo host e preserva os segredos ativos. Ele não reconstrói um host perdido, não migra certificados/chaves e não é uma cópia externa contra falha do disco. O arquivo .env faz parte do backup de configuração e deve ser tratado como sensível, mesmo quando os segredos JWT/MQTT estão em arquivos separados.

Só declare uma instalação portátil pronta quando instruções reproduzíveis, persistência, recuperação e limites de hardware estiverem documentados com evidência proporcional. Um runner virtual não prova compatibilidade universal com x86_64.

