export default function CapacityPanel({ insights }: any) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Capacity</h2>
      <p className="text-slate-400">Disk usage, connections, cache hit ratio</p>
    </div>
  );
}
