import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const transactionsApi = {
  list: (params: any) => api.get('/transactions/', { params }),
  get: (id: string) => api.get(`/transactions/${id}`),
};

export const alertsApi = {
  list: (params: any) => api.get('/alerts/', { params }),
  acknowledge: (id: string) => api.post(`/alerts/${id}/acknowledge`),
  escalate: (id: string, reason: string) => api.post(`/alerts/${id}/escalate`, { reason }),
};

export const casesApi = {
  list: (params: any) => api.get('/cases/', { params }),
  create: (data: any) => api.post('/cases/', data),
  get: (id: string) => api.get(`/cases/${id}`),
  close: (id: string, data: any) => api.put(`/cases/${id}/close`, data),
};

export const accountsApi = {
  profile: (id: string) => api.get(`/accounts/${id}/profile`),
  subgraph: (id: string, params: any) => api.get(`/accounts/${id}/graph`, { params }),
  timeline: (id: string, days: number) => api.get(`/accounts/${id}/timeline`, { params: { days } }),
};

export const reportsApi = {
  generateSTR: (caseId: string) => api.post('/reports/str/generate', { case_id: caseId }),
  submitSTR: (caseId: string, data: any) => api.post(`/reports/str/${caseId}/submit`, data),
};

export const fraudScoringApi = {
  score: (data: any, headers: any) => api.post('/fraud/score', data, { headers }),
};

export default api;
