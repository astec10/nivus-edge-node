# Validação física de hardware

Este roteiro registra evidências em equipamentos reais antes de declarar suporte. A CI e a instalação no notebook CCE U25 não substituem a validação em outras máquinas.

## Escopo atual

| Equipamento | Evidência disponível | Pode ser declarado agora |
|---|---|---|
| CCE U25 | Instalação candidata observada; consultar `docs/PROJECT_STATUS.md` | Somente o que estiver registrado no status |
| Raspberry Pi 3 | Sem execução física registrada | Não declarar suporte nem inferência local |
| Dell Vostro 3268 | Sem execução física registrada | Não declarar suporte nem tarefas de programação |

O agente de nós ainda anuncia uma lista vazia de capacidades. A classificação “texto”, “cálculo” ou “programação” e o scheduler distribuído continuam planejados; uma medição de hardware, isoladamente, não prova essas capacidades.

## Ficha para cada equipamento

Registre antes do teste:

- Modelo, revisão e identificador local não sensível.
- CPU, arquitetura (`uname -m`), RAM, swap, armazenamento livre e fonte de alimentação.
- Distribuição, versão, kernel, Docker e Compose.
- Versão/commit do Nivus instalado e método de instalação.
- Temperatura ambiente aproximada e refrigeração usada.
- Data, duração, resultado de cada etapa e link para logs redigidos.

Não inclua tokens, senhas, banco doméstico, endereços públicos ou telemetria de pessoas.

## Etapas

1. Confirme que o sistema operacional e a arquitetura atendem os requisitos publicados em `deploy/README.md`. Se não atenderem, pare e registre incompatibilidade; não use emulação para afirmar suporte nativo.
2. Siga a instalação candidata em `deploy/README.md` e as verificações seguras em `docs/VM_VALIDATION.md`. Não execute procedimentos de restauração ou rollback sobre o ambiente ativo.
3. Verifique serviços, armazenamento persistente, reinício controlado e endpoint `/health`. Registre consumo de RAM/CPU em repouso e durante a carga normal do dashboard.
4. Confira se telemetria de sensores identificados corresponde ao equipamento. Marque leituras genéricas, ausentes ou sem driver como não validadas; não atribua uma zona ACPI genérica à CPU.
5. Mantenha o sistema em operação por pelo menos 24 horas, incluindo reinicialização, e registre reinícios inesperados, falhas, temperatura e espaço em disco.
6. Repita após atualização e restauração de backup em ambiente isolado, conforme o procedimento operacional aplicável.

## Critério para fechar a validação

A validação de runtime pode ser considerada concluída quando instalação, health check, persistência, reinicialização, telemetria identificável e período de estabilidade estiverem registrados sem falhas abertas. Anexe as evidências redigidas em `docs/PROJECT_STATUS.md` e mantenha limitações por modelo.

Não declare capacidades de IA, cálculo ou programação com base apenas na ficha de hardware. Essas capacidades só poderão ser testadas depois que o executor e o scheduler correspondentes estiverem implementados e a tarefa tiver sido concluída e revisada no próprio equipamento.
