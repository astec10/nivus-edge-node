# Índice de pesquisa dos vídeos

Atualizado em 2026-11-21. Este índice é o catálogo legível por pessoas e agentes. O registro estruturado e os termos de busca estão em [`../knowledge/catalog/video_sources.jsonl`](../knowledge/catalog/video_sources.jsonl); notas atômicas ficam em [`../knowledge/topics/`](../knowledge/topics/).

Nesta atualização, as páginas e transcrições dos dois vídeos novos foram consultadas e as afirmações relevantes foram comparadas com os repositórios dos projetos e a documentação oficial do Home Assistant. As métricas de velocidade e demonstrações continuam sendo relatos dos criadores, não benchmarks independentes. Os itens antigos conservam o nível de evidência de sua revisão. **“Catalogado” não significa que toda alegação do vídeo foi validada.**

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


## Computação distribuída e voz local

### I Turned My Spare Phones Into a Wireless GPU for AI Agents (It Actually Works) — orailnoor

- [Vídeo](https://www.youtube.com/watch?v=reOeczuEzOA)
- **Tema/tags:** inferência móvel, paralelismo de modelo, camadas, API OpenAI-compatible, rede local, memória, latência.
- **Marcos da transcrição:** 0:17 — demonstração motivada por RAM insuficiente num portátil; 1:22 — o criador compara um modelo individual por telefone; 1:37–3:14 — apresenta um grupo de telefones com um dispositivo principal e trabalhadores, repartindo camadas/modelo e encaminhando ativações entre dispositivos; 2:44 — atribuição declarada com base em memória e velocidade disponíveis; 3:56 — afirma cerca de 4–5 tokens/s para o modelo de 26B em quatro dispositivos; 4:21–4:58 — mostra o servidor/API na LAN ligado a clientes de terceiros.
- **Verificação externa:** o release público 1.0.7-cluster confirma o recurso de dividir o modelo por memória livre e velocidade, juntar workers por QR e servir uma API descrita como compatível com OpenAI, protegida por chave, na rede Wi-Fi. O mesmo release publica a faixa de 4–5 tokens/s; isso confirma o que o mantenedor anuncia, não o desempenho de forma independente.
- **Leitura para o Nivus:** trata-se de **paralelismo de modelo** (um modelo dividido em partes), com dependência sequencial de comunicação entre dispositivos. É diferente de repartir tarefas independentes no futuro executor do Nivus. Pode inspirar um adaptador experimental de inferência local e um tipo separado de endpoint OpenAI-compatible na LAN na configuração de provedores. Não deve virar dependência do scheduler nem ser chamado de GPU distribuída genérica.
- **Critérios antes de experimentar:** medir tokens/s e latência completa, memória e temperatura por dispositivo, tráfego por token, resposta a perda de Wi-Fi/worker, autenticação e limite de exposição da API. A versão consultada recomenda mesma rede Wi-Fi e telas ligadas. Desempenho anunciado é autodeclarado; não foi reproduzido no Nivus.
- **Fontes:** [transcrição do vídeo](https://www.youtube.com/watch?v=reOeczuEzOA), [release 1.0.7-cluster](https://github.com/orailnoor/cross-platform-llm-client/releases/tag/1.0.7-cluster), [repositório do cliente (MIT)](https://github.com/orailnoor/cross-platform-llm-client). Não copiamos a transcrição.

### I Rooted an Echo Dot — Andy’s Tech Lab

- [Vídeo](https://www.youtube.com/watch?v=a5bRPBtgw-U)
- **Tema/tags:** Home Assistant, satélite de voz, Assist, ESPHome/Wyoming, STT/TTS local, hardware restrito, segurança física.
- **Marcos da transcrição:** 0:00–1:40 — o vídeo descreve a abertura/modificação física de um Echo e ligação a pontos internos; 2:14 — introduz o projeto de satélite de voz; 3:17–4:20 — demonstra instalação e pipeline local com Whisper/Piper; 4:29–4:51 — o autor relata ajuste do tipo de CPU de uma VM para contornar problema naquele ambiente; 6:08–7:09 — relata latência alta no Whisper e melhora ao mudar para Speech-to-Phrase, com tempos aproximados medidos na configuração mostrada.
- **Discrepância e risco:** a transcrição do vídeo parece identificar o Echo Dot 3 de 2018 como D929T; o README atual do projeto lista D9N29T e firmware específico, e distingue variantes de 2019–2020 e modelos com relógio que não são suportados. Use o identificador do aparelho e firmware do upstream, nunca a grafia incerta da transcrição. O upstream também chama o software de não auditado e alerta que desbloqueio e escrita de partição podem inutilizar o Echo ou deixá-lo exposto na rede. A tarefa de desbloqueio depende de trabalho de terceiros.
- **Verificação útil:** a documentação oficial do Home Assistant já descreve um pipeline Assist totalmente local com dispositivo de voz, STT, processamento de intenção e TTS. Speech-to-Phrase é mais rápido, porém limitado a um subconjunto de comandos; Whisper é mais aberto e demanda mais recursos. Wyoming permite que serviços locais de voz sejam executados em outra máquina da LAN. Confirme disponibilidade/qualidade de idioma português na versão instalada.
- **Leitura para o Nivus:** reutilizar a arquitetura modular de Home Assistant e seus protocolos suportados é mais prático do que rootear hardware. Deixar o Home Assistant gerir dispositivos/Zigbee e manter voz como módulo independente de entrada/saída. Em hardware Celeron, considerar STT num nó mais forte por Wyoming. Comandos de segurança/energia devem passar por regras determinísticas e intertravamentos; uma resposta de LLM não deve acionar diretamente relé, trava ou portão.
- **Recomendação:** estudar como integração futura do módulo de automação, não instalar nem reproduzir o procedimento de desbloqueio. Os tempos mostrados são uma experiência individual, não benchmark comparável.
- **Fontes:** [vídeo](https://www.youtube.com/watch?v=a5bRPBtgw-U), [README do echo-dot-assist](https://github.com/Gamer92000/echo-dot-assist/blob/main/README.md), [Assist local oficial](https://www.home-assistant.io/voice_control/voice_remote_local_assistant), [integração Wyoming](https://www.home-assistant.io/integrations/wyoming). Não copiamos legenda ou instruções de desbloqueio.

## Como integrar à biblioteca compartilhada Nivus

O catálogo preserva origem e status; notas temáticas guardam resumos próprios e pequenos conceitos. A biblioteca compartilhada em runtime ainda é planejada. Para integrá-la, a Fase 4 deve importar registros versionados, manter URL/timestamp, direitos de uso, checksum e confiança, gerar chunks reproduzíveis e permitir pesquisa lexical primeiro. Embeddings podem vir depois de medição. Nenhuma alegação de vídeo deve se tornar fato do Nivus sem evidência primária ou teste reproduzível.
