export default function ActivityFeed({ activity }: any) {
  if (!activity || activity.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>
        <p className="text-slate-400">No recent activity</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {activity.slice(0, 5).map((item: any, idx: number) => (
          <div key={idx} className="p-2 bg-slate-900/30 rounded text-xs border-l-2 border-slate-600">
            <div className="flex justify-between items-start">
              <span className="font-semibold text-slate-300">{item.type}</span>
              <span className="text-slate-500">{new Date(item.timestamp).toLocaleTimeString()}</span>
            </div>
            <p className="text-slate-400 mt-1">{item.title}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
