import { useState, useEffect } from 'react';
import { client } from '../../utils/api';
import PrismaAirsToggle from '../PrismaAirsToggle';

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
  prisma_airs_enabled?: boolean;
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
  // Tracks whether the form has unsaved edits relative to what's in the database.
  const [dirty, setDirty] = useState(false);
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
      const [configRes, toolsRes] = await Promise.all([
        client.get('/chatbot/config'),
        client.get('/chatbot/tools'),
      ]);

      setConfig(configRes.data);
      setAvailableTools(toolsRes.data);
      setDirty(false); // freshly loaded from server = no unsaved changes
      setMessage(null);
    } catch (err: any) {
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
      const response = await client.get(`/chatbot/models?provider=${provider}`);
      setAvailableModels(response.data.models);
    } catch {
      setAvailableModels([]);
    }
  };

  // Any edit to the config goes through here so we can flag unsaved changes.
  const updateConfig = (patch: Partial<ChatbotConfig>) => {
    if (!config) return;
    setConfig({ ...config, ...patch });
    setDirty(true);
  };

  // When the provider changes, the previously-saved model usually isn't valid
  // for the new provider (e.g. switching to Portkey needs an @provider/route).
  // Auto-select the first valid route for the new provider so you can't save a
  // provider/model mismatch.
  const handleProviderChange = async (provider: string) => {
    if (!config) return;
    let nextModel = config.llm_model;
    try {
      const response = await client.get(`/chatbot/models?provider=${provider}`);
      const models: string[] = response.data.models || [];
      if (models.length > 0 && !models.includes(config.llm_model)) {
        nextModel = models[0];
      }
    } catch {
      // If the model list can't be fetched, keep the provider change anyway.
    }
    setConfig({ ...config, llm_provider: provider, llm_model: nextModel });
    setDirty(true);
  };

  const handleSaveConfig = async () => {
    if (!config) return;

    try {
      setSaving(true);
      await client.post('/chatbot/config', config);
      setDirty(false); // saved successfully = back in sync with server
      setMessage({
        type: 'success',
        text: `Configuration saved. Active provider: ${config.llm_provider} (${config.llm_model}).`,
      });
    } catch (err: any) {
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
    updateConfig({ tools });
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
              onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
            >
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="google">Google (Gemini)</option>
              <option value="openai">OpenAI (GPT-4/o)</option>
              <option value="portkey">🔀 Portkey AI Gateway</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Model Name</label>
            {availableModels.length > 0 ? (
              <select
                value={config.llm_model}
                onChange={(e) => updateConfig({ llm_model: e.target.value })}
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
                onChange={(e) => updateConfig({ llm_model: e.target.value })}
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
                onChange={(e) => updateConfig({ enabled: e.target.checked })}
                className="rounded border-slate-600 text-cyan-600"
              />
              <span className="text-sm text-slate-300">Enable Chatbot</span>
            </label>
          </div>
        </div>
      </div>

      {/* Security: legacy direct Prisma AIRS integration */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-1">AI Security (Prisma AIRS)</h2>
        <p className="text-sm text-slate-400 mb-4">
          AIRS scanning is now handled by the Portkey gateway. This switch controls the
          legacy <span className="text-slate-300">direct</span> integration only and is
          normally kept <span className="text-slate-300">off</span> to avoid double-scanning.
        </p>
        <PrismaAirsToggle
          enabled={!!config.prisma_airs_enabled}
          onToggle={(v) => setConfig(config ? { ...config, prisma_airs_enabled: v } : config)}
        />
      </div>

      {/* System Prompt */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-4">System Prompt</h2>
        <textarea
          value={config.system_prompt}
          onChange={(e) => updateConfig({ system_prompt: e.target.value })}
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
                updateConfig({
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
                updateConfig({
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
                updateConfig({
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
                updateConfig({
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

      {/* Unsaved changes banner */}
      {dirty && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-900/20 border border-amber-500/40 text-amber-300 text-sm">
          <span>⚠️</span>
          <span>
            You have unsaved changes. Click <strong>Save Configuration</strong> to apply them —
            selecting a provider or model alone does <strong>not</strong> persist until you save.
          </span>
        </div>
      )}

      {/* Save Button */}
      <div className="flex gap-3">
        <button
          onClick={handleSaveConfig}
          disabled={saving || !dirty}
          className={`flex-1 px-6 py-3 rounded-lg font-semibold transition-colors disabled:cursor-not-allowed ${
            dirty
              ? 'bg-amber-500 hover:bg-amber-400 text-slate-900 animate-pulse'
              : 'bg-cyan-600 text-white opacity-50'
          }`}
        >
          {saving
            ? 'Saving...'
            : dirty
            ? '💾 Save Configuration (unsaved changes)'
            : '✓ All changes saved'}
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
