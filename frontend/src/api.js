import axios from 'axios';

const API = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

API.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem('refresh');
      if (refresh) {
        try {
          const { data } = await axios.post('/api/auth/refresh/', { refresh });
          localStorage.setItem('access', data.access);
          err.config.headers.Authorization = `Bearer ${data.access}`;
          return API.request(err.config);
        } catch (_) {
          localStorage.removeItem('access');
          localStorage.removeItem('refresh');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(err);
  }
);

export const auth = {
  login: (username, password) => API.post('/auth/login/', { username, password }),
  register: (data) => API.post('/auth/register/', data),
};

export const users = {
  list: () => API.get('/users/'),
  me: () => API.get('/users/me/'),
  updateMe: (data) => API.patch('/users/me/', data),
  uploadAvatar: (file) => {
    const formData = new FormData();
    formData.append('avatar', file);
    return API.patch('/users/me/', formData);
  },
  locationStats: () => API.get('/users/location-stats/'),
};

export const rooms = {
  list: () => API.get('/rooms/'),
  create: (data) => API.post('/rooms/', data),
  dm: (userId) => API.post('/rooms/dm/', { user_id: userId }),
  get: (id) => API.get(`/rooms/${id}/`),
  join: (id) => API.post(`/rooms/${id}/join/`),
  leave: (id) => API.post(`/rooms/${id}/leave/`),
};

export const messages = {
  list: (roomId) => API.get('/messages/', { params: { room: roomId } }),
  react: (id, emoji) => API.post(`/messages/${id}/react/`, { emoji }),
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return API.post('/messages/upload/', formData);
  },
};

export default API;
