const API_BASE_URL = 'http://localhost:8000/api/v1';

const API = {
  // Helpers
  _req: async (endpoint, method = 'GET', body = null) => {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) {
      options.body = JSON.stringify(body);
    }
    try {
      const res = await fetch(`${API_BASE_URL}${endpoint}`, options);
      return await res.json();
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      return { success: false, message: 'Network error' };
    }
  },
  
  // Referrals
  createReferral: async (referralData) => {
    const res = await API._req('/referrals', 'POST', referralData);
    if(res.success && res.data) {
        localStorage.setItem('activeReferralId', res.data.id);
    }
    return res;
  },

  getReferral: async (id) => {
    return await API._req(`/referrals/${id}`);
  },
  
  getAllReferrals: async () => {
    return await API._req(`/referrals`);
  },

  updateReferralStatus: async (id, newStatus, extraData = {}) => {
    return await API._req(`/referrals/${id}/status`, 'PUT', { status: newStatus, extraData });
  },

  // Matching
  getMatchingHospitals: async (requirements) => {
    return await API._req('/matching', 'POST', requirements);
  },

  selectHospital: async (referralId, hospitalId, resources) => {
    // 1. Lock resources
    const res = await API._req('/reservations', 'POST', { hospitalId, resources });
    if (!res.success) {
      alert("Failed to lock resources: " + res.message);
      return res;
    }
    // 2. Update status
    return await API.updateReferralStatus(referralId, 'WAITING_HOSPITAL_ACCEPTANCE', { selectedHospitalId: hospitalId, reservationStatus: 'LOCKED', reservedAt: new Date().toISOString() });
  },

  // Hospital Actions
  acceptReferral: async (referralId) => {
    return await API.updateReferralStatus(referralId, 'ACCEPTED', { hospitalAcceptedAt: new Date().toISOString() });
  },

  rejectReferral: async (referralId) => {
    return await API.updateReferralStatus(referralId, 'REJECTED_BY_HOSPITAL', { rejectedAt: new Date().toISOString() });
  },

  getHospitalInventory: async (hospitalId) => {
    return await API._req(`/hospitals/${hospitalId}/inventory`);
  },

  updateHospitalInventory: async (hospitalId, updates) => {
    return await API._req(`/hospitals/${hospitalId}/inventory`, 'PUT', { inventory: updates });
  },

  // Ambulance Actions
  getAmbulances: async () => {
    return await API._req('/ambulances');
  },

  updateAmbulanceStatus: async (ambulanceId, status) => {
    return await API._req(`/ambulances/${ambulanceId}/status`, 'PUT', { status });
  },

  checkAmbulanceAlert: async (ambulanceId) => {
    return await API._req(`/ambulances/${ambulanceId}/alert`);
  },

  acceptDispatch: async (referralId, ambulanceId) => {
    return await API._req(`/referrals/${referralId}/accept_dispatch`, 'POST', { ambulanceId });
  },

  declineDispatch: async (referralId, ambulanceId) => {
    return await API._req(`/referrals/${referralId}/decline_dispatch`, 'POST', { ambulanceId });
  }
};

window.API = API;
