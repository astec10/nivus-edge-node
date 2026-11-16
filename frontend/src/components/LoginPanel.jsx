import React from 'react';

export default function LoginPanel({ token, handleLogin, username, setUsername, password, setPassword }) {
  return (
    <>
      {!token && (
        <section className="login-panel" aria-label="Acesso ao Nivus">
          <div className="login-panel__intro">🔒 Efetue login com as suas credenciais registadas.</div>
          <form onSubmit={handleLogin} className="login-panel__form">
            <input
              type="text"
              autoComplete="username"
              aria-label="Utilizador"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Utilizador"
              required
            />
            <input
              type="password"
              autoComplete="current-password"
              aria-label="Palavra-passe"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Palavra-passe"
              required
            />
            <button type="submit">Entrar</button>
          </form>
        </section>
      )}
    </>
  );
}
