import { useState, useEffect } from 'react';
import axios from 'axios';

interface ChatbotConfig {
  llm_provider: string;
  llm_model: string;
  system_prompt: string;
  tools: string[];
  guardrails: {
    allow_writes: boolean;
    allow_ddl: boolean;
    query_timeout_seconds: number;
    max_rows_return: number;
    restricted_tables: string[];
  };
  enabled: boolean;
}

interface AvailableTools {
  [key: string]: {
    description: string;
    parameters: { [key: string]: string };
  };
}

export default function ChatbotSettings() {
  const [config, setConfig] = useState<ChatbotConfig | null>(null);
  const [availableTools, setAvailableTools] = useState<AvailableTools>({});
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    if (config) {
      loadModelsForProvider(config.llm_provider);
    }
  }, [config?.llm_provider]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const headers = { Authorization: `Bearer ${token}` };
      const [configRes, toolsRes] = await Promise.all([
        axios.get('/api/chatbot/config', { headers }),
        axios.get('/api/chatbot/tools', { headers }),
      ]);

      setConfig(configRes.data);
      setAvailableTools(toolsRes.data);
      setMessage(null);
    } catch (err: any) {
      console.error('Failed to load config:', err);
      setMessage({
        type: 'error',
        text: 'Failed to load configuration',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadModelsForProvider = async (provider: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(`/api/chatbot/models?provider=${provider}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAvailableModels(response.data.models);
    } catch (err: any) {
      console.error('Failed to load models:', err);
      setAvailableModels([]);
    }
  };

  const handleSaveConfig = async () => {
    if (!config) return;

    try {
      setSaving(true);
      const token = localStorage.getItem('access_token');
      await axios.post('/api/chatbot/config', config, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setMessage({
        type: 'success',
        text: 'Configuration saved successfully',
      });
    } catch (err: any) {
      console.error('Failed to save config:', err);
      setMessage({
        type: 'error',
        text: err?.response?.data?.detail || 'Failed to save configuration',
      });
    } finally {
      setSaving(false);
    }
  };

  const toggleTool = (toolName: string) => {
    if (!config) return;
    const tools = config.tools.includes(toolName)
      ? config.tools.filter((t) => t !== toolName)
      : [...config.tools, toolName];
    setConfig({ ...config, tools });
  };

  if (loading) {
    return <div className="text-slate-400">Loading configuration...</div>;
  }

  if (!config) {
    return <div className="text-red-400">Failed to load configuration</div>;
  }

  return (
    <div className="space-y-6">
      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-900/20 border border-green-500/30 text-green-400'
              : 'bg-red-900/20 border border-red-500/30 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* LLM Settings */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-4">LLM Provider Settings</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">LLM Provider</label>
            <select
              value={config.llm_provider}
              onChange={(e) => setConfig({ ...config, llm_provider: e.target.value })}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
            >
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="google">Google (Gemini)</option>
              <option value="openai">OpenAI (GPT-4/o)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Model Name</label>
            {availableModels.length > 0 ? (
              <select
                value={config.llm_model}
                onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              >
                {availableModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={config.llm_model}
                onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
                placeholder="Enter model name"
              />
            )}
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={config.enabled}
                onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
                className="rounded border-slate-600 text-cyan-600"
              />
              <span className="text-sm text-slate-300">Enable Chatbot</span>
            </label>
          </div>
        </div>
      </div>

      {/* System Prompt */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-4">System Prompt</h2>
        <textarea
          value={config.system_prompt}
          onChange={(e) => setConfig({ ...config, system_prompt: e.target.value })}
          rows={6}
          className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 font-mono text-sm focus:outline-none focus:border-cyan-500"
          placeholder="Enter the system prompt for the chatbot..."
        />
      </div>

      {/* Available Tools */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Available Tools</h2>
        <div className="space-y-3">
          {Object.entries(availableTools).map(([toolName, toolDef]) => (
            <div key={toolName} className="flex items-start gap-3">
              <input
                type="checkbox"
                id={toolName}
                checked={config.tools.includes(toolName)}
                onChange={() => toggleTool(toolName)}
                className="mt-1 rounded border-slate-600 text-cyan-600"
              />
              <label htmlFor={toolName} className="cursor-pointer flex-1">
                <div className="font-medium text-slate-100">{toolName}</div>
                <div className="text-sm text-slate-400">{toolDef.description}</div>
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* Guardrails */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Safety Guardrails</h2>
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="allow_writes"
              checked={config.guardrails.allow_writes}
              onChange={(e) =>
                setConfig({
                  ...config,
                  guardrails: { ...config.guardrails, allow_writes: e.target.checked },
                })
              }
              className="rounded border-slate-600 text-cyan-600"
            />
            <label htmlFor="allow_writes" className="ml-2 text-sm text-slate-300">
              Allow Write Queries (INSERT/UPDATE/DELETE)
            </label>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="allow_ddl"
              checked={config.guardrails.allow_ddl}
              onChange={(e) =>
                setConfig({
                  ...config,
                  guardrails: { ...config.guardrails, allow_ddl: e.target.checked },
                })
              }
              className="rounded border-slate-600 text-cyan-600"
            />
            <label htmlFor="allow_ddl" className="ml-2 text-sm text-slate-300">
              Allow DDL Queries (CREATE/ALTER/DROP)
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Query Timeout (seconds)
            </label>
            <input
              type="number"
              min="1"
              max="60"
              value={config.guardrails.query_timeout_seconds}
              onChange={(e) =>
                setConfig({
                  ...config,
                  guardrails: {
                    ...config.guardrails,
                    query_timeout_seconds: parseInt(e.target.value),
                  },
                })
              }
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Maximum Rows per Query
            </label>
            <input
              type="number"
              min="100"
              max="10000"
              step="100"
              value={config.guardrails.max_rows_return}
              onChange={(e) =>
                setConfig({
                  ...config,
                  guardrails: {
                    ...config.guardrails,
                    max_rows_return: parseInt(e.target.value),
                  },
                })
              }
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100"
            />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex gap-3">
        <button
          onClick={handleSaveConfig}
          disabled={saving}
          className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white px-6 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? 'Saving...' : '💾 Save Configuration'}
        </button>
        <button
          onClick={loadConfig}
          className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg font-semibold transition-colors"
        >
          🔄 Reload
        </button>
      </div>
    </div>
  );
}
