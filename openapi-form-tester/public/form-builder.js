/**
 * Schema-driven form builder.
 * Generates DOM form fields from OpenAPI JSON Schema definitions.
 * Exports via window.FormBuilder namespace.
 */
window.FormBuilder = (function () {
  "use strict";
  var el = window.DOM.el;

  function buildSchemaForm(container, schema, prefix, requiredFields) {
    if (!schema) return;
    var props = schema.properties || {};
    var req = schema.required || requiredFields || [];

    for (var key in props) {
      var prop = props[key];
      var fieldName = prefix ? prefix + "." + key : key;
      var isReq = req.indexOf(key) >= 0;
      container.appendChild(buildField(key, fieldName, prop, isReq));
    }
  }

  function buildField(label, fieldName, schema, isRequired) {
    var field = el("div", { className: "form-field" });
    var reqSpan = isRequired ? el("span", { className: "required", textContent: " *" }) : null;
    var typeSpan = el("span", { className: "type-hint", textContent: " " + (schema.type || "any") });

    if (schema.type === "boolean") {
      var checkbox = el("input", { type: "checkbox", dataset: { field: fieldName, type: "boolean" } });
      var lbl = el("label", { className: "checkbox-label" }, [checkbox, label]);
      if (reqSpan) lbl.appendChild(reqSpan);
      lbl.appendChild(typeSpan);
      field.appendChild(lbl);
    } else if (schema.enum) {
      field.appendChild(makeLabel(label, reqSpan, typeSpan));
      var select = el("select", { dataset: { field: fieldName, type: schema.type || "string" } }, [
        el("option", { value: "", textContent: "-- select --" })
      ]);
      for (var i = 0; i < schema.enum.length; i++) {
        select.appendChild(el("option", { value: schema.enum[i], textContent: schema.enum[i] }));
      }
      field.appendChild(select);
    } else if (schema.type === "object" || schema.properties) {
      field.appendChild(makeLabel(label, reqSpan, typeSpan));
      var objGroup = el("div", { className: "object-group" });
      buildSchemaForm(objGroup, schema, fieldName, schema.required || []);
      field.appendChild(objGroup);
    } else if (schema.type === "array") {
      field.appendChild(makeLabel(label, reqSpan, typeSpan));
      var itemType = (schema.items && schema.items.type) || "string";
      var arrayGroup = el("div", { className: "array-group", dataset: { field: fieldName, itemType: itemType } });
      var arrayItems = el("div", { className: "array-items" });
      arrayGroup.appendChild(arrayItems);
      arrayGroup.appendChild(el("button", {
        type: "button", className: "btn-icon", title: "Add item", textContent: "+",
        onClick: function () { addArrayItem(arrayGroup); }
      }));
      field.appendChild(arrayGroup);
    } else if (schema.type === "integer" || schema.type === "number") {
      field.appendChild(makeLabel(label, reqSpan, typeSpan));
      field.appendChild(el("input", {
        type: "number", placeholder: label,
        step: schema.type === "integer" ? "1" : "any",
        dataset: { field: fieldName, type: schema.type }
      }));
    } else {
      field.appendChild(makeLabel(label, reqSpan, typeSpan));
      field.appendChild(el("input", {
        type: "text", placeholder: label,
        dataset: { field: fieldName, type: "string" }
      }));
    }
    return field;
  }

  function makeLabel(text, reqSpan, typeSpan) {
    var lbl = el("label", {}, [text]);
    if (reqSpan) lbl.appendChild(reqSpan);
    lbl.appendChild(typeSpan);
    return lbl;
  }

  function addArrayItem(arrayGroup) {
    var itemsContainer = arrayGroup.querySelector(".array-items");
    var fieldName = arrayGroup.dataset.field;
    var itemType = arrayGroup.dataset.itemType;
    var idx = itemsContainer.children.length;

    var item = el("div", { className: "array-item" });
    item.appendChild(el("input", {
      type: "text", placeholder: "Item " + idx,
      dataset: { field: fieldName + "[" + idx + "]", type: itemType }
    }));
    item.appendChild(el("button", {
      type: "button", className: "btn-icon danger", title: "Remove",
      textContent: "\u00D7",
      onClick: function () { item.remove(); }
    }));
    itemsContainer.appendChild(item);
  }

  function collectFormData() {
    var data = {};
    document.querySelectorAll("[data-field]").forEach(function (node) {
      if (node.classList.contains("array-group")) return;
      var field = node.dataset.field;
      var type = node.dataset.type;
      var val;

      if (type === "boolean") val = node.checked;
      else if (type === "integer") val = node.value === "" ? undefined : parseInt(node.value, 10);
      else if (type === "number") val = node.value === "" ? undefined : parseFloat(node.value);
      else val = node.value === "" ? undefined : node.value;

      if (val === undefined) return;
      setNestedValue(data, field, val);
    });
    return data;
  }

  function setNestedValue(obj, path, value) {
    var parts = path.replace(/\[(\d+)\]/g, ".$1").split(".");
    var current = obj;
    for (var i = 0; i < parts.length - 1; i++) {
      var part = parts[i];
      var nextPart = parts[i + 1];
      if (!(part in current)) current[part] = /^\d+$/.test(nextPart) ? [] : {};
      current = current[part];
    }
    var lastPart = parts[parts.length - 1];
    if (/^\d+$/.test(lastPart)) current[parseInt(lastPart, 10)] = value;
    else current[lastPart] = value;
  }

  return { buildSchemaForm: buildSchemaForm, collectFormData: collectFormData };
})();
