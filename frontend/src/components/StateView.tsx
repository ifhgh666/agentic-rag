import type { ReactNode } from "react";

interface StateViewProps {
  kind: "loading" | "empty" | "error" | "success";
  title: string;
  description?: string;
  action?: ReactNode;
}

export function StateView({ kind, title, description, action }: StateViewProps) {
  return (
    <div className={`state-view state-${kind}`}>
      <div className="state-mark">{kind === "loading" ? "…" : kind === "error" ? "!" : kind === "empty" ? "○" : "✓"}</div>
      <div>
        <strong>{title}</strong>
        {description && <p>{description}</p>}
        {action}
      </div>
    </div>
  );
}
