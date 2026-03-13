const { broadcast } = require('./sse');
const QRCode = require('qrcode');

const VALID_STATUSES = ['waiting', 'called', 'seated', 'completed'];
const AVG_WAIT_PER_PARTY = 5; // minutes per group ahead

function setupRoutes(db) {
  const stmts = {
    insert: db.prepare('INSERT INTO queue (name, party_size) VALUES (?, ?)'),
    getById: db.prepare('SELECT * FROM queue WHERE id = ?'),
    getActive: db.prepare(
      "SELECT * FROM queue WHERE status != 'completed' ORDER BY created_at ASC"
    ),
    getAll: db.prepare('SELECT * FROM queue ORDER BY created_at DESC LIMIT 100'),
    countAhead: db.prepare(
      "SELECT COUNT(*) as cnt FROM queue WHERE status = 'waiting' AND id < ?"
    ),
  };

  // Build timestamp update statements per status
  const timestampStmts = {
    called: db.prepare("UPDATE queue SET called_at = datetime('now','localtime'), status = 'called' WHERE id = ?"),
    seated: db.prepare("UPDATE queue SET seated_at = datetime('now','localtime'), status = 'seated' WHERE id = ?"),
    completed: db.prepare("UPDATE queue SET completed_at = datetime('now','localtime'), status = 'completed' WHERE id = ?"),
    waiting: db.prepare("UPDATE queue SET status = 'waiting' WHERE id = ?"),
  };

  function getQueueState() {
    const rows = stmts.getActive.all();
    return rows.map((row, idx) => {
      const ahead = row.status === 'waiting'
        ? rows.filter(r => r.status === 'waiting' && r.id < row.id).length
        : 0;
      return {
        ...row,
        position: row.status === 'waiting' ? ahead + 1 : null,
        estimated_wait: row.status === 'waiting' ? ahead * AVG_WAIT_PER_PARTY : 0,
      };
    });
  }

  return {
    // POST /api/queue — register new customer
    addToQueue(body) {
      const { name, party_size } = body;
      if (!name || !name.trim()) return { error: '이름을 입력해주세요', status: 400 };
      const size = parseInt(party_size) || 1;
      if (size < 1 || size > 50) return { error: '인원수는 1~50 사이로 입력해주세요', status: 400 };

      const result = stmts.insert.run(name.trim(), size);
      const entry = stmts.getById.get(result.lastInsertRowid);
      const state = getQueueState();
      const mine = state.find(r => r.id === entry.id);
      broadcast('queue-update', state);
      return { data: mine || entry, status: 201 };
    },

    // GET /api/queue — list active queue
    listQueue() {
      return { data: getQueueState(), status: 200 };
    },

    // GET /api/queue/all — list all (including completed)
    listAll() {
      return { data: stmts.getAll.all(), status: 200 };
    },

    // PATCH /api/queue/:id/status — change status
    updateStatus(id, body) {
      const { status } = body;
      if (!VALID_STATUSES.includes(status)) {
        return { error: `유효하지 않은 상태: ${status}`, status: 400 };
      }
      const entry = stmts.getById.get(id);
      if (!entry) return { error: '대기자를 찾을 수 없습니다', status: 404 };

      timestampStmts[status].run(id);
      const updated = stmts.getById.get(id);
      broadcast('queue-update', getQueueState());
      return { data: updated, status: 200 };
    },

    // GET /api/queue/:id — single entry info
    getEntry(id) {
      const entry = stmts.getById.get(id);
      if (!entry) return { error: '대기자를 찾을 수 없습니다', status: 404 };
      const state = getQueueState();
      const mine = state.find(r => r.id === entry.id);
      return { data: mine || entry, status: 200 };
    },

    // GET /api/qrcode?url=... — generate QR code as data URL
    async generateQR(url) {
      try {
        const dataUrl = await QRCode.toDataURL(url, { width: 300, margin: 2 });
        return { data: { qr: dataUrl, url }, status: 200 };
      } catch (err) {
        return { error: 'QR 코드 생성 실패', status: 500 };
      }
    },
  };
}

module.exports = { setupRoutes };
