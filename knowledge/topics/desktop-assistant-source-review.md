---
id: desktop-assistant-source-review
title: Pesquisa aberta para a assistente virtual de mesa
topic: desktop-assistant
tags: pepper-ghost, optical-display, open-source-hardware, voice-assistant, face-tracking, face-recognition, vrm, privacy, esp32-camera, local-ai
source: Curadoria de repositórios, vídeos e documentação técnica ligados abaixo
verified_on: 2026-11-20
confidence: primary-source-review
---

# Pesquisa aplicada ao conceito da assistente de mesa Nivus

Esta nota reúne projetos abertos, vídeos de construção, artigo acadêmico e documentação oficial para resolver lacunas do conceito em [DESKTOP_ASSISTANT.md](../../docs/DESKTOP_ASSISTANT.md). A revisão foi feita em 2026-11-20. “Verificado” significa que a fonte primária foi consultada; não significa que o hardware foi comprado, que o software foi instalado ou que desempenho foi medido no Nivus.

## Hardware divulgado pelas referências Project NOVA / NOVA e AVA

Revisão das páginas públicas em 2026-11-20. Os números abaixo são declarações das fontes; não são benchmark independente nem validação no Nivus.

| Referência | Hardware ou plataforma explicitamente documentados | O que isso significa para o Nivus |
| --- | --- | --- |
| [PradeepaRW/project-nova](https://github.com/PradeepaRW/project-nova) | Repositório de orquestração com n8n, agentes especializados, servidores MCP e Docker Compose. O README não define BOM, computador de mesa, requisito de GPU/RAM nem modelo de inferência local. | Útil para estudar organização de agentes/workflows; não fornece base de dimensionamento do aparelho físico. |
| [dujonwalker/project-nova](https://github.com/dujonwalker/project-nova) | Catálogo agnóstico de 25 servidores MCP e skills opcionais, com implantação por Docker Compose. O README remete os requisitos técnicos aos documentos de cada servidor e não define um computador único para assistente de mesa. | Útil para organização de conectores; escolher serviços individualmente e dimensionar seu host conforme cada serviço, sem inferir que Raspberry Pi seja necessário. |
| [Navjot-Singh7/Project-Nova](https://github.com/Navjot-Singh7/Project-Nova) | O README pede GPU NVIDIA com 4–6 GB de VRAM como mínimo e declara desenvolvimento/teste em RTX 2050 de 4 GB com CUDA e Windows. O software recomenda Python 3.11 e Ollama; usa Phi-3.5 4B quantizado Q4_K_M, roteador qwen3.5:0.8b, Moonshine ASR, Soprano TTS e SmolVLM-256M quantizado, alternando modelos para conter uso de VRAM. CPU e RAM mínimas não são especificadas. | É a referência mais concreta de processamento local multimodal entre os três repositórios, mas seu perfil publicado é PC Windows + NVIDIA. Não comprova execução ou desempenho em Ubuntu Nivus, CPU sem GPU ou Raspberry Pi. |
| [Razer AVA](https://www.razer.com/br-pt/razer-ava) | A página oficial descreve tela de 5,5 polegadas, câmera, microfone e alto-falante integrados, com ligação USB-C direta a um PC Windows. Não publica modelo de CPU/GPU/RAM do PC nem especificação do computador interno do aparelho. | Boa referência de integração física e tethered ao computador; não serve como BOM nem revela a capacidade de processamento interna. |
| [Project NOVA — vídeo de construção](https://www.youtube.com/watch?v=WgqDaqqto90) | A referência do vídeo menciona OLED de 5,5 polegadas, Orange Pi (modelo exato não confirmado), câmera USB, iluminação e base motorizada com feedback de posição/PCBs personalizadas. A lista de peças não está completa. | Demonstra um protótipo embarcado para rastreamento e interação, mas não fixa a versão da placa nem prova que ela rode o modelo local da referência Navjot. |

### Leitura para dimensionamento

- Nenhuma dessas referências torna o Raspberry Pi obrigatório.
- Para o Nivus, o computador x86_64 com Ubuntu Server é o candidato ao papel de host local de IA; a compatibilidade e a latência precisam ser medidas com os modelos escolhidos.
- Um Raspberry Pi pode ser usado como terminal/periférico ou host independente para uma carga reduzida, mas isso exige teste próprio. Não inferir capacidade a partir de um modelo de placa citado em outro protótipo.
- ESP32-CAM e outros microcontroladores devem ser tratados como periféricos de captura/controle; visão, reconhecimento de fala e inferência ficam no host local, salvo benchmark que prove o contrário.
- Nenhuma lista de compra está aprovada. Separar GPU, RAM, CPU, display, câmera, microfone, áudio, óptica e controlador em requisitos distintos antes de selecionar peças.

## Projetos e código aberto

| Fonte | O que a fonte oferece | Licença publicada | Uso recomendado no Nivus e limites |
| --- | --- | --- | --- |
| [OpenGhost](https://github.com/xanderchinxyz/OpenGhost) | Display Pepper’s Ghost para Raspberry Pi 5; tela quadrada de 4", cubo beam splitter de 50 ou 70 mm, arquivos STL e câmera opcional. Usa py5 para gráficos e recomenda fonte USB-C de 5 V. | MIT, declarada no repositório. | Referência reproduzível para testar uma óptica compacta e um invólucro; não demonstra voz, identificação ou avatar conversacional. A geometria do cubo não é igual à cúpula do NOVA. O Raspberry Pi 5 não é um alvo Nivus já validado. |
| [Pepper Pi / veebch/pepper](https://github.com/veebch/pepper) | Construção em cúpula com Raspberry Pi 5, tela redonda Waveshare de 3,4" (86 mm), cúpula de vidro de 90 mm, refletor de acrílico e gabinete impresso. Inclui arquivos 3D e calculadora do formato do refletor. | GPL-3.0, declarada no repositório. | Melhor referência aberta para geometria ajustável à cúpula e ao ângulo de observação. O autor ressalta que o formato depende da cúpula e do campo de visão e registra uma correção ao ângulo mostrado no vídeo. Tratar medidas como ponto inicial e respeitar a licença se reutilizar arquivos/código. |
| [Project NOVA — vídeo e fontes já catalogadas](https://www.youtube.com/watch?v=WgqDaqqto90) | Referência do operador: OLED de 5,5", superfície refletiva/cilindro, iluminação, Orange Pi, câmera USB, base motorizada e placas personalizadas, segundo a descrição/transcrição consultadas. | O vídeo não publica uma licença de reuso para esquemas, PCBs ou personagens. | Referência visual e de interação. Não é uma BOM: fabricante, códigos, dimensões ópticas completas e esquemas não foram confirmados. |
| [ARPAHLS/avatar](https://github.com/ARPAHLS/avatar) | Companion de desktop com modelos VRM, animações VRMA e sincronização labial a partir de áudio; experiência principal em Electron/Windows, com app de navegador para desenvolvimento. | MIT para o projeto; modelos e assets devem ser conferidos separadamente. | Referência de contrato de avatar, controle de expressões e ciclo de áudio. Não prova que a aplicação Electron rode no host Nivus ou na tela refletiva. |
| [xiaokeai](https://github.com/liupig/xiaokeai) | Companion 3D com VRM/GLB, fala, movimento e visão; o README informa código Apache-2.0 e lista várias dependências. A distribuição e recursos locais descritos são voltados principalmente a Windows. | Apache-2.0 para código e arte própria identificada; modelos, movimentos, voz e outros assets preservam seus termos. | Referência de integração modular e inventário de assets. Não copiar o pacote inteiro nem assumir funcionamento leve em Ubuntu/Raspberry Pi; desempenho no hardware Nivus não foi medido. |
| [J.E.S.T.E.R](https://github.com/heeelol/jester) | Interface web com Three.js, rastreamento de mãos por MediaPipe, voz via serviços OpenAI e ações de desktop. | Não foi localizado arquivo LICENSE na listagem consultada. | Serve para estudar a separação entrada/cena/ações. Não reutilizar código sem licença; não transportar ações de controle irrestrito do PC nem exigir túnel público para a câmera do celular. |
| [CompreFace](https://github.com/exadel-inc/CompreFace) | Serviço Docker self-hosted de detecção, verificação e reconhecimento facial. O projeto documenta variantes CPU x86 com AVX/AVX2 e GPU CUDA. | Apache-2.0 para o repositório. | Candidato futuro somente para identidade facial explicitamente ativada, separado de rastreamento de posição. A compatibilidade e latência no PC Nivus precisam de benchmark; cadastros e exclusão de templates exigem uma política de privacidade antes de usar. |
| [ESP32 Camera Driver](https://github.com/espressif/esp32-camera) | Driver oficial para sensores de câmera em ESP32, S2 e S3 e exemplos de captura de quadros. | Apache-2.0 para o driver. | Adequado para estudar captura/envio de JPEG; não tratar a ESP32-CAM como computador de visão. O próprio mantenedor descreve exigência de PSRAM para modos/resoluções além de CIF e custo maior de CPU/memória com múltiplos buffers e Wi-Fi. Medir taxa, latência e falhas no módulo exato. |
| [pixiv/three-vrm](https://github.com/pixiv/three-vrm) | Plugin MIT para carregar avatares VRM em Three.js/WebGL. | MIT para o plugin; cada modelo VRM mantém licença própria. | Candidato para uma cena local em navegador/kiosk com renderer desacoplado da fala e do agente. Fazer primeiro uma prova no display real e validar a licença do modelo 3D. |

## Vídeos de construção e arquitetura

| Vídeo | Informação extraída da fonte | Limite |
| --- | --- | --- |
| [I Build a REAL Holographic AI Assistant! — DD ElectroTech](https://www.youtube.com/watch?v=WgqDaqqto90) | Projeto Project NOVA já descrito no [índice de vídeos](../../docs/VIDEO_RESEARCH_INDEX.md): exibição refletiva, eletrônica personalizada, câmera, voz, movimento e corte físico de câmera/microfone. | A descrição/transcrição automática é uma fonte do criador; nomes de peças podem estar incorretos e não há BOM/esquemas completos disponíveis no material consultado. |
| [The Ghost in the Machine — VEEB](https://www.youtube.com/watch?v=vGyMrAtvg8A) | A descrição do criador enumera Raspberry Pi 5 (16 GB), tela LED redonda, cúpula, refletor transparente e base 3D. Os capítulos destacados são 1:55 princípio óptico, 2:14 geometria, 3:24 montagem, 4:43 teste e 5:35 demonstração. O [artigo do projeto](https://www.veeb.ch/projects/the-valley-beneath-the-pepper-dome) e o [repositório](https://github.com/veebch/pepper) publicam a calculadora e arquivos 3D. | A análise registra descrição e marcadores de capítulo; não afirma que cada etapa do vídeo tenha sido medida independentemente. Construção diferente da tela de 5,5" do NOVA. |
| [Voice Assistant Contest Launch — Home Assistant](https://www.youtube.com/watch?v=99lGuB4J-4o) | A página do vídeo lista um segmento aos 1:01:37 sobre detecção local de wake word em um Wyoming Satellite; útil para arquitetura de captura e pipeline de voz. | Vídeo de comunidade/arquitetura, não demonstra compatibilidade de áudio, latência ou privacidade com o hardware Nivus. |

## Artigos e documentação técnica

- [Pepper’s Cone: An Inexpensive Do-It-Yourself 3D Display, UIST 2017](https://doi.org/10.1145/3126594.3126602). Artigo acadêmico descreve um cone plástico curvo sobre tablet, com pré-distorção da imagem e orientação do espectador para perspectiva; explora visualização em giro completo. Serve para estudar geometria e correção da imagem, não como BOM para o NOVA.
- [University of Wisconsin — Physics Demonstrations: Pepper’s Ghost](https://sprott.physics.wisc.edu/demobook/CHAPTER6.HTM). Explica a combinação de transmissão e reflexão, a necessidade de controlar a iluminação e uma montagem demonstrativa com painel inclinado. Base para o ensaio de contraste, fundo escuro e luz ambiente.
- [Home Assistant — Wyoming Protocol](https://www.home-assistant.io/integrations/wyoming) e [pipeline de voz local](https://www.home-assistant.io/voice_control/). A documentação lista serviços STT, TTS e wake-word que podem ser locais (Whisper, Piper e openWakeWord) e permite que alguns serviços rodem em outro computador na LAN.
- [ESPHome — Voice Assistant](https://esphome.io/components/voice_assistant/). O dispositivo com microfone pode encaminhar áudio ao Home Assistant; a documentação adverte que áudio/voz consomem recursos significativos no microcontrolador. Isso apoia usar MCU como satélite de áudio/periférico e fazer STT/TTS/agente no host, depois de medir.
- [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker). Emite landmarks faciais, blendshapes de expressão e matrizes de transformação para efeitos/avatar. Isso é rastreamento/pose/expressão; não identifica a pessoa.
- [Espressif esp32-camera — notas de desempenho](https://github.com/espressif/esp32-camera#important-to-remember). As notas sobre PSRAM, formato JPEG, buffers e Wi-Fi apoiam um teste com JPEG, poucos buffers e processamento no host.
- [OHF-Voice Piper — licenciamento](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md) e [openWakeWord — licença](https://github.com/dscripka/openWakeWord#license). O engine Piper é GPL-3.0-or-later; modelos de voz Piper têm cartões/licenças próprias. openWakeWord licencia seu código em Apache-2.0, mas os modelos pré-treinados incluídos são CC BY-NC-SA 4.0. Conferir a licença exata do binário/modelo antes de redistribuir ou integrar ao produto Nivus AGPL-3.0-only.
- [VRM Public License](https://vrm.dev/en/licenses/1.0/) e [three-vrm](https://github.com/pixiv/three-vrm). O padrão/plugin de carregamento não transfere os direitos do modelo, textura, voz ou motion file; o avatar Nivus deve ser original/licenciado e cada asset validado separadamente.
- [CompreFace — builds de CPU/GPU](https://github.com/exadel-inc/CompreFace/blob/master/custom-builds/README.md). O próprio projeto diferencia builds, conjuntos de instruções e aceleração; a tabela do projeto não substitui um teste com a CPU real do Nivus.

## Decisões e recomendações resultantes

### Óptica: comparar três geometrias antes de comprar peças finais

1. **NOVA:** painel OLED maior dentro de cilindro com material de espelho semitransparente; maior área para corpo inteiro, mas faltam especificação do filme, dimensões e BOM pública.
2. **Pepper Pi:** painel circular pequeno sob cúpula, com refletor de acrílico cortado segundo uma calculadora; é a referência aberta mais ajustável para um protótipo compacto.
3. **OpenGhost:** tela quadrada e cubo beam splitter; peças e arquivos disponíveis, mas outro tipo de montagem.

Não assumir que os componentes são intercambiáveis. Fotografar os três conceitos no ambiente previsto e comparar: leitura de rosto/traje, imagem dupla, contraste com luz ambiente, reflexos parasitas, distorção, ângulo de visão horizontal/vertical, brilho configurado e aquecimento do display. Usar a tela parada no primeiro ciclo; apenas depois decidir se motor e rastreamento mecânico acrescentam valor.

### Voz, visão e compute: separar funções por capacidade

- Manter o host Nivus x86_64 como candidato ao processamento de fala/visão/renderização, condicionado à medição de CPU/RAM/GPU e latência. A documentação de Raspberry Pi 5 não prova capacidade ou suporte Nivus.
- Tratar ESP32-CAM como sensor/capturador de JPEG e controlador MCU como periférico. Enviar somente quadros sob demanda ao host local; fazer visão e renderização no host, nunca converter a câmera em um serviço aberto à LAN/Internet.
- Para detectar/seguir uma face e animar o avatar, testar MediaPipe Face Landmarker sem identificação. A identidade deve ser um segundo estágio independente, explicitamente ativado e com opt-in, cadastro, revogação e exclusão definidos. CompreFace é apenas um candidato a benchmark x86 local; não está aprovado para implantação.
- Avaliar um pipeline local substituível: microfone → wake-word/VAD → STT → agente → TTS → estado de fala/viseme do avatar. Wyoming pode desacoplar serviços locais da interface e permitir colocar serviços mais pesados no host. Medir latência, falsos despertares, reconhecimento de português e ruído do ambiente antes de escolher componente.
- Para o personagem, manter arte original/licenciada, exportar VRM/GLB e testar renderer em tela cheia. Entregar ao renderer somente fala, expressão, pose e duração tipadas; não permitir que texto do modelo dispare ações de sistema.
- Manter câmera/microfone com corte físico de alimentação e indicador de estado. Separar o interruptor de privacidade do botão de parada de emergência do motor. A parada mecânica deve agir localmente no controlador, sem depender da API, da IA ou da rede.

### Movimento, potência e validação que ainda faltam

A referência NOVA usa motorredutor e potenciômetro de posição; a proposta do operador menciona motor de passo. Não escolher um sem teste. Comparar uma base parada, stepper com referência de origem/limites e solução de motorredutor com feedback real. Mesmo com driver que ofereça detecção de stall, usar limites físicos e parada manual independentes; medir ruído, torque disponível, curso, corrente, aquecimento e comportamento após perda do host.

Especificar alimentação depois de definir painel, LED, MCU e motor. Dimensionar pelo consumo simultâneo e corrente de partida/travamento, separar rails de lógica/áudio/iluminação/motor quando apropriado e usar proteção definida pelos datasheets e requisitos do hardware. Não dimensionar a fonte por valores genéricos de um tutorial.

O teste deve registrar configuração, ambiente, foto, ângulos/distâncias, recursos do host, latência de captura e de fala, temperatura e comportamento de falha. Os limites de aprovação serão definidos para o local real de uso; esta curadoria não inventa uma tolerância de brilho, ângulo ou latência antes de haver medida.

## Questões ainda abertas

- Escolher a geometria óptica depois do ensaio: NOVA/cilindro, cúpula/acrílico ou cubo beam splitter; decidir tamanho e interface do painel.
- Confirmar ambiente, distância de observação, brilho e campo angular aceitáveis.
- Identificar o modelo e a interface de câmera; escolher USB versus ESP32-CAM após medir rede/latência.
- Selecionar microphone array/speaker e pipeline de Português (wake word, VAD, STT, TTS) após comparação local.
- Medir a máquina x86_64 que hospedará a IA e testar carga concorrente com o Nivus.
- Definir se a identidade facial será incluída, a ativação física/lógica, o processo de consentimento e a política de cadastro/exclusão/retenção.
- Escolher driver/motor/feedback após teste estático; documentar limites, parada manual e falha segura.
- Fixar dimensões/materiais do invólucro, licença do modelo 3D e pipeline VRM/GLB.
- Definir fonte e proteção elétrica a partir da BOM final e das fichas técnicas.
