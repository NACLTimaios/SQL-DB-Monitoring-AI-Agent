import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function PerformanceMetrics() {
  const [timeScope, setTimeScope] = useState<'1h' | '6h' | '24h' | '7d'>('1h');

  // Mock performance data for different time scopes
  const generateData = (scope: string) => {
    const dataMap: Record<string, any[]> = {
      '1h': Array.from({ length: 12 }, (_, i) => ({
        time: `${5 * i}m`,
        latency: Math.random() * 150 + 100,
        throughput: Math.random() * 1000 + 500,
        errors: Math.random() * 10,
      })),
      '6h': Array.from({ length: 12 }, (_, i) => ({
        time: `${30 * i}m`,
        latency: Math.random() * 200 + 100,
        throughput: Math.random() * 1500 + 500,
        errors: Math.random() * 20,
      })),
      '24h': Array.from({ length: 24 }, (_, i) => ({
        time: `${i}:00`,
        latency: Math.random() * 250 + 100,
        throughput: Math.random() * 2000 + 500,
        errors: Math.random() * 30,
      })),
      '7d': Array.from({ length: 7 }, (_, i) => ({
        time: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
        latency: Math.random() * 300 + 100,
        throughput: Math.random() * 2500 + 500,
        errors: Math.random() * 50,
      })),
    };
    return dataMap[scope];
  };

  const [metric, setMetric] = useState<'latency' | 'throughput' | 'errors'>('latency');
  const data = generateData(timeScope);

  const metricConfig = {
    latency: { label: 'Query Latency (ms)', color: '#0ea5e9', unit: 'ms' },
    throughput: { label: 'Throughput (queries/s)', color: '#10b981', unit: 'q/s' },
    errors: { label: 'Error Rate (%)', color: '#ef4444', unit: '%' },
  };

  const currentMetric = metricConfig[metric];

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex gap-4 items-center flex-wrap">
        <div className="flex gap-2">
          {(['latency', 'throughput', 'errors'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                metric === m
                  ? 'bg-cyan-600/30 text-cyan-400 border border-cyan-500/30'
                  : 'bg-slate-700/30 text-slate-400 hover:text-slate-300'
              }`}
            >
              {metricConfig[m as keyof typeof metricConfig].label.split(' ')[0]}
            </button>
          ))}
        </div>

        <div className="flex gap-2 ml-auto">
          {(['1h', '6h', '24h', '7d'] as const).map((scope) => (
            <button
              key={scope}
              onClick={() => setTimeScope(scope)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                timeScope === scope
                  ? 'bg-blue-600/30 text-blue-400 border border-blue-500/30'
                  : 'bg-slate-700/30 text-slate-400 hover:text-slate-300'
              }`}
            >
              {scope}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">{currentMetric.label}</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 116, 139, 0.1)" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="rgba(148, 163, 184, 0.5)" />
            <YAxis tick={{ fontSize: 11 }} stroke="rgba(148, 163, 184, 0.5)" />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #475569' }}
              formatter={(value) => `${Number(value).toFixed(2)} ${currentMetric.unit}`}
            />
            <Line
              type="monotone"
              dataKey={metric}
              stroke={currentMetric.color}
              dot={false}
              strokeWidth={2}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {data.length > 0 && (
          <>
            <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Current</p>
              <p className="text-lg font-semibold text-slate-200">
                {Number(data[data.length - 1][metric]).toFixed(1)}
              </p>
              <p className="text-xs text-slate-500">{currentMetric.unit}</p>
            </div>
            <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Average</p>
              <p className="text-lg font-semibold text-slate-200">
                {(data.reduce((sum, d) => sum + d[metric], 0) / data.length).toFixed(1)}
              </p>
              <p className="text-xs text-slate-500">{currentMetric.unit}</p>
            </div>
            <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Peak</p>
              <p className="text-lg font-semibold text-slate-200">
                {Math.max(...data.map((d) => d[metric])).toFixed(1)}
              </p>
              <p className="text-xs text-slate-500">{currentMetric.unit}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
