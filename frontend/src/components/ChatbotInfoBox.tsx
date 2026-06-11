import { useState, useEffect } from 'react';
import { client } from '../utils/api';

interface ChatbotConfig {
  llm_provider?: string;
  llm_model?: string;
}

interface Guardrails {
  allow_writes?: boolean;
  allow_ddl?: boolean;
  query_timeout_seconds?: number;
  max_rows_return?: number;
}

const TOOL_DESCRIPTIONS: { [key: string]: string } = {
  get_metrics: 'Retrieve current database performance metrics including connections, disk usage, and cache hit ratios.',
  get_slow_queries: 'Identify and analyze slow-running queries from the pg_stat_statements extension.',
  get_table_stats: 'Get table sizes, row counts, and storage statistics for all database tables.',
  check_locks: 'Detect active locks and blocking sessions that may impact database performance.',
};

const getQueryDatabaseDescription = (guardrails: Guardrails | null): string => {
  if (!guardrails) {
    return 'Execute queries against the monitored database to retrieve and analyze data.';
  }

  const operations: string[] = ['SELECT'];
  if (guardrails.allow_writes) {
    operations.push('INSERT', 'UPDATE', 'DELETE');
  }
  if (guardrails.allow_ddl) {
    operations.push('CREATE', 'ALTER', 'DROP');
  }

  const operationsList = operations.join(', ');
  const rows = guardrails.max_rows_return || '1000';
  const timeout = guardrails.query_timeout_seconds || '5';

  return `Execute ${operationsList} queries (max ${rows} rows, ${timeout}s timeout).`;
};

export default function ChatbotInfoBox() {
  const [config, setConfig] = useState<ChatbotConfig | null>(null);
  const [tools, setTools] = useState<string[]>([]);
  const [guardrails, setGuardrails] = useState<Guardrails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch chatbot config, guardrails, and tools in parallel
        const [configResponse, guardrailsResponse, toolsResponse] = await Promise.all([
          client.get('/chatbot/config'),
          client.get('/chatbot/guardrails'),
          client.get('/chatbot/tools'),
        ]);

        setConfig(configResponse.data);
        setGuardrails(guardrailsResponse.data);

        if (typeof toolsResponse.data === 'object') {
          setTools(Object.keys(toolsResponse.data));
        }

        setError(null);
      } catch {
        setError('Failed to load chatbot information');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 h-full flex items-center justify-center">
        <p className="text-slate-400 text-sm">Loading...</p>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 border-b border-slate-700 px-4 py-3 flex-shrink-0">
        <h3 className="text-base font-semibold text-white">ℹ️ Assistant Info</h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        {error ? (
          <div className="text-red-400 text-sm">{error}</div>
        ) : (
          <>
            {/* Model Information */}
            <div>
              <h4 className="text-base font-semibold text-cyan-400 mb-2">Model</h4>
              <div className="space-y-1">
                <div className="text-sm text-slate-300">
                  <span className="text-slate-500">Provider:</span>{' '}
                  <span className="text-cyan-300 font-mono">
                    {config?.llm_provider || 'Not configured'}
                  </span>
                </div>
                <div className="text-sm text-slate-300">
                  <span className="text-slate-500">Model:</span>{' '}
                  <span className="text-cyan-300 font-mono text-xs break-all">
                    {config?.llm_model || 'Not configured'}
                  </span>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-slate-700" />

            {/* Available Tools */}
            <div>
              <h4 className="text-base font-semibold text-cyan-400 mb-2">Available Tools</h4>
              <div className="space-y-2">
                {tools.length === 0 ? (
                  <p className="text-sm text-slate-400">No tools available</p>
                ) : (
                  tools.map((tool) => (
                    <div key={tool} className="text-sm">
                      <div className="text-slate-300 font-mono bg-slate-700/30 px-2 py-1 rounded mb-1">
                        • {tool}
                      </div>
                      <p className="text-slate-400 text-xs leading-tight px-2 italic">
                        {tool === 'query_database'
                          ? getQueryDatabaseDescription(guardrails)
                          : TOOL_DESCRIPTIONS[tool] || 'Database analysis tool'}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Info Note */}
            <div className="border-t border-slate-700 pt-4">
              <p className="text-sm text-slate-500">
                💡 Admin users can configure the model and guardrails in the Admin Settings page.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
