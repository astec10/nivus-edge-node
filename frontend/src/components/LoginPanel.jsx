import React from 'react';

export default function LoginPanel({ token, handleLogin, username, setUsername, password, setPassword }) {
  return (
    <>
      {!token && (
        <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', padding: '1rem 1.5rem', borderRadius: '0.75rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>🔒 Efetue login com as suas credenciais registadas.</div>
          <form onSubmit={handleLogin} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input type="text" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} placeholder="Utilizador" style={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: 'white', padding: '0.4rem 0.6rem', borderRadius: '0.375rem', width: '120px' }} />
            <input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Palavra-passe" style={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: 'white', padding: '0.4rem 0.6rem', borderRadius: '0.375rem', width: '130px' }} />
            <button type="submit" style={{ backgroundColor: '#10b981', color: 'white', border: 'none', padding: '0.4rem 1rem', borderRadius: '0.375rem', cursor: 'pointer' }}>Entrar</button>
          </form>
        </div>
      )}
    </>
  );
}
