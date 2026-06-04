import { SEVERITY_CONFIG, type Severity, cn } from "../lib/utils";

interface Props {
  severity: Severity;
  className?: string;
}

export function SeverityBadge({ severity, className }: Props) {
  const config = SEVERITY_CONFIG[severity];
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        config.bg,
        config.color,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
