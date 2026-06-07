
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

export default function CapacityPanel({ insights }: any) {
  const insight = insights?.[0];
  const severity = insight?.severity || 'unknown';

  const capacityData = [
    { name: 'Used', value: 2.6, fill: '#0ea5e9' },
    { name: 'Available', value: 197.4, fill: '#10b981' },
  ];

  const severityColor = severity === 'ok'
    ? 'bg-green-900/20 text-green-400'
    : severity === 'warning'
    ? 'bg-yellow-900/20 text-yellow-400'
    : 'bg-red-900/20 text-red-400';

  return (
    <div className="h-full w-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col overflow-hidden">
      <div className="flex justify-between items-center mb-2 flex-shrink-0">
        <h3 className="text-sm font-semibold text-slate-300 truncate">Capacity</h3>
        <span className={`text-xs font-semibold px-2 py-1 rounded whitespace-nowrap flex-shrink-0 ml-2 ${severityColor}`}>
          {severity.toUpperCase()}
        </span>
      </div>

      <div className="flex-1 min-h-0 flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={capacityData}
              cx="50%"
              cy="50%"
              innerRadius={35}
              outerRadius={55}
              paddingAngle={2}
              dataKey="value"
            >
              {capacityData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: '#1e293b', border: 'none' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 text-xs text-slate-400 flex-shrink-0">
        <p className="truncate">2.6 GB / 200 GB used</p>
        <p className="text-slate-500 mt-1 truncate">{insight?.title || 'Monitoring capacity'}</p>
      </div>
    </div>
  );
}
