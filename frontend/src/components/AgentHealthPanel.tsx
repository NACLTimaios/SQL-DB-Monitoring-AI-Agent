

interface AgentHealthPanelProps {
  agentStatus: any;
  isDbConnected: boolean;
  isOrchestratorRunning: boolean;
}

export default function AgentHealthPanel({
  agentStatus,
  isDbConnected,
  isOrchestratorRunning,
}: AgentHealthPanelProps) {
  const lastCycle = agentStatus?.last_cycle
    ? new Date(agentStatus.last_cycle).toLocaleTimeString()
    : 'Unknown';
  const status = agentStatus?.status?.toUpperCase() || 'UNKNOWN';
  const statusColor = status === 'HEALTHY'
    ? 'bg-green-900/20 text-green-400'
    : status === 'WARNING'
    ? 'bg-yellow-900/20 text-yellow-400'
    : 'bg-red-900/20 text-red-400';

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Agent Health</h2>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Status:</span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColor}`}>
            {status}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Orchestrator:</span>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              isOrchestratorRunning
                ? 'bg-green-900/20 text-green-400'
                : 'bg-red-900/20 text-red-400'
            }`}
          >
            {isOrchestratorRunning ? 'Running' : 'Stopped'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Database:</span>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              isDbConnected
                ? 'bg-green-900/20 text-green-400'
                : 'bg-red-900/20 text-red-400'
            }`}
          >
            {isDbConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="pt-2 border-t border-slate-700/50">
          <p className="text-xs text-slate-500">Last cycle: {lastCycle}</p>
        </div>
      </div>
    </div>
  );
}
