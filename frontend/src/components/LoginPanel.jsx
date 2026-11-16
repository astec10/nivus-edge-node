import React from 'react';

export default function LoginPanel({ token, handleLogin, username, setUsername, password, setPassword, expanded = false, onToggle = () => {} }) {
  return (
    <>
      {!token && (
        <section className="login-panel" aria-label="Acesso ao Nivus">
          <div className="login-panel__intro">
            <span>🔒 Acesso ao Nivus</span>
            <button
              type="button"
              className="login-panel__toggle"
              aria-expanded={expanded}
              aria-controls="nivus-login-form"
              onClick={onToggle}
            >
              {expanded ? 'Fechar login' : 'Mostrar campos de login'}
            </button>
          </div>
          <form id="nivus-login-form" hidden={!expanded} onSubmit={handleLogin} className="login-panel__form">
            <input
              type="text"
              autoComplete="username"
              aria-label="Utilizador"
              value={username}
              onChange={event => setUsername(event.target.value)}
              placeholder="Utilizador"
              required
            />
            <input
              type="password"
              autoComplete="current-password"
              aria-label="Palavra-passe"
              value={password}
              onChange={event => setPassword(event.target.value)}
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
