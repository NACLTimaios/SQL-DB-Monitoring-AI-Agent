export default function CapacityPanel({ insights }: any) {
  const insight = insights?.[0];
  const severity = insight?.severity || 'unknown';
  const severityColor = severity === 'ok'
    ? 'text-green-400'
    : severity === 'warning'
    ? 'text-yellow-400'
    : severity === 'critical'
    ? 'text-red-400'
    : 'text-slate-400';

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <div className="flex items-start justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Capacity</h2>
        <span className={`text-xs font-semibold uppercase px-2 py-1 rounded ${
          severity === 'ok' ? 'bg-green-900/20 text-green-400' :
          severity === 'warning' ? 'bg-yellow-900/20 text-yellow-400' :
          'bg-red-900/20 text-red-400'
        }`}>
          {severity}
        </span>
      </div>
      <p className={`text-sm ${severityColor}`}>
        {insight?.title || 'Monitoring disk usage, connections, cache hit ratio'}
      </p>
    </div>
  );
}
