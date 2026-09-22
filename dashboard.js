// ============================================================
// TASKFLOW — dashboard page behaviour
// All dynamic text (task/subtask titles) is read from data-*
// attributes, never interpolated into inline JS strings — this
// keeps titles containing quotes, ampersands, etc. from ever
// breaking or injecting into a handler.
// ============================================================

function openRescheduleModal(taskId, currentDueDate, taskTitle) {
  var form = document.getElementById("rescheduleForm");
  var input = document.getElementById("new_date");
  form.action = "/reschedule/" + taskId;
  input.value = currentDueDate || "";
  input.min = new Date().toISOString().slice(0, 10);
  document.getElementById("rescheduleSub").textContent =
    "Pick a new due date for \u201c" + taskTitle + "\u201d. The task will be marked in progress.";
  openModal("rescheduleModal");
}

function openDeleteModal(taskId, taskTitle) {
  var form = document.getElementById("deleteForm");
  form.action = "/delete/" + taskId;
  form.reset();
  document.getElementById("customReasonField").style.display = "none";
  document.getElementById("deleteSub").textContent =
    "This can't be undone. Let us know why you're deleting \u201c" + taskTitle + "\u201d.";
  openModal("deleteModal");
}

// Generic confirmation modal, reused for: start task, complete task,
// push to tomorrow, complete subtask, uncomplete subtask, delete subtask.
function confirmAction(options) {
  var form = document.getElementById("confirmActionForm");
  var title = document.getElementById("confirmActionTitle");
  var message = document.getElementById("confirmActionMessage");
  var submitBtn = document.getElementById("confirmActionSubmit");
  var iconWrap = document.getElementById("confirmActionIcon");

  form.action = options.url;
  title.textContent = options.title || "Are you sure?";
  message.textContent = options.message || "";
  submitBtn.textContent = options.confirmLabel || "Confirm";
  submitBtn.className = "btn " + (options.danger ? "btn-danger" : "btn-primary");

  iconWrap.className = "confirm-icon" + (options.danger ? " danger" : "");
  iconWrap.innerHTML = '<i class="fa-solid ' + (options.icon || "fa-check") + '"></i>';

  openModal("confirmActionModal");
}

function openAddSubtaskModal(taskId, taskTitle) {
  var form = document.getElementById("addSubtaskForm");
  form.action = "/add-subtask/" + taskId;
  form.reset();
  document.getElementById("addSubtaskSub").textContent =
    "Break \u201c" + taskTitle + "\u201d into a smaller step.";
  openModal("addSubtaskModal");
}

function openSubtaskDateModal(subtaskId, currentDueDate, subtaskTitle) {
  var form = document.getElementById("subtaskDateForm");
  var input = document.getElementById("subtask_new_date");
  form.action = "/reschedule-subtask/" + subtaskId;
  input.value = currentDueDate || "";
  document.getElementById("subtaskDateSub").textContent =
    "Choose a due date for \u201c" + subtaskTitle + "\u201d, or clear it.";
  openModal("subtaskDateModal");
}

// ---------- Event delegation for every data-driven action button ----------
document.addEventListener("click", function (event) {
  var confirmBtn = event.target.closest(".js-confirm");
  if (confirmBtn) {
    var entityTitle = confirmBtn.dataset.entityTitle || "";
    var template = confirmBtn.dataset.messageTemplate || "%s";
    confirmAction({
      url: confirmBtn.dataset.url,
      title: confirmBtn.dataset.title,
      message: template.replace("%s", entityTitle),
      confirmLabel: confirmBtn.dataset.confirmLabel,
      icon: confirmBtn.dataset.icon,
      danger: confirmBtn.dataset.danger === "true"
    });
    return;
  }

  var rescheduleBtn = event.target.closest(".js-reschedule");
  if (rescheduleBtn) {
    openRescheduleModal(rescheduleBtn.dataset.taskId, rescheduleBtn.dataset.dueDate, rescheduleBtn.dataset.taskTitle);
    return;
  }

  var deleteTaskBtn = event.target.closest(".js-delete-task");
  if (deleteTaskBtn) {
    openDeleteModal(deleteTaskBtn.dataset.taskId, deleteTaskBtn.dataset.taskTitle);
    return;
  }

  var addSubtaskBtn = event.target.closest(".js-add-subtask");
  if (addSubtaskBtn) {
    openAddSubtaskModal(addSubtaskBtn.dataset.taskId, addSubtaskBtn.dataset.taskTitle);
    return;
  }

  var subtaskDateBtn = event.target.closest(".js-subtask-date");
  if (subtaskDateBtn) {
    openSubtaskDateModal(subtaskDateBtn.dataset.subtaskId, subtaskDateBtn.dataset.dueDate, subtaskDateBtn.dataset.subtaskTitle);
    return;
  }
});

document.addEventListener("DOMContentLoaded", function () {
  // Show the free-text field only when "Other reason" is picked
  var reasonInputs = document.querySelectorAll('input[name="deletion_reason"]');
  var customField = document.getElementById("customReasonField");
  var customInput = document.getElementById("custom_reason");

  reasonInputs.forEach(function (input) {
    input.addEventListener("change", function () {
      var showCustom = input.value === "other" && input.checked;
      if (showCustom) {
        customField.style.display = "block";
        customInput.setAttribute("required", "required");
      } else if (input.checked) {
        customField.style.display = "none";
        customInput.removeAttribute("required");
      }
    });
  });

  // Client-side search + filter over the task list already on the page
  var searchInput = document.getElementById("taskSearch");
  var priorityFilter = document.getElementById("priorityFilter");
  var statusFilter = document.getElementById("statusFilter");
  var noResults = document.getElementById("noResults");

  function applyFilters() {
    var query = (searchInput.value || "").trim().toLowerCase();
    var priority = priorityFilter.value;
    var status = statusFilter.value;
    var visibleCount = 0;

    document.querySelectorAll(".task-card").forEach(function (card) {
      var matchesQuery = !query || card.dataset.search.indexOf(query) !== -1;
      var matchesPriority = !priority || card.dataset.priority === priority;
      var matchesStatus = !status || card.dataset.status === status;
      var visible = matchesQuery && matchesPriority && matchesStatus;
      card.style.display = visible ? "" : "none";
      if (visible) visibleCount++;
    });

    if (noResults) noResults.style.display = visibleCount === 0 ? "block" : "none";
  }

  if (searchInput) {
    searchInput.addEventListener("input", applyFilters);
    priorityFilter.addEventListener("change", applyFilters);
    statusFilter.addEventListener("change", applyFilters);
  }
});