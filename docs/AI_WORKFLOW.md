# Fluxo de trabalho para preservar contexto de IA

Este processo reduz mudanças fora de escopo e evita que uma sessão trate planos antigos como código existente. Ele vale para Codex, outras IAs e contribuições humanas assistidas por IA.

## 1. Abrir a tarefa com o estado atual

1. Confira branch, diretório de trabalho e alterações locais antes de editar.
2. Leia README.md, AGENTS.md, docs/AI_CONTEXT.md e docs/PROJECT_STATUS.md.
3. Para mudança estrutural, leia MODULE_MAP.md, ARCHITECTURE.md, DECISIONS.md e PROJECT_ROADMAP.md.
4. Para operação, instalação ou dados, leia também deploy/README.md e VM_VALIDATION.md.
5. Verifique o branch, PR e código atuais. Um resumo de outra sessão, vídeo, issue ou skill é contexto; não é prova de implementação nem autorização para executar.

## 2. Transformar a ideia em tarefa verificável

Registre em poucas linhas:
- objetivo observável e comportamento esperado;
- módulo dono e dependências;
- arquivos/contratos que podem mudar;
- critérios de aceite;
- como validar com dados descartáveis;
- risco, rollback e o que fica fora de escopo.

Escolha um módulo por PR sempre que possível. Mudanças paralelas precisam de fronteiras e contratos definidos antes do trabalho. Não faça alterações simultâneas em arquivos compartilhados sem combinar a ordem de integração.

## 3. Implementar e verificar

1. Inspecione o código que executa hoje; não recrie uma função já existente.
2. Faça uma alteração pequena e compatível. Se precisar quebrar um contrato, inclua migração, documentação e caminho de volta.
3. Não adicione pacotes, serviços, contas ou permissões sem necessidade documentada.
4. Execute verificações pertinentes à mudança em ambiente isolado. Não use banco, segredo ou serviço do notebook ativo como fixture.
5. Registre o comando, o resultado e o alcance real da verificação. Smoke, CI virtual e benchmark físico são evidências diferentes.
6. Atualize PROJECT_STATUS.md, DECISIONS.md e PROJECT_ROADMAP.md somente quando o status, uma decisão ou um critério tiver mudado.
7. Revise diff, licenças e arquivos ignorados antes do PR.

## 4. Cache técnico local, opcional

A consulta frequente de linguagem, bibliotecas e técnicas pode ser acelerada com notas atomizadas, mas a cache deve continuar separada do código público e dos dados do produto.

- Diretório reservado: temp/knowledge/notes/ para notas; índices e pacotes podem ficar em temp/knowledge/ e temp/.
- O padrão do repositório ignora /temp/. Confirme com Git antes de copiar dados para esse local.
- Uma nota deve cobrir um conceito e registrar título, resumo curto, fonte primária, versão ou data de consulta, data da revisão, tags e limitações conhecidas.
- Prefira documentação oficial e repositórios upstream; guarde um trecho curto ou resumo próprio e a URL, não uma cópia extensa de livro ou documentação.
- Atualize ou remova notas obsoletas quando APIs, versões ou avisos mudarem.
- A busca prevista é lexical sobre termos normalizados. “Tokenizado” neste contexto não significa usar o tokenizador interno de cada LLM nem transforma texto em conhecimento automaticamente.
- Nunca armazene chaves, senhas, tokens, arquivos .env, bases SQLite reais, logs, endereços domésticos, rostos, placas ou dados de sensores privados.
- Não envie temp/knowledge, índice ou pacote de contexto ao GitHub. Se uma decisão for duradoura, resuma-a em docs/DECISIONS.md; se for fato operacional, atualize PROJECT_STATUS.md.
- Este branch não fornece um gerador executável de cache. Não indique tools/build_ai_context.py como arquivo disponível nem afirme que o índice foi produzido por este repositório.

## 5. Passagem entre sessões

Ao encerrar ou transferir uma tarefa, deixe uma passagem curta com:
1. objetivo e branch/PR;
2. arquivos alterados e motivo;
3. verificações realmente executadas e seus resultados;
4. estado: feito, em revisão, staging, instalado ou pendente;
5. riscos, rollback e próxima ação;
6. informação que precisa ser confirmada pelo operador.

Não use “concluído” para código que só está planejado, compila localmente ou passou apenas numa VM de CI.