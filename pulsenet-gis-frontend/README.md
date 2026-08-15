# PulseNet-GIS Frontend

PulseNet-GIS is a Real-Time PHC Referral & Hospital Resource Coordination Platform. This repository contains the static frontend designed for a hackathon prototype, heavily mocking backend states using `localStorage`.

## Central Concept
The frontend strictly enforces the following workflow:
**CONFIRM HOSPITAL → RESERVE RESOURCES → THEN DISPATCH AMBULANCE**

This ensures that an ambulance is never dispatched before a hospital has explicitly confirmed it can accept the patient and has reserved the necessary resources (ICU beds, ventilators, blood, etc.).

## Architecture & Tech Stack
- **HTML5 & CSS3**
- **Vanilla JavaScript** (No React/Next.js/Node.js dependencies)
- **Tailwind CSS** (via CDN for rapid prototyping)
- **Leaflet.js & OpenStreetMap** (for mock ambulance navigation)

### State Management & API Readiness
To demonstrate a complete workflow without a backend, the `js/api.js` wrapper mimics a REST API using `localStorage` to simulate a database. The functions include intentional delays to simulate network requests and algorithm processing times. 
When connecting to a real Django REST Framework backend, you simply need to rewrite the methods inside `js/api.js` to use `fetch()` or `axios`.

## File Structure
- `index.html`: Entry redirect.
- `login.html`: Demo authentication for the three roles.
- `css/styles.css`: Custom animations (e.g. pulse-alert) and status colors.
- `js/app.js`: Global utilities like toast notifications.
- `js/auth.js`: Handles mock authentication and role-based redirects.
- `js/mock-data.js`: Seeds the initial hospital inventories, ambulances, and mock state.
- `js/api.js`: The simulated backend contract.
- `js/phc.js`, `js/hospital.js`, `js/ambulance.js`: Logic controllers for specific workflows.

## User Flows

### 1. PHC Doctor Flow (`phc-dashboard.html`)
- **Create Referral (`phc-referral.html`)**: Submit patient details and required resources.
- **Matching (`phc-matching.html`)**: System recommends hospitals. If a hospital rejects, the system re-runs matching and prompts the doctor again.
- **Transfer Timeline (`phc-transfer.html`)**: Real-time view of the strict state machine showing progression from creation to handover.

### 2. Hospital Manager Flow (`hospital-dashboard.html`)
- Displays live resource inventory capacity.
- **Incoming Referrals**: A high-priority panel appears when a referral targets the hospital.
- **Accept/Reject**: Rejecting triggers the PHC retry loop. Accepting immediately reserves the resources locally and authorizes ambulance dispatch.

### 3. Ambulance Driver Flow (`ambulance-dashboard.html`)
- Mobile-first interface.
- Polling waits for a referral to reach the `ACCEPTED` state (resources reserved).
- **Dispatch Alert (`ambulance-dispatch.html`)**: A 15-second countdown to accept or decline. Declining triggers a mock retry loop finding the next driver.
- **Navigation (`ambulance-navigation.html`)**: Leaflet map simulates the route from dispatch to PHC to the final Hospital handover.

## Running Locally
Simply open `index.html` or `login.html` in any modern web browser. No server is required, though a simple static server (like VSCode Live Server or `python -m http.server`) is recommended to avoid CORS issues with module imports or local storage if strict browser policies apply.
