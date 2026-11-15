# Adaptador Gemini para o executor do Nivus

Este módulo é parte da infraestrutura de desenvolvimento do repositório. Ele usa a API Gemini para produzir uma **proposta estruturada** de alteração; não é uma rota da API FastAPI do produto Nivus.

## Papel do supervisor

O agente integrador/supervisor define uma tarefa pequena, confere os critérios de aceite e fornece uma lista exata de caminhos permitidos. O Gemini contribui com uma proposta de conteúdo de arquivos. O supervisor valida escopo, contratos compartilhados, diff e CI antes de abrir um PR para revisão humana.

O adaptador não lê Issues, não faz checkout, não escreve no disco, não executa comandos e não cria PRs. A chave não deve ser colocada no prompt, no código ou no repositório. A integração futura deve fornecê-la como segredo `GEMINI_API_KEY` no ambiente efêmero do runner.

## Modelo e API

- Modelo revisado e fixo: `gemini-3.8-flash`. Este primeiro executor não aceita roteamento para outros modelos.
- API: Gemini Interactions (`/v1beta/interactions`), com resposta JSON estruturada.
- Dependências: biblioteca padrão do Python; sem SDK adicional.
- Orçamento local da chamada: 75 segundos e até 6144 tokens de saída, pensamento baixo. O código não faz repetição automática em `429`, timeout ou erro do provedor.
- `store: false`; prompts, resposta e chave não são gravados pelo adaptador nem incluídos em mensagens de erro.
- A chamada exige `NIVUS_AI_BUDGET_MODE=free-tier` como confirmação explícita do mantenedor. Essa variável não verifica nem limita a cobrança do projeto Google. Use uma chave de um projeto separado sem faturamento vinculado; o código não consegue impedir cobrança se a chave pertencer a um projeto com faturamento.

O plano gratuito atual permite uso limitado de alguns modelos; quotas podem mudar e não garantem que a fila seja atendida continuamente. Na modalidade gratuita, o Google informa que o conteúdo pode ser usado para melhorar seus produtos. Portanto, envie somente código público e contexto sanitizado; nunca envie secrets, banco SQLite, telemetria real, dados domésticos ou informação pessoal. Para material privado, use modalidade/termos adequados ou um provedor aprovado pelo mantenedor.

## Contrato de proposta

O chamador fornece título, descrição, critérios de aceite, contexto sanitizado e allowlist de caminhos exatos. A resposta contém resumo e mudanças `create`/`update`, com conteúdo UTF-8 completo. O adaptador recusa caminhos fora da lista, caminhos sensíveis, payloads excessivos e padrões comuns de credenciais. Essas verificações são uma barreira adicional, não substituem a validação de Issue, revisão de segurança ou CI.

Exemplo de integração, sem fazer uma chamada real:

```python
from tools.ai_executor.gemini_client import GeminiClient

client = GeminiClient()  # Lê GEMINI_API_KEY do ambiente.
proposal = client.propose_changes(
    task_title="Documentar a API do módulo",
    task_description="Adicionar documentação dentro do escopo aprovado.",
    acceptance_criteria=["Documentação em português", "Sem segredos ou dados reais"],
    allowed_paths=["docs/module-example.md"],
    repository_context="Trechos públicos e sanitizados do contrato do módulo.",
)
print(proposal.usage_report.to_dict())  # Metadados sem prompt, resposta ou chave.
```

O workflow `AI task intake` pode apenas enfileirar a Issue ou, após a confirmação explícita do mantenedor, disparar uma única proposta. O worker valida contrato/labels, aplica o limite de tempo solicitado (1–15 minutos), compara o estado dos arquivos e aplica conteúdo somente aos caminhos autorizados; a CI roda em outro runner sem a chave Gemini. Mesmo com a CI aprovada, a revisão e o merge para `main` permanecem humanos.

Para habilitar o uso depois que a revisão for integrada: crie um projeto Google separado, não vincule faturamento e gere uma chave para a Gemini API. Guarde-a como `GEMINI_API_KEY` em **Settings → Secrets and variables → Actions → Secrets**; crie a variável `NIVUS_AI_BUDGET_MODE=free-tier` em **Variables** somente depois de conferir o projeto. Não envie a chave no chat, Issue ou repositório. A configuração é uma confirmação do operador, não um limitador de custo. O executor cria um artifact por tentativa, retido por 30 dias, com modelo, tokens/duração/status e sem conteúdo do prompt.

