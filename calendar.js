// ============================================================
// TASKFLOW — calendar page
// A task appears on the calendar if it has a due date. If it has
// no due date but does have a reminder, it still shows up on the
// reminder's day, clearly labeled "Reminder" so it isn't mistaken
// for an actual deadline.
// ============================================================

(function () {
  var WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

  var state = {
    tasksByDate: {},
    viewYear: new Date().getFullYear(),
    viewMonth: new Date().getMonth(),
    selectedDate: null
  };

  function pad(n) { return n < 10 ? "0" + n : String(n); }
  function dateKey(y, m, d) { return y + "-" + pad(m + 1) + "-" + pad(d); }
  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }

  function renderWeekdayRow() {
    var el = document.getElementById("calWeekdays");
    el.innerHTML = WEEKDAYS.map(function (d) {
      return '<div class="cal-weekday">' + d + "</div>";
    }).join("");
  }

  function renderGrid() {
    var grid = document.getElementById("calGrid");
    var y = state.viewYear;
    var m = state.viewMonth;

    document.getElementById("calMonthLabel").textContent = MONTHS[m] + " " + y;

    var firstDay = new Date(y, m, 1).getDay();
    var daysInMonth = new Date(y, m + 1, 0).getDate();
    var daysInPrevMonth = new Date(y, m, 0).getDate();
    var todayKey = dateKey(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());

    var cells = [];

    for (var i = firstDay - 1; i >= 0; i--) {
      cells.push({ day: daysInPrevMonth - i, out: true, key: null });
    }
    for (var d = 1; d <= daysInMonth; d++) {
      cells.push({ day: d, out: false, key: dateKey(y, m, d) });
    }
    var remainder = (7 - (cells.length % 7)) % 7;
    for (var n = 1; n <= remainder; n++) {
      cells.push({ day: n, out: true, key: null });
    }

    grid.innerHTML = cells
      .map(function (cell) {
        if (cell.out) {
          return '<div class="cal-cell is-out"><div class="cal-date-num">' + cell.day + "</div></div>";
        }
        var tasks = state.tasksByDate[cell.key] || [];
        var isToday = cell.key === todayKey;
        var isSelected = cell.key === state.selectedDate;
        var dots = tasks
          .slice(0, 6)
          .map(function (t) {
            var cls = "cal-dot " + t.priority + (t._calSource === "reminder" ? " is-reminder" : "");
            return '<span class="' + cls + '"></span>';
          })
          .join("");

        return (
          '<div class="cal-cell' + (isToday ? " is-today" : "") + (isSelected ? " has-selection" : "") + '" data-key="' + cell.key + '">' +
          '<div class="cal-date-num">' + cell.day + "</div>" +
          (dots ? '<div class="cal-dots">' + dots + "</div>" : "") +
          "</div>"
        );
      })
      .join("");

    grid.querySelectorAll(".cal-cell[data-key]").forEach(function (cellEl) {
      cellEl.addEventListener("click", function () {
        state.selectedDate = cellEl.dataset.key;
        renderGrid();
        renderDayPanel();
      });
    });
  }

  function priorityLabel(p) {
    return p.charAt(0).toUpperCase() + p.slice(1);
  }

  function taskRowHtml(t) {
    var subLabel = t.status.replace("_", " ");
    if (t._calSource === "reminder") {
      subLabel = "Reminder \u00b7 " + t._calTime;
    }
    return (
      '<div class="cal-day-task">' +
      "<div>" +
      '<div style="font-weight:700;font-size:13.5px">' + escapeHtml(t.title) + "</div>" +
      '<div class="cal-day-task-sub' + (t._calSource === "reminder" ? " is-reminder" : "") + '">' +
      (t._calSource === "reminder" ? '<i class="fa-regular fa-bell"></i> ' : "") + subLabel +
      "</div>" +
      "</div>" +
      '<span class="pill pill-' + t.priority + '">' + priorityLabel(t.priority) + "</span>" +
      "</div>"
    );
  }

  function renderDayPanel() {
    var panel = document.getElementById("calDayPanel");
    if (!state.selectedDate) {
      panel.style.display = "none";
      return;
    }
    panel.style.display = "block";

    var parts = state.selectedDate.split("-");
    var d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    document.getElementById("calDayTitle").textContent =
      d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

    var tasks = state.tasksByDate[state.selectedDate] || [];
    document.getElementById("calDaySubtitle").textContent =
      tasks.length ? tasks.length + " task" + (tasks.length === 1 ? "" : "s") + " on this day" : "Nothing scheduled this day";

    var list = document.getElementById("calDayList");
    if (!tasks.length) {
      list.innerHTML =
        '<div class="empty"><i class="fa-regular fa-face-smile"></i><h3>Nothing scheduled</h3><p>Enjoy the clear day.</p></div>';
      return;
    }

    list.innerHTML = tasks.map(taskRowHtml).join("");
  }

  function renderMonthList() {
    var wrap = document.getElementById("calMonthList");
    if (!wrap) return;

    var y = state.viewYear;
    var m = state.viewMonth;
    var prefix = y + "-" + pad(m + 1) + "-";

    var monthTasks = [];
    Object.keys(state.tasksByDate).forEach(function (key) {
      if (key.indexOf(prefix) === 0) {
        state.tasksByDate[key].forEach(function (t) {
          monthTasks.push(t);
        });
      }
    });
    monthTasks.sort(function (a, b) { return a._calDate.localeCompare(b._calDate); });

    document.getElementById("calMonthListTitle").textContent =
      MONTHS[m] + " " + y + " \u2014 " + monthTasks.length + " task" + (monthTasks.length === 1 ? "" : "s") + " scheduled";

    if (!monthTasks.length) {
      wrap.innerHTML =
        '<div class="empty"><i class="fa-regular fa-calendar"></i><h3>Nothing scheduled this month</h3><p>Tasks with a due date or reminder in ' + MONTHS[m] + " will show up here.</p></div>";
      return;
    }

    wrap.innerHTML = monthTasks
      .map(function (t) {
        var parts = t._calDate.split("-");
        var d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        var dateLabel = d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
        var subLabel = t._calSource === "reminder" ? "Reminder" : t.status.replace("_", " ");
        return (
          '<div class="cal-day-task">' +
          "<div>" +
          '<div style="font-weight:700;font-size:13.5px">' + escapeHtml(t.title) + "</div>" +
          '<div class="cal-day-task-sub' + (t._calSource === "reminder" ? " is-reminder" : "") + '" style="font-family:var(--mono)">' +
          dateLabel + " &middot; " + subLabel +
          "</div>" +
          "</div>" +
          '<span class="pill pill-' + t.priority + '">' + priorityLabel(t.priority) + "</span>" +
          "</div>"
        );
      })
      .join("");
  }

  function loadData() {
    fetch("/calendar-data", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (tasks) {
        state.tasksByDate = {};
        if (Array.isArray(tasks)) {
          tasks.forEach(function (task) {
            // Prefer the due date. If there isn't one but a reminder is
            // set, still surface the task on the reminder's day, tagged
            // so it's clearly a reminder and not a deadline.
            if (task.due_date) {
              task._calDate = String(task.due_date).slice(0, 10);
              task._calSource = "due";
            } else if (task.reminder_at) {
              var raw = String(task.reminder_at);
              task._calDate = raw.slice(0, 10);
              var timePart = raw.slice(11, 16);
              task._calTime = timePart || "";
              task._calSource = "reminder";
            } else {
              return;
            }

            var key = task._calDate;
            if (!state.tasksByDate[key]) state.tasksByDate[key] = [];
            state.tasksByDate[key].push(task);
          });
        }

        // Default to today so the task list is visible immediately,
        // without requiring the user to click a day first.
        var now = new Date();
        state.selectedDate = dateKey(now.getFullYear(), now.getMonth(), now.getDate());

        document.getElementById("calLoading").style.display = "none";
        document.getElementById("calCard").style.display = "block";
        renderGrid();
        renderDayPanel();
        renderMonthList();
      })
      .catch(function () {
        document.getElementById("calLoading").innerHTML =
          '<i class="fa-solid fa-triangle-exclamation"></i><h3>Could not load the calendar</h3><p>Refresh the page to try again.</p>';
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("calCard").style.display = "none";
    renderWeekdayRow();

    document.getElementById("calPrev").addEventListener("click", function () {
      state.viewMonth -= 1;
      if (state.viewMonth < 0) { state.viewMonth = 11; state.viewYear -= 1; }
      renderGrid();
      renderMonthList();
    });
    document.getElementById("calNext").addEventListener("click", function () {
      state.viewMonth += 1;
      if (state.viewMonth > 11) { state.viewMonth = 0; state.viewYear += 1; }
      renderGrid();
      renderMonthList();
    });
    document.getElementById("calToday").addEventListener("click", function () {
      var now = new Date();
      state.viewYear = now.getFullYear();
      state.viewMonth = now.getMonth();
      state.selectedDate = dateKey(now.getFullYear(), now.getMonth(), now.getDate());
      renderGrid();
      renderDayPanel();
      renderMonthList();
    });

    loadData();
  });
})();