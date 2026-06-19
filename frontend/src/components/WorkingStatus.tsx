interface WorkingStatusProps {
  label?: string;
  detail?: string;
  inline?: boolean;
  className?: string;
}

export function WorkingStatus({
  label = "Working",
  detail,
  inline = false,
  className = "",
}: WorkingStatusProps) {
  const classes = [
    "working-status",
    inline ? "working-status-inline" : "",
    className,
  ].filter(Boolean).join(" ");

  const content = (
    <>
      <span className="working-nuclear" aria-hidden="true">☢</span>
      {label && <span className="working-label">{label}</span>}
      {detail && <span className="working-detail">{detail}</span>}
    </>
  );

  if (inline) {
    return <span className={classes} role="status" aria-live="polite">{content}</span>;
  }
  return <div className={classes} role="status" aria-live="polite">{content}</div>;
}
