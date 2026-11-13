import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

export default function PasswordChangeModal({ editingUser, setEditingUser, handlePasswordChangeSubmit, targetNewPassword, setTargetNewPassword, targetConfirmPassword, setTargetConfirmPassword, passwordsDoNotMatch, adminAuthPassword, setAdminAuthPassword }) {
  return (
    <>
      {editingUser && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0, 0, 0, 0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', padding: '2rem', borderRadius: '0.75rem', width: '420px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, color: '#38bdf8', fontSize: '1.2rem' }}>Alterar Senha: {editingUser}</h3>
              <button onClick={() => setEditingUser(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}><X size={20} /></button>
            </div>
            <form onSubmit={handlePasswordChangeSubmit}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.85rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Nova Senha:</label>
                <input type="password" value={targetNewPassword} onChange={e => setTargetNewPassword(e.target.value)} placeholder="Nova senha" required style={{ width: '100%', backgroundColor: '#0f172a', border: '1px solid #334155', color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }} />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.85rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Confirme a Nova Senha:</label>
                <input type="password" value={targetConfirmPassword} onChange={e => setTargetConfirmPassword(e.target.value)} placeholder="Repita a nova senha" required style={{ width: '100%', backgroundColor: '#0f172a', border: `1px solid ${passwordsDoNotMatch ? '#ef4444' : '#334155'}`, color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }} />
                {passwordsDoNotMatch && (
                  <div style={{ color: '#f87171', fontSize: '0.75rem', marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <AlertTriangle size={12} /> As senhas digitadas são diferentes!
                  </div>
                )}
              </div>
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ fontSize: '0.85rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Sua Senha de Administrador:</label>
                <input type="password" value={adminAuthPassword} onChange={e => setAdminAuthPassword(e.target.value)} placeholder="Senha atual de Admin" required style={{ width: '100%', backgroundColor: '#0f172a', border: '1px solid #334155', color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }} />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button type="button" onClick={() => setEditingUser(null)} style={{ backgroundColor: '#475569', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '0.375rem', cursor: 'pointer', flex: 1 }}>Cancelar</button>
                <button type="submit" disabled={passwordsDoNotMatch} style={{ backgroundColor: passwordsDoNotMatch ? '#475569' : '#10b981', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '0.375rem', cursor: passwordsDoNotMatch ? 'not-allowed' : 'pointer', flex: 1, fontWeight: '600' }}>Salvar</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
