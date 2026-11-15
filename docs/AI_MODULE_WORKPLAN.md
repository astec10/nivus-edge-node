# Plano de trabalho paralelo por módulos

Este plano trata do **desenvolvimento do repositório**. Não é o scheduler do produto Nivus e não envia telemetria para um Nó Master.

## Modelo de montagem

```text
Pessoa responsável descreve objetivo e aceite
  -> integrador divide a entrega e registra contratos/dependências
  -> agentes constroem peças em branches/worktrees isolados
  -> CI valida cada peça
  -> integrador monta o conjunto e resolve incompatibilidades
  -> PR integrado -> revisão humana -> merge
```

Cada agente recebe uma tarefa pequena com objetivo, caminhos próprios, dependências, contrato de entrada/saída, critérios de aceite, risco, dados permitidos e limite de recursos. Conversas e arquivos de um agente não são memória compartilhada: a Issue, a documentação versionada e o PR são o handoff comum.

## Pacotes de trabalho e dependências

| Peça | Pode trabalhar em paralelo? | Contrato/dependência | Integração e aceite |
| --- | --- | --- | --- |
| Biblioteca de conhecimento: fontes, notas por tema e índice lexical | Sim, por tema ou fonte | Proveniência, licença e rótulos de verificação definidos em `AI_WORKFLOW.md` | Integrador confere URLs, evidência, duplicatas e índice reproduzível. |
| Adaptador de sensor de hardware | Sim, por família/driver, depois do envelope de amostra | Fonte e unidade explícitas; indisponível = `null`; sem mudar schema compartilhado sem tarefa separada | Fixture sintética e validação da origem do sensor. A telemetria não bloqueia o executor nem os demais módulos. |
| Componentes da dashboard | Sim, por componente, após contrato da API | Payload/API congelado e caminhos de frontend exclusivos | Build e verificação de estados de carregamento, erro e vazio. |
| Router/API de um domínio | Parcialmente | Autorização, schema e persistência acordados antes de workers paralelos | Integrador confere política de acesso, migração e compatibilidade do endpoint. |
| Cadastro e Nó Master | Não antes de definir identidade e contratos de heartbeat | Depende de identidade/revogação e envelope versionado; telemetria agregada começa quando o Master estiver operacional | Integração sequencial com validação de nó autorizado, duplicatas, atraso e nó offline. |
| Controlador do executor no notebook | Separado do runtime Nivus | Fila do GitHub durável; autorização explícita; Actions hospedadas para executar código | Primeiro apenas despacha e acompanha workflows; não tem shell remoto no notebook nem acesso ao banco de telemetria. |
| Worker de código e integração multi-modelo | Após host, modelo e orçamento aprovados | Checkout efêmero, escopos mínimos, caminhos permitidos, limite por tentativa e contrato de artefatos | Abre PR; CI e revisão humana integram o resultado. Não faz merge ou deploy de produção. |

## Contratos compartilhados: serializar antes de paralelizar

Um integrador deve ser o único responsável por decidir mudanças simultâneas em `backend/api/schemas.py`, `backend/database.py`, autorização, envelopes MQTT, `docker-compose.yml` e instalação. Se várias peças dependem de um contrato novo, defina-o primeiro num PR pequeno; depois distribua as implementações paralelas contra esse contrato. Isso evita que cada agente invente uma interface incompatível.

## Responsabilidade do integrador

1. Verificar a árvore de módulos e escolher peças com pouca sobreposição de arquivos.
2. Criar Issues vinculadas, preencher caminhos permitidos e explicitar dependências.
3. Limitar simultaneidade de acordo com limites de modelo e recursos; não abrir várias contas para contornar quotas.
4. Reunir as peças em branch de integração, comparar schemas/rotas/configuração e pedir correção com comentários vinculados à tarefa.
5. Rodar CI para a combinação completa, não apenas confiar nos resultados isolados.
6. Abrir ou atualizar um PR para revisão humana; merge e produção permanecem decisão humana.

## Estado atual do executor

O repositório tem intake por GitHub Issue, validação de escopo e workflow manual que marca `ai:queued`. **Não** há ainda um dispatcher instalado no notebook, chamada a modelo, worker de código, criação automática de PR ou integração com Discord/Jira/Hermes/OmniRoute. A telemetria local do CCE e o futuro Nó Master são independentes desse fluxo.

O notebook pode hospedar um controlador leve por systemd; o processamento e sandbox de código ficam em runners GitHub-hosted descartáveis. Tarefas e resultados no GitHub sobrevivem a uma interrupção do notebook. Ver [`AI_EXECUTOR_IMPLEMENTATION.md`](AI_EXECUTOR_IMPLEMENTATION.md) e [`AI_DEVELOPMENT_ORCHESTRATION.md`](AI_DEVELOPMENT_ORCHESTRATION.md).

