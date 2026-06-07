

export default function ActivityFeed({ activity }: any) {
  if (!activity || activity.length === 0) {
    return (
      <div className="h-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-slate-300 mb-2">Recent Activity</h3>
        <p className="text-slate-400">No recent activity</p>
      </div>
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-l-4 border-red-500 bg-red-900/10';
      case 'warning':
        return 'border-l-4 border-yellow-500 bg-yellow-900/10';
      default:
        return 'border-l-4 border-green-500 bg-green-900/10';
    }
  };

  return (
    <div className="h-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Recent Activity</h3>
      <div className="space-y-2 overflow-y-auto flex-1">
        {activity.slice(0, 8).map((item: any, idx: number) => (
          <div key={idx} className={`p-2 rounded text-xs ${getSeverityColor(item.severity)}`}>
            <div className="flex justify-between items-start">
              <span className="font-semibold text-slate-300 capitalize">{item.type}</span>
              <span className="text-slate-500">{new Date(item.timestamp).toLocaleTimeString()}</span>
            </div>
            <p className="text-slate-400 mt-1 line-clamp-2">{item.title}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
