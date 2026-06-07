

export default function ActivityFeed({ activity }: any) {
  if (!activity || activity.length === 0) {
    return (
      <div className="h-full w-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 overflow-hidden">
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
    <div className="h-full w-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col overflow-hidden">
      <h3 className="text-sm font-semibold text-slate-300 mb-2 flex-shrink-0">Recent Activity</h3>
      <div className="space-y-1 overflow-y-auto flex-1 min-h-0">
        {activity.slice(0, 8).map((item: any, idx: number) => (
          <div key={idx} className={`p-2 rounded text-xs ${getSeverityColor(item.severity)}`}>
            <div className="flex justify-between items-start gap-2">
              <span className="font-semibold text-slate-300 capitalize truncate">{item.type}</span>
              <span className="text-slate-500 whitespace-nowrap flex-shrink-0 text-xs">
                {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <p className="text-slate-400 mt-1 line-clamp-1">{item.title}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
