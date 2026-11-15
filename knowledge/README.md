# Biblioteca de conhecimento do Nivus

Este diretório contém fontes e conhecimento técnico curado, compartilhável pelo GitHub e preparado para ingestão pela biblioteca Nivus futura.

- `catalog/`: registros de fontes e estado de verificação, um JSON por linha.
- `topics/`: notas atômicas próprias, organizadas por tema, com fontes e limites.
- `index/`: arquivos derivados gerados por `tools/build_ai_context.py`; não edite manualmente.

O conteúdo versionado é a fonte para qualquer IA e para futuras instalações. A biblioteca no produto, sincronização entre nós, ACLs e consulta no dashboard ainda não estão implementadas. Não guarde dados domésticos privados, segredos nem cópias integrais de obras protegidas aqui.

Os campos `search_terms` são palavras normalizadas para pesquisa lexical. Não representam IDs de tokenizer de um modelo. Isso permite que ferramentas e modelos diferentes usem o mesmo catálogo sem dependência de fornecedor.

