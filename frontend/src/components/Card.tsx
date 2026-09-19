import type { ReactNode } from "react";

// Section wrapper matching the app's dark card style.
export default function Card({
  title,
  actions,
  children,
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl bg-neutral-900/70 p-5 ring-1 ring-white/5">
      {(title || actions) && (
        <div className="mb-4 flex items-center gap-3">
          {title && (
            <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">
              {title}
            </h2>
          )}
          <div className="flex-1" />
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}

export function Button({
  onClick,
  disabled,
  variant = "primary",
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  variant?: "primary" | "ghost" | "danger";
  children: ReactNode;
}) {
  const styles = {
    primary: "bg-emerald-500 text-neutral-950 hover:bg-emerald-400",
    ghost: "bg-neutral-700 text-neutral-100 hover:bg-neutral-600",
    danger: "bg-red-500/90 text-neutral-950 hover:bg-red-400",
  }[variant];
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 ${styles}`}
    >
      {children}
    </button>
  );
}
