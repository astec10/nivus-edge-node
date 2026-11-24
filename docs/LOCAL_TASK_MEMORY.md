---
title: Memória local reutilizável por tarefa
topic: local-task-memory-design
status: design-only
updated: 2026-11-24
---

# Memória local reutilizável por tarefa

> **Estado:** planejamento da Fase 4. Não há ainda memória de tarefas conectada ao assistente local. Este desenho não executa tarefas, não compartilha dados entre nós e não treina modelos.

## Objetivo

Reutilizar procedimentos curtos que foram executados, validados e aprovados, para que o Nivus possa recuperar uma receita compatível em uma tarefa futura. A memória guarda um artefato derivado e verificável; não guarda conversas completas.

Este mecanismo é diferente de:

- **Biblioteca documental:** fontes e manuais com localização e citações, organizada na Fase 4 do [roteiro](PROJECT_ROADMAP.md) e no [fluxo de trabalho com IA](AI_WORKFLOW.md).
- **Memória de tarefas:** receitas práticas aprovadas, com contexto de compatibilidade, evidência e limites.
- **Fine-tuning/LoRA:** alteração de pesos usando dataset curado. É uma etapa opcional, separada e fora do primeiro escopo.

O primeiro mecanismo reutilizável é retrieval local de receitas. O modelo continua com os mesmos pesos.

## Fluxo de dados

~~~mermaid
flowchart LR
  T[Tarefa concluída] --> V[Validar resultado e evidências]
  V --> S[Sanitizar; remover prompt, anexos e dados privados]
  S --> H{Aprovação explícita para salvar?}
  H -- não --> X[Descartar candidato]
  H -- sim --> R[Gerar receita estruturada e atômica]
  R --> C[Revisar compatibilidade e fonte]
  C --> A[Receita local aprovada em NIVUS_DATA]
  A --> Q[Consulta futura por classe e requisitos]
  Q --> M{Ambiente compatível?}
  M -- não --> N[Não reutilizar; mostrar incompatibilidade]
  M -- sim --> E[Apresentar receita e evidência]
  E --> U[Operador escolhe usar, ignorar ou desativar]
  U --> B[Avaliar resultado reproduzível]
  B --> R
~~~

## O que pode ser salvo

Uma receita deve ser pequena, independente e suficiente para reutilizar um procedimento sem conter a conversa original. O esquema proposto:

~~~json
{
  "recipe_id": "uuid",
  "revision": 1,
  "task_class": "validate-compose-health",
  "title": "Validar health e autenticação da stack Compose",
  "nivus_version_range": ">=2.0,<3.0",
  "model": {
    "provider": "local",
    "name": "llama.cpp",
    "version": "registered-model-version"
  },
  "environment": {
    "os": "ubuntu",
    "architecture": "amd64",
    "capabilities": ["docker-compose-v2"],
    "dependencies": ["docker-engine-version-range"]
  },
  "preconditions": ["stack instalada", "backup recente confirmado"],
  "steps": ["consultar health", "consultar autenticação sem token"],
  "validation": ["health esperado", "rota protegida retorna 401"],
  "result_summary": "Resultado validado sem alterar dados de produção.",
  "known_failures": ["serviço ainda em inicialização"],
  "sources": ["commit ou documento com SHA"],
  "evidence": ["identificador de execução sanitizado"],
  "confidence": "verified",
  "approved_at": "2026-11-24T00:00:00Z",
  "approved_by": "local-operator",
  "expires_at": null,
  "state": "approved"
}
~~~

O exemplo é ilustrativo; não contém comandos de produção nem credenciais. Ao implementar receitas executáveis, cada comando terá allowlist, parâmetros validados, modo de simulação quando aplicável e confirmação própria para ações que alterem dados, serviços ou hardware.

Campos obrigatórios: classe da tarefa, versão Nivus, modelo/runtime quando relevante, pré-condições, passos reutilizáveis, critérios de validação, resumo do resultado, falhas conhecidas, fontes/evidências, confiança e aprovação. Acrescentar arquitetura, versões de dependências, requisitos mínimos e data de expiração quando a compatibilidade depender deles.

## O que não pode ser salvo

- Prompt completo, histórico de conversa, anexos, documentos do usuário ou resposta integral de provedor.
- Segredos, chaves, tokens, senhas, cookies, dados pessoais, endereços privados, MAC, IP, caminhos pessoais ou conteúdo de uma casa.
- Logs brutos de produção ou saída que contenha dados acima.
- Uma receita baseada apenas em afirmação de modelo, sem validação reproduzível.
- Instruções não licenciadas copiadas de manuais, livros ou vídeos.

A etapa de sanitização é obrigatória antes da aprovação. Se não for possível remover dados sensíveis com confiança, descartar o candidato em vez de armazená-lo.

## Armazenamento, estado e auditoria

Manter a memória local separada de documentos-fonte e da busca pública. Proposta de localização:

~~~text
$NIVUS_DATA/task-memory/
├── candidates/       # somente temporários, expiram e são descartados
├── recipes/<id>/     # revisões aprovadas e imutáveis
├── catalog.sqlite    # classe, compatibilidade, estado e proveniência
└── evaluations/      # métricas sintéticas sem prompts nem conteúdo privado
~~~

Permissões mínimas para o serviço local. Índices são derivados e reconstruíveis. Backups devem incluir catálogo e revisões aprovadas; nunca exportar por padrão para GitHub, outros Workers ou provedores. A sincronização futura exige identidade do nó, ACL, consentimento da origem, checksum e política de retenção multi-nó.

Estados propostos: candidate, pending_approval, approved, disabled, stale, superseded, rejected e deleted. A aprovação deve ser uma ação distinta de concluir a tarefa. O operador pode inspecionar a fonte, desativar uma receita incorreta e excluir a revisão. Auditoria conserva somente evento, horário, identificador não reversível e responsável; não conserva prompt, anexos ou conteúdo excluído.

## Recuperação e compatibilidade

A recuperação começa pela classe da tarefa, não por similaridade irrestrita com texto do prompt. Aplicar filtros rígidos para:

1. Versão compatível do Nivus e formato da receita.
2. Modelo/runtime e versão quando passos dependem deles.
3. Arquitetura, sistema operacional, dependências e capacidades exigidas.
4. Estado approved, validade e ausência de revogação.
5. Origem e evidência acessíveis e ainda válidas.

Se um requisito não corresponder ou não puder ser verificado, não sugerir a receita como pronta para uso. Mostrar o motivo e permitir ao operador ignorá-la. Resultados de busca exibem classe, versão, modelo, confiança, fontes e validações; nunca escondem incompatibilidade.

O tokenizer só pode limitar o tamanho do contexto selecionado. A receita continua como estrutura semântica — não como sequência de IDs de tokenizer — e é recuperável por termos independentes de modelo.

## Avaliação antes/depois

Criar um conjunto fixo e público de tarefas sintéticas representativas, com ambiente controlado. Comparar execução sem memória e com receita:

- sucesso dos critérios funcionais;
- citações e evidências corretas;
- tempo total e latência de resposta;
- tokens de contexto/saída quando disponíveis;
- pico de RAM e armazenamento;
- falhas causadas por incompatibilidade ou receita desatualizada;
- taxa de uso, rejeição e desativação pelo operador.

Uma receita só é promovida quando melhora ou mantém os critérios de qualidade sem aumentar risco. Estabelecer limites antes do benchmark. Não medir qualidade pela semelhança textual com uma resposta anterior.

## Fine-tuning e LoRA: trilha opcional

Treino não faz parte da memória inicial. Uma proposta futura precisa de:

1. Dataset separado, consentido, curado e licenciado para treino.
2. Remoção verificável de segredos, dados pessoais e material sem licença.
3. Comando explícito, custos/recursos previstos e versão de dataset/modelo.
4. Métricas de referência contra o modelo base e teste de regressão.
5. Checkpoint imutável, metadados de treinamento e rollback.
6. Aprovação humana antes de habilitar pesos derivados em qualquer nó.

Nunca treinar automaticamente após cada solicitação nem transformar falhas privadas em dataset por padrão. Uma receita reutilizável não é, por si só, autorização para treinar.

## Etapas futuras

1. Fechar o contrato de dados e aprovação sem executar comandos.
2. Implementar armazenamento local, sanitização e CRUD de receitas aprovadas.
3. Implementar busca por classe e filtros de compatibilidade, com explicação de resultados.
4. Criar avaliação sintética e regras de expiração/invalidação.
5. Adicionar integração ao assistente somente após revisão de segurança e teste de remoção.
6. Estudar sincronização entre nós após identidade e ACL multi-nó.
7. Tratar fine-tuning/LoRA em proposta e benchmark separados.

**Critério para primeira versão:** uma tarefa sintética aprovada pode ser salva como receita sem persistir o prompt; uma tarefa futura compatível consegue recuperar a receita com origem visível; uma incompatível não a recebe como sugestão válida; a pessoa consegue desativar e apagar a receita; nenhuma chamada externa ou treinamento acontece sem escolha explícita.
