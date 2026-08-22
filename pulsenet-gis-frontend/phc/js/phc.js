const PHC = {
  // Get all referrals
  getReferrals: () => {
    return JSON.parse(localStorage.getItem('referrals') || '[]');
  },

  initDashboard: async () => {
    const res = await API.getAllReferrals();
    const referrals = res.success ? res.data : [];
    
    let active = 0, pending = 0, transfers = 0, completed = 0;
    
    referrals.forEach(r => {
      if (['PENDING_MATCHING', 'WAITING_HOSPITAL_ACCEPTANCE'].includes(r.status)) pending++;
      else if (['ACCEPTED', 'AMBULANCE_DISPATCHED', 'ROUTING'].includes(r.status)) transfers++;
      else if (['COMPLETED'].includes(r.status)) completed++;
      
      if (r.status !== 'COMPLETED' && r.status !== 'CANCELLED') active++;
    });

    document.getElementById('stat-active').textContent = active;
    document.getElementById('stat-pending').textContent = pending;
    document.getElementById('stat-transfers').textContent = transfers;
    document.getElementById('stat-completed').textContent = completed;

    const listEl = document.getElementById('recent-referrals-list');
    if (referrals.length === 0) {
      listEl.innerHTML = `<div class="p-8 text-center text-gray-500">No active referrals.</div>`;
      return;
    }

    // Sort by newest first
    const sorted = [...referrals].sort((a,b) => new Date(b.createdAt) - new Date(a.createdAt));
    
    listEl.innerHTML = sorted.map(r => {
      let statusColor = 'bg-gray-100 text-gray-700';
      let statusText = r.status.replace(/_/g, ' ');

      if (r.status === 'PENDING_MATCHING') { statusColor = 'bg-yellow-100 text-yellow-800'; }
      if (r.status === 'WAITING_HOSPITAL_ACCEPTANCE') { statusColor = 'bg-blue-100 text-blue-800'; }
      if (r.status === 'REJECTED_BY_HOSPITAL') { statusColor = 'bg-red-100 text-red-800 pulse-alert'; }
      if (r.status === 'ACCEPTED') { statusColor = 'bg-green-100 text-green-800'; }
      if (r.status === 'AMBULANCE_DISPATCHED' || r.status === 'ROUTING') { statusColor = 'bg-indigo-100 text-indigo-800'; }
      if (r.status === 'COMPLETED') { statusColor = 'bg-gray-100 text-gray-600'; }

      // Action link based on status
      let link = '#';
      if (r.status === 'PENDING_MATCHING' || r.status === 'REJECTED_BY_HOSPITAL') link = `phc-matching.html?id=${r.id}`;
      else if (r.status !== 'COMPLETED' && r.status !== 'CANCELLED') link = `phc-transfer.html?id=${r.id}`;

      return `
        <a href="${link}" class="block hover:bg-gray-50 transition-colors p-4 md:p-6">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="flex items-start gap-4">
              <div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-blue-700">personal_injury</span>
              </div>
              <div>
                <h4 class="font-bold text-gray-900">${r.patientId || 'Unknown Patient'}</h4>
                <div class="flex flex-wrap items-center gap-2 text-sm text-gray-500 mt-1">
                  <span>${r.condition || 'General'}</span>
                  <span>&bull;</span>
                  <span class="font-medium text-red-600">${r.severity || 'Medium'}</span>
                  <span>&bull;</span>
                  <span>ID: ${r.id}</span>
                </div>
              </div>
            </div>
            <div class="flex items-center gap-4">
              <span class="px-3 py-1 rounded-full text-xs font-semibold ${statusColor}">
                ${statusText}
              </span>
              <span class="material-symbols-outlined text-gray-400">chevron_right</span>
            </div>
          </div>
        </a>
      `;
    }).join('');
  },

  // other PHC functions will go here
};

window.PHC = PHC;
