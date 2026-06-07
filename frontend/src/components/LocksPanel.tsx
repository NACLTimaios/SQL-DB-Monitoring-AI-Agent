export default function LocksPanel({ insights }: any) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Locks</h2>
      <p className="text-slate-400">Active locks and blocking sessions</p>
    </div>
  );
}
