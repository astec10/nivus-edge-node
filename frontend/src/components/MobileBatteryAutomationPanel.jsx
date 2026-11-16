import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';

const MAX_REPORT_AGE_MS = 60 * 60 * 1000;
const MAX_FUTURE_SKEW_MS = 60 * 1000;

function hasFreshBatteryReading(device) {
  if (device.last_battery_percent == null || !device.last_observed_at) return false;
  const observedAt = Date.parse(device.last_observed_at);
  const age = Date.now() - observedAt;
  return Number.isFinite(observedAt) && age >= -MAX_FUTURE_SKEW_MS && age <= MAX_REPORT_AGE_MS;
}

function formatBatteryReading(device) {
  if (device.last_battery_percent == null) return 'Aguardando leitura';
  const freshness = hasFreshBatteryReading(device) ? 'leitura recente' : 'leitura desatualizada';
  return `Bateria ${device.last_battery_percent}% · ${freshness} · ${formatObservedAt(device.last_observed_at)}`;
}

function formatObservedAt(value) {
  if (!value) return 'horário indisponível';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function MobileBatteryAutomationPanel({ token }) {
  const [devices, setDevices] = useState([]);
  const [deviceName, setDeviceName] = useState('');
  const [createdCredential, setCreatedCredential] = useState(null);
  const [status, setStatus] = useState('As leituras móveis não usam a bateria interna do nó.');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const activeDevices = devices.filter(device => device.active);
  const freshDeviceCount = activeDevices.filter(hasFreshBatteryReading).length;
  const automationStatus = activeDevices.length === 0
    ? 'Aguardando cadastro'
    : freshDeviceCount > 0
      ? `Ativa · ${freshDeviceCount} leitura(s) recente(s)`
      : 'Cadastrada · sem leitura recente';

  const loadDevices = useCallback(async () => {
    try {
      const response = await axios.get('/api/mobile-battery/devices', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setDevices(response.data || []);
      setLoading(false);
    } catch (error) {
      setLoading(false);
      setStatus(error.response?.data?.detail || 'Não foi possível consultar os celulares cadastrados.');
    }
  }, [token]);

  useEffect(() => {
    void loadDevices();
    const interval = window.setInterval(loadDevices, 30000);
    return () => window.clearInterval(interval);
  }, [loadDevices]);

  const createDevice = async event => {
    event.preventDefault();
    setBusy(true);
    setStatus('Cadastrando dispositivo…');
    try {
      const response = await axios.post(
        '/api/mobile-battery/devices',
        { name: deviceName },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      setCreatedCredential(response.data);
      setDeviceName('');
      setStatus('Dispositivo cadastrado. Copie agora o token exibido; ele não será mostrado novamente.');
      await loadDevices();
    } catch (error) {
      setStatus(error.response?.data?.detail || 'Não foi possível cadastrar o dispositivo.');
    } finally {
      setBusy(false);
    }
  };

  const copyToken = async () => {
    try {
      await navigator.clipboard.writeText(createdCredential.token);
      setStatus('Token copiado. Guarde-o somente nos segredos do Home Assistant.');
    } catch {
      setStatus('Cópia automática indisponível. Selecione e copie o token exibido.');
    }
  };

  const revokeDevice = async device => {
    if (!window.confirm(`Revogar o dispositivo “${device.name}”? Ele deixará de comandar o relé.`)) return;
    setBusy(true);
    try {
      await axios.delete(`/api/mobile-battery/devices/${encodeURIComponent(device.device_id)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setCreatedCredential(null);
      setStatus('Credencial revogada; novos relatórios desse celular serão rejeitados.');
      await loadDevices();
    } catch (error) {
      setStatus(error.response?.data?.detail || 'Não foi possível revogar o dispositivo.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="settings-card" aria-labelledby="mobile-battery-title">
      <div className="settings-card-heading">
        <div>
          <h3 id="mobile-battery-title">Automação por bateria móvel</h3>
          <p>Cadastre somente celulares associados ao relé principal. Cada token é mostrado uma única vez e pode ser revogado aqui.</p>
        </div>
        <span className="maintenance-status" role="status">
          {automationStatus}
        </span>
      </div>

      <p className="settings-explanation">
        Uma leitura autenticada e recente de até 20% envia OFF uma vez por ciclo baixo. Acima de 20% apenas rearma a regra; nunca envia ON. Sem leitura recente, após reinício ou durante falha de origem, nenhum comando é enviado. Se houver mais de um celular ativo, qualquer um com leitura recente em 20% ou menos pode enviar OFF. O broker só informa aceitação; não confirma o estado físico.
      </p>

      <form className="mobile-battery-device-form" onSubmit={createDevice}>
        <label className="display-preference-field">
          <span>Nome do celular</span>
          <input
            type="text"
            value={deviceName}
            onChange={event => setDeviceName(event.target.value)}
            maxLength={48}
            pattern="[A-Za-z0-9 _.-]+"
            autoComplete="off"
            required
            disabled={busy}
            placeholder="Ex.: telefone principal"
          />
        </label>
        <button className="maintenance-toggle" type="submit" disabled={busy || !deviceName.trim()}>
          {busy ? 'Aguarde…' : 'Cadastrar celular'}
        </button>
      </form>

      {createdCredential && (
        <div className="mobile-battery-once-token" role="alert">
          <strong>Token exibido uma única vez</strong>
          <p>Copie-o para o arquivo de segredos do Home Assistant. Não o envie por Issue, log ou chat. Se perder, revogue este dispositivo e crie outro.</p>
          <code tabIndex={0}>{createdCredential.token}</code>
          <div className="mobile-battery-controls">
            <button className="maintenance-toggle" type="button" onClick={copyToken}>Copiar token</button>
            <button className="maintenance-toggle" type="button" onClick={() => setCreatedCredential(null)}>Ocultar token</button>
          </div>
        </div>
      )}

      <ul className="mobile-battery-device-list" aria-label="Celulares associados ao relé">
        {devices.map(device => (
          <li className="mobile-battery-device-row" key={device.device_id}>
            <div className="mobile-battery-device-meta">
              <strong>{device.name}</strong>
              <span>{device.active ? 'Automação ativa' : 'Credencial revogada'}</span>
              <span>
                {formatBatteryReading(device)}
              </span>
              {device.low_battery_latched && <small>OFF enviado nesta faixa baixa; aguarda recuperação acima de 20% para rearmar.</small>}
            </div>
            {device.active && (
              <button
                className="mobile-battery-revoke"
                type="button"
                disabled={busy}
                onClick={() => revokeDevice(device)}
              >
                Revogar
              </button>
            )}
          </li>
        ))}
      </ul>

      {loading && <p role="status">Carregando dispositivos…</p>}
      {!loading && devices.length === 0 && <p>Nenhum celular associado.</p>}
      <p className="display-preference-save-status" role="status" aria-live="polite">{status}</p>
      <p className="settings-explanation">
        Configure o Home Assistant conforme <code>docs/MOBILE_BATTERY_AUTOMATION.md</code>. Use HTTPS com certificado confiável; a bateria interna do notebook/Nivus continua separada.
      </p>
    </section>
  );
}
