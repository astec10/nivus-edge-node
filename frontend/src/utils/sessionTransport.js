import axios from 'axios';
import { prepareSessionRequest } from './sessionTransportCore.js';

// Browser credentials travel only in the HttpOnly session cookie.
axios.interceptors.request.use(prepareSessionRequest);
