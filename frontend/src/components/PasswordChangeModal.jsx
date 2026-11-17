import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { meetsPasswordPolicy } from '../utils/passwordPolicy.js';

export default function PasswordChangeModal({
  editingUser,
  setEditingUser,
  handlePasswordChangeSubmit,
  targetNewPassword,
  setTargetNewPassword,
  targetConfirmPassword,
  setTargetConfirmPassword,
  passwordsDoNotMatch,
  adminAuthPassword,
  setAdminAuthPassword,
  passwordChangeRequired = false,
  currentUsername = '',
  handleLogout
}) {
  const forcedChange = passwordChangeRequired;
  const open = Boolean(editingUser) || forcedChange;
  const weakPassword = targetNewPassword.length > 0 && !meetsPasswordPolicy(targetNewPassword);

  return (
    <>
      {open && (
        <div style={{ position: 'fixed', inset: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.82)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000, padding: '1rem' }}>
          <section role="dialog" aria-modal="true" aria-labelledby="password-change-title" style={{ backgroundColor: '#1e293b', border: '1px solid #334155', padding: '2rem', borderRadius: '0.75rem', width: 'min(100%, 420px)', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 id="password-change-title" style={{ margin: 0, color: '#38bdf8', fontSize: '1.2rem' }}>
                {forcedChange ? 'Defina sua senha definitiva' : `Alterar senha: ${editingUser}`}
              </h3>
              {!forcedChange && (
                <button type="button" onClick={() => setEditingUser(null)} aria-label="Fechar" style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                  <X size={20} />
                </button>
              )}
            </div>
            {forcedChange && (
              <p style={{ color: '#cbd5e1', fontSize: '0.9rem' }}>
                A senha temporária de {currentUsername} precisa ser substituída antes de acessar o painel.
              </p>
            )}
            <form onSubmit={handlePasswordChangeSubmit}>
              <div style={{ marginBottom: '1rem' }}>
                <label htmlFor="new-nivus-password" style={{ fontSize: '0.85rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Nova senha:</label>
                <input id="new-nivus-password" type="password" value={targetNewPassword} onChange={e => setTargetNewPassword(e.target.value)} minLength={8} maxLength={256} autoComplete="new-password" placeholder="Nova senha" aria-describedby="password-policy-hint" required style={{ boxSizing: 'border-box', width: '100%', backgroundColor: '#0f172a', border: '1px solid #334155', color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }} />
                <p id="password-policy-hint" style={{ color: weakPassword ? '#f87171' : '#94a3b8', fontSize: '0.75rem', margin: '0.35rem 0 0' }}>
                  Use 8 a 256 caracteres, com pelo menos uma letra e um número.
                </p>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label htmlFor="confirm-nivus-password" style={{ fontSize: '0.85rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Confirme a nova senha:</label>
                <input id="confirm-nivus-password" type="password" value={targetConfirmPassword} onChange={e => setTargetConfirmPassword(e.target.value)} minLength={8} maxLength={256} autoComplete="new-password" placeholder="Repita a nova senha" required style={{ boxSizing: 'border-box', width: '100%', backgroundColor: '#0f172a', border: `1px solid ${passwordsDoNotMatch ? '#ef4444' : '#334155'}`, color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }} />
                {passwordsDoNotMatch && (
                  <div style={{ color: '#f87171', fontSize: '0.75rem', marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <AlertTriangle size={12} /> As senhas digitadas são diferentes.
                  </div>
                )}
              </div>
              {!forcedChange && (
                <div style={{ marginBottom: '1.5rem' }}>
                  <label htmlFor="admin-current-password" style={{ fontSize: '0.85rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Sua senha atual de administrador:</label>
                  <input id="admin-current-password" type="password" value={adminAuthPassword} onChange={e => setAdminAuthPassword(e.target.value)} autoComplete="current-password" placeholder="Senha atual de Admin" required style={{ boxSizing: 'border-box', width: '100%', backgroundColor: '#0f172a', border: '1px solid #334155', color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }} />
                </div>
              )}
              <div style={{ display: 'flex', gap: '1rem' }}>
                {!forcedChange ? (
                  <button type="button" onClick={() => setEditingUser(null)} style={{ backgroundColor: '#475569', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '0.375rem', cursor: 'pointer', flex: 1 }}>Cancelar</button>
                ) : (
                  <button type="button" onClick={handleLogout} style={{ backgroundColor: '#475569', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '0.375rem', cursor: 'pointer', flex: 1 }}>Sair</button>
                )}
                <button type="submit" disabled={passwordsDoNotMatch || weakPassword} style={{ backgroundColor: passwordsDoNotMatch || weakPassword ? '#475569' : '#10b981', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '0.375rem', cursor: passwordsDoNotMatch || weakPassword ? 'not-allowed' : 'pointer', flex: 1, fontWeight: '600' }}>Salvar senha</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
