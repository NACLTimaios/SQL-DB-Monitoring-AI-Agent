export default function DatabaseSummaryPanel({ summary }: any) {
  if (!summary) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Database</h2>
        <p className="text-slate-400">Loading database metrics...</p>
      </div>
    );
  }

  const connPct = Math.round(summary.connections_pct || 0);
  const connColor = connPct > 80 ? 'text-red-400' : connPct > 50 ? 'text-yellow-400' : 'text-green-400';

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Database Summary</h2>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-400">Connections:</span>
          <span className={connColor}>{summary.connections}/{summary.connections_max} ({connPct}%)</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Disk Used:</span>
          <span className="text-slate-300">{summary.disk_size_gb?.toFixed(2)} GB</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">P50 Latency:</span>
          <span className="text-slate-300">{summary.query_latency_ms?.p50?.toFixed(0)}ms</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">P95 Latency:</span>
          <span className="text-slate-300">{summary.query_latency_ms?.p95?.toFixed(0)}ms</span>
        </div>
      </div>
    </div>
  );
}
