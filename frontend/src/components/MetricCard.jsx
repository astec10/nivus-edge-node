import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

const cardStyle = {
  position: 'relative',
  backgroundColor: '#1e293b',
  padding: '1.1rem 1.25rem',
  borderRadius: '0.75rem',
  border: '1px solid #334155',
  minWidth: 0,
};

function MetricCard({ label, value, hint, details, detailsLabel }) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState({ left: 16, top: 16, width: 320 });
  const showTimer = useRef(null);

  const clearTimer = () => {
    if (showTimer.current !== null) {
      window.clearTimeout(showTimer.current);
      showTimer.current = null;
    }
  };

  const startDwell = (event) => {
    clearTimer();
    setVisible(false);
    const bounds = event.currentTarget.getBoundingClientRect();
    const width = Math.min(360, Math.max(180, window.innerWidth - 24));
    const left = Math.max(12, Math.min(bounds.left, window.innerWidth - width - 12));
    const top = Math.max(12, Math.min(bounds.bottom + 8, window.innerHeight - 340));
    setPosition({ left, top, width });
    showTimer.current = window.setTimeout(() => setVisible(true), 3000);
  };

  const hideDetails = () => {
    clearTimer();
    setVisible(false);
  };

  useEffect(() => () => {
    if (showTimer.current !== null) window.clearTimeout(showTimer.current);
  }, []);

  const tooltip = visible && typeof document !== 'undefined'
    ? createPortal(
      <div
        role="tooltip"
        id="metric-details-tooltip"
        style={{
          position: 'fixed',
          zIndex: 1000,
          left: position.left,
          top: position.top,
          width: position.width,
          maxHeight: 'min(55vh, 420px)',
          overflowY: 'auto',
          padding: '0.9rem 1rem',
          border: '1px solid #38bdf8',
          borderRadius: '0.75rem',
          background: '#07111f',
          color: '#f8fafc',
          boxShadow: '0 14px 38px #0009',
          pointerEvents: 'none',
        }}
      >
        <strong style={{ display: 'block', marginBottom: '0.55rem' }}>{detailsLabel || `${label} · detalhes`}</strong>
        {details}
        <small style={{ display: 'block', color: '#94a3b8', marginTop: '0.6rem' }}>Detalhe calculado pelas amostras exibidas no período selecionado.</small>
      </div>,
      document.body,
    )
    : null;

  return (
    <>
      <div
        tabIndex={0}
        role="group"
        aria-label={`${label}: ${value}. Mantenha o ponteiro ou o foco por 3 segundos para ver detalhes.`}
        aria-describedby={visible ? 'metric-details-tooltip' : undefined}
        onPointerEnter={startDwell}
        onPointerLeave={hideDetails}
        onFocus={startDwell}
        onBlur={hideDetails}
        style={{
          ...cardStyle,
          cursor: 'help',
          outlineOffset: '3px',
        }}
      >
        <span style={{ color: '#94a3b8' }}>{label}</span>
        <div style={{ fontSize: '1.8rem', fontWeight: 'bold', lineHeight: 1.3 }}>{value}</div>
        {hint && <small style={{ display: 'block', color: '#94a3b8', minHeight: '1.1rem' }}>{hint}</small>}
        <small style={{ display: 'block', color: '#64748b', marginTop: '0.35rem', fontSize: '0.68rem' }}>Pouse 3 s para detalhes</small>
      </div>
      {tooltip}
    </>
  );
}

export default MetricCard;
