// ============================================================
// TASKFLOW — notifications history page
// ============================================================

document.addEventListener("DOMContentLoaded", function () {
  var csrf = getCsrfToken();

  function markReadRequest(id) {
    return fetch("/notifications/" + encodeURIComponent(id) + "/read", {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-CSRFToken": csrf }
    }).then(function (r) { return r.json(); });
  }

  document.querySelectorAll(".mark-read-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var row = btn.closest(".notif-row");
      var id = btn.dataset.id;
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

      markReadRequest(id)
        .then(function (data) {
          if (!data.success) throw new Error("failed");
          row.classList.remove("is-unread");
          btn.outerHTML = '<span class="pill pill-status" style="align-self:center">Read</span>';
          if (typeof refreshUnreadCount === "function") refreshUnreadCount();
        })
        .catch(function () {
          btn.disabled = false;
          btn.innerHTML = '<i class="fa-solid fa-check"></i> Mark read';
        });
    });
  });

  var markAllBtn = document.getElementById("markAllBtn");
  if (markAllBtn) {
    markAllBtn.addEventListener("click", function () {
      markAllBtn.disabled = true;
      markAllBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Updating…';

      fetch("/notifications/read-all", {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json", "X-CSRFToken": csrf }
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.success) throw new Error("failed");
          document.querySelectorAll(".notif-row.is-unread").forEach(function (row) {
            row.classList.remove("is-unread");
            var btn = row.querySelector(".mark-read-btn");
            if (btn) btn.outerHTML = '<span class="pill pill-status" style="align-self:center">Read</span>';
          });
          if (typeof refreshUnreadCount === "function") refreshUnreadCount();
        })
        .catch(function () {})
        .finally(function () {
          markAllBtn.disabled = false;
          markAllBtn.innerHTML = '<i class="fa-solid fa-check-double"></i> Mark all as read';
        });
    });
  }

  var searchInput = document.getElementById("notifSearch");
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      var query = searchInput.value.trim().toLowerCase();
      document.querySelectorAll(".notif-row").forEach(function (row) {
        row.style.display = !query || row.dataset.search.indexOf(query) !== -1 ? "grid" : "none";
      });
    });
  }
});