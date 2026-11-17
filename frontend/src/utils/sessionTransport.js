import axios from 'axios';

// Browser credentials travel only in the HttpOnly session cookie. Components may
// still pass legacy Bearer headers during the transition; never send them.
axios.interceptors.request.use(config => {
  config.withCredentials = true;
  if (config.headers) {
    delete config.headers.Authorization;
    delete config.headers.authorization;
  }
  return config;
});
