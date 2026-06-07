

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
    <div className="h-full w-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col overflow-hidden">
      <div className="flex justify-between items-center mb-2 flex-shrink-0 gap-2">
        <h3 className="text-sm font-semibold text-slate-300 truncate">Locks</h3>
        <span className={`text-xs font-semibold px-2 py-1 rounded whitespace-nowrap flex-shrink-0 ${severityColor}`}>
          {severity.toUpperCase()}
        </span>
      </div>

      <div className="space-y-1 flex-shrink-0 mb-2">
        {lockData.map((lock) => (
          <div key={lock.type} className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${lock.color}`}></div>
              <span className="text-xs text-slate-400 truncate">{lock.type}</span>
            </div>
            <span className="text-sm font-semibold text-slate-200 flex-shrink-0">{lock.count}</span>
          </div>
        ))}
      </div>

      <div className="flex-1 min-h-0 flex items-center mb-2">
        <div className="w-full p-2 bg-slate-900/50 rounded text-xs text-slate-400 text-center">
          <p className="truncate">✓ No contention detected</p>
        </div>
      </div>

      <p className="text-xs text-slate-500 pt-1 border-t border-slate-700 truncate flex-shrink-0">
        {insight?.title || 'Monitoring locks'}
      </p>
    </div>
  );
}
