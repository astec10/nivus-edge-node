# Estratégia de validação do Nivus

O Nivus não precisa repetir uma instalação manual completa em cada computador a cada mudança. A validação é dividida em três camadas: CI em runners Linux descartáveis hospedados pelo GitHub, uma matriz pequena de máquinas físicas representativas e verificações específicas dos periféricos que realmente serão usados. Nenhuma VM precisa ser iniciada no computador do operador.

## 1. Cada alteração: runner remoto de CI

O workflow [`Ubuntu VM validation`](../.github/workflows/ubuntu-ci.yml) roda num runner hospedado novo com Ubuntu 22.04 amd64 em cada pull request para `main`, push em `main` ou execução manual. O ambiente remoto é descartável e não usa o computador do operador. Ele:

1. valida a sintaxe dos scripts shell e compila os módulos Python;
2. valida o arquivo Compose e constrói as imagens;
3. inicia API, worker, Mosquitto e painel numa stack isolada;
4. verifica health HTTPS, frontend, resposta `401` sem autenticação e ingestão MQTT até SQLite;
5. registra uso instantâneo de CPU e memória dos containers;
6. encerra os containers temporários sem depender de serviços do notebook.

Esse ciclo detecta regressões de código e instalação com baixo esforço. O runner de CI é um Linux x86_64 virtualizado remoto, mas não representa cada chipset, BIOS, placa de rede, disco ou sensor disponível.

## 2. Marcos de compatibilidade: seis plataformas de referência

Para uma declaração de compatibilidade x86_64 com Intel e AMD, selecionar seis máquinas físicas de referência:

| Grupo | Fabricante | Faixa de geração | Objetivo |
| --- | --- | --- | --- |
| I-antigo | Intel | Antiga, ainda capaz de executar Ubuntu 22.04 amd64 | Verificar boot, drivers e orçamento mínimo de recursos |
| I-intermediário | Intel | Geração intermediária | Verificar uma plataforma comum de uso geral |
| I-recente | Intel | Geração recente disponível no laboratório | Confirmar compatibilidade com plataforma atual |
| A-antigo | AMD | Antiga, ainda capaz de executar Ubuntu 22.04 amd64 | Verificar boot, drivers e orçamento mínimo de recursos |
| A-intermediário | AMD | Geração intermediária | Verificar uma plataforma comum de uso geral |
| A-recente | AMD | Geração recente disponível no laboratório | Confirmar compatibilidade com plataforma atual |

As faixas devem ser preenchidas com o modelo exato de CPU, placa-mãe, BIOS/UEFI, controlador de rede e armazenamento quando o hardware for escolhido. Não é necessário testar todas as placas-mãe ou todos os modelos de CPU. Se duas referências compartilharem o mesmo chipset, controlador de rede e tipo de armazenamento, elas podem cobrir comportamento semelhante; diferenças de firmware e periféricos ainda precisam ser registradas.

## 3. Bateria física de compatibilidade

Executar a bateria completa no primeiro ciclo de qualificação e novamente quando uma mudança afetar instalação, kernel, acesso ao host, sistema de arquivos, rede ou periféricos:

- instalar Ubuntu Server minimal amd64 e registrar modelo, firmware, recursos e versão;
- instalar a stack Nivus a partir de clone limpo, sem diretórios de staging;
- reiniciar e confirmar serviços, painel, health, autenticação e dados persistentes;
- observar telemetria por pelo menos 30 minutos e verificar que o SQLite continua íntegro;
- registrar RAM/CPU em repouso, durante build e durante ingestão, além de espaço em disco;
- testar Ethernet e o controlador de armazenamento; anotar drivers ou ajustes manuais;
- salvar resultado por commit, sem capturar senhas, tokens, chaves, endereços domésticos ou dados pessoais.

Sensores, dongles Zigbee, medidores, câmeras, inversores e placas especiais têm testes próprios por modelo e driver. Uma máquina sem esses periféricos não valida essa integração.

## 4. Perfis de recursos

O CI verifica os limites cgroup definidos no Compose e mostra a memória/CPU instantânea dos containers. Isso não equivale a impor ao sistema convidado o mesmo total de RAM/CPU nem substitui medição sustentada. Para cada máquina de referência, testar primeiro o perfil mínimo documentado e depois registrar a configuração real. Não declarar RAM mínima certificada até existir medição de instalação, build, operação, reboot e atualização.

## 5. Como relatar compatibilidade

Manter uma linha por plataforma no relatório de release com: fabricante/faixa, modelo exato, BIOS/UEFI, placa-mãe/chipset, NIC, armazenamento, RAM, Ubuntu, commit, duração, resultado e observações. Uma falha numa referência deve ser corrigida ou documentada como limitação antes de anunciar suporte àquela faixa.

Passar CI significa que o fluxo de software passou no runner Ubuntu 22.04 amd64. Só depois da bateria de seis máquinas será correto dizer que o Nivus foi validado em seis plataformas de referência; isso ainda não promete compatibilidade universal com todo hardware x86_64.

