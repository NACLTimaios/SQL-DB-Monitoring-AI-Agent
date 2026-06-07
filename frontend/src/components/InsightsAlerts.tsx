export default function InsightsAlerts({ insights }: any) {
  if (!insights) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Insights & Alerts</h2>
        <p className="text-slate-400">Loading insights...</p>
      </div>
    );
  }

  const total = insights.total_pending || 0;
  const critical = insights.capacity?.filter((i: any) => i.severity === 'critical').length || 0;
  const warning = insights.capacity?.filter((i: any) => i.severity === 'warning').length || 0;

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Insights & Alerts</h2>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between items-center p-2 bg-slate-900/30 rounded">
          <span className="text-slate-300">Total Pending:</span>
          <span className="text-cyan-400 font-semibold">{total}</span>
        </div>
        {critical > 0 && (
          <div className="flex justify-between items-center p-2 bg-red-900/20 rounded text-red-400">
            <span>Critical Issues:</span>
            <span className="font-semibold">{critical}</span>
          </div>
        )}
        {warning > 0 && (
          <div className="flex justify-between items-center p-2 bg-yellow-900/20 rounded text-yellow-400">
            <span>Warnings:</span>
            <span className="font-semibold">{warning}</span>
          </div>
        )}
      </div>
    </div>
  );
}
