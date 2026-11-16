import React, { lazy, Suspense, useEffect, useState, useRef } from 'react';
import axios from 'axios';
import PasswordChangeModal from './components/PasswordChangeModal';
import DashboardHeader from './components/DashboardHeader';
import DashboardNavigation from './components/DashboardNavigation';
import LoginPanel from './components/LoginPanel';
import UserManagementPanel from './components/UserManagementPanel';
import DashboardPanel from './components/DashboardPanel';
import SettingsPanel from './components/SettingsPanel';
const LegacyDashboardPanel = lazy(() => import('./components/LegacyDashboardPanel'));
import LegalNotice from './components/LegalNotice';
import { thresholdOrDefault } from './utils/telemetry';
import { DEFAULT_DISPLAY_PREFERENCES, loadDisplayPreferences, normalizeDisplayPreferences, saveDisplayPreferences } from './utils/displayPreferences';

const API_BASE = '';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboardVersion, setDashboardVersion] = useState(() => localStorage.getItem('nivus_dashboard_version') === 'legacy' ? 'legacy' : 'current');
  const [legacyRelayState, setLegacyRelayState] = useState(false);
  const [telemetry, setTelemetry] = useState([]);
  const [systemLogs, setSystemLogs] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [alertsHistory, setAlertsHistory] = useState([]);
  const [settings, setSettings] = useState({ temp_threshold: '75', cpu_threshold: '90' });
  const [usersList, setUsersList] = useState([]);
  const [isOnline, setIsOnline] = useState(false);
  const [error, setError] = useState(null);
  
  const [token, setToken] = useState(localStorage.getItem('nivus_token') || '');
  const [displayPreferenceState, setDisplayPreferenceState] = useState(() => ({ owner: 'guest', value: { ...DEFAULT_DISPLAY_PREFERENCES } }));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginExpanded, setLoginExpanded] = useState(false);

  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('viewer');

  const [editingUser, setEditingUser] = useState(null);
  const [adminAuthPassword, setAdminAuthPassword] = useState('');
  const [targetNewPassword, setTargetNewPassword] = useState('');
  const [targetConfirmPassword, setTargetConfirmPassword] = useState('');

  const [actuatorMessage, setActuatorMessage] = useState('');
  const [settingsStatus, setSettingsStatus] = useState('');
  const [maintenanceState, setMaintenanceState] = useState(null);
  const [maintenanceMessage, setMaintenanceMessage] = useState('');
  const [maintenanceBusy, setMaintenanceBusy] = useState(false);
  const [hostTimeSync, setHostTimeSync] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [soundStatus, setSoundStatus] = useState('Aviso sonoro do navegador desativado.');

  const parseJwt = (t) => {
    try { return JSON.parse(atob(t.split('.')[1])); } catch { return null; }
  };

  const userPayload = token ? parseJwt(token) : null;
  const displayPreferenceOwner = userPayload?.sub || 'guest';
  const displayPreferences = displayPreferenceState.owner === displayPreferenceOwner
    ? displayPreferenceState.value
    : DEFAULT_DISPLAY_PREFERENCES;

  useEffect(() => {
    setDisplayPreferenceState({ owner: displayPreferenceOwner, value: loadDisplayPreferences(displayPreferenceOwner) });
  }, [displayPreferenceOwner]);

  const handleDisplayPreferenceChange = (changes) => {
    const current = displayPreferenceState.owner === displayPreferenceOwner
      ? displayPreferenceState.value
      : loadDisplayPreferences(displayPreferenceOwner);
    const next = normalizeDisplayPreferences({ ...current, ...changes });
    setDisplayPreferenceState({ owner: displayPreferenceOwner, value: next });
    return saveDisplayPreferences(displayPreferenceOwner, next);
  };
  const handleToggleDashboardVersion = () => {
    const nextVersion = dashboardVersion === 'current' ? 'legacy' : 'current';
    setDashboardVersion(nextVersion);
    localStorage.setItem('nivus_dashboard_version', nextVersion);
  };
  const passwordChangeRequired = userPayload?.password_change_required === true;
  const isAdmin = userPayload?.role === 'admin';

  useEffect(() => {
    if (!token || passwordChangeRequired || activeTab !== 'settings') {
      if (!token || passwordChangeRequired) setHostTimeSync(null);
      return undefined;
    }
    let cancelled = false;
    const refreshHostTimeSync = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/settings/time-sync`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!cancelled) setHostTimeSync(response.data);
      } catch (err) {
        if (!cancelled) {
          setHostTimeSync({
            state: 'unavailable',
            can_configure: false,
            configured_servers: [],
            suggested_servers: ['a.ntp.br', 'b.ntp.br', 'c.ntp.br'],
            has_rollback: false,
            message: err.response?.data?.detail || 'Não foi possível consultar o estado do relógio do host.'
          });
        }
      }
    };
    void refreshHostTimeSync();
    const interval = setInterval(refreshHostTimeSync, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token, activeTab, passwordChangeRequired]);

  const alertAudioContextRef = useRef(null);
  const lastAlertTimeRef = useRef(0);

  const emitAlertTone = (audioCtx) => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.2);
  };

  const closeAlertAudioContext = () => {
    const audioCtx = alertAudioContextRef.current;
    alertAudioContextRef.current = null;
    if (audioCtx && audioCtx.state !== 'closed') {
      void audioCtx.close().catch(() => {});
    }
  };

  const playAlertSound = async () => {
    const audioCtx = alertAudioContextRef.current;
    if (!audioCtx || audioCtx.state === 'closed' || Date.now() - lastAlertTimeRef.current < 30000) return;
    try {
      if (audioCtx.state === 'suspended') await audioCtx.resume();
      if (audioCtx.state !== 'running') return;
      lastAlertTimeRef.current = Date.now();
      emitAlertTone(audioCtx);
    } catch {
      setSoundStatus('O navegador bloqueou a reprodução do aviso sonoro.');
    }
  };

  const handleToggleAlertSound = async () => {
    if (soundEnabled) {
      setSoundEnabled(false);
      setSoundStatus('Aviso sonoro do navegador desativado.');
      closeAlertAudioContext();
      return;
    }

    const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextConstructor) {
      setSoundStatus('Este navegador não oferece áudio para o aviso.');
      return;
    }

    let audioCtx;
    try {
      audioCtx = new AudioContextConstructor();
      await audioCtx.resume();
      alertAudioContextRef.current = audioCtx;
      setSoundEnabled(true);
      setSoundStatus('Som do navegador ativado; buzzer físico não está integrado.');
      lastAlertTimeRef.current = Date.now();
      emitAlertTone(audioCtx);
    } catch {
      if (audioCtx && audioCtx.state !== 'closed') void audioCtx.close().catch(() => {});
      alertAudioContextRef.current = null;
      setSoundStatus('Não foi possível ativar o áudio neste navegador.');
    }
  };

  useEffect(() => () => {
    const audioCtx = alertAudioContextRef.current;
    alertAudioContextRef.current = null;
    if (audioCtx && audioCtx.state !== 'closed') void audioCtx.close().catch(() => {});
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);
      const res = await axios.post(`${API_BASE}/token`, params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      const newToken = res.data.access_token;
      setToken(newToken);
      setLoginExpanded(false);
      localStorage.setItem('nivus_token', newToken);
      setUsername('');
      setPassword('');
      setAdminAuthPassword('');
      if (res.data.password_change_required) {
        alert('Primeiro acesso: defina sua senha definitiva para continuar.');
        return;
      }
      alert('Autenticado com sucesso!');
      fetchData(newToken);
    } catch (err) {
      const statusCode = err.response?.status;
      if (statusCode === 429) {
        alert(err.response?.data?.detail || 'Conta bloqueada temporariamente.');
      } else if (statusCode === 401) {
        alert('Utilizador ou palavra-passe inválidos.');
      } else {
        alert('Não foi possível autenticar. Verifique a ligação ao Nivus e tente novamente.');
      }
    }
  };

  const handleLogout = () => {
    setToken('');
    setLoginExpanded(false);
    localStorage.removeItem('nivus_token');
    setAdminAuthPassword('');
    setTargetNewPassword('');
    setTargetConfirmPassword('');
    setActiveTab('dashboard');
    setMaintenanceState(null);
    setMaintenanceMessage('');
    setSoundEnabled(false);
    setSoundStatus('Aviso sonoro do navegador desativado.');
    closeAlertAudioContext();
  };

  const fetchData = async (currentToken = token) => {
    try {
      await axios.get(`${API_BASE}/health`);
      setIsOnline(true);
      setError(null);

      if (!currentToken) {
        setTelemetry([]);
        setSystemLogs([]);
        setAuditLogs([]);
        setAlertsHistory([]);
        setUsersList([]);
        setMaintenanceState(null);
        return;
      }

      if (parseJwt(currentToken)?.password_change_required) {
        setTelemetry([]);
        setSystemLogs([]);
        setAuditLogs([]);
        setAlertsHistory([]);
        setUsersList([]);
        setMaintenanceState(null);
        return;
      }

      const headers = currentToken ? { Authorization: `Bearer ${currentToken}` } : {};
      const payload = parseJwt(currentToken);
      const [telRes, logRes, audRes, altRes, setRes, maintenanceRes] = await Promise.all([
        axios.get(`${API_BASE}/api/telemetry?limit=1000`, { headers }),
        axios.get(`${API_BASE}/api/logs?lines=15`, { headers }).catch(() => ({ data: { logs: [] } })),
        axios.get(`${API_BASE}/api/actuator/audit?limit=10`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_BASE}/api/alerts/history?limit=10`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_BASE}/api/settings`, { headers }).catch(() => ({ data: {} })),
        payload?.role === 'admin'
          ? axios.get(`${API_BASE}/api/maintenance`, { headers }).catch(() => ({ data: null }))
          : Promise.resolve({ data: null })
      ]);
      
      const formattedData = telRes.data.map(item => ({
        ...item,
        temperature: item.temperature_source ? item.temperature : null,
        time: new Date(item.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      }));

      setTelemetry(formattedData);
      setSystemLogs(logRes.data.logs || []);
      setAuditLogs(audRes.data || []);
      setAlertsHistory(altRes.data || []);
      if (setRes.data && Object.keys(setRes.data).length > 0) {
        setSettings(prev => ({ ...prev, ...setRes.data }));
      }
      setMaintenanceState(maintenanceRes.data || null);

      if (payload?.role === 'admin') {
        const usersRes = await axios.get(`${API_BASE}/api/users`, { headers }).catch(() => ({ data: [] }));
        setUsersList(usersRes.data || []);
      }
    } catch (err) {
      if (err.response?.status === 401 && currentToken) {
        setToken('');
        localStorage.removeItem('nivus_token');
      }
      setIsOnline(false);
      setError('Erro ao comunicar com o backend do Nivus.');
    }
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/api/users`, { username: newUsername, password: newPassword, role: newRole }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Utilizador criado com sucesso!');
      setNewUsername('');
      setNewPassword('');
      fetchData();
    } catch (err) {
      const statusCode = err.response?.status;
      if (statusCode === 409) {
        alert('Esse nome de utilizador já está registado.');
      } else if (statusCode === 422) {
        const details = err.response?.data?.detail;
        const invalidFields = new Set(
          Array.isArray(details)
            ? details.map(issue => Array.isArray(issue?.loc) ? issue.loc[issue.loc.length - 1] : null)
            : []
        );
        if (invalidFields.has('password')) {
          alert('A senha precisa ter de 8 a 256 caracteres, com pelo menos uma letra e um número.');
        } else if (invalidFields.has('username')) {
          alert('O utilizador precisa ter até 32 caracteres e usar apenas letras, números, ponto, hífen ou sublinhado.');
        } else {
          alert('Confira os campos do formulário e tente novamente.');
        }
      } else if (statusCode === 401) {
        alert('A sessão expirou ou não tem autorização. Entre novamente como administrador.');
      } else {
        alert('Não foi possível guardar o utilizador. Tente novamente.');
      }
    }
  };

  const handlePasswordChangeSubmit = async (e) => {
    e.preventDefault();
    if (targetNewPassword !== targetConfirmPassword) {
      alert('As senhas não coincidem!');
      return;
    }
    const hasLetter = Array.from(targetNewPassword).some(character => character.toLowerCase() !== character.toUpperCase());
    const hasNumber = /[0-9]/.test(targetNewPassword);
    if (targetNewPassword.length < 8 || targetNewPassword.length > 256 || !hasLetter || !hasNumber) {
      alert('Use uma senha de 8 a 256 caracteres, com pelo menos uma letra e um número.');
      return;
    }
    try {
      if (passwordChangeRequired) {
        const response = await axios.post(`${API_BASE}/api/users/first-login-password`, {
          new_password: targetNewPassword
        }, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const replacementToken = response.data.access_token;
        setToken(replacementToken);
        localStorage.setItem('nivus_token', replacementToken);
        setEditingUser(null);
        setAdminAuthPassword('');
        setTargetNewPassword('');
        setTargetConfirmPassword('');
        alert('Senha atualizada. Acesso liberado.');
        fetchData(replacementToken);
        return;
      }

      await axios.post(`${API_BASE}/api/users/change-password`, {
        username: editingUser,
        new_password: targetNewPassword,
        admin_password: adminAuthPassword
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Senha alterada com sucesso!');
      setEditingUser(null);
      setAdminAuthPassword('');
      setTargetNewPassword('');
      setTargetConfirmPassword('');
      fetchData();
    } catch (err) {
      const statusCode = err.response?.status;
      if (statusCode === 401) {
        alert('Senha atual incorreta ou sessão expirada.');
      } else {
        alert('Não foi possível alterar a senha. Verifique os requisitos e tente novamente.');
      }
    }
  };

  const handleDeleteUser = async (targetUser) => {
    if (!window.confirm(`Tem a certeza que deseja remover o utilizador ${targetUser}?`)) return;
    try {
      await axios.delete(`${API_BASE}/api/users/${targetUser}`, { headers: { Authorization: `Bearer ${token}` } });
      fetchData();
    } catch { alert('Erro ao remover.'); }
  };

  const handleActuatorCommand = async (topic, command) => {
    if (!isAdmin) {
      setActuatorMessage('Somente administrador pode enviar comandos.');
      return false;
    }
    const confirmed = window.confirm(`Enviar o comando ${command} ao tópico ${topic}? O dispositivo pode alterar uma carga física.`);
    if (!confirmed) return false;
    setActuatorMessage(`Enviando ${command} ao broker MQTT…`);
    try {
      const response = await axios.post(`${API_BASE}/api/actuator/command`, { topic, command }, { headers: { Authorization: `Bearer ${token}` } });
      setActuatorMessage(response.data.device_confirmed
        ? `Dispositivo confirmou ${command}.`
        : `Broker aceitou ${command}; o dispositivo não confirmou o estado físico.`);
      fetchData();
      return true;
    } catch (err) {
      const detail = err.response?.data?.detail;
      setActuatorMessage(detail || 'O broker MQTT não confirmou o comando; nenhuma confirmação física está disponível.');
      return false;
    }
  };

  const handleLegacyRelayToggle = async () => {
    const nextCommand = legacyRelayState ? 'OFF' : 'ON';
    const accepted = await handleActuatorCommand('nivus/edge/relay1', nextCommand);
    if (accepted) setLegacyRelayState(nextCommand === 'ON');
  };

  const handleUpdateSetting = async (key, value) => {
    if (!isAdmin) {
      setSettingsStatus('Somente administrador pode alterar os limites.');
      return false;
    }
    setSettingsStatus('Salvando limite…');
    try {
      await axios.post(`${API_BASE}/api/settings`, { key, value }, { headers: { Authorization: `Bearer ${token}` } });
      setSettings(prev => ({ ...prev, [key]: value }));
      setSettingsStatus('Limite salvo.');
      return true;
    } catch (err) {
      setSettingsStatus(err.response?.data?.detail || 'Não foi possível salvar o limite.');
      return false;
    }
  };

  const handleApplyHostTimeSync = async (servers) => {
    if (!isAdmin) return { ok: false, message: 'Somente administrador pode alterar o NTP do host.' };
    try {
      const response = await axios.post(`${API_BASE}/api/settings/time-sync`, { servers }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHostTimeSync(response.data);
      return { ok: true, data: response.data };
    } catch (err) {
      return { ok: false, message: err.response?.data?.detail || 'Não foi possível configurar o NTP do host.' };
    }
  };

  const handleRollbackHostTimeSync = async () => {
    if (!isAdmin) return { ok: false, message: 'Somente administrador pode restaurar o NTP do host.' };
    try {
      const response = await axios.post(`${API_BASE}/api/settings/time-sync/rollback`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHostTimeSync(response.data);
      return { ok: true, data: response.data };
    } catch (err) {
      return { ok: false, message: err.response?.data?.detail || 'Não foi possível restaurar a configuração NTP.' };
    }
  };

  const handleToggleMaintenance = async (enabled) => {
    if (!isAdmin) return false;
    if (enabled && !window.confirm('A coleta e a gravação de novas amostras serão pausadas até você retomar a operação. Continuar?')) return false;
    setMaintenanceBusy(true);
    setMaintenanceMessage(enabled ? 'Ativando modo de manutenção…' : 'Retomando coleta…');
    try {
      const response = await axios.post(`${API_BASE}/api/maintenance`, { enabled }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMaintenanceState(response.data);
      setMaintenanceMessage(enabled ? 'Modo de manutenção ativado.' : 'Operação normal retomada.');
      return true;
    } catch (err) {
      setMaintenanceMessage(err.response?.data?.detail || 'Não foi possível alterar o modo de manutenção.');
      return false;
    } finally {
      setMaintenanceBusy(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 5000);
    return () => clearInterval(interval);
  }, [token]);

  const latest = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
  const tempLimit = thresholdOrDefault(settings.temp_threshold, 75);
  const isTempCritical = latest && Number.isFinite(latest.temperature) && latest.temperature > tempLimit;

  useEffect(() => {
    if (isTempCritical && soundEnabled) void playAlertSound();
  }, [isTempCritical, soundEnabled]);

  const passwordsDoNotMatch = targetConfirmPassword.length > 0 && targetNewPassword !== targetConfirmPassword;

  return (
    <div className="dashboard-root" data-theme={displayPreferences.theme} data-high-contrast={String(displayPreferences.highContrast)} data-reduced-motion={String(displayPreferences.reducedMotion)} style={{ minHeight: '100vh', minWidth: 0, backgroundColor: '#0f172a', color: '#f8fafc', padding: 'clamp(0.75rem, 2vw, 1.75rem)', fontFamily: 'system-ui, sans-serif', position: 'relative' }}>
      <PasswordChangeModal editingUser={editingUser} setEditingUser={setEditingUser} handlePasswordChangeSubmit={handlePasswordChangeSubmit} targetNewPassword={targetNewPassword} setTargetNewPassword={setTargetNewPassword} targetConfirmPassword={targetConfirmPassword} setTargetConfirmPassword={setTargetConfirmPassword} passwordsDoNotMatch={passwordsDoNotMatch} adminAuthPassword={adminAuthPassword} setAdminAuthPassword={setAdminAuthPassword} passwordChangeRequired={passwordChangeRequired} currentUsername={userPayload?.sub || ''} handleLogout={handleLogout} />
      {!passwordChangeRequired && (
        <>
          <DashboardHeader token={token} userPayload={userPayload} fetchData={fetchData} isOnline={isOnline} dashboardVersion={dashboardVersion} onToggleDashboardVersion={handleToggleDashboardVersion} isTempCritical={isTempCritical} loginExpanded={loginExpanded} onToggleLogin={() => setLoginExpanded(value => !value)} />
          <DashboardNavigation token={token} isAdmin={isAdmin} activeTab={activeTab} setActiveTab={setActiveTab} handleLogout={handleLogout} displayPreferences={displayPreferences} />
          <LoginPanel token={token} handleLogin={handleLogin} username={username} setUsername={setUsername} password={password} setPassword={setPassword} expanded={loginExpanded} onToggle={() => setLoginExpanded(value => !value)} />
          <UserManagementPanel token={token} isAdmin={isAdmin} activeTab={activeTab} newUsername={newUsername} setNewUsername={setNewUsername} newPassword={newPassword} setNewPassword={setNewPassword} newRole={newRole} setNewRole={setNewRole} handleSaveUser={handleSaveUser} usersList={usersList} setEditingUser={setEditingUser} setTargetNewPassword={setTargetNewPassword} setTargetConfirmPassword={setTargetConfirmPassword} setAdminAuthPassword={setAdminAuthPassword} handleDeleteUser={handleDeleteUser} />
          {activeTab === 'settings' && token && (
            <SettingsPanel
              isAdmin={isAdmin}
              displayPreferences={displayPreferences}
              onDisplayPreferenceChange={handleDisplayPreferenceChange}
              maintenanceState={maintenanceState}
              maintenanceMessage={maintenanceMessage}
              maintenanceBusy={maintenanceBusy}
              onToggleMaintenance={handleToggleMaintenance}
              timeSyncState={hostTimeSync}
              onApplyTimeSync={handleApplyHostTimeSync}
              onRollbackTimeSync={handleRollbackHostTimeSync}
            />
          )}
          {dashboardVersion === 'current' ? (
            <DashboardPanel activeTab={activeTab} error={error} latest={latest} settings={settings} isAdmin={isAdmin} isTempCritical={isTempCritical} handleUpdateSetting={handleUpdateSetting} telemetry={telemetry} handleActuatorCommand={handleActuatorCommand} actuatorMessage={actuatorMessage} settingsStatus={settingsStatus} soundEnabled={soundEnabled} soundStatus={soundStatus} onToggleAlertSound={handleToggleAlertSound} systemLogs={systemLogs} auditLogs={auditLogs} alertsHistory={alertsHistory} />
          ) : (
            <Suspense fallback={<div role="status">Carregando versão leve…</div>}>
              <LegacyDashboardPanel activeTab={activeTab} error={error} latest={latest} settings={settings} setSettings={setSettings} isAdmin={isAdmin} handleUpdateSetting={handleUpdateSetting} telemetry={telemetry} relayState={legacyRelayState} handleRelayToggle={handleLegacyRelayToggle} systemLogs={systemLogs} />
            </Suspense>
          )}
        </>
      )}
      <LegalNotice />
    </div>
  );
}

export default App;
