// Utility functions for UI elements

const App = {
  showToast: (message, type = 'info') => {
    // Create toast container if it doesn't exist
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'fixed bottom-4 right-4 z-50 flex flex-col gap-2';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const colorClasses = {
      success: 'bg-green-100 border-green-500 text-green-700',
      error: 'bg-red-100 border-red-500 text-red-700',
      info: 'bg-blue-100 border-blue-500 text-blue-700',
      warning: 'bg-yellow-100 border-yellow-500 text-yellow-700',
    }[type] || colorClasses.info;

    toast.className = `border-l-4 p-4 rounded shadow-lg transition-opacity duration-300 ${colorClasses}`;
    toast.innerHTML = `<p class="font-medium">${message}</p>`;

    container.appendChild(toast);

    // Fade out and remove
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  },

  formatTime: (date = new Date()) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  },

  // Update navigation links to highlight active page
  initNavigation: (currentPageId) => {
    const navLinks = document.querySelectorAll('[data-nav]');
    navLinks.forEach(link => {
      if (link.dataset.nav === currentPageId) {
        link.classList.add('bg-blue-50', 'text-blue-700', 'font-semibold');
        link.classList.remove('text-gray-600', 'hover:bg-gray-50');
      } else {
        link.classList.remove('bg-blue-50', 'text-blue-700', 'font-semibold');
        link.classList.add('text-gray-600', 'hover:bg-gray-50');
      }
    });
  }
};

window.App = App;
