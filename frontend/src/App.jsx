import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import PasswordChangeModal from './components/PasswordChangeModal';
import DashboardHeader from './components/DashboardHeader';
import DashboardNavigation from './components/DashboardNavigation';
import LoginPanel from './components/LoginPanel';
import UserManagementPanel from './components/UserManagementPanel';
import DashboardPanel from './components/DashboardPanel';
import LegalNotice from './components/LegalNotice';
import { thresholdOrDefault } from './utils/telemetry';

const API_BASE = '';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [telemetry, setTelemetry] = useState([]);
  const [systemLogs, setSystemLogs] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [alertsHistory, setAlertsHistory] = useState([]);
  const [settings, setSettings] = useState({ temp_threshold: '75', cpu_threshold: '90' });
  const [usersList, setUsersList] = useState([]);
  const [isOnline, setIsOnline] = useState(false);
  const [error, setError] = useState(null);
  
  const [token, setToken] = useState(localStorage.getItem('nivus_token') || '');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('viewer');

  const [editingUser, setEditingUser] = useState(null);
  const [adminAuthPassword, setAdminAuthPassword] = useState('');
  const [targetNewPassword, setTargetNewPassword] = useState('');
  const [targetConfirmPassword, setTargetConfirmPassword] = useState('');

  const [actuatorMessage, setActuatorMessage] = useState('');
  const [settingsStatus, setSettingsStatus] = useState('');

  const parseJwt = (t) => {
    try { return JSON.parse(atob(t.split('.')[1])); } catch { return null; }
  };

  const userPayload = token ? parseJwt(token) : null;
  const passwordChangeRequired = userPayload?.password_change_required === true;
  const isAdmin = userPayload?.role === 'admin';
  const lastAlertTimeRef = useRef(0);

  const playAlertSound = () => {
    try {
      const now = Date.now();
      if (now - lastAlertTimeRef.current < 30000) return;
      lastAlertTimeRef.current = now;
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.2);
    } catch {}
  };

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
    localStorage.removeItem('nivus_token');
    setAdminAuthPassword('');
    setTargetNewPassword('');
    setTargetConfirmPassword('');
    setActiveTab('dashboard');
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
        return;
      }

      if (parseJwt(currentToken)?.password_change_required) {
        setTelemetry([]);
        setSystemLogs([]);
        setAuditLogs([]);
        setAlertsHistory([]);
        setUsersList([]);
        return;
      }

      const headers = currentToken ? { Authorization: `Bearer ${currentToken}` } : {};
      const [telRes, logRes, audRes, altRes, setRes] = await Promise.all([
        axios.get(`${API_BASE}/api/telemetry?limit=1000`, { headers }),
        axios.get(`${API_BASE}/api/logs?lines=15`, { headers }).catch(() => ({ data: { logs: [] } })),
        axios.get(`${API_BASE}/api/actuator/audit?limit=10`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_BASE}/api/alerts/history?limit=10`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_BASE}/api/settings`, { headers }).catch(() => ({ data: {} }))
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

      const payload = currentToken ? parseJwt(currentToken) : null;
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

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 5000);
    return () => clearInterval(interval);
  }, [token]);

  const latest = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
  const tempLimit = thresholdOrDefault(settings.temp_threshold, 75);
  const cpuLimit = thresholdOrDefault(settings.cpu_threshold, 90);
  const isTempCritical = latest && Number.isFinite(latest.temperature) && latest.temperature > tempLimit;
  const isCpuCritical = latest && latest.cpu_percent > cpuLimit;
  const hasActiveAlert = isTempCritical || isCpuCritical;

  useEffect(() => { if (hasActiveAlert) playAlertSound(); }, [hasActiveAlert]);

  const passwordsDoNotMatch = targetConfirmPassword.length > 0 && targetNewPassword !== targetConfirmPassword;

  return (
    <div className="dashboard-root" style={{ minHeight: '100vh', minWidth: 0, backgroundColor: '#0f172a', color: '#f8fafc', padding: 'clamp(0.75rem, 2vw, 1.75rem)', fontFamily: 'system-ui, sans-serif', position: 'relative' }}>
      <PasswordChangeModal editingUser={editingUser} setEditingUser={setEditingUser} handlePasswordChangeSubmit={handlePasswordChangeSubmit} targetNewPassword={targetNewPassword} setTargetNewPassword={setTargetNewPassword} targetConfirmPassword={targetConfirmPassword} setTargetConfirmPassword={setTargetConfirmPassword} passwordsDoNotMatch={passwordsDoNotMatch} adminAuthPassword={adminAuthPassword} setAdminAuthPassword={setAdminAuthPassword} passwordChangeRequired={passwordChangeRequired} currentUsername={userPayload?.sub || ''} handleLogout={handleLogout} />
      {!passwordChangeRequired && (
        <>
          <DashboardHeader token={token} userPayload={userPayload} fetchData={fetchData} isOnline={isOnline} />
          <DashboardNavigation token={token} isAdmin={isAdmin} activeTab={activeTab} setActiveTab={setActiveTab} handleLogout={handleLogout} />
          <LoginPanel token={token} handleLogin={handleLogin} username={username} setUsername={setUsername} password={password} setPassword={setPassword} />
          <UserManagementPanel token={token} isAdmin={isAdmin} activeTab={activeTab} newUsername={newUsername} setNewUsername={setNewUsername} newPassword={newPassword} setNewPassword={setNewPassword} newRole={newRole} setNewRole={setNewRole} handleSaveUser={handleSaveUser} usersList={usersList} setEditingUser={setEditingUser} setTargetNewPassword={setTargetNewPassword} setTargetConfirmPassword={setTargetConfirmPassword} setAdminAuthPassword={setAdminAuthPassword} handleDeleteUser={handleDeleteUser} />
          <DashboardPanel activeTab={activeTab} error={error} latest={latest} settings={settings} isAdmin={isAdmin} isTempCritical={isTempCritical} handleUpdateSetting={handleUpdateSetting} telemetry={telemetry} handleActuatorCommand={handleActuatorCommand} actuatorMessage={actuatorMessage} settingsStatus={settingsStatus} systemLogs={systemLogs} auditLogs={auditLogs} alertsHistory={alertsHistory} />
        </>
      )}
      <LegalNotice />
    </div>
  );
}

export default App;
