const Ambulance = {
  
  initDashboard: (unitId) => {
    // Sync current status to buttons
    Ambulance.updateStatusUI();

    // Start polling for dispatch alerts
    setInterval(() => {
      Ambulance.checkDispatch(unitId);
    }, 2000);
  },

  setStatus: async (status) => {
    const user = Auth.getCurrentUser();
    if(user) {
      await API.updateAmbulanceStatus(user.ambulanceId, status);
      Ambulance.updateStatusUI();
    }
  },

  updateStatusUI: async () => {
    const user = Auth.getCurrentUser();
    if(!user) return;
    
    const res = await API.getAmbulances();
    if(res.success) {
      const myUnit = res.data.find(a => a.id === user.ambulanceId);
      if(myUnit) {
        const btnAvail = document.getElementById('btn-status-avail');
        const btnBusy = document.getElementById('btn-status-busy');
        
        if (myUnit.status === 'AVAILABLE') {
          btnAvail.className = 'px-6 py-2 rounded-md font-bold text-sm transition-colors bg-green-500 text-white shadow-sm';
          btnBusy.className = 'px-6 py-2 rounded-md font-bold text-sm transition-colors text-gray-600 hover:bg-gray-200';
        } else {
          btnBusy.className = 'px-6 py-2 rounded-md font-bold text-sm transition-colors bg-red-500 text-white shadow-sm';
          btnAvail.className = 'px-6 py-2 rounded-md font-bold text-sm transition-colors text-gray-600 hover:bg-gray-200';
        }
      }
    }
  },

  checkDispatch: async (unitId) => {
    // Check if the driver is AVAILABLE
    const ambRes = await API.getAmbulances();
    if (!ambRes.success) return;
    const myUnit = ambRes.data.find(a => a.id === unitId);
    if (!myUnit || myUnit.status !== 'AVAILABLE') return;

    // Check cascade alert queue
    const alertRes = await API.checkAmbulanceAlert(unitId);
    
    if (alertRes.success && alertRes.data) {
      window.location.href = `ambulance-dispatch.html?id=${alertRes.data.id}`;
    }
  }
};

window.Ambulance = Ambulance;
