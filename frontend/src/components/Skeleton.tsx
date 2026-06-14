interface SkeletonProps {
  height?: number | string;
  width?: number | string;
  style?: React.CSSProperties;
}

export function Skeleton({ height = 14, width = "100%", style }: SkeletonProps) {
  return (
    <div
      className="skeleton"
      style={{ height, width, ...style }}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton-card">
      <Skeleton height={14} width="55%" style={{ marginBottom: 10 }} />
      {Array.from({ length: lines - 1 }).map((_, i) => (
        <Skeleton key={i} height={12} width={i === lines - 2 ? "70%" : "100%"} style={{ marginBottom: 8 }} />
      ))}
    </div>
  );
}
