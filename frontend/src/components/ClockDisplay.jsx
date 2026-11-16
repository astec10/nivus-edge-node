import React, { useEffect, useState } from 'react';
import { DEFAULT_DISPLAY_PREFERENCES, formatDisplayDate } from '../utils/displayPreferences';

function formatDisplayTime(date, timeZone, timeFormat) {
  try {
    const options = {
      timeZone,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      ...(timeFormat === '12h' ? { hour12: true } : { hourCycle: 'h23' }),
    };
    return new Intl.DateTimeFormat('pt-BR', options).format(date);
  } catch {
    return date.toLocaleTimeString('pt-BR', { hour12: timeFormat === '12h' });
  }
}

export default function ClockDisplay({ preferences = DEFAULT_DISPLAY_PREFERENCES }) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const time = formatDisplayTime(now, preferences.timeZone, preferences.timeFormat);
  const date = formatDisplayDate(now, preferences.timeZone, preferences.dateFormat);
  const label = `${time}, ${date}, fuso ${preferences.timeZone}`;

  return (
    <div className="clock-display" role="group" aria-label={`Relógio digital. ${label}`} title={label}>
      <time className="clock-display__time" dateTime={now.toISOString()}>{time}</time>
      <time className="clock-display__date" dateTime={now.toISOString()}>{date}</time>
    </div>
  );
}
