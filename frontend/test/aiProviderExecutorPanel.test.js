import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const panel = readFileSync(
  new URL('../src/components/AIProviderExecutorPanel.jsx', import.meta.url),
  'utf8',
);
const styles = readFileSync(
  new URL('../src/components/AIProviderExecutorPanel.css', import.meta.url),
  'utf8',
);

test('Single/Parallel and data classification controls have native accessible labels', () => {
  assert.match(
    panel,
    /<label className="display-preference-field">\s*<span>Modo<\/span>\s*<select/,
  );
  assert.match(
    panel,
    /<label className="display-preference-field">\s*<span>Classe dos dados<\/span>\s*<select/,
  );
  assert.match(
    panel,
    /<fieldset className="ai-provider-executor-options">\s*<legend>Provedores selecionados/,
  );
  assert.match(panel, /<label key=\{item\.id\}>\s*<input type="checkbox"/);
});

test('Parallel selection and shared-budget policy are visible before submission', () => {
  assert.match(panel, /Paralelo \(2–3 provedores\)/);
  assert.match(panel, /Provedores selecionados \(\{providerIds\.length\}\/3\)/);
  assert.match(panel, /O mesmo orçamento máximo vale para o lote inteiro/);
  assert.match(panel, /selected\.length < 2 \|\| selected\.length > 3/);
  assert.match(panel, /Orçamento máximo da tarefa \(USD\)/);
});

test('execution feedback is announced and prompt/result content is not persisted by the panel', () => {
  assert.match(panel, /role="status" aria-live="polite"/);
  assert.match(panel, /Instrução <small>\(não é salva pelo Nivus\)<\/small>/);
  assert.match(panel, /Cada provedor pode receber uma chamada; o Nivus não faz retry nem fallback/);
  assert.doesNotMatch(panel, /localStorage|sessionStorage|dangerouslySetInnerHTML/);
});

test('the executor layout adapts to narrow screens', () => {
  assert.match(styles, /@media \(max-width: 640px\)/);
  assert.match(styles, /\.ai-provider-executor-grid \{ grid-template-columns: 1fr;/);
});
