/**
 * MapService handles initialization and management of Leaflet maps
 */
const MapService = {
  // Tile layer standard configurations
  defaultTiles: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
  attribution: '&copy; OpenStreetMap contributors',
  
  // Icon presets
  icons: {
    hospital: null,
    ambulance: null,
    phc: null,
    default: null
  },
  
  initIcons() {
    if (typeof L === 'undefined') return;
    
    // Create custom SVG icons
    const createIcon = (color, symbol) => {
      return L.divIcon({
        className: 'custom-map-icon',
        html: `
          <div style="
            background-color: ${color};
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
          ">
            <span class="material-symbols-outlined" style="font-size: 20px;">${symbol}</span>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16]
      });
    };

    this.icons.hospital = createIcon('#4f46e5', 'local_hospital'); // Indigo
    this.icons.ambulance = createIcon('#ef4444', 'ambulance'); // Red
    this.icons.phc = createIcon('#2563eb', 'medical_services'); // Blue
    this.icons.default = createIcon('#6b7280', 'location_on'); // Gray
  },

  /**
   * Initialize a new Leaflet map
   * @param {string} containerId - The ID of the div container
   * @param {Array} center - [lat, lng] array
   * @param {number} zoom - initial zoom level
   * @returns {L.Map} - The Leaflet map instance
   */
  initMap(containerId, center = [18.5204, 73.8567], zoom = 12) {
    if (typeof L === 'undefined') {
      console.error('Leaflet is not loaded');
      return null;
    }

    if (!this.icons.default) {
      this.initIcons();
    }

    const map = L.map(containerId).setView(center, zoom);
    
    L.tileLayer(this.defaultTiles, {
      attribution: this.attribution
    }).addTo(map);
    
    return map;
  },

  /**
   * Add a generic marker to the map
   */
  addMarker(map, latlng, title = '', type = 'default') {
    if (!map) return null;
    const icon = this.icons[type] || this.icons.default;
    const marker = L.marker(latlng, { icon }).addTo(map);
    if (title) {
      marker.bindPopup(`<strong>${title}</strong>`);
    }
    return marker;
  },

  /**
   * Fit the map to an array of markers or coordinates
   */
  fitBounds(map, latlngs) {
    if (!map || latlngs.length === 0) return;
    map.fitBounds(latlngs, { padding: [50, 50] });
  },

  /**
   * Draw a route between two points using OSRM
   */
  async drawRoute(map, start, end, color = '#2563eb') {
    if (!map) return null;
    
    // OSRM expects coordinates in lon,lat order
    const startStr = `${start[1]},${start[0]}`;
    const endStr = `${end[1]},${end[0]}`;
    
    try {
      const url = `https://router.project-osrm.org/route/v1/driving/${startStr};${endStr}?overview=full&geometries=geojson`;
      const res = await fetch(url);
      const data = await res.json();
      
      if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
        const route = data.routes[0];
        const geometry = route.geometry;
        
        const routeLine = L.geoJSON(geometry, {
          style: {
            color: color,
            weight: 5,
            opacity: 0.8
          }
        }).addTo(map);
        
        return {
          layer: routeLine,
          distance: route.distance, // in meters
          duration: route.duration  // in seconds
        };
      } else {
        console.warn("OSRM routing failed, falling back to straight line");
        const routeLine = L.polyline([start, end], {color: color, weight: 5, dashArray: '10, 10'}).addTo(map);
        return { layer: routeLine, distance: 0, duration: 0 };
      }
    } catch (err) {
      console.error("OSRM API error", err);
      const routeLine = L.polyline([start, end], {color: color, weight: 5, dashArray: '10, 10'}).addTo(map);
      return { layer: routeLine, distance: 0, duration: 0 };
    }
  }
};
