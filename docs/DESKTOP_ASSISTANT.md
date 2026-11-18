# Assistente virtual de mesa e avatar 3D

**Estado:** proposta de produto em descoberta. Nenhum hardware, modelo de IA ou integração foi selecionado ou implementado.

Este documento separa os detalhes vistos na referência do YouTube da adaptação proposta pelo operador para o Nivus. A descrição e a transcrição do YouTube estavam em dublagem automática quando consultadas em 2026-11-17; nomes técnicos reconhecidos por voz podem conter erros. O vídeo é uma referência de projeto, não uma especificação de compra.

## Referência do vídeo Project NOVA

Fonte: [I Build a REAL Holographic AI Assistant! — DD ElectroTech](https://www.youtube.com/watch?v=WgqDaqqto90). A descrição pública do vídeo menciona display OLED de 5,5 polegadas, computador Orange Pi, PCBs personalizadas e peças impressas em 3D. O modelo exato do Orange Pi não ficou confirmado.

Detalhes apresentados no vídeo e na transcrição automática:

- A imagem de “holograma” é uma ilusão óptica: personagem renderizado sobre fundo preto, display refletivo, cobertura transparente e iluminação controlada. Não é uma imagem volumétrica flutuando livremente.
- O vídeo compara duas experiências iniciais: uma pirâmide de quatro peças transparentes sobre o celular, que exige escurecer o ambiente e cresce demais para um personagem de tamanho real; e uma peça impressa em 3D, cuja imagem só fica correta de um ângulo limitado. A equipe cita o conceito Razer Project AVA como referência para continuar a investigação.
- Uma primeira montagem usou um display de 5,5 polegadas, película/espelho semitransparente, peças impressas, faixa ARGB, difusor em meia-lua e cilindro transparente. O protótipo inicial conectava o display a um laptop por HDMI.
- Para o ângulo de visão, a equipe descreve uma base giratória com rolamentos, motorredutor e potenciômetro acoplado por engrenagem para medir posição. O texto automático cita cinco rolamentos; a contagem deve ser conferida no vídeo antes de reproduzir a mecânica.
- O vídeo mostra uma câmera USB e um computador Orange Pi para processamento embarcado. A descrição menciona rastreamento facial e das mãos; a transcrição também fala em reconhecimento de objetos.
- A equipe relata calibração entre posição do rosto, ângulo do display e posição do motor. O ajuste final evita girar a tela para pequenas mudanças: perto do aparelho, o personagem altera a pose; mais longe, a base acompanha a pessoa.
- O criador relata três PCBs: duas para iluminação endereçável e uma placa de controle para LEDs, alto-falante, motor e comunicação com o computador, incluindo a manutenção do ângulo do display. Antes das placas finais, testou o circuito e o feedback de posição em protoboard.
- As peças do invólucro foram impressas, montadas e ajustadas por tentativa e erro antes da versão final.
- A descrição e a demonstração incluem conversas por voz, respostas sobre objetos e ambiente, controle de luz/ar-condicionado, música, personagens 3D, animações, expressões e um aplicativo Android para escolher personagem, controlar luz e ligar/desligar rastreamentos.
- Na demonstração, a assistente comenta a aparência do usuário, identifica um multímetro e pergunta sobre o trabalho em andamento; depois ajusta luz e ar-condicionado por pedido e inicia música. Isso demonstra a interface apresentada no vídeo, mas não comprova a segurança do controle de aparelhos.
- O áudio usa alto-falante e controle físico de volume. Um interruptor físico corta a alimentação da câmera e do microfone.
- O criador informa que os personagens 3D foram desenhados pela equipe. Esses modelos são conteúdo próprio do vídeo e não fazem parte dos arquivos de referência do Nivus.

### Referências de peças e conjuntos mostrados

O vídeo ajuda a identificar categorias e alguns parâmetros, mas não fornece uma BOM completa, códigos de fabricante, links de compra, esquemas elétricos nem especificações suficientes para copiar a montagem sem validação.

| Peça/conjunto | Referência citada ou mostrada | O que ainda não foi identificado |
| --- | --- | --- |
| Display | OLED de 5,5 polegadas; protótipo inicial ligado a um laptop por HDMI | Fabricante, modelo, resolução, brilho e interface da unidade final |
| Computador embarcado | Orange Pi | Modelo exato, RAM, armazenamento e acelerador; o nome ouvido na transcrição automática não é confiável o bastante para fixar uma versão |
| Conjunto óptico | Película/espelho semitransparente, cilindro/cobertura transparente, fundo preto e difusor em meia-lua | Material, espessura, dimensões, geometria e tratamento óptico |
| Iluminação | Faixa ARGB endereçável | Tipo/quantidade de LEDs, tensão, corrente, controlador e difusão final |
| Câmera | Câmera USB para acompanhar a pessoa | Fabricante, sensor, lente, resolução e campo de visão |
| Base motorizada | Motorredutor, base giratória e rolamentos; a transcrição menciona cinco rolamentos, contagem a confirmar | Modelo e relação do motor, quantidade/tipo de rolamentos, torque, velocidade e limites mecânicos |
| Feedback de posição | Potenciômetro ligado por engrenagem ao mecanismo | Modelo, curso, resolução, montagem e calibração |
| Eletrônica de controle | Três PCBs relatadas: duas para LEDs e uma para controle/comunicação de LEDs, alto-falante e motor | Esquemas, componentes, microcontrolador, drivers, conectores e arquivos das placas |
| Áudio | Alto-falante e controle físico de volume | Modelos, potência, amplificador e microfone usado na versão final |
| Protótipos ópticos | Pirâmide de quatro peças transparentes sobre um celular e peça refletiva impressa em 3D | Material e medidas exatos; foram experiências iniciais, não a solução final |

O vídeo descreve um motorredutor com realimentação por potenciômetro; isso não confirma o uso de motor de passo na proposta Nivus. Esses dados servem para orientar pesquisa e prototipagem, não para emitir uma lista de compras.

## Adaptação proposta pelo operador

O operador descreveu uma assistente de mesa com tela, efeitos de iluminação, motor de passo, ESP32-CAM, microfone e um computador para processar imagem e áudio, acompanhar a pessoa, reconhecer rostos e atender comandos. Essa é a lista da proposta do Nivus; o vídeo, por sua vez, descreve câmera USB, motorredutor com feedback de posição e Orange Pi. Os componentes não devem ser tratados como equivalentes até que a seleção seja feita.

Preferências já definidas pelo operador: usar uma exibição refletiva inspirada no Project NOVA; combinar o traje azul-marinho/dourado com elementos steampunk; permitir identificação facial somente após ativação explícita. A ativação deve começar desligada. O tamanho da tela, o método dessa ativação e a política de processamento/armazenamento ainda não foram definidos.

O computador principal poderá ser o host Nivus disponível, mas o desempenho ainda precisa ser medido. O microcontrolador deve cuidar de periféricos e movimento; visão computacional, áudio e agente conversacional ficam em um processo substituível. A primeira integração com Home Assistant/Nivus deve ser somente de leitura e usar uma allowlist estreita para comandos posteriores.

```mermaid
flowchart LR
  Screen[Display e personagem 3D] <-->|imagem e estado| Host[Computador Nivus: visão, áudio e agente]
  Camera[Câmera local] -->|quadros temporários| Host
  Mic[Microfone com corte físico] -->|áudio temporário| Host
  Host -->|alvo limitado| MCU[Controlador de periféricos]
  MCU --> Driver[Driver do motor e limites físicos]
  Driver --> Motor[Base giratória]
  MCU --> LEDs[Iluminação e difusor]
  Host <-->|entidades allowlisted| HA[Home Assistant / Nivus]
  MCU --> Switch[Privacidade e parada manual]
  Switch -.corta energia de câmera/mic e inibe movimento.-> Camera
  Switch -.-> Mic
  Switch -.-> Driver
```

## Base visual para o modelo 3D

As imagens fornecidas pelo operador serão referências visuais para o avatar 3D, não para a eletrônica. A direção principal escolhida combina o traje azul-marinho com linhas douradas, cabelo curto escuro/azul, calça escura e botas altas com elementos steampunk das outras referências: gola/ombros estruturados, couro, fivelas, braceletes e ferragens metálicas. O objetivo é um único traje coeso, com desenho original, e não alternar entre dois personagens separados.

Para a criação do personagem, o pacote de arte deverá definir uma malha original ou licenciada, vistas ortográficas consistentes, escala, rig de cabeça/olhos/corpo, expressões, poses, gestos e sincronização labial. A resolução, o formato de exportação e o pipeline 3D ainda estão em aberto. As imagens não foram copiadas para este repositório; a origem e os direitos de uso precisam ser confirmados antes de publicar arte derivada ou distribuir o modelo.

O personagem na tela deve renderizar sobre fundo preto para apoiar a ilusão refletiva do display. A forma de tela, a película semitransparente e o difusor precisam ser testados juntos; uma tela comum em uma pirâmide de acrílico não garante a mesma imagem fora de um ângulo restrito.

## Mapa mental

```mermaid
mindmap
  root((Assistente de mesa Nivus))
    Avatar 3D
      Imagens do operador como referência
      Malha original ou licenciada
      Rig e expressões
      Voz e sincronização labial
    Exibição
      Ilusão refletiva escolhida como direção
      Tamanho do display ainda pendente
      Fundo preto
      Espelho semitransparente
      Invólucro e difusor
      Iluminação ARGB controlada
    Percepção local
      Câmera
      Rastreamento sem identidade por padrão
      Identificação facial somente após ativação explícita
      Ativação começa desligada
      Microfone e áudio
      Sem retenção bruta por padrão
    Movimento seguro
      Controlador separado
      Posição e deadband
      Limites mecânicos e de corrente
      Parada manual e watchdog
    Integração Nivus
      Home Assistant com escopo mínimo
      Começar em leitura
      Comandos não críticos por allowlist
      Sem decisão física baseada só em IA
```

## Privacidade, segurança e falhas

- Rastreamento de posição no quadro é o padrão inicial. O operador escolheu permitir reconhecimento facial de identidade somente quando explicitamente ativado; ele começa desligado. Ainda falta decidir como ativar, como registrar consentimento, quais identidades podem ser cadastradas e como revogar/excluir esses dados.
- Processamento local e ausência de gravação bruta por padrão são propostas de privacidade, ainda sem confirmação final. A política de quadros, áudio, embeddings faciais, transcrições, métricas, acesso e retenção precisa ser definida antes de implementar a identificação.
- Requisito físico proposto: um interruptor deve cortar a alimentação da câmera e do microfone e indicar claramente quando estão ativos. A necessidade e o desenho desse corte ainda aguardam confirmação do operador; botão de software sozinho não oferece isolamento físico.
- A perda do host, da rede, do heartbeat ou da posição deve interromper o movimento sem uma rotação corretiva inesperada. O controlador local aplica velocidade, curso e corrente máximos; incluir parada manual, watchdog e proteção contra aprisionamento.
- Reconhecimento facial, inferência ou voz não podem, isoladamente, destrancar portas, abrir portões, desligar alarmes ou controlar cargas críticas. Comandos comuns passam por allowlist determinística, confirmação adequada e registro sem conteúdo de voz.
- Começar com display/avatar e leitura somente. Câmera, movimento e controle doméstico entram em etapas separadas, primeiro simuladas e depois em dispositivos não críticos.

## Etapas e decisões em aberto

1. Transformar as referências visuais em um brief e modelo 3D original/licenciado, sem sensores nem movimento.
2. Testar display, reflexo, iluminação e difusor em uma estrutura estática; registrar o ângulo de visão útil e a legibilidade em ambiente iluminado.
3. Selecionar câmera e plataforma de processamento; medir detecção/rastreamento sem identificação. Especificar ativação explícita, consentimento, processamento local/remoto e retenção antes de habilitar reconhecimento facial.
4. Selecionar motor, driver, feedback de posição e estrutura; validar deadband, curso limitado, ruído, temperatura e parada manual.
5. Adicionar microfone/alto-falante com corte físico e interação local; só depois integrar comandos de baixo risco ao Home Assistant/Nivus.

Ainda precisam de decisão: tamanho/modelo do display; câmera USB ou ESP32-CAM; placa/controlador de motor; tipo de motor e feedback; microfone/alto-falante; computador e modelos locais; tecnologia de reconhecimento de fala/visão; ativação e gestão de consentimento para identidade facial; processamento local/remoto e retenção; corte físico dos sensores; dimensão e material do invólucro; formatos do modelo 3D; entidades domésticas permitidas.
