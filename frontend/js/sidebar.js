/* ── Sidebar + Topbar + Bottom Nav builder ─────────────────── */

function buildLayout(pageKey, pageTitle, tag = '') {
  const nav = [
    { key:'dashboard',  label:'Dashboard',        icon:'fa-th-large',           href:'dashboard.html' },
    { key:'attendance', label:'Attendance',        icon:'fa-camera',             href:'attendance.html' },
    { key:'register',   label:'Register',          icon:'fa-user-plus',          href:'register.html' },
    { key:'students',   label:'Students',          icon:'fa-user-graduate',      href:'students.html' },
    { key:'classes',    label:'Classes',           icon:'fa-chalkboard-teacher', href:'classes.html' },
    { key:'history',    label:'History',           icon:'fa-clock-rotate-left',  href:'history.html' },
  ];

  const adminUser = localStorage.getItem('adminUser') || 'Admin';
  const av        = adminUser.charAt(0).toUpperCase();

  /* ── Desktop Sidebar ─────────────────────────────── */
  document.getElementById('sidebar').innerHTML = `
    <div class="sidebar-logo">
      <div class="logo-mark"><i class="fas fa-brain"></i></div>
      <div class="logo-text">
        <strong>AI Face Attendance</strong>
        <span>Biometric System</span>
      </div>
    </div>
    <nav class="sidebar-nav">
      <div class="nav-section">
        <span class="nav-section-label">Navigation</span>
        ${nav.map(n => `
          <div class="nav-item ${n.key === pageKey ? 'active' : ''}"
               onclick="navTo('${n.href}')">
            <i class="fas ${n.icon}"></i> ${n.label}
            ${n.key === 'attendance' ? '<span class="badge-dot"></span>' : ''}
          </div>`).join('')}
      </div>
    </nav>
    <div class="sidebar-footer">
      <div class="admin-row">
        <div class="admin-ring">${av}</div>
        <div class="admin-info">
          <div class="admin-name">${adminUser}</div>
          <div class="admin-role">Administrator</div>
        </div>
      </div>
      <button class="btn btn-ghost btn-sm btn-full" onclick="logout()">
        <i class="fas fa-right-from-bracket"></i> Logout
      </button>
    </div>`;

  /* ── Topbar ─────────────────────────────────────── */
  document.getElementById('topbar').innerHTML = `
    <div class="topbar-left">
      <button class="hamburger" onclick="openSidebar()" aria-label="Menu">
        <i class="fas fa-bars"></i>
      </button>
      <div class="topbar-title">${pageTitle}</div>
      ${tag ? `<span class="page-tag">${tag}</span>` : ''}
    </div>
    <div class="topbar-right" id="topbarActions">
      <span class="topbar-time mono" id="topbarClock"></span>
    </div>`;

  /* ── Sidebar overlay (mobile) ───────────────────── */
  if (!document.getElementById('sidebarOverlay')) {
    const overlay = document.createElement('div');
    overlay.id        = 'sidebarOverlay';
    overlay.className = 'sidebar-overlay';
    overlay.onclick   = closeSidebar;
    document.body.appendChild(overlay);
  }

  /* ── Bottom nav (mobile) ────────────────────────── */
  const bottomNavItems = [
    { key:'dashboard',  icon:'fa-th-large',    label:'Home' },
    { key:'attendance', icon:'fa-camera',       label:'Attend' },
    { key:'register',   icon:'fa-user-plus',    label:'Register' },
    { key:'students',   icon:'fa-users',        label:'Students' },
    { key:'history',    icon:'fa-history',      label:'History' },
  ];

  if (!document.getElementById('bottomNav')) {
    const bn = document.createElement('nav');
    bn.id        = 'bottomNav';
    bn.className = 'bottom-nav';
    bn.innerHTML = bottomNavItems.map(item => `
      <button class="bn-item ${item.key === pageKey ? 'active' : ''}"
              onclick="navTo('${nav.find(n=>n.key===item.key)?.href || '#'}')">
        <i class="fas ${item.icon}"></i>
        <span>${item.label}</span>
      </button>`).join('');
    document.body.appendChild(bn);
  }

  /* ── Live clock ─────────────────────────────────── */
  setInterval(() => {
    const el = document.getElementById('topbarClock');
    if (el) el.textContent = new Date().toLocaleTimeString('en-IN',
      { hour:'2-digit', minute:'2-digit', second:'2-digit' });
  }, 1000);
}

/* ── Sidebar open/close ──────────────────────────────── */
function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('sidebarOverlay').classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay')?.classList.remove('show');
  document.body.style.overflow = '';
}

function toggleSidebar() {
  const s = document.getElementById('sidebar');
  s.classList.contains('open') ? closeSidebar() : openSidebar();
}

/* ── Navigate ─────────────────────────────────────────── */
function navTo(href) {
  closeSidebar();
  location.href = href;
}

/* ── Close sidebar on resize to desktop ─────────────── */
window.addEventListener('resize', () => {
  if (window.innerWidth > 960) closeSidebar();
});

/* ── Swipe to open sidebar (mobile) ─────────────────── */
let touchStartX = 0;
document.addEventListener('touchstart', e => {
  touchStartX = e.touches[0].clientX;
}, { passive: true });
document.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (touchStartX < 24 && dx > 60) openSidebar();
  if (dx < -60 && document.getElementById('sidebar').classList.contains('open')) closeSidebar();
}, { passive: true });
