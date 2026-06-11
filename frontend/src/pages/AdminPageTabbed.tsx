import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '../utils/api';
import ChatbotSettings from '../components/admin/ChatbotSettings';
import UserManagement from '../components/admin/UserManagement';

interface UserInfo {
  id: number;
  username: string;
  enabled: boolean;
  roles: string[];
  created_at?: string;
}

export default function AdminPageTabbed() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'chatbot' | 'users'>('chatbot');
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await client.get('/me');
      setUser(response.data);
    } catch {
      // 401 is handled globally by the axios interceptor (redirect to login)
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'chatbot', label: '⚙️ Chatbot Settings', icon: 'chatbot' },
    { id: 'users', label: '👥 User Management', icon: 'users' },
  ] as const;

  // Check if user has admin role
  const isAdmin = user?.roles.includes('admin') ?? false;

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-slate-400 mb-4">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-slate-900 p-8">
        <div className="max-w-2xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent mb-2">
                Access Denied
              </h1>
              <p className="text-slate-400">Admin Settings</p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg font-semibold transition-colors"
            >
              ← Back to Dashboard
            </button>
          </div>

          {/* Access Denied Message */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-8">
            <div className="text-center space-y-6">
              <div className="text-6xl">🔒</div>

              <div>
                <h2 className="text-2xl font-bold text-white mb-2">Admin Access Required</h2>
                <p className="text-slate-300 mb-4">
                  You are currently logged in as <span className="font-semibold text-cyan-400">{user?.username}</span> with the{' '}
                  <span className="font-semibold text-slate-400">{user?.roles.join(', ')}</span> role.
                </p>
              </div>

              <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-6 text-left">
                <p className="text-slate-300 mb-3">
                  The Admin Settings page is restricted to users with administrator privileges. To access this section, you will need to:
                </p>
                <ul className="space-y-2 text-slate-400">
                  <li className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold mt-1">•</span>
                    <span>Contact your system administrator to request admin access</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold mt-1">•</span>
                    <span>Ask them to update your user role to "admin"</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-cyan-400 font-bold mt-1">•</span>
                    <span>Log out and log back in to refresh your permissions</span>
                  </li>
                </ul>
              </div>

              <div className="pt-4">
                <p className="text-slate-500 text-sm">
                  If you believe this is an error, please contact your system administrator.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent mb-2">Settings</h1>
            <p className="text-slate-400">Manage configuration and user accounts</p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg font-semibold transition-colors"
          >
            ← Back to Dashboard
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 border-b border-slate-700">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-3 font-semibold transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          {activeTab === 'chatbot' ? (
            <ChatbotSettings />
          ) : (
            <UserManagement />
          )}
        </div>
      </div>
    </div>
  );
}
