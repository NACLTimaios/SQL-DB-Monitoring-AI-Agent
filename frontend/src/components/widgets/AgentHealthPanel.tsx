import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface AgentHealthPanelProps {
  agentStatus: any;
  healthData: any;
}

export default function AgentHealthPanel({
  agentStatus,
  healthData,
}: AgentHealthPanelProps) {
  const isRunning = healthData?.orchestrator_running ?? false;
  const isDbConnected = healthData?.db_connected ?? false;
  const lastCycle = agentStatus?.last_cycle
    ? new Date(agentStatus.last_cycle).toLocaleTimeString()
    : 'Unknown';
  const status = agentStatus?.status?.toUpperCase() || 'UNKNOWN';

  // Mock trend data - in production, fetch from API
  const trendData = [
    { time: '1h ago', uptime: 98 },
    { time: '50m ago', uptime: 98 },
    { time: '40m ago', uptime: 99 },
    { time: '30m ago', uptime: 98 },
    { time: '20m ago', uptime: 99 },
    { time: '10m ago', uptime: 99 },
    { time: 'now', uptime: 100 },
  ];

  const statusColor =
    status === 'HEALTHY'
      ? 'text-green-400 bg-green-900/20'
      : status === 'WARNING'
      ? 'text-yellow-400 bg-yellow-900/20'
      : 'text-red-400 bg-red-900/20';

  return (
    <div className="h-full w-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col overflow-hidden">
      <h3 className="text-sm font-semibold text-slate-300 mb-2 flex-shrink-0">Agent Health</h3>

      <div className="space-y-1 mb-2 flex-shrink-0">
        <div className="flex justify-between items-center gap-2">
          <span className="text-xs text-slate-400">Status:</span>
          <span className={`text-xs font-semibold px-2 py-1 rounded whitespace-nowrap ${statusColor}`}>
            {status}
          </span>
        </div>
        <div className="flex justify-between items-center gap-2">
          <span className="text-xs text-slate-400">Orchestrator:</span>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded whitespace-nowrap ${
              isRunning ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'
            }`}
          >
            {isRunning ? '✓ Running' : '✗ Stopped'}
          </span>
        </div>
        <div className="flex justify-between items-center gap-2">
          <span className="text-xs text-slate-400">Database:</span>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded whitespace-nowrap ${
              isDbConnected ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'
            }`}
          >
            {isDbConnected ? '✓ Connected' : '✗ Offline'}
          </span>
        </div>
      </div>

      <div className="flex-1 min-h-0 mb-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 116, 139, 0.1)" />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="rgba(148, 163, 184, 0.5)" />
            <YAxis tick={{ fontSize: 10 }} stroke="rgba(148, 163, 184, 0.5)" domain={[95, 100]} />
            <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '4px' }} />
            <Line
              type="monotone"
              dataKey="uptime"
              stroke="#10b981"
              dot={false}
              strokeWidth={2}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-slate-500 pt-1 border-t border-slate-700 truncate flex-shrink-0">
        Last cycle: {lastCycle}
      </p>
    </div>
  );
}
