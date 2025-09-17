// frontend/src/services/api.js
import axios from 'axios';

// Configuración de URLs por entorno - CORREGIDO
const getApiBaseUrl = () => {
  // 1. Prioridad: Variable de entorno explícita
  if (process.env.REACT_APP_API_URL) {
    console.log('Using REACT_APP_API_URL:', process.env.REACT_APP_API_URL);
    return process.env.REACT_APP_API_URL;
  }

  // 2. Desarrollo local
  if (process.env.NODE_ENV === 'development') {
    console.log('Development mode: using localhost');
    return 'http://localhost:8001/smau-proto';  // Puerto por defecto de tu FastAPI
  }

  // 3. Detección automática por hostname - CORREGIDO SEGÚN TUS PIPELINES
  const hostname = window.location.hostname;
  console.log('Detecting environment from hostname:', hostname);
  
  if (hostname.includes('dev') || hostname.includes('purple-') || hostname.includes('dev-')) {
    // CORREGIDO: Según tu pipeline, el health check apunta a devapi.grantthornton.es
    const apiUrl = 'https://devapi.grantthornton.es/smau-proto';
    console.log('DEV environment detected, using:', apiUrl);
    return apiUrl;
  } else if (hostname.includes('test') || hostname.includes('green-') || hostname.includes('test-')) {
    const apiUrl = 'https://testapi.grantthornton.es';
    console.log('TEST environment detected, using:', apiUrl);
    return apiUrl;
  } else {
    const apiUrl = 'https://api.grantthornton.es';
    console.log('PROD environment detected, using:', apiUrl);
    return apiUrl;
  }
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
});

// Interceptor para requests
api.interceptors.request.use(
  (config) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('API Request:', config.method?.toUpperCase(), config.url);
      console.log('Full URL:', `${API_BASE_URL}${config.url}`);
    }
    return config;
  },
  (error) => {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }
);

// Interceptor para responses
api.interceptors.response.use(
  (response) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('API Response:', response.status, response.config.url);
    }
    return response;
  },
  (error) => {
    console.error('API Error:', error.message);
    console.error('Full error:', error);
    
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
      
      switch (error.response.status) {
        case 404:
          error.message = 'Recurso no encontrado';
          break;
        case 500:
          error.message = 'Error interno del servidor';
          break;
        case 503:
          error.message = 'Servicio no disponible';
          break;
      }
    } else if (error.request) {
      error.message = `No se pudo conectar con el servidor en ${API_BASE_URL}`;
    }
    
    return Promise.reject(error);
  }
);

export default api;