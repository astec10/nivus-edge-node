import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import PasswordChangeModal from './components/PasswordChangeModal';
import DashboardHeader from './components/DashboardHeader';
import DashboardNavigation from './components/DashboardNavigation';
import LoginPanel from './components/LoginPanel';
import UserManagementPanel from './components/UserManagementPanel';
import DashboardPanel from './components/DashboardPanel';
import LegalNotice from './components/LegalNotice';

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

  const [controlMode, setControlMode] = useState('auto');
  const [relayState, setRelayState] = useState(false);

  const parseJwt = (t) => {
    try { return JSON.parse(atob(t.split('.')[1])); } catch (e) { return null; }
  };

  const userPayload = token ? parseJwt(token) : null;
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
    } catch (e) {}
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
      alert('Autenticado com sucesso!');
      fetchData(newToken);
    } catch (err) {
      if (err.response && err.response.status === 429) {
        alert(err.response.data.detail || 'Conta bloqueada temporariamente.');
      } else {
        alert('Erro de autenticação.');
      }
    }
  };

  const handleLogout = () => {
    setToken('');
    localStorage.removeItem('nivus_token');
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

      const headers = currentToken ? { Authorization: `Bearer ${currentToken}` } : {};
      const [telRes, logRes, audRes, altRes, setRes] = await Promise.all([
        axios.get(`${API_BASE}/api/telemetry?limit=30`, { headers }),
        axios.get(`${API_BASE}/api/logs?lines=15`, { headers }).catch(() => ({ data: { logs: [] } })),
        axios.get(`${API_BASE}/api/actuator/audit?limit=10`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_BASE}/api/alerts/history?limit=10`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_BASE}/api/settings`, { headers }).catch(() => ({ data: {} }))
      ]);
      
      const formattedData = telRes.data.map(item => ({
        ...item,
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
      alert('Erro ao guardar utilizador.');
    }
  };

  const handlePasswordChangeSubmit = async (e) => {
    e.preventDefault();
    if (targetNewPassword !== targetConfirmPassword) {
      alert('As senhas não coincidem!');
      return;
    }
    try {
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
      alert('Falha na autenticação do Administrador ou erro no servidor.');
    }
  };

  const handleDeleteUser = async (targetUser) => {
    if (!window.confirm(`Tem a certeza que deseja remover o utilizador ${targetUser}?`)) return;
    try {
      await axios.delete(`${API_BASE}/api/users/${targetUser}`, { headers: { Authorization: `Bearer ${token}` } });
      fetchData();
    } catch (err) { alert('Erro ao remover.'); }
  };

  const handleActuatorCommand = async (topic, command) => {
    if (!isAdmin) {
      alert('Modo de Leitura (Viewer): Sem permissão.');
      return;
    }
    try {
      await axios.post(`${API_BASE}/api/actuator/command`, { topic, command }, { headers: { Authorization: `Bearer ${token}` } });
      fetchData();
    } catch (err) { alert('Acesso negado.'); }
  };

  const handleRelayToggle = () => {
    if (!isAdmin) {
      alert('Modo de Leitura (Viewer): Sem permissão.');
      return;
    }
    const newState = !relayState;
    setRelayState(newState);
    handleActuatorCommand('nivus/edge/relay1', newState ? 'ON' : 'OFF');
  };

  const handleUpdateSetting = async (key, value) => {
    if (!isAdmin) {
      alert('Modo de Leitura (Viewer): Sem permissão.');
      return;
    }
    try {
      await axios.post(`${API_BASE}/api/settings`, { key, value }, { headers: { Authorization: `Bearer ${token}` } });
      setSettings(prev => ({ ...prev, [key]: value }));
      alert('Definição atualizada!');
    } catch (err) { alert('Acesso negado.'); }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 5000);
    return () => clearInterval(interval);
  }, [token]);

  const latest = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
  const tempLimit = parseFloat(settings.temp_threshold) || 75;
  const cpuLimit = parseFloat(settings.cpu_threshold) || 90;
  const isTempCritical = latest && Number.isFinite(latest.temperature) && latest.temperature > tempLimit;
  const isCpuCritical = latest && latest.cpu_percent > cpuLimit;
  const hasActiveAlert = isTempCritical || isCpuCritical;

  useEffect(() => { if (hasActiveAlert) playAlertSound(); }, [hasActiveAlert]);

  const passwordsDoNotMatch = targetConfirmPassword.length > 0 && targetNewPassword !== targetConfirmPassword;

  return (
    <div className="dashboard-root" style={{ minHeight: '100vh', backgroundColor: '#0f172a', color: '#f8fafc', padding: '2rem', fontFamily: 'system-ui, sans-serif', position: 'relative' }}>
      <PasswordChangeModal editingUser={editingUser} setEditingUser={setEditingUser} handlePasswordChangeSubmit={handlePasswordChangeSubmit} targetNewPassword={targetNewPassword} setTargetNewPassword={setTargetNewPassword} targetConfirmPassword={targetConfirmPassword} setTargetConfirmPassword={setTargetConfirmPassword} passwordsDoNotMatch={passwordsDoNotMatch} adminAuthPassword={adminAuthPassword} setAdminAuthPassword={setAdminAuthPassword} />
      <DashboardHeader token={token} userPayload={userPayload} fetchData={fetchData} />
      <DashboardNavigation token={token} isAdmin={isAdmin} activeTab={activeTab} setActiveTab={setActiveTab} handleLogout={handleLogout} />
      <LoginPanel token={token} handleLogin={handleLogin} username={username} setUsername={setUsername} password={password} setPassword={setPassword} />
      <UserManagementPanel token={token} isAdmin={isAdmin} activeTab={activeTab} newUsername={newUsername} setNewUsername={setNewUsername} newPassword={newPassword} setNewPassword={setNewPassword} newRole={newRole} setNewRole={setNewRole} handleSaveUser={handleSaveUser} usersList={usersList} setEditingUser={setEditingUser} setTargetNewPassword={setTargetNewPassword} setTargetConfirmPassword={setTargetConfirmPassword} setAdminAuthPassword={setAdminAuthPassword} handleDeleteUser={handleDeleteUser} />
      <DashboardPanel activeTab={activeTab} error={error} latest={latest} settings={settings} setSettings={setSettings} isAdmin={isAdmin} handleUpdateSetting={handleUpdateSetting} telemetry={telemetry} controlMode={controlMode} setControlMode={setControlMode} relayState={relayState} handleRelayToggle={handleRelayToggle} systemLogs={systemLogs} />
      <LegalNotice />
    </div>
  );
}

export default App;
