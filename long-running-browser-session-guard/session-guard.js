/**
 * Session Guard — Long-Running Browser Session OOM Protection
 * Drop-in JS library: monitors memory, predicts OOM, auto-recovers.
 * Target: <5KB gzipped
 */
(function (root) {
  'use strict';

  var DEFAULTS = {
    pollInterval: 5000,
    historySize: 60,
    heapThreshold: 0.85,
    domThreshold: 50000,
    autoRecover: true,
    stateKey: '__sg_state',
    metaKey: '__sg_meta',
    showOverlay: true,
    onWarning: null,
    onRecover: null,
    stateSelector: null
  };

  function SessionGuard(opts) {
    this.cfg = assign({}, DEFAULTS, opts || {});
    this.samples = [];
    this.events = [];
    this.startTime = Date.now();
    this.recovered = false;
    this._timers = [];
    this._overlay = null;
    this._wsPatched = false;
    this._esPatched = false;
    this.init();
  }

  var P = SessionGuard.prototype;

  P.init = function () {
    this._tryRestore();
    this._startPolling();
    if (this.cfg.showOverlay) this._createOverlay();
    this._patchWebSocket();
    this._patchEventSource();
  };

  P.collect = function () {
    var mem = performance.memory || {};
    var nodes = document.querySelectorAll('*').length;
    var sample = {
      t: Date.now(),
      heapUsed: mem.usedJSHeapSize || 0,
      heapTotal: mem.totalJSHeapSize || 0,
      heapLimit: mem.jsHeapSizeLimit || 0,
      domNodes: nodes
    };
    this.samples.push(sample);
    if (this.samples.length > this.cfg.historySize) this.samples.shift();
    return sample;
  };

  P.predictOOM = function () {
    var s = this.samples;
    if (s.length < 5) return null;
    var n = s.length;
    var sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
    var t0 = s[0].t;
    for (var i = 0; i < n; i++) {
      var x = (s[i].t - t0) / 1000;
      var y = s[i].heapUsed;
      sumX += x; sumY += y; sumXY += x * y; sumX2 += x * x;
    }
    var denom = n * sumX2 - sumX * sumX;
    if (denom === 0) return null;
    var slope = (n * sumXY - sumX * sumY) / denom;
    var intercept = (sumY - slope * sumX) / n;
    if (slope <= 0) return { slope: slope, oomIn: Infinity, growing: false };
    var limit = s[n - 1].heapLimit || (s[n - 1].heapTotal * 2);
    var currentX = (s[n - 1].t - t0) / 1000;
    var timeToLimit = (limit - (slope * currentX + intercept)) / slope;
    return { slope: slope, oomIn: Math.max(0, timeToLimit), growing: slope > 100 };
  };

  P.assess = function (sample) {
    var level = 'ok';
    var reasons = [];
    var pred = this.predictOOM();
    if (sample.heapLimit > 0) {
      var ratio = sample.heapUsed / sample.heapLimit;
      if (ratio > this.cfg.heapThreshold) {
        level = 'critical';
        reasons.push('Heap at ' + (ratio * 100).toFixed(1) + '%');
      } else if (ratio > this.cfg.heapThreshold * 0.8) {
        level = 'warn';
        reasons.push('Heap at ' + (ratio * 100).toFixed(1) + '%');
      }
    }
    if (sample.domNodes > this.cfg.domThreshold) {
      level = level === 'ok' ? 'warn' : level;
      reasons.push(sample.domNodes + ' DOM nodes');
    }
    if (pred && pred.growing && pred.oomIn < 300) {
      level = 'critical';
      reasons.push('OOM predicted in ' + formatTime(pred.oomIn));
    } else if (pred && pred.growing && pred.oomIn < 600) {
      level = level === 'ok' ? 'warn' : level;
      reasons.push('OOM predicted in ' + formatTime(pred.oomIn));
    }
    return { level: level, reasons: reasons, prediction: pred, sample: sample };
  };

  P._startPolling = function () {
    var self = this;
    var tid = setInterval(function () {
      var sample = self.collect();
      var result = self.assess(sample);
      if (result.level !== 'ok') {
        self._logEvent(result.level, result.reasons.join('; '));
        if (self.cfg.onWarning) self.cfg.onWarning(result.level, result);
      }
      if (result.level === 'critical' && self.cfg.autoRecover) self._recover(result);
      if (self._overlay) self._updateOverlay(result);
    }, this.cfg.pollInterval);
    this._timers.push(tid);
    var s = this.collect();
    var r = this.assess(s);
    if (this._overlay) this._updateOverlay(r);
  };

  P._recover = function (result) {
    this._logEvent('recover', 'Initiating auto-recovery');
    var state = null;
    if (this.cfg.stateSelector) {
      try { state = this.cfg.stateSelector(); } catch (e) { /* ignore */ }
    }
    var snapshot = {
      state: state,
      url: location.href,
      scroll: { x: window.scrollX, y: window.scrollY },
      time: Date.now(),
      reason: result.reasons.join('; ')
    };
    try {
      sessionStorage.setItem(this.cfg.stateKey, JSON.stringify(snapshot));
      sessionStorage.setItem(this.cfg.metaKey, JSON.stringify({
        recoveryCount: this._getRecoveryCount() + 1,
        lastRecovery: Date.now()
      }));
    } catch (e) { /* storage full */ }
    if (this.cfg.onRecover) this.cfg.onRecover(snapshot);
    setTimeout(function () { location.reload(); }, 100);
  };

  P._tryRestore = function () {
    var raw = sessionStorage.getItem(this.cfg.stateKey);
    if (!raw) return;
    try {
      var snapshot = JSON.parse(raw);
      sessionStorage.removeItem(this.cfg.stateKey);
      this.recovered = true;
      this.lastSnapshot = snapshot;
      if (snapshot.scroll) {
        setTimeout(function () { window.scrollTo(snapshot.scroll.x, snapshot.scroll.y); }, 100);
      }
      this._logEvent('restored', 'Session restored from snapshot');
      console.log('[SessionGuard] Restored session state', snapshot.state);
      if (this.cfg.onRecover) this.cfg.onRecover(snapshot);
    } catch (e) {
      sessionStorage.removeItem(this.cfg.stateKey);
    }
  };

  P._getRecoveryCount = function () {
    try {
      var m = JSON.parse(sessionStorage.getItem(this.cfg.metaKey) || '{}');
      return m.recoveryCount || 0;
    } catch (e) { return 0; }
  };

  P._patchWebSocket = function () {
    if (this._wsPatched || typeof WebSocket === 'undefined') return;
    this._wsPatched = true;
    var OrigWS = root.WebSocket;
    var self = this;
    function GuardedWS(url, protocols) {
      var ws = protocols ? new OrigWS(url, protocols) : new OrigWS(url);
      var attempt = 0;
      ws.addEventListener('close', function reconnect(e) {
        if (e.code === 1000) return;
        attempt++;
        var delay = Math.min(1000 * Math.pow(2, attempt), 30000);
        self._logEvent('ws-reconnect', 'Attempt ' + attempt + ' in ' + delay + 'ms');
        setTimeout(function () {
          var nws = protocols ? new OrigWS(url, protocols) : new OrigWS(url);
          nws.addEventListener('close', reconnect);
          if (ws.onmessage) nws.onmessage = ws.onmessage;
          if (ws.onerror) nws.onerror = ws.onerror;
          if (ws.onopen) nws.onopen = function (ev) { attempt = 0; ws.onopen(ev); };
        }, delay);
      });
      return ws;
    }
    GuardedWS.CONNECTING = OrigWS.CONNECTING;
    GuardedWS.OPEN = OrigWS.OPEN;
    GuardedWS.CLOSING = OrigWS.CLOSING;
    GuardedWS.CLOSED = OrigWS.CLOSED;
    root.WebSocket = GuardedWS;
  };

  P._patchEventSource = function () {
    if (this._esPatched || typeof EventSource === 'undefined') return;
    this._esPatched = true;
    var OrigES = root.EventSource;
    var self = this;
    function GuardedES(url, opts) {
      var es = new OrigES(url, opts);
      var attempt = 0;
      es.addEventListener('error', function () {
        if (es.readyState === EventSource.CLOSED) {
          attempt++;
          var delay = Math.min(1000 * Math.pow(2, attempt), 30000);
          self._logEvent('es-reconnect', 'Attempt ' + attempt + ' in ' + delay + 'ms');
          setTimeout(function () {
            var nes = new OrigES(url, opts);
            if (es.onmessage) nes.onmessage = es.onmessage;
            if (es.onerror) nes.onerror = es.onerror;
            if (es.onopen) nes.onopen = es.onopen;
          }, delay);
        }
      });
      return es;
    }
    root.EventSource = GuardedES;
  };

  P._createOverlay = function () {
    var el = document.createElement('div');
    el.id = 'sg-overlay';

    var header = document.createElement('div');
    header.id = 'sg-header';
    var statusSpan = document.createElement('span');
    statusSpan.id = 'sg-status';
    statusSpan.textContent = '●';
    header.appendChild(statusSpan);
    header.appendChild(document.createTextNode(' Session Guard'));
    var toggleBtn = document.createElement('button');
    toggleBtn.id = 'sg-toggle';
    toggleBtn.textContent = '_';
    header.appendChild(toggleBtn);

    var body = document.createElement('div');
    body.id = 'sg-body';
    var ids = ['sg-uptime', 'sg-heap', 'sg-dom', 'sg-prediction', 'sg-recoveries'];
    var labels = ['Uptime: 0s', 'Heap: —', 'DOM: —', 'OOM: —', 'Recoveries: 0'];
    for (var i = 0; i < ids.length; i++) {
      var d = document.createElement('div');
      d.id = ids[i];
      d.textContent = labels[i];
      body.appendChild(d);
    }
    var canvas = document.createElement('canvas');
    canvas.id = 'sg-chart';
    canvas.width = 200;
    canvas.height = 60;
    body.appendChild(canvas);
    var evDiv = document.createElement('div');
    evDiv.id = 'sg-events';
    body.appendChild(evDiv);

    el.appendChild(header);
    el.appendChild(body);

    var style = document.createElement('style');
    style.textContent = '#sg-overlay{position:fixed;bottom:12px;right:12px;width:240px;' +
      'font:12px/1.4 monospace;background:#1a1a2e;color:#e0e0e0;border:1px solid #333;' +
      'border-radius:8px;z-index:999999;box-shadow:0 4px 20px rgba(0,0,0,.4);overflow:hidden}' +
      '#sg-header{display:flex;align-items:center;justify-content:space-between;' +
      'padding:6px 10px;background:#16213e;cursor:pointer;user-select:none}' +
      '#sg-toggle{background:none;border:none;color:#888;cursor:pointer;font:12px monospace;padding:0 4px}' +
      '#sg-body{padding:8px 10px}#sg-body.collapsed{display:none}' +
      '#sg-status{margin-right:6px}' +
      '#sg-chart{width:100%;height:60px;margin:6px 0;border:1px solid #333;border-radius:4px}' +
      '#sg-events{max-height:60px;overflow-y:auto;font-size:10px;color:#888;margin-top:4px}' +
      '.sg-ok{color:#4ecca3}.sg-warn{color:#f0a500}.sg-critical{color:#e74c3c}';

    document.head.appendChild(style);
    document.body.appendChild(el);
    this._overlay = el;

    toggleBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      body.classList.toggle('collapsed');
      toggleBtn.textContent = body.classList.contains('collapsed') ? '□' : '_';
    });
  };

  P._updateOverlay = function (result) {
    if (!this._overlay) return;
    var s = result.sample;
    var pred = result.prediction;
    var uptime = (Date.now() - this.startTime) / 1000;
    var statusEl = this._overlay.querySelector('#sg-status');
    statusEl.className = 'sg-' + result.level;
    setText('#sg-uptime', 'Uptime: ' + formatTime(uptime));
    setText('#sg-heap', 'Heap: ' + formatBytes(s.heapUsed) + ' / ' + formatBytes(s.heapLimit));
    setText('#sg-dom', 'DOM: ' + s.domNodes + ' nodes');
    setText('#sg-prediction', pred && pred.growing
      ? 'OOM in: ' + formatTime(pred.oomIn) + ' (' + formatBytes(pred.slope) + '/s)'
      : 'OOM: stable');
    setText('#sg-recoveries', 'Recoveries: ' + this._getRecoveryCount());
    this._drawChart();
    this._renderEvents();
  };

  P._drawChart = function () {
    var canvas = this._overlay.querySelector('#sg-chart');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var w = canvas.width, h = canvas.height;
    var s = this.samples;
    if (s.length < 2) return;
    ctx.clearRect(0, 0, w, h);
    var maxHeap = 0;
    for (var i = 0; i < s.length; i++) {
      if (s[i].heapUsed > maxHeap) maxHeap = s[i].heapUsed;
    }
    if (s[0].heapLimit > 0 && s[0].heapLimit > maxHeap) maxHeap = s[0].heapLimit;
    if (maxHeap === 0) maxHeap = 1;
    ctx.beginPath();
    ctx.strokeStyle = '#4ecca3';
    ctx.lineWidth = 1.5;
    for (var j = 0; j < s.length; j++) {
      var x = (j / (s.length - 1)) * w;
      var y = h - (s[j].heapUsed / maxHeap) * h * 0.9;
      if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
    if (s[0].heapLimit > 0) {
      ctx.beginPath();
      ctx.strokeStyle = '#e74c3c44';
      ctx.setLineDash([4, 4]);
      var limitY = h - (s[0].heapLimit / maxHeap) * h * 0.9;
      ctx.moveTo(0, limitY);
      ctx.lineTo(w, limitY);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  };

  P._renderEvents = function () {
    var el = this._overlay.querySelector('#sg-events');
    if (!el) return;
    while (el.firstChild) el.removeChild(el.firstChild);
    var recent = this.events.slice(-5);
    for (var i = recent.length - 1; i >= 0; i--) {
      var ev = recent[i];
      var div = document.createElement('div');
      div.className = 'sg-' + ev.level;
      div.textContent = new Date(ev.t).toLocaleTimeString() + ' ' + ev.msg;
      el.appendChild(div);
    }
  };

  P._logEvent = function (level, msg) {
    this.events.push({ t: Date.now(), level: level, msg: msg });
    if (this.events.length > 50) this.events.shift();
    console.log('[SessionGuard][' + level + '] ' + msg);
  };

  P.destroy = function () {
    for (var i = 0; i < this._timers.length; i++) clearInterval(this._timers[i]);
    if (this._overlay && this._overlay.parentNode) this._overlay.parentNode.removeChild(this._overlay);
  };

  function assign(target) {
    for (var i = 1; i < arguments.length; i++) {
      var src = arguments[i];
      if (src) for (var k in src) if (src.hasOwnProperty(k)) target[k] = src[k];
    }
    return target;
  }

  function formatBytes(b) {
    if (b === 0 || !b) return '0 B';
    if (b === Infinity) return '∞';
    var u = ['B', 'KB', 'MB', 'GB'];
    var i = Math.floor(Math.log(Math.abs(b)) / Math.log(1024));
    i = Math.min(i, u.length - 1);
    return (b / Math.pow(1024, i)).toFixed(1) + ' ' + u[i];
  }

  function formatTime(sec) {
    if (!isFinite(sec)) return '∞';
    if (sec < 60) return Math.round(sec) + 's';
    if (sec < 3600) return Math.round(sec / 60) + 'm';
    return (sec / 3600).toFixed(1) + 'h';
  }

  function setText(sel, text) {
    var el = document.querySelector(sel);
    if (el) el.textContent = text;
  }

  root.SessionGuard = SessionGuard;
})(typeof window !== 'undefined' ? window : this);
