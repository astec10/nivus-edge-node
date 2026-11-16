# Apoio do notebook aos executores

O notebook CCE pode atuar como um runner auxiliar de validação no Ubuntu real. Ele não é o executor do modelo nem substitui a CI hospedada pelo GitHub: proposta de IA e validação de pull requests continuam em runners hospedados. A validação local é manual e posterior ao merge, para conferir o código confiável da branch padrão no hardware Ubuntu disponível.

## Limite de segurança

O repositório Nivus é público. O GitHub alerta que runners self-hosted em repositórios públicos podem ser comprometidos por workflows que executem código não confiável. Por isso, este runner:

- aceita apenas o workflow manual Notebook support, iniciado por astec10 na branch padrão;
- nunca é selecionado pelos workflows de pull request, fork ou pelo executor de IA;
- faz checkout somente da branch padrão, sem opção para informar branch, commit, issue ou comando;
- não recebe segredos, permissão de escrita, acesso ao Docker, à instalação Nivus, banco, diretórios pessoais ou serviços Compose;
- roda como usuário de sistema separado, com isolamento de filesystem pelo systemd;
- executa testes Python e build/lint do frontend; não instala nem atualiza o Nivus.

Esse recorte reduz a superfície, mas não elimina o risco residual de código ou dependências aprovados e incorporados à branch padrão. A conta ainda tem acesso de rede de saída à Internet e à LAN; ela não deve receber acesso a serviços ou credenciais domésticas. Se esse risco residual não for aceitável, não registre o runner. A instalação é opcional. Se o runner deixar de ser necessário, remova-o com remove-runner.sh.

## Instalação

1. Abra astec10/nivus-edge-node no GitHub e vá a **Settings → Actions → Runners → New self-hosted runner**.
2. Selecione **Linux** e **x64**. Deixe essa tela aberta; não gere o token ainda.
3. Depois que esta alteração estiver integrada, no notebook baixe o script deste repositório e rode-o com sudo:

       curl --fail --location --output /tmp/nivus-install-runner.sh https://raw.githubusercontent.com/astec10/nivus-edge-node/main/deploy/notebook-support/install-runner.sh
       sudo bash /tmp/nivus-install-runner.sh

4. Quando o script pedir, gere o token de registro na tela do GitHub e cole-o somente no prompt oculto do terminal. O token expira em uma hora. Não o envie no chat, Issue ou arquivo.
5. O script verifica a impressão SHA-256 do pacote oficial, instala dependências necessárias, cria o usuário nivus-support e o serviço systemd. Ele não adiciona a conta ao grupo Docker nem altera os serviços, dados ou dashboard do Nivus.
6. Confira Settings → Actions → Runners: o runner nivus-notebook-support deve aparecer como **Idle**.

A instalação usa aproximadamente 230 MB para baixar o pacote do runner, além de espaço para ferramentas e workspaces dos jobs. O limite systemd de memória do serviço é 2 GiB; o runner pode usar os dois núcleos. O notebook precisa estar ligado e conectado à Internet para receber um job. Se estiver desligado, os runners hospedados e a fila do executor continuam funcionando.

## Executar uma validação no notebook

1. No GitHub, abra **Actions → Notebook support → Run workflow**.
2. Mantenha a branch padrão selecionada e inicie o workflow.
3. Acompanhe logs, revisão de sintaxe Python/Bash, testes unitários e build do frontend no GitHub Actions.

O workflow não bloqueia PR nem deploy e não roda automaticamente. Ele valida apenas o commit atual da branch padrão; não substitui a validação pré-merge, teste de instalação/rollback, medições térmicas ou certificação Intel/AMD. O runner não recebe segredos nem dados de telemetria.

## Remoção

No GitHub, abra **Settings → Actions → Runners → nivus-notebook-support → Remove** para obter um token temporário. No notebook:

       curl --fail --location --output /tmp/nivus-remove-runner.sh https://raw.githubusercontent.com/astec10/nivus-edge-node/main/deploy/notebook-support/remove-runner.sh
       sudo bash /tmp/nivus-remove-runner.sh

Digite a frase solicitada e cole o token somente no prompt oculto. A remoção desregistra o runner e apaga apenas sua instalação e workspace; não altera o Nivus, seu banco ou seus backups.
