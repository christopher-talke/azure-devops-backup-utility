/* ADO Backup Dashboard — vanilla JS, no dependencies */

(function () {
  "use strict";

  var state = {
    backups: [],
    selectedId: null,
  };

  // -----------------------------------------------------------------------
  // Utilities
  // -----------------------------------------------------------------------

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }

  function fmtTimestamp(iso) {
    if (!iso) return "-";
    // Parse ISO and display as local date+time in a readable form.
    try {
      var d = new Date(iso);
      return d.toLocaleString(undefined, {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
      });
    } catch (e) { return iso; }
  }

  function fmtDuration(seconds) {
    if (!seconds && seconds !== 0) return "-";
    var s = Math.round(seconds);
    if (s < 60) return s + "s";
    var m = Math.floor(s / 60), rem = s % 60;
    return m + "m " + rem + "s";
  }

  // Parse "20260410T020000Z" into a readable date.
  function fmtRunTimestamp(ts) {
    // ts = YYYYMMDDTHHMMSSZ
    if (!ts || ts.length < 15) return ts;
    var y = ts.slice(0,4), mo = ts.slice(4,6), d = ts.slice(6,8);
    var h = ts.slice(9,11), mi = ts.slice(11,13);
    return y + "-" + mo + "-" + d + " " + h + ":" + mi + " UTC";
  }

  function api(path) {
    return fetch(path).then(function (r) {
      if (!r.ok) return null;
      return r.json();
    }).catch(function () { return null; });
  }

  function statusPill(status) {
    var cls = "status-" + (status || "skip");
    return '<span class="status-pill ' + cls + '">' + escapeHtml(status || "–") + "</span>";
  }

  // -----------------------------------------------------------------------
  // Sidebar: backup list
  // -----------------------------------------------------------------------

  function loadBackups() {
    var list = document.getElementById("backup-list");
    list.innerHTML = '<div class="list-loading">Loading&hellip;</div>';

    api("/api/backups").then(function (data) {
      if (!data) {
        list.innerHTML = '<div class="list-loading">Failed to load backups.</div>';
        return;
      }
      state.backups = data.backups || [];
      renderBackupList();
    });
  }

  function renderBackupList() {
    var container = document.getElementById("backup-list");
    if (state.backups.length === 0) {
      container.innerHTML = '<div class="list-loading">No backups found.</div>';
      return;
    }
    container.innerHTML = "";
    state.backups.forEach(function (b) {
      var isSelected = b.id === state.selectedId;
      var dotCls = b.total_errors === 0 ? "dot-ok" : "dot-warn";

      var div = document.createElement("div");
      div.className = "backup-item" + (isSelected ? " selected" : "");
      div.setAttribute("role", "button");
      div.setAttribute("tabindex", "0");
      div.innerHTML =
        '<div class="run-title">' +
          '<span class="run-status-dot ' + dotCls + '"></span>' +
          escapeHtml(fmtRunTimestamp(b.timestamp)) +
        "</div>" +
        '<div class="run-meta">' +
          '<span class="run-org">' + escapeHtml(b.org) + "</span>" +
          " &middot; " + b.total_entities.toLocaleString() + " entities" +
          " &middot; " +
          (b.total_errors === 0
            ? '<span class="badge badge-ok">0 errors</span>'
            : '<span class="badge badge-warn">' + b.total_errors + " error" + (b.total_errors !== 1 ? "s" : "") + "</span>"
          ) +
        "</div>";

      div.addEventListener("click", function () { selectBackup(b.id, b); });
      div.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") selectBackup(b.id, b);
      });
      container.appendChild(div);
    });
  }

  function selectBackup(id, b) {
    state.selectedId = id;
    renderBackupList();

    // Update content header
    var backup = b || state.backups.find(function (x) { return x.id === id; }) || {};
    document.getElementById("content-title").textContent = fmtRunTimestamp(backup.timestamp || "");
    document.getElementById("content-title").className = ""; // remove empty-state class
    var sub = document.getElementById("content-subtitle");
    sub.textContent = backup.org + " · " + backup.host;
    sub.hidden = false;

    loadSummary(id);
    switchTab("summary");
  }

  // -----------------------------------------------------------------------
  // Pivot tabs
  // -----------------------------------------------------------------------

  function switchTab(name) {
    document.querySelectorAll(".pivot-item").forEach(function (btn) {
      btn.classList.toggle("active", btn.dataset.tab === name);
    });
    document.querySelectorAll(".tab-panel").forEach(function (panel) {
      var active = panel.id === "tab-" + name;
      panel.classList.toggle("active", active);
      panel.hidden = !active;
    });

    if (!state.selectedId) return;
    if (name === "errors")       loadErrors(state.selectedId);
    if (name === "inventory")    loadInventory(state.selectedId);
    if (name === "verification") loadVerification(state.selectedId);
  }

  document.querySelectorAll(".pivot-item").forEach(function (btn) {
    btn.addEventListener("click", function () { switchTab(btn.dataset.tab); });
  });

  // -----------------------------------------------------------------------
  // Summary tab
  // -----------------------------------------------------------------------

  function loadSummary(id) {
    var prompt = document.getElementById("empty-prompt");
    var content = document.getElementById("summary-content");
    prompt.style.display = "none";
    content.hidden = false;

    var strip = document.getElementById("stat-strip");
    var limitsSection = document.getElementById("limits-section");
    strip.innerHTML = "<p style='color:var(--text-secondary)'>Loading&hellip;</p>";
    limitsSection.hidden = true;

    api("/api/backups/" + encodeURIComponent(id) + "/manifest").then(function (m) {
      if (!m) {
        strip.innerHTML = "<p style='color:var(--red-fg)'>Failed to load manifest.</p>";
        return;
      }

      var errValue = m.total_errors || 0;
      var stats = [
        { label: "Started",    value: fmtTimestamp(m.started_at) },
        { label: "Completed",  value: fmtTimestamp(m.completed_at) },
        { label: "Duration",   value: fmtDuration(m.duration_seconds) },
        { label: "Entities",   value: (m.total_entities || 0).toLocaleString() },
        {
          label: "Errors",
          value: errValue.toLocaleString(),
          valueClass: errValue === 0 ? "value-ok" : "value-error"
        },
        { label: "Version",    value: m.version || "-" },
      ];

      strip.innerHTML = stats.map(function (s) {
        return '<div class="stat-card">' +
          '<div class="stat-label">' + escapeHtml(s.label) + "</div>" +
          '<div class="stat-value ' + (s.valueClass || "") + '">' + escapeHtml(String(s.value)) + "</div>" +
          "</div>";
      }).join("");

      // Limits
      var limits = m.limits_applied || {};
      var chips = [];
      if (limits.max_items) chips.push({ label: "Max items", value: limits.max_items });
      if (limits.since)     chips.push({ label: "Since",     value: limits.since });
      if (limits.components && limits.components.length) {
        chips.push({ label: "Components", value: limits.components.join(", ") });
      }

      if (chips.length > 0) {
        limitsSection.hidden = false;
        document.getElementById("limits-content").innerHTML = chips.map(function (c) {
          return '<span class="limit-chip"><strong>' + escapeHtml(c.label) + ":</strong> " +
            escapeHtml(String(c.value)) + "</span>";
        }).join("");
      }

      // Update errors pivot badge
      var errBadge = document.getElementById("errors-badge");
      if (errValue > 0) {
        errBadge.textContent = errValue > 99 ? "99+" : errValue;
        errBadge.hidden = false;
      } else {
        errBadge.hidden = true;
      }
    });
  }

  // -----------------------------------------------------------------------
  // Errors tab
  // -----------------------------------------------------------------------

  function loadErrors(id) {
    var tbody = document.querySelector("#errors-table tbody");
    var label = document.getElementById("errors-count-label");
    tbody.innerHTML = "<tr><td colspan='4' style='color:var(--text-secondary)'>Loading&hellip;</td></tr>";
    label.textContent = "";

    api("/api/backups/" + encodeURIComponent(id) + "/errors").then(function (errors) {
      if (!errors || errors.length === 0) {
        tbody.innerHTML = "<tr><td colspan='4' style='color:var(--text-secondary)'>No errors recorded.</td></tr>";
        label.textContent = "";
        return;
      }
      label.textContent = errors.length + " error" + (errors.length !== 1 ? "s" : "");
      tbody.innerHTML = "";
      errors.forEach(function (e) {
        var tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" + escapeHtml(e.category || "") + "</td>" +
          "<td class='cell-secondary'>" + escapeHtml(e.name || "") + "</td>" +
          "<td class='cell-error'>" + escapeHtml(e.error || "") + "</td>" +
          "<td class='cell-secondary'>" + escapeHtml(fmtTimestamp(e.timestamp)) + "</td>";
        tbody.appendChild(tr);
      });
    });
  }

  // -----------------------------------------------------------------------
  // Inventory tab
  // -----------------------------------------------------------------------

  var _inventoryData = [];

  function loadInventory(id) {
    var tbody = document.querySelector("#inventory-table tbody");
    var label = document.getElementById("inventory-count-label");
    tbody.innerHTML = "<tr><td colspan='5' style='color:var(--text-secondary)'>Loading&hellip;</td></tr>";
    label.textContent = "";

    api("/api/backups/" + encodeURIComponent(id) + "/inventory").then(function (items) {
      _inventoryData = items || [];
      populateCategoryFilter();
      renderInventory(_inventoryData);
    });
  }

  function populateCategoryFilter() {
    var select = document.getElementById("inventory-filter");
    var categories = {};
    _inventoryData.forEach(function (item) {
      if (item.category) categories[item.category] = true;
    });
    select.innerHTML = '<option value="">All</option>';
    Object.keys(categories).sort().forEach(function (cat) {
      var opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = cat;
      select.appendChild(opt);
    });
  }

  function renderInventory(items) {
    var tbody = document.querySelector("#inventory-table tbody");
    var label = document.getElementById("inventory-count-label");
    if (items.length === 0) {
      tbody.innerHTML = "<tr><td colspan='5' style='color:var(--text-secondary)'>No inventory entries.</td></tr>";
      label.textContent = "";
      return;
    }
    label.textContent = items.length.toLocaleString() + " item" + (items.length !== 1 ? "s" : "");
    tbody.innerHTML = "";
    items.forEach(function (e) {
      var tr = document.createElement("tr");
      var sha = e.sha256 ? e.sha256.substring(0, 16) + "…" : "";
      tr.innerHTML =
        "<td>" + escapeHtml(e.category || "") + "</td>" +
        "<td>" + escapeHtml(e.name || "") + "</td>" +
        "<td>" + (e.count != null ? e.count.toLocaleString() : "") + "</td>" +
        '<td class="cell-mono" title="' + escapeHtml(e.sha256 || "") + '">' + escapeHtml(sha) + "</td>" +
        "<td class='cell-secondary'>" + escapeHtml(fmtTimestamp(e.timestamp)) + "</td>";
      tbody.appendChild(tr);
    });
  }

  document.getElementById("inventory-filter").addEventListener("change", function () {
    var val = this.value;
    renderInventory(val
      ? _inventoryData.filter(function (e) { return e.category === val; })
      : _inventoryData
    );
  });

  // -----------------------------------------------------------------------
  // Verification tab
  // -----------------------------------------------------------------------

  function loadVerification(id) {
    var bar    = document.getElementById("verification-summary-bar");
    var noMsg  = document.getElementById("no-verification-msg");
    var tbody  = document.querySelector("#verification-table tbody");

    bar.hidden   = true;
    noMsg.hidden = true;
    tbody.innerHTML = "<tr><td colspan='6' style='color:var(--text-secondary)'>Loading&hellip;</td></tr>";

    api("/api/backups/" + encodeURIComponent(id) + "/verification").then(function (report) {
      if (!report) {
        noMsg.hidden = false;
        tbody.innerHTML = "";
        return;
      }

      // Summary bar
      var s = report.summary || {};
      bar.hidden = false;
      bar.innerHTML =
        "Verified at: <strong>" + escapeHtml(fmtTimestamp(report.verified_at)) + "</strong>" +
        "&ensp;" +
        statusPill("pass") + " " + (s.passed  || 0) +
        "&ensp;" +
        statusPill("fail") + " " + (s.failed  || 0) +
        "&ensp;" +
        statusPill("skip") + " " + (s.skipped || 0);

      var results = report.results || [];
      if (results.length === 0) {
        tbody.innerHTML = "<tr><td colspan='6' style='color:var(--text-secondary)'>No results.</td></tr>";
        return;
      }
      tbody.innerHTML = "";
      results.forEach(function (r) {
        var tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" + escapeHtml(r.category || "") + "</td>" +
          "<td class='cell-secondary'>" + escapeHtml(r.project || "") + "</td>" +
          "<td>" + escapeHtml(r.item || "") + "</td>" +
          "<td>" + statusPill(r.status) + "</td>" +
          "<td class='cell-secondary'>" + escapeHtml(r.check || "") + "</td>" +
          "<td class='cell-secondary'>" + escapeHtml(r.note || "") + "</td>";
        tbody.appendChild(tr);
      });
    });
  }

  // -----------------------------------------------------------------------
  // Init
  // -----------------------------------------------------------------------

  loadBackups();
})();
