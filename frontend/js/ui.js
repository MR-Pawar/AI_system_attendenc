/* ── Global UI helpers ─────────────────────────────── */

// ── Toast system ───────────────────────────────────────
function ensureToastContainer() {
  let el = document.getElementById('toastContainer');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toastContainer';
    el.className = 'toast-container';
    document.body.appendChild(el);
  }
  return el;
}

function showToast(message, type = 'info', duration = 3400) {
  const icons = { success:'fa-check-circle', error:'fa-times-circle', info:'fa-info-circle', warning:'fa-exclamation-triangle' };
  const colors = { success:'#34d399', error:'#fb7185', info:'#38bdf8', warning:'#fbbf24' };
  const container = ensureToastContainer();

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <i class="fas ${icons[type]}" style="color:${colors[type]};font-size:16px;flex-shrink:0;"></i>
    <span style="color:#e2e8f0;">${message}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'toastOut .3s forwards';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Add toastOut keyframes once
const toastStyle = document.createElement('style');
toastStyle.textContent = '@keyframes toastOut{to{opacity:0;transform:translateX(110%)}}';
document.head.appendChild(toastStyle);

// ── Format helpers ─────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN',
    { day:'2-digit', month:'short', year:'numeric' });
}

function formatTime(timeStr) {
  if (!timeStr) return '—';
  const [h, m] = timeStr.split(':');
  const hour = parseInt(h);
  return `${hour % 12 || 12}:${m} ${hour >= 12 ? 'PM' : 'AM'}`;
}

function initials(name) {
  return (name || '?').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
}

// ── Mobile sidebar toggle ──────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar')?.classList.toggle('open');
}

// ── Overlay for mobile ─────────────────────────────────
document.addEventListener('click', e => {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  if (window.innerWidth <= 960 && sidebar.classList.contains('open')) {
    if (!sidebar.contains(e.target) && !e.target.closest('.hamburger')) {
      sidebar.classList.remove('open');
    }
  }
});
