# Índice de pesquisa dos vídeos

Atualizado em 2026-11-24. Este índice é o catálogo legível por pessoas e agentes. O registro estruturado e os termos de busca estão em [`../knowledge/catalog/video_sources.jsonl`](../knowledge/catalog/video_sources.jsonl).

A cobertura varia por fonte: para o vídeo de gateway de IA abaixo, a página pública e as legendas automáticas em português foram consultadas; os demais itens preservam o estado de verificação indicado em cada entrada. Cada item distingue demonstração, legenda/descrição, rótulo do operador e documentação primária. **“Catalogado” não significa “conteúdo integral transcrito ou verificado”.**

## Execução de software e paralelismo

### Paralelismo com IAs, Multi Contas

- [Vídeo](https://www.youtube.com/watch?v=Q-yobCYc71A)
- **Tema/tags:** agente persistente, multi-modelo, Discord, Jira, GitHub, fila, CI, revisão humana.
- **Extraído:** o caso de uso informado pelo operador descreve VPS + Hermes + OmniRoute, tarefas originadas no Discord/Jira, execução isolada, PR, CI/homologação e aprovação humana.
- **Verificação:** a descrição veio de um comentário de inscrito, não da transcrição do vídeo. As capacidades de cada peça foram conferidas em fontes oficiais separadas; a integração completa e o ciclo de correção não foram comprovados.
- **Nota:** [`AI_DEVELOPMENT_ORCHESTRATION.md`](AI_DEVELOPMENT_ORCHESTRATION.md).

### Código e interação com o ambiente

- [Vídeo](https://www.youtube.com/watch?v=z3wpOywp358)
- **Tema/tags:** agente de código, ferramentas, execução de comandos, interação com programas.
- **Verificação:** tema fornecido pelo operador; conteúdo e comandos ainda precisam de legenda/transcrição. Não transforme o rótulo em recomendação de dependências.

### IA e interação com programas

- [Vídeo](https://www.youtube.com/watch?v=gQ3BewdJEOs)
- **Tema/tags:** agente, ferramenta, automação de programas, sandbox.
- **Verificação:** tema fornecido pelo operador; alegações, comandos e riscos ainda não extraídos da fonte primária.

## IA local e hardware

### Transformei uma TV Box Antiga em Gateway de IA! | Armbian + FreeLM — Café com Dados & Gatos

- [Vídeo](https://www.youtube.com/watch?v=O6_d15v1Zy0)
- **Tema/tags:** gateway de IA, FreeLM, API compatível com OpenAI, túnel SSH, TV Box ARM, privacidade de prompts.
- **Estado da fonte:** página pública e descrição consultadas; legendas automáticas em português revisadas no navegador. Os tempos abaixo são aproximados e a transcrição automática pode conter erros. Nenhuma transcrição integral foi copiada.
- **Demonstração do vídeo:** a BTV é usada como gateway para encaminhar pedidos a provedores externos; a descrição diz que a TV Box não executa um modelo grande localmente. A demonstração configura uma API local compatível com OpenAI e acessa o serviço por túnel SSH.
- **Tempos úteis nas legendas:** 00:43–01:00 (gateway versus inferência local); 02:08–04:27 (endpoint FreeLM e túnel); 09:07–10:16 (teste por USB e observação de Wi-Fi); 12:06–13:45 (instalação interna específica da placa); 16:47–19:35 (FreeLM e acesso gráfico); 23:39–24:37 (teste do endpoint e próximos passos).
- **Checagem primária:** o README do FreeLM descreve `freelm serve` em `127.0.0.1:4000/v1` por padrão e recomenda configurar autenticação ao expor o serviço. A documentação também alerta que endpoints públicos sem chave podem registrar prompts e têm limites baixos. Consulte [FreeLM](https://github.com/shihabshahrier/freelm).
- **Limite de hardware:** o relato upstream identifica uma BTV 10 BX, Amlogic S905X, placa p212, 2 GB de RAM e 16 GB eMMC; o autor relata boot USB e instalação eMMC para essa unidade. A lista genérica [Armbian aml-s9xx-box](https://armbian.com/boards/aml-s9xx-box) e esse único relato não garantem compatibilidade de outras TV Boxes nem suporte do Nivus. Consulte [relato upstream da BTV 10 BX](https://github.com/ophub/amlogic-s9xxx-armbian/issues/3676).
- **Aplicação ao Nivus:** gateway encaminha pedidos; inferência local executa o modelo no próprio nó. O primeiro não combina CPUs/RAM nem prova distribuição P2P. Qualquer uso de provedor externo precisa declarar o fluxo dos prompts, limites, autorização e política de dados.
- **Limites da demonstração:** o vídeo trata o New API e a integração Telegram como passos futuros, não como recursos confirmados nessa instalação. O ID de instalação e os arquivos de boot são específicos do hardware; não os reutilize em outras placas.
- **Nota de segurança:** [`ai-gateway-security-boundaries.md`](../knowledge/topics/ai-gateway-security-boundaries.md).
### Every Size Local AI In 24 Minutes — Tina Huang

- [Vídeo](https://www.youtube.com/watch?v=rPGJhrunbxo)
- **Tema/tags:** tamanho de modelo, RAM/VRAM, quantização, dispositivo, desempenho local.
- **Extraído:** há um espelho de legenda de terceiros que indica uma comparação de modelos locais em classes de hardware. Não importamos benchmarks nem recomendações de modelo.
- **Verificação:** legenda secundária; números e demonstrações devem ser confirmados no vídeo e nos repositórios dos modelos/runtime antes de uso.

### local AI's biggest problem... they solved it? — NetworkChuck

- [Vídeo](https://www.youtube.com/watch?v=cFdoXn6yvE4)
- **Tema/tags:** GPU remota, rede, inferência local, transferência de dados, hardware compartilhado.
- **Extraído:** espelhos de legenda descrevem uma demonstração patrocinada de GPU WiCi conectada pela rede e uso de IA local. Isso é compartilhamento de acelerador remoto; não prova que P2P combina RAM/VRAM de vários nós ou acelera qualquer tarefa.
- **Verificação:** somente legenda/cópias secundárias e conteúdo promocional; throughput, desempenho e compatibilidade ainda precisam de teste independente.

### IAs locais sem restrição

- [Vídeo](https://www.youtube.com/watch?v=VqXbFtjq0m4)
- **Tema/tags:** modelos locais, políticas de uso, execução offline.
- **Verificação:** rótulo enviado pelo operador; título, modelos, comandos e significado de “sem restrição” ainda precisam de transcrição. Não interpretar como ausência de licença, segurança ou regras legais.

### Link compartilhado aos 5:44

- [Vídeo](https://www.youtube.com/watch?v=YC5sG321g0Y&t=344s)
- **Tema/tags:** inferência local (provisório; não confirmado).
- **Verificação:** URL e timestamp foram enviados pelo operador; o tema e os comandos desse trecho ainda não foram confirmados. A visão do projeto mantém a referência sem escolher runtime/modelo com base somente no título.

## Interface e automação residencial

### I Build a REAL Holographic AI Assistant! — DD ElectroTech

- [Vídeo](https://www.youtube.com/watch?v=WgqDaqqto90)
- **Tema/tags:** interface multimodal, voz, visão, hardware embarcado, privacidade física, automação residencial.
- **Extraído:** a descrição indexada apresenta um protótipo chamado NOVA com display, rastreamento, voz, integração residencial e chave física para câmera/microfone.
- **Verificação:** informação de descrição/promocional; arquivos de construção, segurança do controle doméstico e funcionamento offline não foram verificados.

## Como integrar à biblioteca compartilhada Nivus

O catálogo preserva origem e status; notas temáticas guardam resumos próprios e pequenos conceitos. A biblioteca compartilhada em runtime ainda é planejada. Para integrá-la, a Fase 4 deve importar registros versionados, manter URL/timestamp, direitos de uso, checksum e confiança, gerar chunks reproduzíveis e permitir pesquisa lexical primeiro. Embeddings podem vir depois de medição. Nenhuma alegação de vídeo deve se tornar fato do Nivus sem evidência primária ou teste reproduzível.
