/* global __adobe_cep__ */
(function () {
  'use strict';
  var URL = 'https://taps.uz/fikrosfera/d';
  var KEY = 'uzscribe.donation.v1';
  var DAY = 86400000;
  var notice = document.getElementById('donationNotice');
  var support = document.getElementById('support');
  var never = document.getElementById('donationNever');
  var link = document.getElementById('donateLink');
  var status = document.getElementById('donationStatus');
  var state = { nextNoticeAt: 0, never: false };
  var persistent = false;
  if (!notice || !support || !never || !link || !status) return;

  try {
    var raw = localStorage.getItem(KEY);
    if (raw) {
      var saved = JSON.parse(raw);
      state.never = saved.never === true;
      if (typeof saved.nextNoticeAt === 'number' && isFinite(saved.nextNoticeAt) && saved.nextNoticeAt > 0) {
        state.nextNoticeAt = saved.nextNoticeAt;
      }
    }
    persistent = true;
  } catch (_) {
    // No persistent storage: keep only the manual button, so reopening never nags.
  }
  never.checked = state.never;
  function save() {
    if (!persistent) return false;
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
      return true;
    } catch (_) {
      persistent = false;
      return false;
    }
  }
  function hide(days) {
    notice.hidden = true;
    state.nextNoticeAt = Math.max(state.nextNoticeAt, Date.now() + days * DAY);
    save();
  }
  // Consume the monthly slot on showing, even if the panel is closed without dismissing.
  // Small panels need all their space for editing; the manual support button stays.
  if (persistent && !state.never && Date.now() >= state.nextNoticeAt &&
      !document.uzscribeBusy && (typeof window === 'undefined' || window.innerHeight > 380)) {
    state.nextNoticeAt = Date.now() + 30 * DAY;
    if (save()) notice.hidden = false;
  }
  document.getElementById('donationDismiss').onclick = function () { hide(30); };
  document.getElementById('donationShow').onclick = function (event) {
    if (event) event.stopPropagation();
    hide(30);
    support.open = true;
    link.focus();
  };
  never.onchange = function () {
    state.never = never.checked;
    hide(30);
    status.textContent = save() ?
      (state.never ? 'Donat eslatmasi o‘chirildi. Tugmadan istalgan payt foydalanishingiz mumkin.' : 'Donat eslatmasi oyiga bir martadan ko‘p chiqmaydi.') :
      'Bu panelda eslatma sozlamasi saqlanmadi. Avtomatik eslatma ko‘rsatilmaydi.';
  };
  link.onclick = function (event) {
    status.textContent = '';
    if (typeof __adobe_cep__ !== 'undefined' && typeof __adobe_cep__.openURLInDefaultBrowser === 'function') {
      if (event) event.preventDefault();
      try {
        __adobe_cep__.openURLInDefaultBrowser(URL);
      } catch (_) {
        status.textContent = 'Sahifa ochilmadi. QR kodni skanerlang yoki taps.uz/fikrosfera/d havolasini brauzerda oching.';
        return;
      }
    }
    // Opening a link is not proof of payment. Just pause reminders longer.
    hide(90);
  };
}());
