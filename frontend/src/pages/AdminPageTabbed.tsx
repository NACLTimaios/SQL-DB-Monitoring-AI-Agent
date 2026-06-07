import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ChatbotSettings from '../components/admin/ChatbotSettings';
import UserManagement from '../components/admin/UserManagement';

export default function AdminPageTabbed() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'chatbot' | 'users'>('chatbot');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  const tabs = [
    { id: 'chatbot', label: '⚙️ Chatbot Settings', icon: 'chatbot' },
    { id: 'users', label: '👥 User Management', icon: 'users' },
  ] as const;

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
          {loading ? (
            <div className="text-center py-12">
              <p className="text-slate-400">Loading...</p>
            </div>
          ) : activeTab === 'chatbot' ? (
            <ChatbotSettings />
          ) : (
            <UserManagement />
          )}
        </div>
      </div>
    </div>
  );
}
