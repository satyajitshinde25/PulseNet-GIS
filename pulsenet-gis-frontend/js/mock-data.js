const MockData = {
  seed: () => {
    if (!localStorage.getItem('hospitals')) {
      localStorage.setItem('hospitals', JSON.stringify([
        {
          id: 'h1',
          name: 'City Hospital',
          distance: '2.1 km',
          eta: '8 mins',
          load: 'High',
          inventory: {
            icu: { total: 45, reserved: 5, available: 8 },
            ventilator: { total: 120, reserved: 10, available: 72 },
            bloodO_neg: { total: 50, reserved: 5, available: 12 },
            general: { total: 200, reserved: 20, available: 45 }
          }
        },
        {
          id: 'h2',
          name: 'District General Hospital',
          distance: '5.4 km',
          eta: '15 mins',
          load: 'Medium',
          inventory: {
            icu: { total: 30, reserved: 2, available: 15 },
            ventilator: { total: 60, reserved: 5, available: 40 },
            bloodO_neg: { total: 20, reserved: 1, available: 10 },
            general: { total: 150, reserved: 10, available: 60 }
          }
        },
        {
          id: 'h3',
          name: 'LifeCare Hospital',
          distance: '8.2 km',
          eta: '22 mins',
          load: 'Low',
          inventory: {
            icu: { total: 20, reserved: 0, available: 18 },
            ventilator: { total: 40, reserved: 1, available: 35 },
            bloodO_neg: { total: 30, reserved: 0, available: 28 },
            general: { total: 100, reserved: 5, available: 80 }
          }
        }
      ]));
    }

    if (!localStorage.getItem('ambulances')) {
      localStorage.setItem('ambulances', JSON.stringify([
        { id: 'a1', name: 'Unit A1', status: 'AVAILABLE', distance: '1.5 km', eta: '5 mins' },
        { id: 'a2', name: 'Unit A2', status: 'BUSY', distance: '3.0 km', eta: '10 mins' },
        { id: 'a3', name: 'Unit A3', status: 'AVAILABLE', distance: '4.2 km', eta: '12 mins' },
        { id: 'a4', name: 'Unit A4', status: 'AVAILABLE', distance: '6.5 km', eta: '18 mins' }
      ]));
    }

    // Ensure there's a referrals array
    if (!localStorage.getItem('referrals')) {
      localStorage.setItem('referrals', JSON.stringify([]));
    }
  },

  reset: () => {
    localStorage.clear();
    MockData.seed();
  }
};

// Seed on load
MockData.seed();
window.MockData = MockData;
