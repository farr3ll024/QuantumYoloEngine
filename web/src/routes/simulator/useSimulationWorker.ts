import { useCallback, useEffect, useRef, useState } from "react";
import type { EngineEvent, EquitySample, Order, Position, Strategy, Tick } from "../../engine/model";
import type { WorkerCommand, WorkerDoneMessage, WorkerMessage, WorkerProgressMessage } from "../../worker/simulation.worker";

export type RunPhase = "idle" | "running" | "paused" | "completed" | "canceled";

export interface SimulationResult {
  orders: Order[];
  positions: Position[];
  events: EngineEvent[];
  equitySamples: EquitySample[];
  maxDrawdown: number;
  endingEquity: number;
}

export function useSimulationWorker() {
  const workerRef = useRef<Worker | null>(null);
  const [phase, setPhase] = useState<RunPhase>("idle");
  const [progress, setProgress] = useState<WorkerProgressMessage | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ensureWorker = useCallback((): Worker => {
    if (!workerRef.current) {
      workerRef.current = new Worker(new URL("../../worker/simulation.worker.ts", import.meta.url), {
        type: "module",
      });
      workerRef.current.onmessage = (ev: MessageEvent<WorkerMessage>) => {
        const msg = ev.data;
        if (msg.type === "progress") {
          setProgress(msg);
        } else if (msg.type === "done") {
          const done = msg as WorkerDoneMessage;
          setResult({
            orders: done.orders,
            positions: done.positions,
            events: done.events,
            equitySamples: done.equitySamples,
            maxDrawdown: done.maxDrawdown,
            endingEquity: done.endingEquity,
          });
          setPhase(done.status);
        } else if (msg.type === "error") {
          setError(msg.message);
          setPhase("idle");
        }
      };
    }
    return workerRef.current;
  }, []);

  useEffect(() => {
    return () => {
      workerRef.current?.terminate();
      workerRef.current = null;
    };
  }, []);

  const post = useCallback(
    (cmd: WorkerCommand) => {
      ensureWorker().postMessage(cmd);
    },
    [ensureWorker],
  );

  const start = useCallback(
    (runId: string, strategy: Strategy, ticks: Tick[], speed: number) => {
      setError(null);
      setResult(null);
      setProgress(null);
      setPhase("running");
      post({ type: "start", runId, strategy, ticks, startedAt: new Date().toISOString(), speed });
    },
    [post],
  );

  const pause = useCallback(() => {
    post({ type: "pause" });
    setPhase("paused");
  }, [post]);

  const resume = useCallback(() => {
    post({ type: "resume" });
    setPhase("running");
  }, [post]);

  const step = useCallback(() => {
    post({ type: "step" });
    setPhase("paused");
  }, [post]);

  const cancel = useCallback(() => {
    post({ type: "cancel" });
  }, [post]);

  const reset = useCallback(() => {
    post({ type: "reset" });
    setPhase("idle");
    setProgress(null);
    setResult(null);
    setError(null);
  }, [post]);

  const setSpeed = useCallback(
    (speed: number) => {
      post({ type: "setSpeed", speed });
    },
    [post],
  );

  return { phase, progress, result, error, start, pause, resume, step, cancel, reset, setSpeed };
}
