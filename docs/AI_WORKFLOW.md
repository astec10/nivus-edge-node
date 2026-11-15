# Conhecimento compartilhado e trabalho com IA

## Fonte comum

O GitHub é a fonte versionada das decisões do Nivus e do conhecimento técnico curado para o projeto. Organize material duradouro por tema em `docs/` e `knowledge/topics/`; os registros das fontes ficam em `knowledge/catalog/`. Assim, qualquer IA que leia o repositório recebe os mesmos resumos, metadados e limites, sem depender da memória de uma conversa ou de um fornecedor.

O produto ainda não implementa a biblioteca compartilhada entre nós. O catálogo e os resumos deste repositório são conteúdo curado para essa biblioteca futura, não uma funcionalidade já disponível na dashboard.

## Fluxo de ingestão

1. Registrar uma fonte com URL, autor/canal quando conhecido, data de consulta, tema e licença/condições de uso.
2. Extrair apenas o que está acessível. Quando houver legenda, guardar localmente apenas se permitido; não publicar transcrição integral protegida.
3. Atomizar em conceitos independentes: uma nota curta por mecanismo, afirmação ou decisão.
4. Rotular cada afirmação como `observed`, `primary-docs-verified`, `secondary-source`, `user-provided` ou `needs-transcript`.
5. Preservar timestamp de vídeo, página/seção de documento, versão, proveniência e limites.
6. Normalizar termos para busca, gerar o índice lexical e revisar o diff. Índice e notas derivados devem ser reproduzíveis a partir das fontes versionadas.
7. Atualizar a nota se uma fonte corrigir ou contradizer a afirmação; não conservar versões incompatíveis sem explicar a diferença.

## Termos de busca e tokens

`tools/build_ai_context.py` normaliza texto com Unicode NFKC e caixa baixa, preserva identificadores úteis e cria `knowledge/index/records.jsonl` e `knowledge/index/terms.json`. Esses são termos lexicais independentes de modelo, não IDs de token de BPE/SentencePiece. Um tokenizer de modelo muda conforme o modelo e a versão; nenhum modelo específico é requisito para consultar o índice.

Na raiz do repositório:

```bash
python3 tools/build_ai_context.py
python3 tools/build_ai_context.py --query "hermes gateway discord jira"
```

`records.jsonl` contém um registro por nota/fonte e a lista de termos normalizados. `terms.json` mapeia cada termo para IDs de registros. Não adicione embeddings ou banco vetorial até que uma avaliação de busca mostre benefício mensurável.

## Privacidade, licenças e uso compartilhado

- Versione somente informação que possa ser pública e útil a todos os contribuidores.
- Não versione senhas, tokens, arquivos de configuração privada, métricas de uma casa, imagens, placas, rostos, logs de produção ou banco real.
- Para vídeos e livros, prefira notas e resumos próprios com timestamps/citações de origem. Não copie a legenda ou o livro completo sem autorização/licença compatível.
- Uma fonte de terceiro não vira documentação oficial do Nivus. Registre separadamente fato, alegação promocional, teste local e inferência.
- A biblioteca compartilhada futura deve aplicar identidade, ACL, versão de esquema e proveniência antes de sincronizar dados entre nós.

## Duas formas distintas de paralelismo

- **Desenvolvimento:** agente externo recebe tarefa, trabalha em sandbox/branch, abre PR, passa CI e espera revisão humana.
- **Runtime do Nivus:** scheduler futuro distribui tarefas de dados/IA entre nós autenticados conforme capacidade, quota, lease, prazo e política de segurança.

Um roteador de modelos não é uma fila de tarefas; compartilhar arquivos/GPU pela rede não combina automaticamente RAM/VRAM. Veja [`AI_DEVELOPMENT_ORCHESTRATION.md`](AI_DEVELOPMENT_ORCHESTRATION.md) e a Fase 5 do [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md).

O executor de desenvolvimento por GitHub Issues está documentado em [`AI_EXECUTOR_IMPLEMENTATION.md`](AI_EXECUTOR_IMPLEMENTATION.md). O branch de revisão já contém intake, adaptador Gemini e worker que prepara PR em rascunho após autorização `ai:ready`; ainda faltam configuração da chave, validação end-to-end e integração no `main`.
