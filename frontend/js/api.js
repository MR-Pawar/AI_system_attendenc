/**
 * api.js — All backend API calls
 * BASE_URL is auto-detected from config.js
 */

// Wait for config to load, fallback to localhost
const BASE_URL = (window.BACKEND_URL || 'http://localhost:8000') + '/api';

// Log for debugging
console.log('[API] BASE_URL configured:', BASE_URL);

const API = {
  getToken() { return localStorage.getItem('token'); },

  async request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const token   = this.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const url = `${BASE_URL}${path}`;
    console.log(`[API] ${method} ${url}`); // Debug logging

    try {
      const res = await fetch(url, options);

      if (res.status === 401) {
        localStorage.clear();
        const isInPages = window.location.pathname.includes('/pages/');
        window.location.href = isInPages ? '../index.html' : 'index.html';
        return;
      }

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        let errorMsg = data.detail || `HTTP ${res.status}`;
        
        // Enhanced error messages
        if (res.status === 503) {
          errorMsg = `⚠️ Database Error: ${data.detail || 'Cannot connect to database. Check your network and Supabase credentials.'}`;
        } else if (res.status === 500) {
          errorMsg = `Server Error: ${errorMsg}. Check backend logs for details.`;
        }
        
        console.error(`[API Error] ${method} ${url}: ${res.status}`, errorMsg);
        throw new Error(errorMsg);
      }
      console.log(`[API Success] ${method} ${url}:`, data);
      return data;
    } catch (error) {
      console.error(`[API Network Error] ${method} ${url}:`, error);
      
      // Provide helpful error messages
      if (error.message.includes('Failed to fetch')) {
        throw new Error(`Network Error: Cannot reach backend at ${BASE_URL}. Make sure backend server is running.`);
      }
      throw error;
    }
  },

  // ── Health Check ──────────────────────────────────────
  async testConnection() {
    try {
      const response = await fetch('http://localhost:8000/api/health');
      return await response.json();
    } catch (error) {
      return { status: 'error', message: error.message };
    }
  },

  // ── Auth ──────────────────────────────────────────────
  login(username, password) {
    return this.request('POST', '/auth/login', { username, password });
  },

  // ── Classes ───────────────────────────────────────────
  getClasses()          { return this.request('GET',    '/classes/'); },
  createClass(data)     { return this.request('POST',   '/classes/', data); },
  updateClass(id, data) { return this.request('PUT',    `/classes/${id}`, data); },
  deleteClass(id)       { return this.request('DELETE', `/classes/${id}`); },
  getStudentsByClass(cls){ return this.request('GET',   `/classes/${encodeURIComponent(cls)}/students`); },

  // ── Students ──────────────────────────────────────────
  getStudents(search='', cls='') {
    let q = '/students/?';
    if (search) q += `search=${encodeURIComponent(search)}&`;
    if (cls)    q += `class_name=${encodeURIComponent(cls)}`;
    return this.request('GET', q);
  },
  getStudent(id)           { return this.request('GET',    `/students/${id}`); },
  registerStudent(data, img){ return this.request('POST',  '/students/register', { ...data, face_image: img }); },
  captureFace(id, img)     { return this.request('POST',   `/students/${id}/capture-face`, { face_image: img }); },
  updateStudent(id, data)  { return this.request('PUT',    `/students/${id}`, data); },
  deleteStudent(id)        { return this.request('DELETE', `/students/${id}`); },
  checkFaceQuality(img)    { return this.request('POST',   '/students/check-face-quality', { face_image: img }); },
  updateFaceEncoding(id, imgs){ return this.request('POST',`/students/${id}/update-face`, { face_images: imgs }); },

  // ── Attendance ────────────────────────────────────────
  recognizeFace(img)       { return this.request('POST', '/attendance/recognize',    { face_image: img }); },
  detectFace(img)          { return this.request('POST', '/attendance/detect-face',  { face_image: img }); },
  getTodayAttendance()     { return this.request('GET',  '/attendance/today'); },
  getAttendanceHistory(p={}) {
    const q = new URLSearchParams(p).toString();
    return this.request('GET', `/attendance/history?${q}`);
  },
  markManualAttendance(d)  { return this.request('POST', '/attendance/manual', d); },
  exportAttendance(p={})   {
    const q = new URLSearchParams(p).toString();
    return this.request('GET', `/attendance/export?${q}`);
  },
  startSession()           { return this.request('POST', '/attendance/session/start', {}); },
  stopSession()            { return this.request('POST', '/attendance/session/stop',  {}); },
  sessionStatus()          { return this.request('GET',  '/attendance/session/status'); },
  sessionLog()             { return this.request('GET',  '/attendance/session/log'); },

  // ── Dashboard ─────────────────────────────────────────
  getDashboardStats()      { return this.request('GET', '/dashboard/stats'); },
  getMonthlyReport(y, m)   { return this.request('GET', `/dashboard/monthly-report?year=${y}&month=${m}`); },
  getDashboardStudents(p)  { return this.request('GET', `/dashboard/students?${new URLSearchParams(p)}`); },
  getDashboardTodayAtt(p)  { return this.request('GET', `/dashboard/attendance-today?${new URLSearchParams(p)}`); },
  getDashboardHistory(p)   { return this.request('GET', `/dashboard/attendance-history?${new URLSearchParams(p)}`); },
  getDashboardExport(p)    { return this.request('GET', `/dashboard/export?${new URLSearchParams(p)}`); },
};
