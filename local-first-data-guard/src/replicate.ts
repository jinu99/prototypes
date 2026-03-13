/** Cross-storage replication: IndexedDB <-> OPFS with auto-recovery */

const DB_NAME = 'data-guard-store';
const DB_VERSION = 1;
const STORE_NAME = 'records';
const OPFS_DIR = 'data-guard-backup';

export interface Record {
  key: string;
  value: string;
  updatedAt: number;
}

// ─── IndexedDB operations ───

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'key' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbPut(record: Record): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).put(record);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

async function idbGet(key: string): Promise<Record | undefined> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const req = tx.objectStore(STORE_NAME).get(key);
    req.onsuccess = () => { db.close(); resolve(req.result); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

async function idbGetAll(): Promise<Record[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const req = tx.objectStore(STORE_NAME).getAll();
    req.onsuccess = () => { db.close(); resolve(req.result); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

async function idbDelete(key: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).delete(key);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

async function idbClear(): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).clear();
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

// ─── OPFS operations ───

async function opfsDir(): Promise<FileSystemDirectoryHandle> {
  const root = await navigator.storage.getDirectory();
  return root.getDirectoryHandle(OPFS_DIR, { create: true });
}

async function opfsPut(record: Record): Promise<void> {
  const dir = await opfsDir();
  const fileHandle = await dir.getFileHandle(`${record.key}.json`, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(JSON.stringify(record));
  await writable.close();
}

async function opfsGet(key: string): Promise<Record | undefined> {
  try {
    const dir = await opfsDir();
    const fileHandle = await dir.getFileHandle(`${key}.json`);
    const file = await fileHandle.getFile();
    const text = await file.text();
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

async function opfsGetAll(): Promise<Record[]> {
  const records: Record[] = [];
  try {
    const dir = await opfsDir();
    for await (const [name, handle] of (dir as any).entries()) {
      if (name.endsWith('.json') && handle.kind === 'file') {
        const file = await (handle as FileSystemFileHandle).getFile();
        const text = await file.text();
        records.push(JSON.parse(text));
      }
    }
  } catch {
    // OPFS not available
  }
  return records;
}

async function opfsClear(): Promise<void> {
  try {
    const root = await navigator.storage.getDirectory();
    await root.removeEntry(OPFS_DIR, { recursive: true });
  } catch {
    // ignore if doesn't exist
  }
}

// ─── Public API ───

export type StorageStrategy = 'idb-primary' | 'opfs-primary';

export interface ReplicatorOptions {
  strategy?: StorageStrategy;
  onRecovery?: (key: string, source: 'opfs' | 'indexeddb') => void;
}

export class DataGuardReplicator {
  private strategy: StorageStrategy;
  private onRecovery?: (key: string, source: 'opfs' | 'indexeddb') => void;
  private opfsAvailable: boolean | null = null;

  constructor(opts: ReplicatorOptions = {}) {
    this.strategy = opts.strategy ?? 'idb-primary';
    this.onRecovery = opts.onRecovery;
  }

  private async checkOPFS(): Promise<boolean> {
    if (this.opfsAvailable !== null) return this.opfsAvailable;
    try {
      await navigator.storage.getDirectory();
      this.opfsAvailable = true;
    } catch {
      this.opfsAvailable = false;
    }
    return this.opfsAvailable;
  }

  /** Write data with automatic cross-storage replication */
  async put(key: string, value: string): Promise<void> {
    const record: Record = { key, value, updatedAt: Date.now() };
    // Write to primary
    await idbPut(record);
    // Replicate to backup
    if (await this.checkOPFS()) {
      await opfsPut(record);
    }
  }

  /** Read with automatic recovery if primary is missing */
  async get(key: string): Promise<string | undefined> {
    // Try primary first
    const idbRecord = await idbGet(key);
    if (idbRecord) return idbRecord.value;

    // Primary miss — try recovery from OPFS
    if (await this.checkOPFS()) {
      const opfsRecord = await opfsGet(key);
      if (opfsRecord) {
        // Recover to primary
        await idbPut(opfsRecord);
        this.onRecovery?.(key, 'opfs');
        return opfsRecord.value;
      }
    }
    return undefined;
  }

  /** Get all records (merged from both stores, primary wins) */
  async getAll(): Promise<Record[]> {
    const idbRecords = await idbGetAll();
    const map = new Map<string, Record>();
    for (const r of idbRecords) map.set(r.key, r);

    if (await this.checkOPFS()) {
      const opfsRecords = await opfsGetAll();
      for (const r of opfsRecords) {
        if (!map.has(r.key)) {
          map.set(r.key, r);
          // Auto-recover to primary
          await idbPut(r);
          this.onRecovery?.(r.key, 'opfs');
        }
      }
    }
    return Array.from(map.values());
  }

  /** Delete from all stores */
  async delete(key: string): Promise<void> {
    await idbDelete(key);
    // Note: we keep OPFS backup intentionally for recovery demo
  }

  /** Clear only IndexedDB (simulates storage loss) */
  async simulateStorageLoss(): Promise<void> {
    await idbClear();
  }

  /** Clear everything */
  async clearAll(): Promise<void> {
    await idbClear();
    await opfsClear();
  }

  /** Check recovery: see what can be recovered from backup */
  async checkRecoverable(): Promise<Record[]> {
    if (!(await this.checkOPFS())) return [];
    const idbRecords = await idbGetAll();
    const idbKeys = new Set(idbRecords.map(r => r.key));
    const opfsRecords = await opfsGetAll();
    return opfsRecords.filter(r => !idbKeys.has(r.key));
  }

  /** Recover all missing records from backup */
  async recoverAll(): Promise<Record[]> {
    const recoverable = await this.checkRecoverable();
    for (const r of recoverable) {
      await idbPut(r);
      this.onRecovery?.(r.key, 'opfs');
    }
    return recoverable;
  }
}
