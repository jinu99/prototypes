/** Browser storage durability detection engine */

export type DurabilityLevel = 'safe' | 'warning' | 'danger';

export interface StorageReport {
  indexedDB: DurabilityLevel;
  opfs: DurabilityLevel;
  cacheAPI: DurabilityLevel;
  overall: DurabilityLevel;
  persisted: boolean | null;
  details: {
    persistSupported: boolean;
    persistGranted: boolean | null;
    opfsAvailable: boolean;
    isSafari: boolean;
    isITP: boolean;
    storageEstimate: { quota: number; usage: number } | null;
  };
}

function detectSafari(): boolean {
  const ua = navigator.userAgent;
  return /Safari/.test(ua) && !/Chrome/.test(ua) && !/Chromium/.test(ua);
}

function detectITP(isSafari: boolean): boolean {
  // Safari 12.1+ has ITP which can purge storage after 7 days of no interaction
  if (!isSafari) return false;
  const match = navigator.userAgent.match(/Version\/(\d+)/);
  if (!match) return true; // assume ITP if can't detect version
  return parseInt(match[1], 10) >= 12;
}

async function checkPersist(): Promise<{ supported: boolean; granted: boolean | null }> {
  if (!navigator.storage?.persist) {
    return { supported: false, granted: null };
  }
  try {
    // Check if already persisted first
    const already = await navigator.storage.persisted();
    if (already) return { supported: true, granted: true };
    // Request persistence
    const granted = await navigator.storage.persist();
    return { supported: true, granted };
  } catch {
    return { supported: true, granted: null };
  }
}

async function checkOPFS(): Promise<boolean> {
  try {
    if (!navigator.storage?.getDirectory) return false;
    await navigator.storage.getDirectory();
    return true;
  } catch {
    return false;
  }
}

async function getStorageEstimate(): Promise<{ quota: number; usage: number } | null> {
  try {
    if (!navigator.storage?.estimate) return null;
    const est = await navigator.storage.estimate();
    return { quota: est.quota ?? 0, usage: est.usage ?? 0 };
  } catch {
    return null;
  }
}

function scoreIndexedDB(persisted: boolean | null, isSafari: boolean, isITP: boolean): DurabilityLevel {
  if (persisted === true) return 'safe';
  if (isITP) return 'danger';
  if (isSafari) return 'warning';
  // Chrome without persist: eviction possible under storage pressure
  return persisted === false ? 'warning' : 'warning';
}

function scoreOPFS(available: boolean, persisted: boolean | null, isITP: boolean): DurabilityLevel {
  if (!available) return 'danger';
  if (persisted === true) return 'safe';
  if (isITP) return 'warning'; // OPFS is slightly more durable than IDB under ITP
  return 'safe';
}

function scoreCacheAPI(persisted: boolean | null, isITP: boolean): DurabilityLevel {
  if (persisted === true) return 'safe';
  if (isITP) return 'danger';
  return 'warning';
}

function overallScore(idb: DurabilityLevel, opfs: DurabilityLevel, cache: DurabilityLevel): DurabilityLevel {
  const scores = { safe: 2, warning: 1, danger: 0 };
  const avg = (scores[idb] + scores[opfs] + scores[cache]) / 3;
  if (avg >= 1.5) return 'safe';
  if (avg >= 0.8) return 'warning';
  return 'danger';
}

export async function detectDurability(): Promise<StorageReport> {
  const isSafari = detectSafari();
  const isITP = detectITP(isSafari);
  const { supported: persistSupported, granted: persistGranted } = await checkPersist();
  const opfsAvailable = await checkOPFS();
  const storageEstimate = await getStorageEstimate();

  const persisted = persistGranted;
  const idb = scoreIndexedDB(persisted, isSafari, isITP);
  const opfs = scoreOPFS(opfsAvailable, persisted, isITP);
  const cache = scoreCacheAPI(persisted, isITP);

  return {
    indexedDB: idb,
    opfs: opfs,
    cacheAPI: cache,
    overall: overallScore(idb, opfs, cache),
    persisted,
    details: {
      persistSupported,
      persistGranted,
      opfsAvailable,
      isSafari,
      isITP,
      storageEstimate,
    },
  };
}
