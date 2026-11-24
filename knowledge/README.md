# Biblioteca de conhecimento do Nivus

Este diretório contém fontes e conhecimento técnico curado, compartilhável pelo GitHub e preparado para ingestão pela biblioteca Nivus futura.

- catalog/: registros de fontes e estado de verificação, um JSON por linha.
- topics/: notas atômicas próprias, organizadas por tema, com fontes e limites.
- index/: arquivos derivados gerados por tools/build_ai_context.py; não edite manualmente.

O conteúdo versionado é a fonte para qualquer IA e para futuras instalações. A biblioteca no produto, sincronização entre nós, ACLs e consulta no dashboard ainda não estão implementadas. Não guarde dados domésticos privados, segredos nem cópias integrais de obras protegidas aqui.

Os campos search_terms são palavras normalizadas para pesquisa lexical. Não representam IDs de tokenizer de um modelo. Isso permite que ferramentas e modelos diferentes usem o mesmo catálogo sem dependência de fornecedor.

## Biblioteca documental local (planejada)

O desenho de ingestão incremental da Fase 4 está em [docs/LOCAL_KNOWLEDGE_INGESTION.md](../docs/LOCAL_KNOWLEDGE_INGESTION.md). Ele separa documentos privados em NIVUS_DATA do catálogo público versionado neste repositório, define proveniência e licenças, hash, quarentena, extração limitada, trechos com citações e atualização explícita.

Este link é documentação de arquitetura. A biblioteca local e a busca nela ainda não estão implementadas. Para a sequência de fases e dependências, consulte [docs/PROJECT_ROADMAP.md](../docs/PROJECT_ROADMAP.md), [docs/MODULE_MAP.md](../docs/MODULE_MAP.md) e [docs/AI_WORKFLOW.md](../docs/AI_WORKFLOW.md).
