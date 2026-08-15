const Hospital = {
  
  initDashboard: async (hospitalId) => {
    // 1. Fetch Inventory
    const invRes = await API.getHospitalInventory(hospitalId);
    if(invRes.success) {
      Hospital.renderInventory(invRes.data);
    }
    
    // 2. Auto-polling for incoming referrals assigned to this hospital
    setInterval(() => {
      Hospital.checkIncoming(hospitalId);
    }, 2000);
    Hospital.checkIncoming(hospitalId);
  },

  renderInventory: (inv) => {
    const grid = document.getElementById('inventory-grid');
    if(!grid) return;
    
    // Convert backend plain numbers to UI structure
    const toCard = (key, title, icon, avail) => {
      const total = (avail || 0) + Math.floor(Math.random() * 10) + 2; // fake total
      const reserved = total - (avail || 0);
      return { key, title, icon, data: { total, reserved, available: avail || 0 } };
    };

    const cards = [
      toCard('icu', 'ICU Beds', 'bed', inv.icu),
      toCard('ventilator', 'Ventilators', 'air', inv.ventilator),
      toCard('blood', 'Blood Units', 'water_drop', inv.blood),
      toCard('general', 'General Beds', 'hotel', inv.general)
    ];

    grid.innerHTML = cards.map(c => {
      const cap = Math.round(((c.data.total - c.data.available) / c.data.total) * 100);
      let statusColor = 'text-green-600 bg-green-50';
      if(cap > 80) statusColor = 'text-yellow-600 bg-yellow-50';
      if(cap > 95 || c.data.available < 1) statusColor = 'text-red-600 bg-red-50 font-bold';

      return `
        <div class="bg-white p-5 rounded-xl shadow-sm border border-gray-200">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-indigo-500">${c.icon}</span>
              <h3 class="font-bold text-gray-800">${c.title}</h3>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2 text-center text-sm mb-3">
            <div class="bg-gray-50 rounded py-1">
              <span class="block text-gray-500 text-xs">Total</span>
              <span class="font-medium text-gray-900">${c.data.total}</span>
            </div>
            <div class="bg-orange-50 rounded py-1">
              <span class="block text-orange-600 text-xs">Locked</span>
              <span class="font-medium text-orange-800">${c.data.reserved}</span>
            </div>
            <div class="bg-blue-50 rounded py-1 border border-blue-100">
              <span class="block text-blue-600 text-xs">Avail</span>
              <span class="font-bold text-blue-800">${c.data.available}</span>
            </div>
          </div>
          <div class="text-right">
            <span class="text-xs px-2 py-1 rounded ${statusColor}">${cap}% Capacity</span>
          </div>
        </div>
      `;
    }).join('');
  },

  checkIncoming: async (hospitalId) => {
    const res = await API.getAllReferrals();
    if (!res.success) return;
    const refs = res.data;

    const incoming = refs.find(r => r.selectedHospitalId === hospitalId && r.status === 'WAITING_HOSPITAL_ACCEPTANCE');
    
    const panel = document.getElementById('urgent-referral-panel');
    if(!panel) return;

    if (incoming) {
      if(panel.classList.contains('hidden')) {
        // Just appeared
        document.getElementById('inc-patient').textContent = `${incoming.patientId} (${incoming.age}${incoming.gender})`;
        document.getElementById('inc-condition').textContent = `${incoming.condition} • ${incoming.severity}`;
        
        const reqs = [];
        if(incoming.resources.icu) reqs.push('<li>ICU Bed</li>');
        if(incoming.resources.ventilator) reqs.push('<li>Ventilator</li>');
        if(incoming.resources.general) reqs.push('<li>General Bed</li>');
        if(incoming.resources.blood) reqs.push(`<li>Blood (${incoming.resources.bloodUnits} units)</li>`);
        
        document.getElementById('inc-resources').innerHTML = reqs.join('') || '<li>No specific resources</li>';

        document.getElementById('btn-accept').onclick = () => Hospital.acceptReferral(incoming.id, hospitalId);
        document.getElementById('btn-reject').onclick = () => Hospital.rejectReferral(incoming.id, hospitalId);

        panel.classList.remove('hidden');
        App.showToast("New Urgent Referral Received", "warning");
      }
    } else {
      panel.classList.add('hidden');
    }
  },

  acceptReferral: async (refId, hospitalId) => {
    // Hide panel immediately
    document.getElementById('urgent-referral-panel').classList.add('hidden');
    
    await API.acceptReferral(refId);
    
    // Refresh inventory
    const invRes = await API.getHospitalInventory(hospitalId);
    if(invRes.success) {
      Hospital.renderInventory(invRes.data);
    }

    // Show modal
    const modal = document.getElementById('accept-modal');
    if(modal) {
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }
  },

  rejectReferral: async (refId, hospitalId) => {
    if(confirm("Are you sure you want to reject this referral? It is highly discouraged unless strictly necessary.")) {
      document.getElementById('urgent-referral-panel').classList.add('hidden');
      await API.rejectReferral(refId);
      App.showToast("Referral Rejected", "error");
      
      // Refresh inventory because rejection releases lock
      const invRes = await API.getHospitalInventory(hospitalId);
      if(invRes.success) {
        Hospital.renderInventory(invRes.data);
      }
    }
  },

  closeAcceptModal: () => {
    const modal = document.getElementById('accept-modal');
    if(modal) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }
  }

};

window.Hospital = Hospital;
