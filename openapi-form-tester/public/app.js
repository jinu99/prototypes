/**
 * Main app: sidebar, panel orchestration, request sending, drift display.
 * Depends on: dom-utils.js, form-builder.js
 */
(function () {
  "use strict";
  var el = window.DOM.el;
  var clear = window.DOM.clear;

  var spec = null;
  var selectedEndpoint = null;
  var lastResponse = null;

  // ─── Init ───
  async function init() {
    try {
      var res = await fetch("/api/spec");
      spec = await res.json();
      if (spec.error) {
        document.getElementById("apiTitle").textContent = "Error: " + spec.error;
        return;
      }
      document.getElementById("apiTitle").textContent = spec.title + " v" + spec.version;
      renderEndpointList();
    } catch (err) {
      document.getElementById("apiTitle").textContent = "Failed to load spec";
    }
  }

  // ─── Sidebar ───
  function renderEndpointList() {
    var container = document.getElementById("endpointList");
    clear(container);

    var tagged = {};
    var untagged = [];
    for (var i = 0; i < spec.endpoints.length; i++) {
      var ep = spec.endpoints[i];
      if (ep.tags && ep.tags.length > 0) {
        for (var t = 0; t < ep.tags.length; t++) {
          var tag = ep.tags[t];
          if (!tagged[tag]) tagged[tag] = [];
          tagged[tag].push(ep);
        }
      } else {
        untagged.push(ep);
      }
    }

    function addEndpoints(endpoints) {
      for (var j = 0; j < endpoints.length; j++) {
        (function (ep) {
          container.appendChild(el("div", {
            className: "endpoint-item",
            dataset: { operationId: ep.operationId },
            onClick: function () { selectEndpoint(ep); }
          }, [
            el("span", { className: "method-badge method-" + ep.method, textContent: ep.method }),
            el("span", { className: "endpoint-path", textContent: ep.path })
          ]));
        })(endpoints[j]);
      }
    }

    for (var tagName in tagged) {
      container.appendChild(el("div", { className: "tag-header", textContent: tagName }));
      addEndpoints(tagged[tagName]);
    }
    if (untagged.length > 0) addEndpoints(untagged);
  }

  function selectEndpoint(ep) {
    selectedEndpoint = ep;
    lastResponse = null;
    document.querySelectorAll(".endpoint-item").forEach(function (item) {
      item.classList.toggle("active", item.dataset.operationId === ep.operationId);
    });
    renderMainPanel();
  }

  // ─── Main Panel ───
  function renderMainPanel() {
    var panel = document.getElementById("mainPanel");
    clear(panel);
    var ep = selectedEndpoint;

    panel.appendChild(el("div", { className: "panel-header" }, [
      el("span", { className: "method-badge method-" + ep.method, textContent: ep.method }),
      el("h2", { textContent: ep.path }),
      ep.summary ? el("span", { className: "summary", textContent: ep.summary }) : null
    ]));

    var content = el("div", { className: "panel-content" });

    // Server
    var serverSection = el("div", { className: "section" }, [el("div", { className: "section-title", textContent: "Server" })]);
    var serverRow = el("div", { className: "server-row" }, [el("label", { textContent: "Base URL" })]);
    if (spec.servers.length > 1) {
      var select = el("select", { id: "serverSelect" });
      for (var i = 0; i < spec.servers.length; i++)
        select.appendChild(el("option", { value: spec.servers[i].url, textContent: spec.servers[i].url }));
      serverRow.appendChild(select);
    } else {
      serverRow.appendChild(el("input", { id: "serverInput", value: spec.servers[0].url }));
    }
    serverSection.appendChild(serverRow);
    content.appendChild(serverSection);

    // Request body
    var bodySection = el("div", { className: "section" }, [el("div", { className: "section-title", textContent: "Request Body" })]);
    if (ep.requestBody && ep.requestBody.schema) {
      var fc = el("div", { id: "formContainer" });
      window.FormBuilder.buildSchemaForm(fc, ep.requestBody.schema, "", ep.requestBody.schema.required || []);
      bodySection.appendChild(fc);
    } else {
      bodySection.appendChild(el("p", { className: "no-body", textContent: "No request body for this endpoint" }));
    }
    content.appendChild(bodySection);

    // Send
    content.appendChild(el("div", { className: "send-row" }, [
      el("button", { className: "btn-send", id: "btnSend", textContent: "Send Request", onClick: handleSend }),
      el("span", { className: "send-status", id: "sendStatus" })
    ]));

    // Response + Drift (hidden)
    var rs = el("div", { id: "responseSection", style: "display:none" });
    rs.appendChild(el("div", { className: "section", style: "margin-top:24px" }, [
      el("div", { className: "section-title", textContent: "Response" }),
      el("div", { className: "response-meta", id: "responseMeta" }),
      el("div", { className: "response-body", id: "responseBody" })
    ]));
    rs.appendChild(el("div", { className: "section" }, [
      el("div", { className: "section-title", textContent: "Spec Drift Analysis" }),
      el("div", { className: "drift-summary", id: "driftSummary" }),
      el("div", { id: "driftDetails" })
    ]));
    content.appendChild(rs);
    panel.appendChild(content);
  }

  // ─── Send ───
  async function handleSend() {
    var btn = document.getElementById("btnSend");
    var status = document.getElementById("sendStatus");
    btn.disabled = true;
    status.textContent = "Sending...";

    var baseUrl = (document.getElementById("serverSelect") || document.getElementById("serverInput")).value;
    var url = baseUrl + selectedEndpoint.path;
    var body = selectedEndpoint.requestBody ? window.FormBuilder.collectFormData() : undefined;

    try {
      var res = await fetch("/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url, method: selectedEndpoint.method, body: body })
      });
      lastResponse = await res.json();
      if (lastResponse.error) { status.textContent = "Error: " + lastResponse.error; btn.disabled = false; return; }
      status.textContent = "Done (" + lastResponse.status + ")";
      renderResponse();
      await validateDrift();
    } catch (err) {
      status.textContent = "Error: " + err.message;
    }
    btn.disabled = false;
  }

  // ─── Response ───
  function renderResponse() {
    document.getElementById("responseSection").style.display = "block";
    var meta = document.getElementById("responseMeta");
    clear(meta);
    var cls = lastResponse.status >= 500 ? "status-5xx" : lastResponse.status >= 400 ? "status-4xx" : "status-2xx";
    meta.appendChild(el("span", { className: "status-badge " + cls, textContent: lastResponse.status + " " + lastResponse.statusText }));
    document.getElementById("responseBody").textContent =
      typeof lastResponse.body === "object" ? JSON.stringify(lastResponse.body, null, 2) : String(lastResponse.body);
  }

  // ─── Drift ───
  async function validateDrift() {
    var schema = findResponseSchema(selectedEndpoint, lastResponse.status);
    var ds = document.getElementById("driftSummary");
    var dd = document.getElementById("driftDetails");

    if (!schema) {
      clear(ds); clear(dd);
      ds.appendChild(el("span", { className: "drift-count warn", textContent: "No schema for status " + lastResponse.status }));
      return;
    }
    try {
      var res = await fetch("/api/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ responseBody: lastResponse.body, schema: schema })
      });
      renderDrift(await res.json());
    } catch (err) {
      clear(ds);
      ds.appendChild(el("span", { className: "drift-count err", textContent: "Validation error: " + err.message }));
    }
  }

  function findResponseSchema(ep, status) {
    var r = ep.responses;
    if (r[String(status)] && r[String(status)].schema) return r[String(status)].schema;
    var range = String(status).charAt(0) + "XX";
    if (r[range] && r[range].schema) return r[range].schema;
    if (r["default"] && r["default"].schema) return r["default"].schema;
    return null;
  }

  function renderDrift(result) {
    var summary = document.getElementById("driftSummary");
    var details = document.getElementById("driftDetails");
    clear(summary); clear(details);

    if (result.count === 0) {
      summary.appendChild(el("span", { className: "drift-count ok", textContent: "No drift detected" }));
      return;
    }

    var counts = { missing: 0, type_mismatch: 0, undocumented: 0 };
    result.drifts.forEach(function (d) { counts[d.type]++; });

    if (counts.missing > 0) summary.appendChild(el("span", { className: "drift-count err", textContent: counts.missing + " missing" }));
    if (counts.type_mismatch > 0) summary.appendChild(el("span", { className: "drift-count warn", textContent: counts.type_mismatch + " type mismatch" }));
    if (counts.undocumented > 0) summary.appendChild(el("span", { className: "drift-count info", textContent: counts.undocumented + " undocumented" }));

    var table = el("table", { className: "drift-table" });
    var thead = el("thead");
    thead.appendChild(el("tr", {}, [el("th", { textContent: "Type" }), el("th", { textContent: "Path" }), el("th", { textContent: "Expected" }), el("th", { textContent: "Actual" })]));
    table.appendChild(thead);

    var tbody = el("tbody");
    result.drifts.forEach(function (d) {
      var lbl = d.type === "type_mismatch" ? "Type Mismatch" : d.type === "missing" ? "Missing" : "Undocumented";
      tbody.appendChild(el("tr", {}, [
        el("td", {}, [el("span", { className: "drift-type " + d.type, textContent: lbl })]),
        el("td", { textContent: d.path }),
        el("td", { textContent: d.expected || "\u2014" }),
        el("td", { textContent: d.actual || "\u2014" })
      ]));
    });
    table.appendChild(tbody);
    details.appendChild(table);
  }

  init();
})();
