import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDateTime } from '../utils/format';
import { logout } from '../utils/api';
import PasswordChangeModal from './PasswordChangeModal';

interface HeaderProps {
  status: string;
  lastCycle: string;
  isRunning: boolean;
}

export default function Header({ status, lastCycle, isRunning }: HeaderProps) {
  const navigate = useNavigate();
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const dotColor =
    status === 'ok' || status === 'healthy'
      ? 'bg-green-500'
      : status === 'warning' || status === 'degraded'
      ? 'bg-yellow-500'
      : 'bg-red-500';

  const badgeClass = isRunning
    ? 'bg-green-900/50 text-green-300 border border-green-700'
    : 'bg-red-900/50 text-red-300 border border-red-700';

  return (
    <header className="bg-[#0d1120] border-b-2 border-blue-600 px-6 py-4">
      <div className="max-w-screen-2xl mx-auto flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">SQL Agent</h1>
          <p className="text-sm text-gray-400">Health &amp; Insights Dashboard</p>
        </div>

        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold ${badgeClass}`}>
            <span className={`w-2 h-2 rounded-full ${dotColor} animate-pulse`} />
            {isRunning ? 'RUNNING' : status.toUpperCase() || 'UNKNOWN'}
          </span>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Last Cycle</p>
            <p className="text-sm text-gray-300 font-mono">
              {lastCycle ? formatDateTime(lastCycle) : '—'}
            </p>
          </div>
          <button
            onClick={() => navigate('/admin')}
            className="px-3 py-1.5 text-xs font-semibold text-blue-300 hover:text-blue-200 border border-blue-600 hover:border-blue-500 rounded-lg transition-colors"
          >
            ⚙️ Admin
          </button>
          <button
            onClick={() => setIsPasswordModalOpen(true)}
            className="px-3 py-1.5 text-xs font-semibold text-amber-300 hover:text-amber-200 border border-amber-600 hover:border-amber-500 rounded-lg transition-colors"
          >
            🔐 Password
          </button>
          <button
            onClick={logout}
            className="px-3 py-1.5 text-xs font-semibold text-gray-400 hover:text-gray-200 border border-gray-700 hover:border-gray-600 rounded-lg transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      <PasswordChangeModal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
      />
    </header>
  );
}
