class CameraManager {
  constructor(videoId, canvasId) {
    this.video = document.getElementById(videoId);
    this.canvas = document.getElementById(canvasId);
    this.stream = null;
    this.active = false;
  }

  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' }
      });
      this.video.srcObject = this.stream;
      await this.video.play();
      this.active = true;
      return true;
    } catch (err) {
      console.error('Camera error:', err);
      return false;
    }
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    this.active = false;
  }

  capture() {
    if (!this.active) return null;
    const ctx = this.canvas.getContext('2d');
    this.canvas.width = this.video.videoWidth || 640;
    this.canvas.height = this.video.videoHeight || 480;
    ctx.drawImage(this.video, 0, 0);
    return this.canvas.toDataURL('image/jpeg', 0.85);
  }

  captureBase64() {
    const dataUrl = this.capture();
    if (!dataUrl) return null;
    return dataUrl; // includes "data:image/jpeg;base64,..."
  }
}

function showToast(message, type = 'info', duration = 3500) {
  const existing = document.getElementById('globalToast');
  if (existing) existing.remove();

  const icons = { success: 'check-circle', error: 'times-circle', info: 'info-circle', warning: 'exclamation-triangle' };
  const colors = { success: '#10b981', error: '#ef4444', info: '#3b82f6', warning: '#f59e0b' };

  const toast = document.createElement('div');
  toast.id = 'globalToast';
  toast.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:9999;
    background:#1e293b; border:1px solid #334155;
    border-left:4px solid ${colors[type]};
    border-radius:10px; padding:14px 18px;
    display:flex; align-items:center; gap:12px;
    box-shadow:0 8px 32px rgba(0,0,0,.5);
    font-size:14px; max-width:340px;
    animation: slideIn .3s ease;
  `;
  toast.innerHTML = `
    <i class="fas fa-${icons[type]}" style="color:${colors[type]};font-size:18px;"></i>
    <span style="color:#f1f5f9;">${message}</span>
  `;

  const style = document.createElement('style');
  style.textContent = `@keyframes slideIn{from{transform:translateX(120%);opacity:0}to{transform:translateX(0);opacity:1}}`;
  document.head.appendChild(style);
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatTime(timeStr) {
  if (!timeStr) return '—';
  const [h, m] = timeStr.split(':');
  const hour = parseInt(h);
  const ampm = hour >= 12 ? 'PM' : 'AM';
  return `${hour % 12 || 12}:${m} ${ampm}`;
}

function exportTableToCSV(tableId, filename) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const rows = Array.from(table.querySelectorAll('tr'));
  const csv = rows.map(row =>
    Array.from(row.querySelectorAll('th, td'))
      .map(cell => `"${cell.innerText.replace(/"/g, '""')}"`)
      .join(',')
  ).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename || 'export.csv';
  a.click();
}
