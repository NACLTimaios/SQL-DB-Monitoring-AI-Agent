import React, { useState, useEffect } from 'react';
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

export default function AdminPage() {
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
      const token = localStorage.getItem('token');
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
      const token = localStorage.getItem('token');
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
      const token = localStorage.getItem('token');
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
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-400">Loading configuration...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-400">Failed to load configuration</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-dark p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-100 mb-8">
          Chatbot Configuration
        </h1>

        {/* Status message */}
        {message && (
          <div
            className={`mb-6 p-4 rounded-lg ${
              message.type === 'success'
                ? 'bg-green-900/20 border border-green-500/30 text-green-400'
                : 'bg-red-900/20 border border-red-500/30 text-red-400'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* LLM Settings */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">
            LLM Settings
          </h2>

          <div className="space-y-4">
            {/* Provider */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                LLM Provider
              </label>
              <select
                value={config.llm_provider}
                onChange={(e) =>
                  setConfig({ ...config, llm_provider: e.target.value })
                }
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-cyan-500"
              >
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="google">Google (Gemini)</option>
                <option value="openai">OpenAI (GPT-4/o)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Select the LLM provider. All three providers are supported.
              </p>
            </div>

            {/* Model */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Model Name
              </label>
              {availableModels.length > 0 ? (
                <select
                  value={config.llm_model}
                  onChange={(e) =>
                    setConfig({ ...config, llm_model: e.target.value })
                  }
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-cyan-500"
                >
                  <option value="">Select a model...</option>
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
                  onChange={(e) =>
                    setConfig({ ...config, llm_model: e.target.value })
                  }
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-cyan-500"
                  placeholder="Enter model name"
                />
              )}
              <p className="text-xs text-gray-500 mt-1">
                {availableModels.length > 0
                  ? 'Select from available models for this provider'
                  : 'Enter custom model name or select a different provider'}
              </p>
            </div>

            {/* Enabled */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="enabled"
                checked={config.enabled}
                onChange={(e) =>
                  setConfig({ ...config, enabled: e.target.checked })
                }
                className="rounded border-gray-700 text-cyan-600 focus:ring-cyan-500"
              />
              <label
                htmlFor="enabled"
                className="ml-2 text-sm text-gray-300 cursor-pointer"
              >
                Enable Chatbot
              </label>
            </div>
          </div>
        </div>

        {/* System Prompt */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">
            System Prompt
          </h2>

          <textarea
            value={config.system_prompt}
            onChange={(e) =>
              setConfig({ ...config, system_prompt: e.target.value })
            }
            rows={6}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 font-mono text-sm focus:outline-none focus:border-cyan-500"
            placeholder="Enter the system prompt for the chatbot..."
          />
          <p className="text-xs text-gray-500 mt-2">
            Define the assistant's role and behavior
          </p>
        </div>

        {/* Tools */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">
            Available Tools
          </h2>

          <div className="space-y-3">
            {Object.entries(availableTools).map(([toolName, toolDef]) => (
              <div key={toolName} className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id={toolName}
                  checked={config.tools.includes(toolName)}
                  onChange={() => toggleTool(toolName)}
                  className="rounded border-gray-700 text-cyan-600 focus:ring-cyan-500 mt-1"
                />
                <label htmlFor={toolName} className="cursor-pointer flex-1">
                  <div className="font-medium text-gray-100">{toolName}</div>
                  <div className="text-sm text-gray-400">
                    {toolDef.description}
                  </div>
                </label>
              </div>
            ))}
          </div>
        </div>

        {/* Guardrails */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-100 mb-4">
            Safety Guardrails
          </h2>

          <div className="space-y-4">
            {/* Write Protection */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="allow_writes"
                checked={config.guardrails.allow_writes}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    guardrails: {
                      ...config.guardrails,
                      allow_writes: e.target.checked,
                    },
                  })
                }
                className="rounded border-gray-700 text-cyan-600 focus:ring-cyan-500"
              />
              <label
                htmlFor="allow_writes"
                className="ml-2 text-sm text-gray-300 cursor-pointer"
              >
                Allow Write Queries (INSERT/UPDATE/DELETE)
              </label>
            </div>

            {/* DDL Protection */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="allow_ddl"
                checked={config.guardrails.allow_ddl}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    guardrails: {
                      ...config.guardrails,
                      allow_ddl: e.target.checked,
                    },
                  })
                }
                className="rounded border-gray-700 text-cyan-600 focus:ring-cyan-500"
              />
              <label
                htmlFor="allow_ddl"
                className="ml-2 text-sm text-gray-300 cursor-pointer"
              >
                Allow DDL Queries (CREATE/ALTER/DROP)
              </label>
            </div>

            {/* Query Timeout */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
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
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Max Rows */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
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
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-cyan-500"
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
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
          <button
            onClick={loadConfig}
            className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded-lg font-semibold transition-colors"
          >
            Reload
          </button>
        </div>
      </div>
    </div>
  );
}
