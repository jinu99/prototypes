/** Local-First Data Guard — Main API */

export { detectDurability } from './detect';
export type { StorageReport, DurabilityLevel } from './detect';

export { DataGuardReplicator } from './replicate';
export type { Record, ReplicatorOptions, StorageStrategy } from './replicate';
