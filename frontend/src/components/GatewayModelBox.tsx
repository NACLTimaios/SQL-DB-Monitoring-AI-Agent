import { useEffect, useState } from 'react';
import { client } from '../utils/api';

interface ChatbotConfig {
  llm_provider?: string;
  llm_model?: string;
}

/**
 * Compact box showing the active gateway and model for the Assistant.
 * Routing is handled by Portkey, so no per-request route is shown.
 */
export default function GatewayModelBox() {
  const [config, setConfig] = useState<ChatbotConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client
      .get('/chatbot/config')
      .then((r) => setConfig(r.data))
      .catch(() => setConfig(null))
      .finally(() => setLoading(false));
  }, []);

  const isPortkey = config?.llm_provider === 'portkey';
  const gateway = isPortkey ? 'Portkey AI Gateway' : config?.llm_provider || 'Not configured';
  const model = config?.llm_model || 'Not configured';

  return (
    <div className="flex items-center gap-4 bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl px-4 py-2.5">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-lg" aria-hidden>{isPortkey ? '🔀' : '🤖'}</span>
        <div className="leading-tight min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">Gateway</div>
          <div className="text-sm font-semibold text-cyan-300 truncate">
            {loading ? '…' : gateway}
          </div>
        </div>
      </div>

      <div className="h-8 w-px bg-slate-700 flex-shrink-0" />

      <div className="leading-tight min-w-0">
        <div className="text-[10px] uppercase tracking-wider text-slate-500">Model</div>
        <div className="text-sm font-mono text-cyan-300 truncate">
          {loading ? '…' : model}
        </div>
      </div>
    </div>
  );
}
