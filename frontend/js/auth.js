function requireAuth() {
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = window.location.pathname.includes('/pages/') ? '../index.html' : 'index.html';
    return false;
  }
  const adminUser = localStorage.getItem('adminUser') || 'Admin';
  const el = document.getElementById('adminName');
  if (el) el.textContent = adminUser;
  const av = document.getElementById('adminAvatar');
  if (av) av.textContent = adminUser.charAt(0).toUpperCase();
  return true;
}

function logout() {
  localStorage.clear();
  window.location.href = window.location.pathname.includes('/pages/') ? '../index.html' : 'index.html';
}

function setActiveNav(page) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
}

function navigateTo(page) {
  window.location.href = page;
}
