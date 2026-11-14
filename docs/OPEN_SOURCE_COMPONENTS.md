# Catálogo de componentes open source candidatos

Revisado: 2026-11-14. A lista organiza opções para investigação; não significa que foram instaladas, aprovadas para produção ou integradas ao Nivus. Links apontam aos projetos/fontes primárias.

## Produtividade de desenvolvimento

| Ferramenta | Uso possível | Prioridade | Limite |
| --- | --- | --- | --- |
| [ShellCheck](https://github.com/koalaman/shellcheck) | Detectar erros comuns e práticas inseguras em scripts Bash/sh, inclusive deploy. | Alta, somente CI/desenvolvimento. | Não prova segurança nem substitui execução num Ubuntu descartável. Não instalar na imagem de runtime. |
| [actionlint](https://github.com/rhysd/actionlint) | Validar workflows GitHub Actions, expressões e parâmetros. | Alta, somente CI/desenvolvimento. | Complementa, não substitui, a execução real do workflow. |
| [Ruff](https://github.com/astral-sh/ruff) | Lint e formatação de Python com execução rápida. | Alta para lint; adotar formatação depois de definir baseline. | Evitar formatar todo o backend sem revisão do diff. Não adicionar ao container de produção. |

Essas ferramentas têm baixo impacto no nó porque podem rodar no CI e no ambiente de contribuição, fora das imagens distribuídas.

## Backup, recuperação e SQLite

| Projeto | Uso possível | Prioridade | Limite |
| --- | --- | --- | --- |
| [restic](https://github.com/restic/restic) | Criptografar, deduplicar e enviar arquivos de backup para disco ou backend remoto. | Avaliar depois de estabilizar o backup SQLite existente. | Empacotar primeiro o snapshot consistente produzido pelo deploy/backup.sh; não copiar o banco/WAL ativo como se fosse uma cópia íntegra. Guardar chave do repositório fora do host. |
| [Litestream](https://github.com/benbjohnson/litestream) | Replicar continuamente SQLite/WAL para armazenamento local ou remoto compatível. | Piloto separado, com leitura e restauração em banco descartável. | Acrescenta agente, configuração e manutenção; a documentação do projeto informa que cria a tabela _litestream_lock na base de origem. Não substituir backup/restore existente antes de medir e validar. |

Restic e Litestream resolvem problemas diferentes: arquivo de backup versionado versus replicação contínua. Nenhum deles substitui o procedimento de restauração/rollback já documentado.

## Sensores e métricas do host

| Projeto/fonte | Uso possível | Prioridade | Limite |
| --- | --- | --- | --- |
| [Linux hwmon](https://docs.kernel.org/hwmon/sysfs-interface.html) | Interface de kernel para sensores, labels, unidades e canais. | Fonte principal para sensores Linux. | Os nomes/canais variam conforme driver, placa e firmware; não há um número de canal universal para CPU. |
| [lm-sensors](https://github.com/lm-sensors/lm-sensors) | Descoberta e diagnóstico de chips e fontes hwmon em Ubuntu. | Ferramenta de diagnóstico; comparar com /sys/class/hwmon no host. | Não inventar valor quando o driver não expõe sensor confiável; não é necessário executar um daemon adicional por padrão. |
| [node_exporter](https://github.com/prometheus/node_exporter) | Exportar várias métricas Linux para Prometheus. | Somente se a arquitetura de métricas for ampliada. | Pode duplicar o agente atual e expor um endpoint e coletores adicionais. Avaliar superfície, consumo e política de rede antes. |
| [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) | Diagnóstico mais amplo de sensores no Windows, quando necessário. | Referência para ferramenta Windows; não é o coletor Linux do Nivus. | API e disponibilidade de sensores dependem de hardware e permissões. |
| [Open Hardware Monitor original](https://github.com/openhardwaremonitor/openhardwaremonitor) e [página de releases](https://github.com/openhardwaremonitor/openhardwaremonitor/releases) | Referência histórica para sensores Windows. | Legado; usar somente para comparação. | O upstream original é legado e sua página de releases não apresenta uma versão recente. Não confundir com forks independentes. |

A correção de temperatura deve ser baseada no driver, label e unidade observados na máquina. Para o objetivo Ubuntu, use kernel/hwmon e lm-sensors no diagnóstico; os programas Windows citados pelo usuário são referências comparativas.

## Automação residencial e dispositivos

| Projeto | Integração possível | Prioridade | Limite |
| --- | --- | --- | --- |
| [Home Assistant](https://github.com/home-assistant/core) | Adaptador opcional para entidades, estados e serviços da casa. Há APIs [REST](https://developers.home-assistant.io/docs/api/rest/) e [WebSocket](https://developers.home-assistant.io/docs/api/websocket/). | Fase futura; começar por leitura. | Manter credenciais separadas, permissões mínimas e comportamento local se a integração falhar. |
| [Zigbee2MQTT](https://github.com/Koenkk/zigbee2mqtt) | Ponte entre adaptador Zigbee e MQTT, útil para sensores Zigbee. | Fase futura; depende de hardware USB/serial e ACL MQTT. | Compatibilidade depende do coordenador, firmware e dispositivo. Não publicar MQTT na rede sem autenticação/ACL. |
| [ESPHome](https://github.com/esphome/esphome) | Construção e gestão de firmware para dispositivos ESP32/ESP8266. | Fase futura, por adaptador Home Assistant/MQTT. | Firmware, segurança de rede e atualizações dos dispositivos continuam responsabilidade do projeto. |
| [Frigate](https://github.com/blakeblackshear/frigate) | NVR local que publica eventos de detecção, inclusive via MQTT. | Serviço opcional num host separado com recursos adequados. | Processamento de vídeo pode exigir acelerador e muita memória/CPU. Integrar metadados; não permitir que uma detecção isolada abra portões. |

## Conhecimento e modelos de IA

| Projeto | Uso possível | Prioridade | Limite |
| --- | --- | --- | --- |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | Inferência local com modelos quantizados em CPU/GPU compatível. | Protótipo futuro separado do runtime básico. | Medir RAM, latência, temperatura e desempenho no hardware real; modelo local não garante qualidade ou segurança. |
| [LiteLLM](https://github.com/BerriAI/litellm) | Interface/proxy comum para diversos provedores e modelos. | Opcional, fora do núcleo do nó até existir política de custo. | Conta e APIs externas podem custar dinheiro e impor limites. Configurar armazenamento e orçamentos antes de depender de budgets; não alegar que modelos são gratuitos. |

## Critérios para aceitar uma dependência

Antes de propor um projeto ao Nivus, registre:
1. problema e módulo que o possui;
2. repositório upstream, atividade, licença e política de segurança;
3. protocolo e fronteira de dados, incluindo uso offline;
4. RAM, CPU, armazenamento, portas e permissões;
5. comportamento em timeout, reinício e falha de rede;
6. manutenção, atualização, backup, rollback e estratégia de remoção;
7. validação num ambiente descartável e por que uma implementação própria seria pior.

## Decisão atual

Apenas ShellCheck, actionlint e Ruff são recomendados como ferramentas de desenvolvimento/CI de baixo risco. restic, Litestream, node_exporter, integrações domésticas, Frigate, llama.cpp e LiteLLM continuam candidatos para avaliações separadas. Nenhum novo runtime, serviço ou dependência foi instalado por causa deste catálogo.