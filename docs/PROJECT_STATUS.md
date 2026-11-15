# Estado do projeto Nivus

Atualizado: 2026-11-15 01:04 UTC
Licença: AGPL-3.0-only

## Resumo verificado

O Nivus tem uma base modular de API FastAPI, autenticação por senha/JWT, telemetria via MQTT, persistência SQLite, painel React e instalação candidata em Docker Compose. O objetivo de rodar em computadores x86_64 com Ubuntu Server minimal continua sendo um alvo; compatibilidade geral ainda não foi demonstrada.

A árvore de módulos e dependências está em MODULE_MAP.md. O catálogo de nós, Home Assistant/Zigbee, IA local, tarefas distribuídas e provedores comerciais são capacidades futuras, não funcionalidades atuais.

## CI de instalação e recuperação

O PR #2 está aberto e não foi mesclado. O run 43652960603 passou nos dois jobs Ubuntu 22.04 amd64:

- Build e smoke Compose com MQTT chegando ao SQLite.
- Instalação limpa num runner virtual descartável, backup consistente, modo de verificação sem mutação, rollback induzido por health inválido, restauração normal, health HTTPS 200, API sem token 401, integridade SQLite e retomada da telemetria.
- Smoke dos filtros, contadores e atualização manual do painel.

Essa evidência valida os fluxos de software num runner Linux descartável. Não comprova reboot de hardware, compatibilidade com todos os chipsets, sensores, BIOS, NICs ou armazenamento, nem recuperação de uma máquina perdida. A restauração atual cobre a base SQLite no mesmo host; preserve as chaves, certificados e demais arquivos de configuração por um procedimento separado.

O PR #4 também passou seu smoke Compose no run 43652755033. Esse smoke não valida sensores em outros computadores.

## Notebook de teste após o reinício

Em 2026-11-15 01:04 UTC, uma sessão SSH com verificação estrita da chave do host confirmou, em leitura:

- O coletor Compose está ativo e sem reinícios; quatro containers candidatos estão em execução. O Mosquitto antigo também permanece ativo.
- HTTPS health respondeu 200 e a rota de telemetria sem token respondeu 401.
- SQLite retornou quick_check ok e a telemetria recente continuava chegando.
- As últimas amostras permaneciam sem origem térmica identificada; motherboard_temperature e gpu_temperature também estavam nulos.
- A release ativa não contém telemetry/hardware_sensors.py nem o componente React LegalNotice usado pelo código térmico candidato.

A saúde da API e do banco não comprova rollback integral do ensaio térmico: o build anterior da interface falhou pela ausência de LegalNotice e o script reportou que não encontrou a imagem anterior ao tentar reverter. O API/worker e a interface não estavam na mesma versão térmica. Os backups desses ensaios foram preservados.

## Correção térmica preparada

O primeiro pacote, 20261115T002514Z, parou ao tentar construir um serviço Compose inexistente. Uma repetição foi interrompida pela guarda “Backup already exists”; isso evitou sobrescrever o backup anterior e não aplicou outra mudança.

O ensaio 20261115T003216Z compilou o API, mas a compilação do frontend parou porque o pacote não incluía LegalNotice.jsx. O rollback emitiu aviso de imagem ausente, portanto não foi considerado bem-sucedido.

Um pacote revisado, 20261115T004156Z, foi transferido para staging no notebook. O arquivo-fonte está completo, inclui LegalNotice.jsx, corresponde ao SHA-256 declarado e passou bash -n no Ubuntu do notebook. O caminho de backup desse pacote ainda não existe. A atualização não foi executada: o script exige sudo interativo e a senha deve ser digitada somente no terminal do notebook. O pacote cria tags Docker para as imagens anteriores antes de construir e preserva os backups já existentes.

## Módulos e contexto para desenvolvimento com IA

As skills Nivus, o mapa de módulos, os modelos de issue/PR e a automação de manutenção do repositório estão em revisão separada no PR #3. Skills são instruções para ferramentas de desenvolvimento, não módulos executados pelo produto.

O índice local de conhecimento em temp/ continua fora do GitHub. Ele agrupa notas com fonte e data; termos normalizados para busca não são IDs de token de um modelo. Não coloque PDFs privados, credenciais ou telemetria da casa no repositório.

A avaliação de Hermes/OmniRoute está em AI_DEVELOPMENT_ORCHESTRATION.md. Essa é uma opção de workflow externo para desenvolvimento, não uma dependência do nó Nivus.

## Validação restante

- Aplicar o pacote térmico revisado e conferir a nova origem de CPU/APU, UI, health, 401, SQLite e coleta contínua.
- Revalidar o conjunto de imagens e fontes do notebook depois do ensaio parcial; uma resposta health 200 isolada não comprova consistência integral.
- Acrescentar casos de inicialização após reinício ao laboratório automatizado quando houver runner apropriado.
- Medir consumo e disponibilidade de sensores em computadores Intel e AMD de diferentes gerações antes de afirmar compatibilidade ampla.

O operador deixou de usar a VM local instável. A validação repetível de rotina usa runners Linux descartáveis; não há requisito para alterar ou reparar a VM do computador do operador.

