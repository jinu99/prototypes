/**
 * Core logic test: verifies detectDurability and DataGuardReplicator
 * in a simulated browser environment using fake-indexeddb.
 */
import 'fake-indexeddb/auto';

// Mock navigator.storage for Node.js environment
const opfsFiles = new Map();

const mockStorage = {
  persist: async () => false, // simulate denied
  persisted: async () => false,
  estimate: async () => ({ quota: 1e9, usage: 5e6 }),
  getDirectory: async () => {
    const dirHandle = {
      getFileHandle: async (name, opts) => {
        if (!opfsFiles.has(name) && !(opts && opts.create)) {
          throw new Error('Not found');
        }
        return {
          getFile: async () => ({
            text: async () => opfsFiles.get(name) || ''
          }),
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
          yield [name, {
            kind: 'file',
            getFile: async () => ({
              text: async () => opfsFiles.get(name) || ''
            })
          }];
        }
      },
      removeEntry: async () => { opfsFiles.clear(); }
    };
    return {
      getDirectoryHandle: async () => dirHandle,
      removeEntry: async () => { opfsFiles.clear(); }
    };
  }
};

if (!globalThis.navigator) {
  globalThis.navigator = { userAgent: 'Mozilla/5.0 Chrome/120.0.0.0', storage: mockStorage };
} else {
  globalThis.navigator.storage = mockStorage;
}

// Dynamic import after polyfills are set up
const { detectDurability, DataGuardReplicator } = await import('./dist/data-guard.js');

let passed = 0;
let failed = 0;

function assert(condition, msg) {
  if (condition) {
    console.log('  PASS: ' + msg);
    passed++;
  } else {
    console.log('  FAIL: ' + msg);
    failed++;
  }
}

// ─── Test 1: detectDurability ───
console.log('\n=== Test 1: detectDurability() ===');
const report = await detectDurability();
assert(report.overall !== undefined, 'overall score exists');
assert(['safe', 'warning', 'danger'].includes(report.overall), 'overall is valid level: ' + report.overall);
assert(['safe', 'warning', 'danger'].includes(report.indexedDB), 'indexedDB score: ' + report.indexedDB);
assert(['safe', 'warning', 'danger'].includes(report.opfs), 'opfs score: ' + report.opfs);
assert(['safe', 'warning', 'danger'].includes(report.cacheAPI), 'cacheAPI score: ' + report.cacheAPI);
assert(report.persisted === false, 'persist denied (simulated)');
assert(report.details.persistSupported === true, 'persist supported');
assert(report.details.persistGranted === false, 'persist not granted');
assert(report.details.opfsAvailable === true, 'OPFS available');
assert(report.details.isSafari === false, 'not Safari (Chrome UA)');
assert(report.details.storageEstimate !== null, 'storage estimate available');

// ─── Test 2: persist() denied → strategy branching ───
console.log('\n=== Test 2: persist() denied strategy ===');
assert(report.persisted === false, 'persist denied triggers replication strategy');
assert(report.indexedDB === 'warning', 'IndexedDB gets warning when persist denied');

// ─── Test 3: Cross-storage replication ───
console.log('\n=== Test 3: Cross-storage replication ===');
const recoveries = [];
const replicator = new DataGuardReplicator({
  onRecovery: (key, source) => recoveries.push({ key, source })
});

// Write data
await replicator.put('test-key', 'test-value');
await replicator.put('user-data', '{"name":"Alice"}');
await replicator.put('settings', '{"theme":"dark"}');

// Verify data is readable
const val = await replicator.get('test-key');
assert(val === 'test-value', 'can read written data');

const all = await replicator.getAll();
assert(all.length === 3, 'all 3 records stored');

// ─── Test 4: Simulate storage loss and recovery ───
console.log('\n=== Test 4: Storage loss + auto-recovery ===');
await replicator.simulateStorageLoss();

// Check what's recoverable
const recoverable = await replicator.checkRecoverable();
assert(recoverable.length === 3, '3 records recoverable from OPFS');

// Auto-recover
const recovered = await replicator.recoverAll();
assert(recovered.length === 3, '3 records recovered');
assert(recoveries.length >= 3, 'onRecovery called for each record');

// Verify recovered data
const recoveredVal = await replicator.get('test-key');
assert(recoveredVal === 'test-value', 'recovered data matches original');

const recoveredUser = await replicator.get('user-data');
assert(recoveredUser === '{"name":"Alice"}', 'recovered user data matches');

// ─── Test 5: Auto-recovery on get() ───
console.log('\n=== Test 5: Auto-recovery on get() ===');
opfsFiles.clear();
await replicator.clearAll();

// Write new data
await replicator.put('auto-test', 'auto-value');
// Delete only IndexedDB
await replicator.simulateStorageLoss();
// get() should auto-recover from OPFS
const autoRecovered = await replicator.get('auto-test');
assert(autoRecovered === 'auto-value', 'auto-recovery on get() works');

// ─── Summary ───
console.log('\n' + '='.repeat(40));
console.log('Results: ' + passed + ' passed, ' + failed + ' failed');
console.log('='.repeat(40));

if (failed > 0) process.exit(1);
