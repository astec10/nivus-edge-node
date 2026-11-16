---
id: nivus-mobile-battery-relay
title: "Automação limitada do relé pela bateria do celular"
topic: home-automation
source: docs/MOBILE_BATTERY_AUTOMATION.md
verified_on: 2026-11-16
confidence: implementation-candidate
tags: mobile-battery, home-assistant, actuator, mqtt, safety
---

O mantenedor solicitou desligar o relé principal quando a bateria de um telefone associado chegar a 20% ou menos. A bateria interna do nó e o banco de 48 V do inversor são fontes diferentes. A proposta usa uma entidade de bateria do Home Assistant Companion App e uma credencial aleatória por telefone.

A regra deve enviar somente OFF com leitura recente, identificada, autenticada, dentro de 0–100 e não repetida. Acima de 20%, a leitura apenas rearma o próximo ciclo baixo; nunca enviar ON pela recuperação. Leituras ausentes, expiradas, futuras, repetidas, revogadas e falhas do broker não podem emitir ON. O broker não confirma o estado físico. O destino fica fixo no allowlist do serviço Nivus; o Home Assistant não recebe credenciais MQTT.

Referência de configuração, contrato HTTP e limites de frescor: docs/MOBILE_BATTERY_AUTOMATION.md. A validação do PR usa leituras simuladas e publisher MQTT em mock; isso não substitui uma validação física autorizada.
