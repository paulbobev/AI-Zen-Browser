import { useState } from "react";
import IntentBar from "./IntentBar.tsx";
import AgentHUD from "./AgentHUD.tsx";
import { useWebSocket } from "./useWebSocket.ts";

export default function App() {
  const { status, updates, summary, sendIntent } = useWebSocket();
  const [showHUD, setShowHUD] = useState(false);

  const handleSubmit = (intent: string) => {
    sendIntent(intent);
    setShowHUD(true);
  };

  return (
    <div className="flex flex-col min-w-[380px] min-h-[420px] max-h-[560px] bg-zen-bg overflow-auto">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-zen-border">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-zen-accent animate-pulse" />
          <span className="text-sm font-semibold tracking-wide text-zen-text">
            ZENITH
          </span>
        </div>
        <span className="text-xs text-zen-muted">
          {status === "connected" ? "connected" : "offline"}
        </span>
      </header>

      {/* Intent Bar — always visible */}
      <IntentBar onSubmit={handleSubmit} disabled={status !== "connected"} />

      {/* Agent HUD — shown once a task is running */}
      {showHUD && (
        <AgentHUD
          updates={updates}
          summary={summary}
          onClose={() => setShowHUD(false)}
        />
      )}
    </div>
  );
}
