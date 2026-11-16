export const DEFAULT_DISPLAY_PREFERENCES = Object.freeze({
  timeZone: 'America/Sao_Paulo',
  timeFormat: '24h',
  dateFormat: 'dd/MM/yyyy',
  theme: 'current',
  highContrast: false,
  reducedMotion: false,
});

export const TIME_ZONES = [
  { value: 'America/Sao_Paulo', label: 'Brasília / São Paulo' },
  { value: 'America/Manaus', label: 'Manaus' },
  { value: 'America/Rio_Branco', label: 'Rio Branco' },
  { value: 'America/Noronha', label: 'Fernando de Noronha' },
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'Nova York' },
  { value: 'Europe/Lisbon', label: 'Lisboa' },
  { value: 'Europe/London', label: 'Londres' },
];

export const DATE_FORMATS = [
  { value: 'dd/MM/yyyy', label: 'DD/MM/AAAA' },
  { value: 'yyyy-MM-dd', label: 'AAAA-MM-DD' },
  { value: 'MM/dd/yyyy', label: 'MM/DD/AAAA' },
];

export const DASHBOARD_THEMES = [
  { value: 'current', label: 'Atual (padrão)' },
  { value: 'bento', label: 'Bento Grid minimalista' },
  { value: 'glass', label: 'Glassmorphism e neon' },
  { value: 'scada', label: 'SCADA industrial escuro' },
  { value: 'cupertino', label: 'Cupertino claro' },
  { value: 'eink', label: 'E-Ink / brutalismo técnico' },
];

const STORAGE_PREFIX = 'nivus_display_preferences:';
const ALLOWED_TIME_ZONES = new Set(TIME_ZONES.map(({ value }) => value));
const ALLOWED_DATE_FORMATS = new Set(DATE_FORMATS.map(({ value }) => value));
const ALLOWED_THEMES = new Set(DASHBOARD_THEMES.map(({ value }) => value));

function getStorage() {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function normalizeDisplayPreferences(value = {}) {
  return {
    timeZone: ALLOWED_TIME_ZONES.has(value.timeZone) ? value.timeZone : DEFAULT_DISPLAY_PREFERENCES.timeZone,
    timeFormat: value.timeFormat === '12h' ? '12h' : '24h',
    dateFormat: ALLOWED_DATE_FORMATS.has(value.dateFormat) ? value.dateFormat : DEFAULT_DISPLAY_PREFERENCES.dateFormat,
    theme: ALLOWED_THEMES.has(value.theme) ? value.theme : DEFAULT_DISPLAY_PREFERENCES.theme,
    highContrast: value.highContrast === true,
    reducedMotion: value.reducedMotion === true,
  };
}

export function loadDisplayPreferences(username) {
  const storage = getStorage();
  if (!storage) return { ...DEFAULT_DISPLAY_PREFERENCES };
  try {
    const saved = storage.getItem(STORAGE_PREFIX + encodeURIComponent(username || 'guest'));
    return normalizeDisplayPreferences(saved ? JSON.parse(saved) : {});
  } catch {
    return { ...DEFAULT_DISPLAY_PREFERENCES };
  }
}

export function saveDisplayPreferences(username, preferences) {
  const storage = getStorage();
  if (!storage) return false;
  try {
    storage.setItem(
      STORAGE_PREFIX + encodeURIComponent(username || 'guest'),
      JSON.stringify(normalizeDisplayPreferences(preferences)),
    );
    return true;
  } catch {
    return false;
  }
}

export function formatUtcOffset(timeZone, date = new Date()) {
  try {
    const parts = new Intl.DateTimeFormat('en', {
      timeZone,
      timeZoneName: 'longOffset',
      hour: '2-digit',
    }).formatToParts(date);
    const offset = parts.find(({ type }) => type === 'timeZoneName')?.value;
    if (!offset) return 'UTC indisponível';
    return offset === 'GMT' ? 'UTC+00:00' : offset.replace(/^GMT/, 'UTC');
  } catch {
    return 'UTC indisponível';
  }
}

export function formatDisplayDate(date, timeZone, format) {
  try {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone,
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).formatToParts(date);
    const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
    const formats = {
      'dd/MM/yyyy': `${values.day}/${values.month}/${values.year}`,
      'yyyy-MM-dd': `${values.year}-${values.month}-${values.day}`,
      'MM/dd/yyyy': `${values.month}/${values.day}/${values.year}`,
    };
    return formats[format] || formats[DEFAULT_DISPLAY_PREFERENCES.dateFormat];
  } catch {
    return date.toLocaleDateString('pt-BR');
  }
}
