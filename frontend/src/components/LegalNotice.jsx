const repositoryUrl = 'https://github.com/astec10/nivus-edge-node';
const licenseUrl = `${repositoryUrl}/blob/main/LICENSE`;

export default function LegalNotice() {
  return (
    <footer
      aria-label="Informações sobre a licença do Nivus"
      style={{
        marginTop: '2rem',
        paddingTop: '1rem',
        borderTop: '1px solid #334155',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        gap: '0.75rem',
        color: '#94a3b8',
        fontSize: '0.75rem',
      }}
    >
      <span>
        Copyright © 2026 Nivus Edge Node contributors · AGPL-3.0-only · Sem garantia.
        Você pode compartilhar e modificar este programa conforme a licença.
      </span>
      <nav aria-label="Código-fonte e licença" style={{ display: 'flex', gap: '1rem' }}>
        <a href={repositoryUrl} target="_blank" rel="noreferrer" style={{ color: '#67e0bd' }}>
          Código-fonte
        </a>
        <a href={licenseUrl} target="_blank" rel="noreferrer" style={{ color: '#67e0bd' }}>
          Licença AGPL-3.0
        </a>
      </nav>
    </footer>
  );
}
