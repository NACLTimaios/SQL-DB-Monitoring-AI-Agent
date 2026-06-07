
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DatabaseSummaryPanel({ summary }: any) {
  if (!summary) {
    return (
      <div className="h-full w-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 overflow-hidden">
        <p className="text-slate-400">Loading metrics...</p>
      </div>
    );
  }

  const connPct = Math.round(summary.connections_pct || 0);
  const connColor = connPct > 80 ? 'text-red-400' : connPct > 50 ? 'text-yellow-400' : 'text-green-400';

  const latencyData = [
    { time: '1h', latency: 250 },
    { time: '50m', latency: 280 },
    { time: '40m', latency: 260 },
    { time: '30m', latency: 300 },
    { time: '20m', latency: 290 },
    { time: '10m', latency: 285 },
    { time: 'now', latency: summary.query_latency_ms?.p50 || 285 },
  ];

  return (
    <div className="h-full w-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col overflow-hidden">
      <h3 className="text-sm font-semibold text-slate-300 mb-2 flex-shrink-0">Database Metrics</h3>

      <div className="grid grid-cols-2 gap-2 mb-2 flex-shrink-0">
        <div className="bg-slate-900/50 p-2 rounded min-w-0">
          <p className="text-xs text-slate-400 truncate">Connections</p>
          <p className={`text-sm font-semibold truncate ${connColor}`}>
            {summary.connections}/{summary.connections_max}
          </p>
        </div>
        <div className="bg-slate-900/50 p-2 rounded min-w-0">
          <p className="text-xs text-slate-400 truncate">Disk Used</p>
          <p className="text-sm font-semibold text-slate-200 truncate">{summary.disk_size_gb?.toFixed(2)} GB</p>
        </div>
      </div>

      <div className="flex-1 min-h-0 mb-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={latencyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 116, 139, 0.1)" />
            <XAxis dataKey="time" tick={{ fontSize: 9 }} stroke="rgba(148, 163, 184, 0.5)" />
            <YAxis tick={{ fontSize: 9 }} stroke="rgba(148, 163, 184, 0.5)" />
            <Tooltip contentStyle={{ background: '#1e293b', border: 'none' }} />
            <Area type="monotone" dataKey="latency" fill="#3b82f6" stroke="#0ea5e9" isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-slate-500 pt-1 border-t border-slate-700 truncate flex-shrink-0">
        P50: {summary.query_latency_ms?.p50?.toFixed(0)}ms | P95: {summary.query_latency_ms?.p95?.toFixed(0)}ms
      </p>
    </div>
  );
}
