import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// Auth
export const login = (email, password) =>
  api.post('/auth/login', new URLSearchParams({ username: email, password }));
export const register = (data) => api.post('/auth/register', data);
export const getMe = () => api.get('/auth/me');

// Farmer
export const getMyProfile = () => api.get('/farmers/me');
export const updateMyProfile = (data) => api.put('/farmers/me', data);
export const getMyFarms = () => api.get('/farmers/farms');
export const createFarm = (data) => api.post('/farmers/farms', data);
export const getMyProduction = () => api.get('/farmers/production');
export const createProduction = (data) => api.post('/farmers/production', data);
export const getMySales = () => api.get('/farmers/sales');
export const createSales = (data) => api.post('/farmers/sales', data);

// Passport
export const getMyPassport = () => api.get('/passport/me');
export const generatePassport = () => api.post('/passport/generate');
export const whatIfSimulation = (data) => api.post('/passport/what-if', data);
export const getMarketPrices = (crop, state) =>
  api.get('/passport/market/prices', { params: { crop, state } });

// Consent
export const listConsents = () => api.get('/consent/');
export const getPendingConsents = () => api.get('/consent/pending');
export const grantConsent = (id, data) => api.post(`/consent/${id}/grant`, data);
export const revokeConsent = (id) => api.post(`/consent/${id}/revoke`);
export const getDataAccessHistory = () => api.get('/consent/data-access-history');

// Credit
export const createCreditApplication = (data) => api.post('/credit/', data);
export const listCreditApplications = () => api.get('/credit/');

// FPO
export const listFpos = () => api.get('/fpo/');
export const listMyMembers = () => api.get('/fpo/my/members');
export const addMember = (data) => api.post('/fpo/my/members', data);
export const listFpoVerifications = () => api.get('/fpo/my/verifications');
export const createVerification = (data) => api.post('/fpo/my/verify', data);
export const updateVerification = (id, data) => api.put(`/fpo/my/verify/${id}`, data);

// Lender
export const getConsentedFarmers = () => api.get('/lender/consented-farmers');
export const getFarmerPassportForLender = (id) => api.get(`/lender/farmers/${id}/passport`);
export const getLenderApplications = () => api.get('/lender/applications');
export const makeDecision = (id, data) => api.post(`/lender/applications/${id}/decision`, data);
