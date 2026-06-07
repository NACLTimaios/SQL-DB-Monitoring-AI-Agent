
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function PerformancePanel({ insights }: any) {
  const insight = insights?.[0];
  const severity = insight?.severity || 'unknown';

  const queryData = [
    { query: 'Q1', time: 285 },
    { query: 'Q2', time: 450 },
    { query: 'Q3', time: 320 },
    { query: 'Q4', time: 510 },
    { query: 'Q5', time: 380 },
  ];

  const severityColor = severity === 'ok'
    ? 'bg-green-900/20 text-green-400'
    : severity === 'warning'
    ? 'bg-yellow-900/20 text-yellow-400'
    : 'bg-red-900/20 text-red-400';

  return (
    <div className="h-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-slate-300">Performance</h3>
        <span className={`text-xs font-semibold px-2 py-1 rounded ${severityColor}`}>
          {severity.toUpperCase()}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={100}>
        <BarChart data={queryData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 116, 139, 0.1)" />
          <XAxis dataKey="query" tick={{ fontSize: 10 }} stroke="rgba(148, 163, 184, 0.5)" />
          <YAxis tick={{ fontSize: 10 }} stroke="rgba(148, 163, 184, 0.5)" />
          <Tooltip contentStyle={{ background: '#1e293b', border: 'none' }} />
          <Bar dataKey="time" fill="#f59e0b" radius={4} />
        </BarChart>
      </ResponsiveContainer>

      <p className="text-xs text-slate-500 mt-2 pt-2 border-t border-slate-700">
        {insight?.title || 'Analyzing slow queries'}
      </p>
    </div>
  );
}
