// ============================================================
// TASKFLOW — global behaviour shared by every page
// ============================================================

function getCsrfToken() {
  var input = document.querySelector('input[name="csrf_token"]');
  return input ? input.value : "";
}

// ---------- Modals ----------
function openModal(id) {
  var overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.classList.add("open");
  var focusable = overlay.querySelector("input, select, textarea, button");
  if (focusable) focusable.focus();
  document.addEventListener("keydown", handleModalEscape);
}

function closeModal(id) {
  var overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.classList.remove("open");
  document.removeEventListener("keydown", handleModalEscape);
}

function handleModalEscape(event) {
  if (event.key === "Escape") {
    document.querySelectorAll(".modal-overlay.open").forEach(function (overlay) {
      overlay.classList.remove("open");
    });
  }
}

document.addEventListener("click", function (event) {
  if (event.target.classList && event.target.classList.contains("modal-overlay")) {
    event.target.classList.remove("open");
  }
});

// ---------- Mobile sidebar ----------
document.addEventListener("DOMContentLoaded", function () {
  var sidebar = document.getElementById("sidebar");
  var mainArea = document.querySelector(".main");
  if (sidebar && mainArea) {
    mainArea.addEventListener("click", function (event) {
      if (sidebar.classList.contains("open") && !sidebar.contains(event.target)) {
        sidebar.classList.remove("open");
      }
    });
  }
});

// ---------- Notifications bell ----------
function timeAgo(isoString) {
  if (!isoString) return "";
  var then = new Date(isoString.replace(" ", "T"));
  var diffMinutes = Math.round((Date.now() - then.getTime()) / 60000);
  if (diffMinutes < 1) return "Just now";
  if (diffMinutes < 60) return diffMinutes + "m ago";
  var diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return diffHours + "h ago";
  var diffDays = Math.round(diffHours / 24);
  return diffDays + "d ago";
}

function escapeHtml(text) {
  var div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

function renderNotifPanel(items) {
  var body = document.getElementById("notifPanelBody");
  if (!body) return;

  if (!items || !items.length) {
    body.innerHTML = '<div class="notif-empty">You\u2019re all caught up.</div>';
    return;
  }

  body.innerHTML = items
    .map(function (item) {
      var isOverdue = item.notification_type === "task_overdue";
      return (
        '<div class="notif-item">' +
        '<div class="notif-icon' + (isOverdue ? " overdue" : "") + '">' +
        '<i class="fa-solid ' + (isOverdue ? "fa-triangle-exclamation" : "fa-bell") + '"></i>' +
        "</div>" +
        '<div class="notif-body">' +
        '<div class="notif-title">' + escapeHtml(item.title) + "</div>" +
        (item.message ? '<div class="notif-msg">' + escapeHtml(item.message) + "</div>" : "") +
        '<div class="notif-time">' + timeAgo(item.created_at) + "</div>" +
        "</div>" +
        "</div>"
      );
    })
    .join("");
}

function updateBadges(count) {
  var bellDot = document.getElementById("bellDot");
  var navBadge = document.getElementById("navNotifBadge");
  if (bellDot) bellDot.classList.toggle("show", count > 0);
  if (navBadge) {
    navBadge.textContent = count > 99 ? "99+" : String(count);
    navBadge.classList.toggle("show", count > 0);
  }
}

function refreshUnreadCount() {
  fetch("/notifications/unread-count", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (data) { updateBadges(data.count || 0); })
    .catch(function () {});
}

function loadNotifPanel() {
  fetch("/notifications", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (data) { renderNotifPanel(data); })
    .catch(function () {
      var body = document.getElementById("notifPanelBody");
      if (body) body.innerHTML = '<div class="notif-empty">Could not load notifications.</div>';
    });
}

document.addEventListener("DOMContentLoaded", function () {
  var bellBtn = document.getElementById("notifBellBtn");
  var panel = document.getElementById("notifPanel");

  if (bellBtn && panel) {
    bellBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      var isOpen = panel.classList.toggle("open");
      bellBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (isOpen) loadNotifPanel();
    });

    document.addEventListener("click", function (event) {
      if (panel.classList.contains("open") && !panel.contains(event.target) && event.target !== bellBtn) {
        panel.classList.remove("open");
        bellBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  refreshUnreadCount();
  setInterval(refreshUnreadCount, 60000);
});