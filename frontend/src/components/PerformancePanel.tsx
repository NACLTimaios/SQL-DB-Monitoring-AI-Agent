export default function PerformancePanel({ insights }: any) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Performance</h2>
      <p className="text-slate-400">Slow queries and table statistics</p>
    </div>
  );
}
