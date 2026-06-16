import { useState } from 'react';
import { client } from '../utils/api';

interface PrismaAirsToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
}

export default function PrismaAirsToggle({ enabled, onToggle }: PrismaAirsToggleProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggle = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await client.post('/chatbot/prisma-airs/toggle');
      onToggle(response.data.prisma_airs_enabled);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to toggle Prisma AIRS');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleToggle}
        disabled={loading}
        className={`px-3 py-2 rounded-lg font-medium text-sm transition-all ${
          enabled
            ? 'bg-green-900/40 text-green-400 hover:bg-green-900/60 border border-green-700/50'
            : 'bg-red-900/40 text-red-400 hover:bg-red-900/60 border border-red-700/50'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {loading ? 'Toggling...' : enabled ? '🔒 Prisma AIRS: ON' : '🔓 Prisma AIRS: OFF'}
      </button>
      {error && <span className="text-red-400 text-xs">{error}</span>}
    </div>
  );
}
