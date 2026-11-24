---
title: Biblioteca local incremental de conhecimento
topic: local-knowledge-ingestion-design
status: design-only
updated: 2026-11-24
---

# Biblioteca local incremental de conhecimento

> **Estado:** desenho técnico da Fase 4. Este documento não instala nem ativa ingestão, indexação ou consultas na aplicação. O Nivus ainda não possui biblioteca documental integrada.

## Objetivo e limites

Permitir que o futuro assistente local consulte documentação importada pelo operador, mesmo sem Internet, e responda com citações para a edição, seção e página do original.

O repositório público guarda apenas código, metadados que possam ser compartilhados e resumos próprios. Documentos originais e derivados privados vivem em NIVUS_DATA, fora do checkout Git. A biblioteca não envia documentos, consultas ou trechos a provedores externos por conta própria.

Esta proposta pertence à [Fase 4 do roteiro](PROJECT_ROADMAP.md) e complementa o [mapa de módulos](MODULE_MAP.md) e o [fluxo de trabalho com IA](AI_WORKFLOW.md). Ela não declara OCR, busca vetorial, sincronização entre nós ou geração de respostas já implementados.

## Invariantes

1. **Originais são imutáveis enquanto retidos.** Importar outra edição cria uma nova identidade de versão; nunca sobrescreve bytes anteriores.
2. **Derivados são descartáveis e reproduzíveis.** Texto extraído, trechos e índices podem ser reconstruídos do original e das versões registradas de parser e processamento.
3. **Nada é baixado automaticamente.** Importação de arquivo é ação local explícita. Download exige comando explícito e uma origem permitida.
4. **Licença desconhecida significa quarentena.** Não extrair para consulta nem distribuir até revisão do operador.
5. **Toda resposta recuperada conserva proveniência.** Documento, edição, página/seção e trecho acompanham o resultado.
6. **Pesquisa lexical vem primeiro.** Embeddings só entram após medições reproduzíveis de qualidade, latência, RAM e disco.
7. **Tokenizer não é índice.** Termos lexicais são independentes de modelo; IDs de tokenizer servem apenas para respeitar o contexto de um modelo selecionado.

## Armazenamento proposto

A raiz vem de uma configuração absoluta NIVUS_DATA. A inicialização deve falhar com mensagem clara quando ela não estiver configurada ou quando, após resolver links simbólicos, apontar para dentro do checkout público.

~~~text
$NIVUS_DATA/library/
├── inbox/                 # arquivos recém-importados; sem execução
├── quarantine/            # licença, tipo ou arquivo aguardando revisão
├── originals/sha256/      # bytes imutáveis organizados pelo hash
├── derived/<source-id>/   # extração e trechos por fingerprint
├── index/                 # índice local reconstruível
├── catalog.sqlite         # metadados e estados, sem telemetria doméstica
└── tmp/                   # área temporária limitada e removida após processamento
~~~

Restringir permissões ao usuário/serviço Nivus. O leitor recebe acesso somente de leitura a originais e derivados. O parser não recebe rede, segredos, socket Docker, dispositivos do host ou diretórios fora da área de trabalho. Backups preservam originais e fazem cópia consistente do catálogo; verificar checksum após restauração. Índices derivados podem ser reconstruídos.

Não colocar caminhos pessoais absolutos, arquivos importados, bancos locais, trechos privados ou logs de execução no GitHub. Não registrar conteúdo de documentos em logs de erro.

## Registro de fonte e edição

Separar identidade lógica da fonte e cada edição importada. Cada edição tem ao menos:

~~~json
{
  "source_id": "lfs-book",
  "edition_id": "lfs-13.1-systemd",
  "canonical_url": "https://www.linuxfromscratch.org/lfs/download.html",
  "canonical_document_url": "https://www.linuxfromscratch.org/lfs/downloads/stable-systemd/LFS-BOOK-13.1-NOCHUNKS.html",
  "title": "Linux From Scratch",
  "author": "Linux From Scratch editors",
  "edition": "13.1-systemd",
  "license_declared": "CC BY-NC-SA 2.0",
  "license_scope_note": "A edição permite extrair instruções de computador sob MIT; verificar o escopo de cada derivado.",
  "consulted_at": "2026-11-24T00:00:00Z",
  "imported_at": null,
  "sha256": null,
  "mime_type": null,
  "size_bytes": null,
  "page_count": null,
  "source_etag": null,
  "source_last_modified": null,
  "parser_version": null,
  "chunker_version": null,
  "tokenizer": null,
  "index_version": null,
  "state": "pending"
}
~~~

Hash, tipo, tamanho e páginas só são preenchidos com a edição realmente importada; o exemplo não afirma que o PDF foi baixado. Usar UTC. Guardar licença declarada pela fonte por extenso e, havendo correspondência segura, também identificador SPDX. Não inferir uma licença permissiva quando a licença é desconhecida.

## Fluxo

~~~mermaid
flowchart LR
  A[Arquivo local ou comando explícito de download] --> B[Validação de origem e limites]
  B --> C{Licença e tipo conhecidos?}
  C -- não --> Q[Quarentena para revisão]
  C -- sim --> H[SHA-256 e deduplicação]
  H -- duplicado --> D[Registrar duplicata; reutilizar edição existente]
  H -- novo --> O[Salvar original imutável em NIVUS_DATA]
  O --> X[Extrair em sandbox sem rede]
  X -- falha --> F[Registrar falha isolada]
  X -- sucesso --> K[Dividir por seção e conceito]
  K --> I[Gerar índice lexical local]
  I --> R[Recuperar trechos com localização]
  R --> S[Resposta com citações e confiança]
~~~

### 1. Entrada e quarentena

- A importação manual aceita inicialmente TXT, Markdown e PDF.
- Calcular SHA-256 durante a cópia para a área de entrada, detectar tipo pelo conteúdo e comparar com a extensão. Não confiar só no nome ou MIME informado pelo cliente.
- Configurar limites explícitos para bytes, páginas, tempo, memória e número de arquivos. Recusar ou colocar em quarentena o que exceder limites.
- Arquivos compactados, macros, anexos embutidos e formatos executáveis ficam fora do primeiro escopo.
- Uma URL só pode ser buscada com subcomando explícito, esquema HTTPS e host numa allowlist administrável. Revalidar o host após cada redirecionamento e bloquear loopback, redes privadas, link-local e endereços de metadados de nuvem para evitar SSRF. Limitar redirecionamentos, bytes e tempo.
- Não fazer scraping genérico. Um monitor de atualização pode consultar metadados condicionais (ETag/Last-Modified) na agenda configurada. Se a origem mudou, marcar update_available; não baixar nem substituir sem confirmação.

Estados mínimos: pending, quarantined, indexed, stale, duplicate, failed, update_available e rejected. Registrar motivo e horário das transições, sem copiar o conteúdo para logs.

### 2. Hash e deduplicação

- Calcular SHA-256 dos bytes originais antes da extração e procurar uma edição idêntica.
- O mesmo hash pode ser referenciado por mais de uma URL/fonte; guardar cada proveniência sem duplicar os bytes.
- Reutilizar derivados apenas quando coincidirem hash, identidade/edição, parser e configuração de extração, estratégia/versão do chunker e formato do índice.
- Registrar versão do tokenizer somente quando ela afetar um artefato derivado ou limite de contexto. Trocar o modelo não deve reconstruir o índice lexical se nenhum ID de tokenizer foi usado nele.
- Mudança numa fonte invalida apenas os derivados dessa edição. Preservar edição anterior e citações antigas enquanto ela for retida.

### 3. Extração restrita

Executar cada arquivo em processo isolado, sem rede, com limites de CPU, RAM, tempo, páginas e tamanho de saída. Montar original como somente leitura. Usar diretório temporário exclusivo e removê-lo após sucesso ou falha.

Extrair TXT e Markdown preservando parágrafos, títulos, tabelas simples e blocos de código. Para PDF, preservar número da página e estrutura identificável; PDF digitalizado sem camada textual fica com estado explícito “OCR não disponível” até uma etapa de OCR ser avaliada. Não tratar texto extraído como confiável para instruções executáveis. Uma falha de parser marca somente aquela edição como failed e não interrompe o restante da biblioteca.

Metadados por trecho incluem source_id, edition_id, hash, URL, página quando houver, caminho de títulos (capítulo/seção), ordem do parágrafo e fingerprint da extração.

### 4. Atomização e citações

Dividir por seção, parágrafo ou conceito coerente, mantendo título e relação com trechos próximos quando necessário. Preservar blocos de código completos sempre que o limite permitir. Não criar um registro por palavra/token, não cortar comandos em linhas inválidas e não misturar edições.

Cada trecho recuperável carrega um localizador estável, por exemplo:

~~~text
lfs-book / lfs-13.1-systemd / Chapter 8 > 8.3.1 / p. 148
~~~

Para Markdown/TXT sem paginação, usar título e número do parágrafo. Se um PDF não tiver paginação confiável, registrar página física observada e regra usada. A resposta cita edição e localização e permite abrir o documento local. Se a evidência for fraca ou contraditória, responder que não encontrou suporte suficiente.

### 5. Índice, busca e tokenizer

Primeira versão: índice lexical determinístico, offline e reconstruível, com stemming/normalização documentados se usados. O contrato de busca devolve IDs de trechos, pontuação e localizadores, sem depender de provedor de IA. Consultas e resultados não guardam conteúdo integral em logs.

A busca lexical existente em knowledge/index é o índice público de documentação e não substitui o catálogo privado em NIVUS_DATA. O tokenizer do modelo é etapa separada: quando necessário para limitar contexto, registrar modelo, versão do tokenizer, tokens estimados e regra de truncamento. Não persistir IDs do tokenizer como termos de pesquisa compartilhados entre modelos.

Medir, antes de considerar vetores: conjunto de consultas de referência, relevância/citações corretas, tempo de resposta, pico de RAM, armazenamento e custo de reconstrução. Só adicionar embeddings se a busca lexical não cumprir critérios definidos; embeddings precisam de versão, política de atualização, orçamento de disco e plano de rebuild.

## URLs, versões e exemplo LFS

A página oficial do [Linux From Scratch](https://www.linuxfromscratch.org/lfs/download.html) indica a edição stable mais recente; a edição estável consultada em 2026-11-24 é **13.1-systemd**, publicada em 2026-09-01. Em cada importação, confirmar a edição no próprio documento, registrar o SHA-256 do arquivo obtido e consultar também a [errata 13.1](https://www.linuxfromscratch.org/lfs/errata/13.1-systemd/). Não deixar “stable” como versão imutável no catálogo.

O apêndice oficial de [licenças da edição 13.1](https://www.linuxfromscratch.org/lfs/view/13.1-systemd/appendices/licenses.html) declara CC BY-NC-SA 2.0 para o livro e permite extrair instruções de computador sob MIT. Portanto:

- O PDF completo fica apenas em NIVUS_DATA, não no repositório público.
- A permissão MIT cobre instruções de computador conforme o escopo indicado pela fonte; não aplicar automaticamente a prosa, figuras, comentários ou livro inteiro.
- Cada instrução extraída mantém edição, seção, URL, hash e aviso de licença/proveniência.
- Não copiar trechos extensos. Publicar resumos originais ou instruções cujo escopo/licença foi verificado.

## Incrementalidade, atualização e remoção

Na inicialização ou agenda configurada, percorrer apenas arquivos elegíveis da caixa de entrada. O scanner é idempotente: repetir a operação com as mesmas entradas e versões não altera resultados indexados. Originais com hash conhecido são ignorados; alterações criam edição pendente ou update_available, sem substituir a anterior.

Um comando de atualização mostra fonte, edição atual, metadados remotos, tamanho esperado quando conhecido e licença antes de buscar o corpo. Após confirmação, salva a nova edição separadamente e só promove seus derivados depois da extração, validação de citações e construção do índice. Falha mantém a edição antiga pesquisável.

Remoção solicitada pelo operador apaga bytes, derivados e referências da edição escolhida, incluindo índices/embeddings. O log de auditoria pode reter somente identificador não reversível, data e motivo operacional; não reter trechos nem conteúdo apagado. Documentar retenção e como confirmar backups antigos antes de criar opção de exclusão na interface.

## Entregas sugeridas para implementação futura

1. Resolver NIVUS_DATA, permissões e diretórios com validação de caminhos e symlinks.
2. Importação manual de TXT/Markdown com hash, catálogo, licença, quarentena e limites.
3. Extração PDF isolada com páginas/localizadores e casos de falha.
4. Chunking semântico e índice lexical privado, com busca offline e citações.
5. Importação remota explícita com allowlist, proteção SSRF e checagem de versão sem download automático.
6. Backups/restauração, retenção, remoção e testes de segurança.
7. Benchmark para decidir se embeddings têm valor no hardware suportado.

Cada etapa precisa de testes sintéticos com arquivos de licença conhecida/desconhecida, duplicados, grandes, inválidos e com atualização simulada. Não usar PDFs privados ou protegidos em CI pública.

## Referências primárias

- [LFS downloads e edição estável](https://www.linuxfromscratch.org/lfs/download.html)
- [LFS 13.1-systemd, livro oficial](https://www.linuxfromscratch.org/lfs/downloads/stable-systemd/LFS-BOOK-13.1-NOCHUNKS.html)
- [LFS 13.1-systemd, apêndice de licenças](https://www.linuxfromscratch.org/lfs/view/13.1-systemd/appendices/licenses.html)
- [Errata da edição 13.1-systemd](https://www.linuxfromscratch.org/lfs/errata/13.1-systemd/)
