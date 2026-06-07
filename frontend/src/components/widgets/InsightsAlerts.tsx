

export default function InsightsAlerts({ insights }: any) {
  if (!insights) {
    return (
      <div className="h-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4">
        <p className="text-slate-400">Loading insights...</p>
      </div>
    );
  }

  const total = insights.total_pending || 0;
  const critical = (insights.capacity?.filter((i: any) => i.severity === 'critical').length || 0) +
                   (insights.performance?.filter((i: any) => i.severity === 'critical').length || 0) +
                   (insights.locks?.filter((i: any) => i.severity === 'critical').length || 0);
  const warning = (insights.capacity?.filter((i: any) => i.severity === 'warning').length || 0) +
                  (insights.performance?.filter((i: any) => i.severity === 'warning').length || 0) +
                  (insights.locks?.filter((i: any) => i.severity === 'warning').length || 0);

  return (
    <div className="h-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Insights & Alerts</h3>

      <div className="space-y-2">
        <div className="bg-slate-900/50 p-3 rounded border-l-4 border-cyan-500">
          <p className="text-xs text-slate-400">Total Pending</p>
          <p className="text-lg font-bold text-cyan-400">{total}</p>
        </div>

        {critical > 0 && (
          <div className="bg-red-900/20 p-3 rounded border-l-4 border-red-500">
            <p className="text-xs text-red-400">🔴 Critical Issues</p>
            <p className="text-lg font-bold text-red-300">{critical}</p>
          </div>
        )}

        {warning > 0 && (
          <div className="bg-yellow-900/20 p-3 rounded border-l-4 border-yellow-500">
            <p className="text-xs text-yellow-400">⚠️ Warnings</p>
            <p className="text-lg font-bold text-yellow-300">{warning}</p>
          </div>
        )}

        {critical === 0 && warning === 0 && (
          <div className="bg-green-900/20 p-3 rounded border-l-4 border-green-500">
            <p className="text-xs text-green-400">✓ All Clear</p>
            <p className="text-sm text-green-300">No issues detected</p>
          </div>
        )}
      </div>
    </div>
  );
}
