import { cn } from "@/lib/utils";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
}

/**
 * A plain div-based progress bar rather than pulling in
 * @radix-ui/react-progress — unlike Dialog (real focus-trap/ESC/ARIA
 * needs), a progress indicator's accessibility surface is just
 * role="progressbar" plus the aria-value* attributes, which a bare
 * div covers without a dependency.
 */
export function Progress({ value, className, ...props }: ProgressProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn("h-2 w-full overflow-hidden rounded-full bg-secondary", className)}
      {...props}
    >
      <div
        className="h-full rounded-full bg-primary transition-all duration-300"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}