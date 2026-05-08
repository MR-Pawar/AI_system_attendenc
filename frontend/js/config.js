/**
 * config.js — Auto-detect backend URL
 *
 * Works for ALL scenarios:
 *  ✅ PC browser (localhost)
 *  ✅ Phone on same WiFi
 *  ✅ VS Code Dev Tunnels (devtunnels.ms)
 *  ✅ ngrok / localtunnel
 *  ✅ Any deployed domain
 */

(function () {
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;

  let backendURL;
  let configMethod = 'unknown';

  /* ── 1. Running directly on PC (file:// or localhost) ─── */
  if (
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    window.location.protocol === 'file:'
  ) {
    backendURL = 'http://localhost:8000';
    configMethod = 'Local PC (localhost)';
  }

  /* ── 2. VS Code Dev Tunnels ──────────────────────────── */
  /*  Frontend: https://abc-3000.devtunnels.ms
      Backend:  https://abc-8000.devtunnels.ms
      We replace the port number in the subdomain         */
  else if (hostname.includes('devtunnels.ms')) {
    // Replace port in subdomain: xyz-5500 → xyz-8000
    backendURL = `${protocol}//${hostname.replace(/-\d+\.devtunnels/, '-8000.devtunnels')}`;
    configMethod =  'VS Code Dev Tunnels';
  }

  /* ── 3. ngrok (e.g. abc123.ngrok.io) ────────────────── */
  else if (hostname.includes('ngrok')) {
    // User must set BACKEND_URL manually or use same tunnel
    backendURL = localStorage.getItem('BACKEND_URL') || `${protocol}//${hostname}`;
    configMethod = 'ngrok tunnel';
  }

  /* ── 4. Local network IP (192.168.x.x, 10.x.x.x) ────── */
  else if (
    hostname.startsWith('192.168.') ||
    hostname.startsWith('10.') ||
    hostname.startsWith('172.')
  ) {
    backendURL = `http://${hostname}:8000`;
    configMethod = 'Local Network IP';
  }

  /* ── 5. Any other domain — same origin, port 8000 ────── */
  else {
    backendURL = `${protocol}//${hostname}:8000`;
    configMethod = 'Domain (custom)';
  }

  window.BACKEND_URL = backendURL;
  
  // Enhanced logging with timestamp
  const logMsg = `[Config] Backend URL: ${window.BACKEND_URL} | Method: ${configMethod} | Hostname: ${hostname}`;
  console.log(logMsg);
  
  // Store config in window for debugging
  window.CONFIG_DEBUG = {
    backendURL: window.BACKEND_URL,
    method: configMethod,
    hostname,
    protocol,
    timestamp: new Date().toISOString(),
  };
  
  console.log('[Config] Debug info:', window.CONFIG_DEBUG);
})();

