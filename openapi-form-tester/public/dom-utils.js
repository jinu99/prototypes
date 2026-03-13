/**
 * Shared DOM utilities for safe element creation (no innerHTML).
 * Exports via window.DOM namespace.
 */
window.DOM = (function () {
  "use strict";

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      for (var key in attrs) {
        if (key === "className") node.className = attrs[key];
        else if (key === "textContent") node.textContent = attrs[key];
        else if (key.startsWith("on")) node.addEventListener(key.slice(2).toLowerCase(), attrs[key]);
        else if (key === "dataset") {
          for (var dk in attrs[key]) node.dataset[dk] = attrs[key][dk];
        }
        else node.setAttribute(key, attrs[key]);
      }
    }
    if (children) {
      if (!Array.isArray(children)) children = [children];
      for (var i = 0; i < children.length; i++) {
        var child = children[i];
        if (typeof child === "string") node.appendChild(document.createTextNode(child));
        else if (child) node.appendChild(child);
      }
    }
    return node;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  return { el: el, clear: clear };
})();
