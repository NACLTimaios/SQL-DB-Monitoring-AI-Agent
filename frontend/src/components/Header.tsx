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
    <header className="sticky top-0 z-50 bg-[#0d1120] border-b-2 border-blue-600 px-8 py-3">
      <div className="max-w-full flex items-center justify-between gap-8">
        {/* Left: Logo */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <span className="text-white font-bold text-lg">S</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent tracking-tight">
              SELECTer
            </h1>
            <p className="text-xs text-gray-400">SQL Monitoring</p>
          </div>
        </div>

        {/* Center: Status and Last Cycle */}
        <div className="flex items-center gap-6 flex-1 justify-center min-w-0">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Status</p>
            <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${badgeClass}`}>
              <span className={`w-2 h-2 rounded-full ${dotColor} animate-pulse`} />
              {isRunning ? 'RUNNING' : status.toUpperCase() || 'UNKNOWN'}
            </span>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Last Cycle</p>
            <p className="text-xs text-gray-300 font-mono">
              {lastCycle ? formatDateTime(lastCycle) : '—'}
            </p>
          </div>
        </div>

        {/* Right: Buttons */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <button
            onClick={() => navigate('/admin')}
            className="px-3 py-2 text-xs font-semibold text-blue-300 hover:text-blue-200 border border-blue-600 hover:border-blue-500 rounded-lg transition-colors hover:bg-blue-600/10"
          >
            Admin
          </button>
          <button
            onClick={() => setIsPasswordModalOpen(true)}
            className="px-3 py-2 text-xs font-semibold text-amber-300 hover:text-amber-200 border border-amber-600 hover:border-amber-500 rounded-lg transition-colors hover:bg-amber-600/10"
          >
            Password
          </button>
          <button
            onClick={logout}
            className="px-3 py-2 text-xs font-semibold text-gray-400 hover:text-gray-200 border border-gray-700 hover:border-gray-600 rounded-lg transition-colors hover:bg-gray-700/20"
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
