const Auth = {
  login: (email, password) => {
    // Demo credentials
    const demoUsers = {
      'doctor@phc.in': { id: 'u1', name: 'Dr. Sarah Jenkins', role: 'PHC_DOCTOR', location: 'PHC North', phcId: 'phc-1', password: 'demo123' },
      'doctor2@phc.in': { id: 'u12', name: 'Dr. Rahul Mehta', role: 'PHC_DOCTOR', location: 'Shirur PHC', phcId: 'phc-2', password: 'phc2pass' },
      'doctor3@phc.in': { id: 'u13', name: 'Dr. Priya Sharma', role: 'PHC_DOCTOR', location: 'Bhor PHC', phcId: 'phc-3', password: 'phc3pass' },
      'doctor4@phc.in': { id: 'u14', name: 'Dr. Anil Kumar', role: 'PHC_DOCTOR', location: 'Khed PHC', phcId: 'phc-4', password: 'phc4pass' },

      'manager@hospital.in': { id: 'u2', name: 'Manager Smith', role: 'HOSPITAL_MANAGER', hospitalId: 'hosp-1', password: 'demo123' },
      'manager2@hospital.in': { id: 'u22', name: 'Manager John', role: 'HOSPITAL_MANAGER', hospitalId: 'hosp-2', password: 'hosp2pass' },
      'manager3@hospital.in': { id: 'u23', name: 'Manager Lisa', role: 'HOSPITAL_MANAGER', hospitalId: 'hosp-3', password: 'hosp3pass' },
      'manager4@hospital.in': { id: 'u24', name: 'Manager David', role: 'HOSPITAL_MANAGER', hospitalId: 'hosp-4', password: 'hosp4pass' },
      'manager5@hospital.in': { id: 'u25', name: 'Manager Emma', role: 'HOSPITAL_MANAGER', hospitalId: 'hosp-5', password: 'hosp5pass' },
      'manager6@hospital.in': { id: 'u26', name: 'Manager Noah', role: 'HOSPITAL_MANAGER', hospitalId: 'hosp-6', password: 'hosp6pass' },

      'driver@ambulance.in': { id: 'u3', name: 'Driver Mike', role: 'AMBULANCE_DRIVER', unitId: 'amb-1', password: 'demo123' },
      'driver2@ambulance.in': { id: 'u32', name: 'Driver Sanjay', role: 'AMBULANCE_DRIVER', unitId: 'amb-2', password: 'amb2pass' },
      'driver3@ambulance.in': { id: 'u33', name: 'Driver Amit', role: 'AMBULANCE_DRIVER', unitId: 'amb-3', password: 'amb3pass' },
      'driver4@ambulance.in': { id: 'u34', name: 'Driver Prakash', role: 'AMBULANCE_DRIVER', unitId: 'amb-4', password: 'amb4pass' },
      'driver5@ambulance.in': { id: 'u35', name: 'Driver Ramesh', role: 'AMBULANCE_DRIVER', unitId: 'amb-5', password: 'amb5pass' }
    };
    
    const user = demoUsers[email];
    if (user && user.password === password) {
      // Don't store password in localStorage
      const { password: _, ...userToStore } = user;
      
      if (user.role === 'PHC_DOCTOR') localStorage.setItem('phc_currentUser', JSON.stringify(userToStore));
      else if (user.role === 'HOSPITAL_MANAGER') localStorage.setItem('hospital_currentUser', JSON.stringify(userToStore));
      else if (user.role === 'AMBULANCE_DRIVER') localStorage.setItem('ambulance_currentUser', JSON.stringify(userToStore));
      
      return user.role;
    }
    return null;
  },

  logout: () => {
    const path = window.location.pathname;
    if (path.includes('/phc/')) localStorage.removeItem('phc_currentUser');
    else if (path.includes('/hospital/')) localStorage.removeItem('hospital_currentUser');
    else if (path.includes('/ambulance/')) localStorage.removeItem('ambulance_currentUser');
    else {
      localStorage.removeItem('phc_currentUser');
      localStorage.removeItem('hospital_currentUser');
      localStorage.removeItem('ambulance_currentUser');
    }
    window.location.href = '/login.html';
  },

  getCurrentUser: (allowedRoles) => {
    const path = window.location.pathname;
    const isPHC = (allowedRoles && allowedRoles.includes('PHC_DOCTOR')) || path.includes('/phc/');
    const isHospital = (allowedRoles && allowedRoles.includes('HOSPITAL_MANAGER')) || path.includes('/hospital/');
    const isAmbulance = (allowedRoles && allowedRoles.includes('AMBULANCE_DRIVER')) || path.includes('/ambulance/');
    
    if (isPHC) {
      const u = localStorage.getItem('phc_currentUser');
      if (u) return JSON.parse(u);
    }
    if (isHospital) {
      const u = localStorage.getItem('hospital_currentUser');
      if (u) return JSON.parse(u);
    }
    if (isAmbulance) {
      const u = localStorage.getItem('ambulance_currentUser');
      if (u) return JSON.parse(u);
    }
    return null;
  },

  requireRole: (allowedRoles) => {
    const user = Auth.getCurrentUser(allowedRoles);
    if (!user) {
      window.location.href = '/login.html';
      return null;
    }
    if (allowedRoles && !allowedRoles.includes(user.role)) {
      window.location.href = '/login.html'; // Or forbidden page
      return null;
    }
    
    // Auto-update user name in UI if element exists
    const userNameEl = document.getElementById('user-name-display');
    if (userNameEl) {
      userNameEl.textContent = user.name;
    }
    
    return user;
  }
};

window.Auth = Auth;
