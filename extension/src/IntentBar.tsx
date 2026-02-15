import { useState, useRef, useEffect, type FormEvent } from "react";

interface IntentBarProps {
  onSubmit: (intent: string) => void;
  disabled?: boolean;
}

export default function IntentBar({ onSubmit, disabled }: IntentBarProps) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus on mount and when Ctrl+L / Cmd+K fires (the extension command
  // opens the popup/sidebar, which mounts this component).
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="px-4 pt-4 pb-2">
      <div className="relative group">
        {/* Glow ring on focus */}
        <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-zen-accent/30 to-zen-primary/30 opacity-0 group-focus-within:opacity-100 transition-opacity blur-sm" />

        <div className="relative flex items-center gap-2 bg-zen-surface border border-zen-border rounded-xl px-4 py-3 focus-within:border-zen-accent/50 transition-colors">
          {/* Search / sparkle icon */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-5 h-5 text-zen-muted shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z"
            />
          </svg>

          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={
              disabled
                ? "Connecting to Zenith backend…"
                : "What should I do? e.g. Find the cheapest RTX 5070 on eBay…"
            }
            disabled={disabled}
            className="flex-1 bg-transparent text-zen-text placeholder-zen-muted text-sm outline-none disabled:opacity-40"
          />

          {/* Submit chip */}
          {value.trim() && !disabled && (
            <button
              type="submit"
              className="shrink-0 text-xs font-medium bg-zen-accent/90 hover:bg-zen-accent text-white px-3 py-1 rounded-lg transition-colors"
            >
              Run
            </button>
          )}

          {/* Keyboard shortcut hint */}
          {!value && (
            <kbd className="hidden sm:inline-block shrink-0 text-[10px] text-zen-muted border border-zen-border rounded px-1.5 py-0.5">
              Ctrl+L
            </kbd>
          )}
        </div>
      </div>
    </form>
  );
}
