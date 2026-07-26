import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import type { Dataset, EngineEvent, EquitySample, Order, Position, Run, Strategy } from "../engine/model";

export interface StoredRun {
  run: Run;
  orders: Order[];
  positions: Position[];
  events: EngineEvent[];
  equitySamples: EquitySample[];
}

interface QyeSchema extends DBSchema {
  strategies: { key: string; value: Strategy & { id: string }; indexes: { updatedAt: string } };
  datasets: { key: string; value: Dataset };
  runs: { key: string; value: StoredRun; indexes: { startedAt: string } };
  preferences: { key: string; value: unknown };
}

const DB_NAME = "quantum-yolo-engine";
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<QyeSchema>> | null = null;

export function getDb(): Promise<IDBPDatabase<QyeSchema>> {
  if (!dbPromise) {
    dbPromise = openDB<QyeSchema>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        const strategies = db.createObjectStore("strategies", { keyPath: "id" });
        strategies.createIndex("updatedAt", "updatedAt");

        db.createObjectStore("datasets", { keyPath: "datasetId" });

        const runs = db.createObjectStore("runs", { keyPath: "run.runId" });
        runs.createIndex("startedAt", "run.startedAt");

        db.createObjectStore("preferences");
      },
    });
  }
  return dbPromise;
}

export async function saveStrategy(id: string, strategy: Strategy): Promise<void> {
  const db = await getDb();
  await db.put("strategies", { ...strategy, id });
}

export async function listStrategies(): Promise<(Strategy & { id: string })[]> {
  const db = await getDb();
  return db.getAllFromIndex("strategies", "updatedAt");
}

export async function deleteStrategy(id: string): Promise<void> {
  const db = await getDb();
  await db.delete("strategies", id);
}

export async function saveDataset(dataset: Dataset): Promise<void> {
  const db = await getDb();
  await db.put("datasets", dataset);
}

export async function listDatasets(): Promise<Dataset[]> {
  const db = await getDb();
  return db.getAll("datasets");
}

export async function saveRun(stored: StoredRun): Promise<void> {
  const db = await getDb();
  await db.put("runs", stored);
}

export async function getRun(runId: string): Promise<StoredRun | undefined> {
  const db = await getDb();
  return db.get("runs", runId);
}

export async function listRuns(): Promise<StoredRun[]> {
  const db = await getDb();
  const all = await db.getAllFromIndex("runs", "startedAt");
  return all.reverse();
}

export async function deleteRun(runId: string): Promise<void> {
  const db = await getDb();
  await db.delete("runs", runId);
}

export async function getPreference<T>(key: string, fallback: T): Promise<T> {
  const db = await getDb();
  const value = await db.get("preferences", key);
  return value === undefined ? fallback : (value as T);
}

export async function setPreference(key: string, value: unknown): Promise<void> {
  const db = await getDb();
  await db.put("preferences", value, key);
}
