# Sensores de hardware e temperatura

## Base técnica

No Ubuntu, a fonte é o que o kernel e o driver realmente expõem em `hwmon`/sysfs. O agente atual usa `psutil.sensors_temperatures()` para ler esses sensores sem executar uma ferramenta externa a cada amostra. `lm-sensors` (`sensors`) é uma ferramenta opcional de diagnóstico e ajuda a descobrir nomes/labels, mas não instala um driver que o kernel não tem.

No Windows, LibreHardwareMonitor e o fork mantido de Open Hardware Monitor podem servir como referências visuais para sensores de CPU, GPU e placa-mãe. HWiNFO, CPU-Z e GPU-Z também ajudam a conferir identificação e leituras. Esses programas não são dependências nem provas de que o Ubuntu exponha o mesmo sensor. A cobertura Windows, Linux e cada chipset deve ser testada separadamente.

## Contrato das métricas

- `temperature` é a temperatura CPU/APU selecionada, para preservar os clientes antigos.
- `temperature_source` conserva driver e label para a UI e para auditoria da amostra.
- `cpu_hotspot_temperature`/`cpu_hotspot_source` são opcionais e só recebem valor se o driver rotular explicitamente uma leitura de CPU/APU como `hotspot` ou `junction`; não são inferidos das temperaturas de pacote/núcleo.
- `motherboard_temperature`/`motherboard_temperature_source` e `gpu_temperature`/`gpu_temperature_source` são valores independentes e opcionais.
- `gpu_hotspot_temperature`/`gpu_hotspot_source` representam somente uma leitura explicitamente rotulada `hotspot` ou `junction` pelo driver da GPU. Não são inferidos a partir da temperatura comum da GPU.
- Sensor ausente, inacessível ou sem identificação confiável permanece `null`; a UI apresenta `N/D`. Não usar zero, ACPI genérico nem a última amostra antiga como substituto.
- Para Intel, preferir o pacote `coretemp` a sensores ACPI genéricos. Para AMD, preferir `Tdie` quando disponível; `Tctl` só deve ser rotulado conforme a semântica fornecida pelo driver. Uma APU pode não expor uma leitura térmica separada da CPU ou GPU.
- Identificar placa/GPU pelo driver e label. Uma zona `acpitz` ou `thermal_zone0` isolada não prova que a leitura seja CPU ou placa-mãe.

As colunas de origem, hotspots, placa-mãe e GPU são adicionadas por migração SQLite aditiva. Registros antigos sem `temperature_source` são mantidos, mas não são plotados como temperatura da CPU.

## Gráficos e detalhes na interface

O dashboard separa séries de temperatura (°C), uso (CPU/memória/disco em %) e potência estimada (W), para que escalas diferentes não escondam a variação térmica. O usuário pode escolher 5, 15, 30 ou 60 minutos, ou todas as até 1000 amostras recebidas pela API. O alcance real em tempo depende da cadência e da disponibilidade da coleta.

Os cartões de métricas e os pontos do gráfico exibem detalhes depois de 3 segundos de foco/hover. CPU/APU e GPU podem mostrar hotspot dentro desses detalhes quando a fonte está explícita; o hotspot não é um cartão nem uma linha permanente do gráfico, e aparece apenas no detalhe após 3 segundos. Não há hotspot para placa-mãe. Mínimo e máximo são calculados apenas sobre as amostras válidas do período selecionado; não representam extremos históricos ou limites seguros do componente. GPU, hotspots e placa-mãe sem sensor disponível aparecem como `N/D`. O painel informa o horário da amostra mais recente para diferenciar um valor térmico estável de uma coleta parada.

## Evidência observada no CCE U25

No notebook de referência, um Intel Celeron 847 com Ubuntu x86_64 expõe `coretemp` (pacote e núcleos) e `acpitz`. Uma consulta do sistema mostrava aproximadamente 55 °C no pacote e 53–54 °C nos núcleos, enquanto `acpitz` reportava 29,8 °C. O banco histórico permanecia em 29,8 °C: o coletor anterior selecionava o primeiro sensor disponível e o rotulava genericamente como temperatura da CPU.

Durante uma carga curta e limitada de CPU, o pacote `coretemp` variou de 55 °C para 61 °C. A função candidata escolheu `coretemp: Package id 0`; em uma leitura posterior, mediu 57 °C. Não foi encontrado sensor de temperatura de GPU Intel nem da placa-mãe exposto pelo driver naquele host. Por isso, os cartões correspondentes devem mostrar `N/D` nesse notebook.

Esta observação comprova o bug e a fonte no CCE U25. Não demonstra suporte a todas as CPUs, placas-mãe, GPUs, BIOS ou versões do Linux. Para ampliar a matriz, validar ao menos Intel e AMD, GPU integrada e dedicada, e comparar fontes equivalentes (pacote com pacote).

## Implementação e limites

`telemetry/hardware_sensors.py` classifica fontes conhecidas e labels; falha de API ou leitura inválida não interrompe o restante da coleta. `telemetry/agent.py` publica os campos opcionais; `backend/mqtt_worker.py` valida e grava os campos; `backend/database.py` migra o schema sem apagar histórico; os componentes em `frontend/src/components/` diferenciam CPU/APU, placa-mãe, GPU e hotspots identificados. A interface mostra também frescor da amostra, alertas registrados e auditoria MQTT; o aceite do broker não confirma o estado físico do atuador.

O pacote não instala `lm-sensors`, não executa `sensors-detect` automaticamente e não carrega módulos do kernel. Se uma placa não expõe o sensor, a correção apropriada é registrar essa limitação ou acrescentar suporte explícito ao driver, não adivinhar o componente.

## Fontes upstream

### Comparadores Windows

- **Open Hardware Monitor original (`openhardwaremonitor/openhardwaremonitor`) é legado.** Na consulta de 14/11/2026, a página oficial de releases não listava versões empacotadas; manter como referência histórica, não como dependência.
- **LibreHardwareMonitor** é a referência open source preferida para comparar sensores no Windows. A leitura no Windows não comprova que o Ubuntu exponha o mesmo sensor.
- **HardwareMonitor/OpenHardwareMonitor** é um fork separado baseado no projeto original e publica releases próprios. Não confundir os dois repositórios; conferir os requisitos de privilégio/driver antes de executar.
- HWiNFO, CPU-Z e GPU-Z servem como referências de identificação e leitura, não como dependências do Nivus.

- [Open Hardware Monitor original: releases](https://github.com/openhardwaremonitor/openhardwaremonitor/releases)
- [HardwareMonitor/OpenHardwareMonitor: releases do fork](https://github.com/HardwareMonitor/OpenHardwareMonitor/releases)

- [Linux kernel hwmon sysfs interface](https://docs.kernel.org/hwmon/sysfs-interface.html)
- [lm-sensors](https://github.com/lm-sensors/lm-sensors)
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
- [HardwareMonitor/OpenHardwareMonitor](https://github.com/HardwareMonitor/OpenHardwareMonitor)
