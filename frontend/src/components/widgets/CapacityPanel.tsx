
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
    <div className="h-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-slate-300">Capacity</h3>
        <span className={`text-xs font-semibold px-2 py-1 rounded ${severityColor}`}>
          {severity.toUpperCase()}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={120}>
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

      <div className="mt-3 text-xs text-slate-400">
        <p>2.6 GB / 200 GB used</p>
        <p className="text-slate-500 mt-1">{insight?.title || 'Monitoring capacity'}</p>
      </div>
    </div>
  );
}
