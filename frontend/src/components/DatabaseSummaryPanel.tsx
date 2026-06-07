export default function DatabaseSummaryPanel({ summary }: any) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Database Summary</h2>
      <p className="text-slate-400">Connections, latency, disk, RAM</p>
    </div>
  );
}
