const AUTH_KEY = 'pulsenet_token';
const USER_KEY = 'pulsenet_user';
let _gpsInterval = null;

const Auth = {
  getToken: () => localStorage.getItem(AUTH_KEY),
  getUser: () => { const u = localStorage.getItem(USER_KEY); return u ? JSON.parse(u) : null; },

  login: async (email, password) => {
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');
      localStorage.setItem(AUTH_KEY, data.access_token);
      const user = {
        role: data.role, entity_id: data.entity_id,
        name: data.doctorName || data.driverName || data.name || email,
        phcId: data.phcId, hospitalId: data.hospitalId,
        ambulanceId: data.ambulanceId, plate: data.plate
      };
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      if (data.role === 'AMBULANCE') Auth._startGPS();
      return data.role;
    } catch (e) { throw e; }
  },

  logout: () => {
    Auth._stopGPS();
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = '/login.html';
  },

  getCurrentUser: () => Auth.getUser(),

  requireRole: (allowedRoles) => {
    const user = Auth.getUser();
    const token = Auth.getToken();
    if (!user || !token) { window.location.href = '/login.html'; return null; }
    if (allowedRoles && !allowedRoles.includes(user.role)) { window.location.href = '/login.html'; return null; }
    const el = document.getElementById('user-name-display');
    if (el) el.textContent = user.name;
    if (user.role === 'AMBULANCE') Auth._startGPS();
    return user;
  },

  _startGPS: () => {
    if (_gpsInterval) return;
    if (!navigator.geolocation) return;
    const send = () => {
      navigator.geolocation.getCurrentPosition(pos => {
        fetch('/api/v1/ambulances/location', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${Auth.getToken()}` },
          body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
        }).catch(() => {});
      }, () => {}, { enableHighAccuracy: true });
    };
    send();
    _gpsInterval = setInterval(send, 10000);
  },

  _stopGPS: () => { if (_gpsInterval) { clearInterval(_gpsInterval); _gpsInterval = null; } }
};

window.Auth = Auth;
