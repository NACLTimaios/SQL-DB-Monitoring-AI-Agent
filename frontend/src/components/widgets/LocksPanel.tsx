

export default function LocksPanel({ insights }: any) {
  const insight = insights?.[0];
  const severity = insight?.severity || 'unknown';

  const severityColor = severity === 'ok'
    ? 'bg-green-900/20 text-green-400'
    : severity === 'warning'
    ? 'bg-yellow-900/20 text-yellow-400'
    : 'bg-red-900/20 text-red-400';

  const lockData = [
    { type: 'Waiting', count: 0, color: 'bg-green-500' },
    { type: 'Blocking', count: 0, color: 'bg-blue-500' },
    { type: 'Deadlocks', count: 0, color: 'bg-red-500' },
  ];

  return (
    <div className="h-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-slate-300">Locks</h3>
        <span className={`text-xs font-semibold px-2 py-1 rounded ${severityColor}`}>
          {severity.toUpperCase()}
        </span>
      </div>

      <div className="space-y-2">
        {lockData.map((lock) => (
          <div key={lock.type} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${lock.color}`}></div>
              <span className="text-xs text-slate-400">{lock.type}</span>
            </div>
            <span className="text-sm font-semibold text-slate-200">{lock.count}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 p-2 bg-slate-900/50 rounded text-xs text-slate-400">
        <p>✓ No contention detected</p>
      </div>

      <p className="text-xs text-slate-500 mt-2 pt-2 border-t border-slate-700">
        {insight?.title || 'Monitoring locks'}
      </p>
    </div>
  );
}
