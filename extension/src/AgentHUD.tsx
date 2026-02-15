import type { StateUpdate } from "./useWebSocket.ts";

interface AgentHUDProps {
  updates: StateUpdate[];
  summary: string | null;
  onClose: () => void;
}

const NODE_LABELS: Record<string, string> = {
  parse_intent: "Planning",
  browser_action: "Browsing",
  self_correct: "Verifying",
  advance: "Next task",
  summarize: "Summarizing",
  done: "Complete",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-zen-muted/40",
  running: "bg-yellow-500/80 animate-pulse",
  done: "bg-emerald-500/80",
  failed: "bg-red-500/80",
};

export default function AgentHUD({ updates, summary, onClose }: AgentHUDProps) {
  const latest = updates[updates.length - 1] ?? null;

  return (
    <div className="flex-1 flex flex-col overflow-hidden border-t border-zen-border">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-zen-surface/60">
        <span className="text-xs font-semibold tracking-widest uppercase text-zen-muted">
          Agent HUD
        </span>
        <button
          onClick={onClose}
          className="text-zen-muted hover:text-zen-text text-xs transition-colors"
        >
          close
        </button>
      </div>

      {/* Scrollable log */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {/* Sub-task list (from latest update) */}
        {latest?.sub_tasks && latest.sub_tasks.length > 0 && (
          <div className="space-y-1.5">
            {latest.sub_tasks.map((t) => (
              <div
                key={t.id}
                className="flex items-start gap-2 text-xs leading-relaxed"
              >
                <span
                  className={`mt-1 shrink-0 w-2 h-2 rounded-full ${STATUS_COLORS[t.status] ?? "bg-zen-muted/40"}`}
                />
                <span
                  className={
                    t.status === "done"
                      ? "text-zen-muted line-through"
                      : "text-zen-text"
                  }
                >
                  {t.desc}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Thought stream */}
        <div className="space-y-1">
          {updates.map((u, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-xs text-zen-muted"
            >
              <span className="shrink-0 font-mono text-zen-accent/70 w-20 text-right">
                {NODE_LABELS[u.node_status] ?? u.node_status}
              </span>
              <span className="text-zen-text/80">{u.thought}</span>
            </div>
          ))}
        </div>

        {/* Final summary */}
        {summary && (
          <div className="mt-4 p-3 rounded-lg bg-zen-primary/30 border border-zen-accent/20">
            <h3 className="text-xs font-semibold text-zen-accent mb-1 tracking-wide uppercase">
              Result
            </h3>
            <p className="text-sm text-zen-text leading-relaxed whitespace-pre-wrap">
              {summary}
            </p>
          </div>
        )}
      </div>

      {/* Status footer */}
      {latest && !summary && (
        <div className="px-4 py-2 border-t border-zen-border bg-zen-surface/40 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-zen-accent animate-pulse" />
          <span className="text-[11px] text-zen-muted">
            {NODE_LABELS[latest.node_status] ?? latest.node_status}
            {latest.total_tasks > 0 &&
              ` — task ${latest.current_task_index + 1}/${latest.total_tasks}`}
          </span>
        </div>
      )}
    </div>
  );
}
