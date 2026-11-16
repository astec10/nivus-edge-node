# Automação do relé por bateria móvel

Este módulo usa a bateria de um celular reportada pelo Home Assistant Companion App. Ela é separada da bateria interna do computador Nivus e da bateria de 48 V do inversor.

## Regra e estado persistente

Cada celular cadastrado em Configuração → Automação por bateria móvel fica associado ao relé nivus/edge/relay1. Fontes ativas continuam cadastradas após reiniciar o Nivus; a regra só age após receber uma leitura autenticada, nova e recente.

- battery_percent precisa ser inteiro entre 0 e 100.
- observed_at deve ser ISO 8601 com fuso horário, no máximo 60 segundos no futuro e não mais antiga que 60 minutos.
- Uma leitura de 20% ou menos envia somente OFF, uma vez por ciclo baixo.
- Uma leitura acima de 20% rearma a regra, mas nunca envia ON.
- Leituras ausentes, antigas, repetidas ou fora de ordem, fontes revogadas e falha do broker não enviam ON.
- Falha do broker limita novas tentativas de OFF a uma por cinco minutos.
- A aceitação MQTT não comprova o estado físico do relé; o painel deixa isso explícito.
- Se mais de um celular estiver cadastrado, qualquer fonte ativa que reporte 20% ou menos pode desligar o relé.

O token aleatório de cada celular é exibido uma única vez na criação. O banco guarda somente SHA-256 do token. A lista e os logs nunca devolvem a credencial. Revogue e crie outro token se houver perda ou suspeita de exposição.

## Endpoints

Os endpoints de cadastro e revogação exigem sessão de administrador:

- GET /api/mobile-battery/devices: lista fontes cadastradas, sem credenciais.
- POST /api/mobile-battery/devices: cria associação; corpo {"name":"telefone principal"}. A resposta contém o token apenas nessa chamada.
- DELETE /api/mobile-battery/devices/{device_id}: revoga uma associação.
- POST /api/mobile-battery/report: recebe relatório de uma fonte, usando o header X-Nivus-Device-Token.

Corpo do relatório:

~~~json
{
  "battery_percent": 20,
  "observed_at": "2026-11-16T18:30:00-03:00"
}
~~~

O endpoint de relatório aceita somente a credencial própria do celular; ele não aceita tópicos, comandos ou nomes de relé fornecidos pelo cliente. O destino é fixo em nivus/edge/relay1. Não forneça credenciais MQTT ao Home Assistant e não exponha o broker à rede.

## Configuração no Home Assistant

1. Ative o sensor de bateria no Home Assistant Companion App e localize a entidade real do telefone, por exemplo sensor.telefone_principal_battery_level. O nome varia por instalação.
2. Cadastre o aparelho na dashboard Nivus e copie o token exibido. Guarde-o em secrets.yaml do Home Assistant, fora do Git:

   ~~~yaml
   nivus_phone_battery_token: "COLE_O_TOKEN_AQUI"
   ~~~

3. Configure o comando REST abaixo substituindo <NIVUS_HOST> pelo DNS/IP cujo certificado HTTPS seja confiável para o Home Assistant:

   ~~~yaml
   rest_command:
     nivus_mobile_battery_report:
       url: "https://<NIVUS_HOST>/api/mobile-battery/report"
       method: POST
       verify_ssl: true
       headers:
         X-Nivus-Device-Token: !secret nivus_phone_battery_token
         Content-Type: application/json
       payload: >-
         {"battery_percent": {{ battery_percent | int }},
          "observed_at": "{{ observed_at }}"}
   ~~~

4. Adicione uma automação para reportar mudança de bateria e estado atual ao iniciar o Home Assistant. Troque a entidade de exemplo pelo sensor correto:

   ~~~yaml
   automation:
     - alias: Reportar bateria móvel ao Nivus
       trigger:
         - platform: state
           entity_id: sensor.telefone_principal_battery_level
         - platform: homeassistant
           event: start
       variables:
         battery_level: "{{ states('sensor.telefone_principal_battery_level') | float(-1) }}"
         observed_at: >-
           {{ as_timestamp(states.sensor.telefone_principal_battery_level.last_updated, 0)
              | timestamp_custom('%Y-%m-%dT%H:%M:%S%z', true) }}
       condition:
         - condition: template
           value_template: "{{ 0 <= (battery_level | float(-1)) <= 100 }}"
       action:
         - service: rest_command.nivus_mobile_battery_report
           data:
             battery_percent: "{{ battery_level | int }}"
             observed_at: "{{ observed_at }}"
   ~~~

5. Garanta que o Home Assistant confia no certificado do Nivus. Mantenha verify_ssl: true; não desative a validação TLS para contornar certificado local.
6. Confirme na dashboard que a fonte mostra uma leitura recente. Não teste com relé físico conectado: a suíte automatizada simula relatórios e substitui o publisher MQTT por mock.

O sensor móvel pode atualizar em intervalos diferentes conforme o telefone/OS e as permissões de segundo plano. O Nivus ignora relatórios quando o horário observado ultrapassa a janela de frescor; ele não usa um timestamp de envio recente para mascarar uma leitura antiga.

Documentação oficial:

- https://companion.home-assistant.io/docs/core/sensors/
- https://www.home-assistant.io/integrations/rest_command/
