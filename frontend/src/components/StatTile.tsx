interface StatTileProps {
  label: string;
  value: string | number;
  unit?: string;
  accent?: boolean;
}

export default function StatTile({ label, value, unit, accent }: StatTileProps) {
  return (
    <div className="card stat-tile">
      <div className="stat-label">{label}</div>
      <div className={"stat-value" + (accent ? " accent" : "")}>
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
    </div>
  );
}
