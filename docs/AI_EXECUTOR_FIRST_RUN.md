# Executor de Desenvolvimento Nivus (Início Rápido)

Esta nota resume o propósito e os limites do executor opcional de desenvolvimento com IA do projeto Nivus.

## Propósito e Funcionamento

- O executor trata tarefas delimitadas e issues específicas do repositório público.
- Ele opera em sandbox com escopo estrito e caminhos pré-autorizados.
- Ao concluir o processamento, o executor não aplica alterações diretamente no branch principal; ele propõe as mudanças exclusivamente por meio de um draft pull request (PR).

## Limites e Governança

- **Validação contínua:** O pipeline de CI executa verificações automatizadas (testes, builds e checagens estáticas) sobre a proposta submetida no PR.
- **Revisão humana obrigatória:** Nenhuma alteração é mesclada (`merge`) ou enviada para produção/deploy sem inspeção, aprovação explícita e intervenção de um revisor humano.
- **Segurança e privacidade:** O executor não possui acesso a credenciais, dados privados ou telemetria doméstica real. Apenas dados sintéticos e código público são processados.
