# Índice de pesquisa dos vídeos

Atualizado em 2026-11-15. Este índice é o catálogo legível por pessoas e agentes. O registro estruturado e os termos de busca estão em [`../knowledge/catalog/video_sources.jsonl`](../knowledge/catalog/video_sources.jsonl).

O YouTube limitou a leitura direta das páginas durante esta revisão. Por isso, cada item distingue legenda secundária, metadado de descrição, rótulo enviado pelo operador e afirmação verificada em documentação primária. **“Catalogado” não significa “conteúdo integral assistido e verificado”.**

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

## Como integrar à biblioteca compartilhada Nivus

O catálogo preserva origem e status; notas temáticas guardam resumos próprios e pequenos conceitos. A biblioteca compartilhada em runtime ainda é planejada. Para integrá-la, a Fase 4 deve importar registros versionados, manter URL/timestamp, direitos de uso, checksum e confiança, gerar chunks reproduzíveis e permitir pesquisa lexical primeiro. Embeddings podem vir depois de medição. Nenhuma alegação de vídeo deve se tornar fato do Nivus sem evidência primária ou teste reproduzível.

