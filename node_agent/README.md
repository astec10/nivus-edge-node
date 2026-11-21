# Agente de identidade de nós Nivus

Este agente conecta um Ubuntu Server ao Nó Master para cadastrar a identidade do dispositivo, enviar heartbeats e, na candidata de telemetria multi-nó, enviar um envelope HTTPS com uso de CPU, memória e disco. A coleta usa `/proc` e a biblioteca padrão do Python; a primeira leitura de CPU é marcada indisponível porque ainda não há intervalo para calcular o uso. Não lê temperatura/bateria, não executa comandos, não usa MQTT, não transfere arquivos e não atualiza o sistema.

## Requisitos

- Python 3.10 ou superior.
- URL HTTPS do Nó Master com certificado confiável.
- Código de pareamento de uso único gerado por um administrador autenticado. O código expira em 10 minutos.
- Usuário Linux sem privilégios de root.

## Parear um nó

A partir da raiz do repositório, execute:

    python3 -m node_agent.agent pair --master-url https://HOST-DO-MASTER --name "Edge Sala"

O agente solicitará o código de pareamento em uma entrada oculta. O código não é aceito por argumento de linha de comando. Para uma autoridade certificadora privada, informe o caminho para o certificado público confiável:

    python3 -m node_agent.agent pair --master-url https://HOST-DO-MASTER --name "Edge Sala" --ca-file /caminho/ca-master.crt

O agente grava a credencial retornada pelo servidor em ~/.config/nivus-node-agent/credentials.json, com pasta 0700 e arquivo 0600. O arquivo contém a credencial bearer necessária ao agente; mantenha backups protegidos e nunca o copie para o GitHub ou envie em mensagens. Sessões não são persistidas e são renovadas no início do processo. O mesmo token deve ser usado por somente um agente ativo.

## Executar

    python3 -m node_agent.agent run

Na candidata local de telemetria, o processo envia heartbeat no intervalo configurado (30 segundos por padrão; 5 a 600 segundos). Quando `/proc` está disponível, coleta e envia telemetria no máximo a cada 30 segundos, mesmo que os heartbeats sejam mais frequentes. Heartbeat e amostra usam a mesma sequência crescente do nó. O servidor impõe o mesmo intervalo mínimo por nó e responde `429` com `Retry-After`; o agente respeita esse cabeçalho. Se uma resposta de telemetria se perder, o agente repete o mesmo envelope e sequência; o servidor deduplica uma repetição idêntica. Falhas transitórias usam espera exponencial limitada; uma revogação encerra o agente. Para encerrá-lo, pressione Ctrl+C.

O agente envia apenas métricas declaradas na allowlist: `cpu.utilization`, `memory.utilization` e `disk.utilization`, em porcentagem. O horário `observed_at` usa UTC do host; a API registra separadamente o horário de recebimento do servidor e informa o desvio. Uso de memória sem `MemAvailable` é marcado como estimado; fontes ausentes ou inválidas ficam com qualidade `unavailable` e valor nulo.

Para executar como serviço permanente, use deploy/nivus-node-agent.service.example como base. Instale o agente e credenciais para uma conta de serviço sem login interativo; não execute o unit como root. Depois de parear, o administrador pode revogar o nó no painel. Revogação exige novo código de pareamento para voltar a conectar.

## Confiança e privacidade

- HTTP sem TLS é recusado; validação de certificado permanece ativa.
- Redirecionamentos HTTP não são seguidos, evitando encaminhar o token a outro host.
- A API do servidor atribui a identidade; IP, hostname e nome amigável não autenticam o dispositivo.
- O token não é impresso, registrado nem enviado em argumentos de processo.
- Heartbeats e envelopes usam sequência crescente e sessão renovada; falha de rede não apaga a identidade nem converte uma amostra repetida em uma nova leitura.
- O token local é protegido por permissões POSIX, não por criptografia. Use criptografia de disco/backup do sistema para proteger o host.
- O servidor persiste apenas o hash SHA-256 do token. Perda do arquivo local requer revogação e novo pareamento.

## Validação de desenvolvimento

Na raiz do repositório, os testes de backend incluem clientes isolados contra um adaptador da API temporária apoiado pelo SQLite descartável. Eles verificam contrato, qualidade, valores inválidos, sequência, repetição idempotente, perda de resposta e retenção:

    python3 -m unittest discover -s backend -p 'test_*.py'

O smoke com dois equipamentos físicos continua pendente e não é substituído pela CI hospedada.
