---
id: ref-multipaz-developer-website
title: Multipaz Developer Website retrieval pattern
topic: local-knowledge
source: https://github.com/openwallet-foundation/multipaz-developer-website
verified_on: 2026-11-15
confidence: verified-primary-source
tags: documentation, BM25, retrieval, token budget, Docusaurus, local-first
---
# Multipaz Developer Website: padrão de busca documental

## O que foi verificado

Este repositório mantém um site Docusaurus para documentação do Multipaz e um widget "Ask AI". A interface chama uma API Node.js; a chave do provedor fica no servidor e não no navegador. O README descreve o fluxo com Gemini e Vercel.

## Fluxo de conhecimento

- Um script de build agrega Markdown local e arquivos selecionados do repositório principal do Multipaz, acrescentando caminhos de origem e links para citação.
- O contexto é separado por arquivos e por títulos Markdown. O divisor evita cortar blocos de código, limita o tamanho dos trechos e usa uma busca lexical BM25 para selecionar passagens relacionadas à pergunta.
- A busca mantém uma pequena visão geral fixa e limita o total de trechos por orçamento de caracteres; o histórico enviado ao modelo também tem limites de turnos e tamanho.
- O servidor transmite a resposta por SSE e limita chamadas por IP e por dia. Upstash Redis compartilha os contadores entre instâncias quando configurado; sem ele, os limites são apenas em memória por instância.

## Observações e limites

- O README principal não está totalmente sincronizado com a implementação: seu diagrama descreve o corpus inteiro no prompt e menciona Gemini 2.5 Flash; o README da API e o código usam recuperação BM25 e permitem configurar o modelo. Trate os arquivos de implementação como evidência do comportamento atual.
- O build busca documentos do branch remoto main. Na revisão, o upstream estava no commit 8efb1ec9eff6c79af2193be18e2b3dba67e9c64f. Isso facilita atualização, mas o resultado depende da rede e pode mudar sem alteração neste site. Para o Nivus, fontes externas devem ser fixadas por commit/hash e importadas em build explícito; a consulta em runtime deve continuar local.
- A API é pública e sem autenticação de usuário. Há limites de taxa e quota diária, mas o fallback em memória não é uma quota global. O parser de corpo HTTP não impõe um limite de bytes antes de acumular e interpretar o JSON; um serviço público precisaria de proteções adicionais.
- A busca em inglês usa tokenização simples e BM25 lexical. Para a biblioteca Nivus, isso é uma referência de método; português, sinônimos técnicos, ranking por título/tags, proveniência e permissões precisam de critérios próprios.
- Não foi encontrado arquivo LICENSE no repositório nem licença declarada nos metadados consultados. Reutilizar a ideia geral é diferente de copiar código; não copiar arquivos até a licença ser esclarecida.

## Aplicação recomendada ao Nivus

A biblioteca compartilhada pode usar arquivos de conhecimento com metadados de tema, origem, licença, data de verificação e confiança; quebrar documentos em unidades curtas por seção; gerar um índice lexical versionado; e entregar ao modelo somente os trechos relevantes dentro de um orçamento de tokens, preservando caminhos e citações. BM25 é uma alternativa leve para melhorar o ranking do índice lexical atual sem exigir banco vetorial ou GPU. Primeiro medir a busca em português com perguntas reais/sintéticas; depois decidir se embeddings acrescentam valor. O índice deve ser gerado offline, ter saída reprodutível e poder ser reconstruído a partir das fontes.

## Fontes primárias

- Repositório e README: https://github.com/openwallet-foundation/multipaz-developer-website
- Construtor do contexto: https://github.com/openwallet-foundation/multipaz-developer-website/blob/8efb1ec9eff6c79af2193be18e2b3dba67e9c64f/api/build-docs-context.js
- Busca BM25: https://github.com/openwallet-foundation/multipaz-developer-website/blob/8efb1ec9eff6c79af2193be18e2b3dba67e9c64f/api/docs-retrieval.js
- Montagem de prompt e limites de histórico: https://github.com/openwallet-foundation/multipaz-developer-website/blob/8efb1ec9eff6c79af2193be18e2b3dba67e9c64f/api/chat-request.js
- Limites de API: https://github.com/openwallet-foundation/multipaz-developer-website/blob/8efb1ec9eff6c79af2193be18e2b3dba67e9c64f/api/limits.js
- Servidor e endpoints: https://github.com/openwallet-foundation/multipaz-developer-website/blob/8efb1ec9eff6c79af2193be18e2b3dba67e9c64f/api/server.js
