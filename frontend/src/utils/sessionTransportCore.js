export function prepareSessionRequest(config) {
  config.withCredentials = true;
  const headers = config.headers;
  if (headers && typeof headers.delete === 'function') {
    headers.delete('Authorization');
  } else if (headers) {
    for (const name of Object.keys(headers)) {
      if (name.toLowerCase() === 'authorization') delete headers[name];
    }
  }
  return config;
}
