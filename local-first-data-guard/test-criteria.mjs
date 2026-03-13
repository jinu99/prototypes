/**
 * Phase 4: Verify all spec completion criteria
 */
import 'fake-indexeddb/auto';

// ─── Mock OPFS ───
const opfsFiles = new Map();
const dirHandle = {
  getFileHandle: async (name, opts) => {
    if (!opfsFiles.has(name) && !(opts && opts.create)) throw new Error('Not found');
    return {
      getFile: async () => ({ text: async () => opfsFiles.get(name) || '' }),
      createWritable: async () => {
        let data = '';
        return {
          write: async (content) => { data = content; },
          close: async () => { opfsFiles.set(name, data); }
        };
      }
    };
  },
  entries: async function* () {
    for (const [name] of opfsFiles) {
      yield [name, { kind: 'file', getFile: async () => ({ text: async () => opfsFiles.get(name) || '' }) }];
    }
  },
  removeEntry: async () => { opfsFiles.clear(); }
};

Object.defineProperty(globalThis, 'navigator', {
  value: {
    userAgent: 'Mozilla/5.0 Chrome/120.0.0.0',
    storage: {
      persist: async () => false,
      persisted: async () => false,
      estimate: async () => ({ quota: 1e9, usage: 5e6 }),
      getDirectory: async () => ({
        getDirectoryHandle: async () => dirHandle,
        removeEntry: async () => { opfsFiles.clear(); }
      })
    }
  },
  writable: true,
  configurable: true
});

const { detectDurability, DataGuardReplicator } = await import('./dist/data-guard.js');

console.log('╔══════════════════════════════════════════════╗');
console.log('║  Phase 4: Spec Completion Criteria Check     ║');
console.log('╚══════════════════════════════════════════════╝\n');

let allPass = true;

// ─── Criterion 1: detectDurability() returns safe/warning/danger ───
console.log('[ Criterion 1 ] detectDurability() returns storage durability scores');
const report = await detectDurability();
const validLevels = ['safe', 'warning', 'danger'];
const c1 = validLevels.includes(report.indexedDB)
  && validLevels.includes(report.opfs)
  && validLevels.includes(report.cacheAPI)
  && validLevels.includes(report.overall);
console.log('  IndexedDB: ' + report.indexedDB + ', OPFS: ' + report.opfs + ', Cache: ' + report.cacheAPI + ', Overall: ' + report.overall);
console.log('  Result: ' + (c1 ? 'PASS' : 'FAIL'));
if (!c1) allPass = false;

// ─── Criterion 2: IndexedDB <-> OPFS cross-storage replication, delete + recovery ───
console.log('\n[ Criterion 2 ] Cross-storage replication: delete primary -> recover from backup');
const replicator = new DataGuardReplicator();
await replicator.put('doc-1', '{"title":"Important"}');
await replicator.put('doc-2', '{"title":"Critical"}');

// Verify both stored
const before = await replicator.getAll();
const c2a = before.length === 2;
console.log('  Records before loss: ' + before.length + ' — ' + (c2a ? 'OK' : 'FAIL'));

// Simulate loss
await replicator.simulateStorageLoss();

// Recover
const recovered = await replicator.recoverAll();
const c2b = recovered.length === 2;
console.log('  Records recovered: ' + recovered.length + ' — ' + (c2b ? 'OK' : 'FAIL'));

// Verify content
const doc1 = await replicator.get('doc-1');
const c2c = doc1 === '{"title":"Important"}';
console.log('  Content integrity: ' + (c2c ? 'PASS' : 'FAIL'));
const c2 = c2a && c2b && c2c;
console.log('  Result: ' + (c2 ? 'PASS' : 'FAIL'));
if (!c2) allPass = false;

// ─── Criterion 3: persist() result branching ───
console.log('\n[ Criterion 3 ] navigator.storage.persist() strategy branching');
// Test with persist denied (current mock)
const c3a = report.details.persistGranted === false;
console.log('  persist() denied scenario: indexedDB=' + report.indexedDB + ' — ' + (c3a ? 'OK' : 'FAIL'));

// Simulate persist granted
globalThis.navigator.storage.persist = async () => true;
globalThis.navigator.storage.persisted = async () => true;
const reportGranted = await detectDurability();
const c3b = reportGranted.details.persistGranted === true;
const c3c = reportGranted.indexedDB === 'safe'; // persist granted → safe
console.log('  persist() granted scenario: indexedDB=' + reportGranted.indexedDB + ' — ' + (c3b && c3c ? 'OK' : 'FAIL'));
const c3 = c3a && c3b && c3c;
console.log('  Result: ' + (c3 ? 'PASS' : 'FAIL'));
if (!c3) allPass = false;

// ─── Criterion 4: HTML demo page with Chrome/Safari comparison ───
console.log('\n[ Criterion 4 ] HTML demo page with browser comparison');
const fs = await import('fs');
const html = fs.readFileSync('./index.html', 'utf8');
const hasComparison = html.includes('browser-grid') && html.includes('safari-bars') && html.includes('current-bars');
const hasDashboard = html.includes('score-overall') && html.includes('score-idb') && html.includes('score-opfs');
const hasDemo = html.includes('btn-save') && html.includes('btn-delete') && html.includes('btn-recover');
const hasPersistSection = html.includes('strategy-info') && html.includes('persist');
const c4 = hasComparison && hasDashboard && hasDemo && hasPersistSection;
console.log('  Browser comparison section: ' + (hasComparison ? 'OK' : 'MISSING'));
console.log('  Durability dashboard: ' + (hasDashboard ? 'OK' : 'MISSING'));
console.log('  Replication demo controls: ' + (hasDemo ? 'OK' : 'MISSING'));
console.log('  Persist strategy section: ' + (hasPersistSection ? 'OK' : 'MISSING'));
console.log('  Result: ' + (c4 ? 'PASS' : 'FAIL'));
if (!c4) allPass = false;

// ─── Summary ───
console.log('\n╔══════════════════════════════════════════════╗');
console.log('║  Status: ' + (allPass ? 'SUCCESS — All criteria passed' : 'PARTIAL — Some criteria failed') + '     ║');
console.log('╚══════════════════════════════════════════════╝');

if (!allPass) process.exit(1);
