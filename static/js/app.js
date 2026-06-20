/* 360° NPS Platform — Vanilla JS */

// ── SSE Notifications ──
(function initSSE() {
  const container = document.getElementById('sse-toast-container');
  const bell = document.querySelector('.notif-bell');
  const dot = document.querySelector('.notif-dot');
  if (!container) return;

  const es = new EventSource('/api/events');

  es.addEventListener('critical_feedback', (e) => {
    const data = JSON.parse(e.data);
    showToast(data.message || 'Nuevo feedback crítico recibido', data.ticket_number, data.priority);
    if (dot) dot.classList.add('active');
  });

  es.onerror = () => {
    // SSE reconnects automatically; ignore transient errors
  };

  function showToast(message, ticketNo, priority) {
    const toast = document.createElement('div');
    toast.className = 'sse-toast';
    toast.innerHTML = `
      <div class="toast-title">⚠️ Feedback Crítico</div>
      <div class="toast-body">${message}</div>
      ${ticketNo ? `<div class="toast-body mt-4" style="font-weight:600;">Ticket: ${ticketNo}</div>` : ''}
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 8000);
  }
})();

// ── NPS Scale Interactive ──
(function initNPSScale() {
  const btns = document.querySelectorAll('.nps-btn');
  const hiddenInput = document.getElementById('nps-hidden-input');
  const submitBtn = document.getElementById('survey-submit-btn');

  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      const score = parseInt(btn.dataset.score, 10);
      if (hiddenInput) hiddenInput.value = score;
      if (submitBtn) submitBtn.disabled = false;
    });
  });
})();

// ── Dashboard Filter Form Auto-Submit ──
(function initFilterAutoSubmit() {
  const filterSelects = document.querySelectorAll('[data-auto-submit]');
  filterSelects.forEach(el => {
    el.addEventListener('change', () => el.closest('form').submit());
  });
})();

// ── Ticket Status Update ──
(function initTicketForm() {
  const statusSelect = document.getElementById('ticket-status-select');
  if (!statusSelect) return;
  statusSelect.addEventListener('change', () => {
    const resolved = statusSelect.value === 'resolved';
    const notesGroup = document.getElementById('resolution-notes-group');
    if (notesGroup) notesGroup.style.display = resolved ? 'block' : 'none';
  });
})();

// ── Checklist Progress ──
(function initChecklist() {
  const checkboxes = document.querySelectorAll('.checklist-checkbox');
  const progressBar = document.getElementById('checklist-progress-bar');
  const progressText = document.getElementById('checklist-progress-text');
  if (!checkboxes.length) return;

  function updateProgress() {
    const total = checkboxes.length;
    const checked = Array.from(checkboxes).filter(c => c.checked).length;
    const pct = total ? Math.round((checked / total) * 100) : 0;
    if (progressBar) progressBar.style.width = pct + '%';
    if (progressText) progressText.textContent = `${checked}/${total} completados (${pct}%)`;
  }

  checkboxes.forEach(cb => cb.addEventListener('change', updateProgress));
  updateProgress();
})();

// ── Topbar mobile menu toggle ──
(function initMobileMenu() {
  const toggle = document.getElementById('menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (!toggle || !sidebar) return;
  toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
})();

// ── Alert auto-dismiss ──
(function initAlertDismiss() {
  document.querySelectorAll('[data-auto-dismiss]').forEach(el => {
    const delay = parseInt(el.dataset.autoDismiss, 10) || 5000;
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, delay);
  });
})();
