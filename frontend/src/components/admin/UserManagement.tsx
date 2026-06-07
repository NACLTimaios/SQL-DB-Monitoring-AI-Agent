import { useState } from 'react';

export default function UserManagement() {
  const [activeSubTab, setActiveSubTab] = useState<'view' | 'create'>('view');

  // Mock user data - in production, fetch from API
  const users = [
    {
      id: 1,
      username: 'admin',
      roles: ['admin'],
      enabled: true,
      created_at: '2026-06-07T10:00:00Z',
    },
    {
      id: 2,
      username: 'dbadmin',
      roles: ['admin'],
      enabled: true,
      created_at: '2026-06-07T11:00:00Z',
    },
    {
      id: 3,
      username: 'viewer',
      roles: ['dashboard'],
      enabled: true,
      created_at: '2026-06-07T12:00:00Z',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Sub-tabs */}
      <div className="flex gap-2 border-b border-slate-700">
        <button
          onClick={() => setActiveSubTab('view')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeSubTab === 'view'
              ? 'border-b-2 border-cyan-500 text-cyan-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          👥 Users
        </button>
        <button
          onClick={() => setActiveSubTab('create')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeSubTab === 'create'
              ? 'border-b-2 border-cyan-500 text-cyan-400'
              : 'text-slate-400 hover:text-slate-300'
          }`}
        >
          ➕ Create User
        </button>
      </div>

      {activeSubTab === 'view' ? (
        // View Users
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">System Users</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-slate-400">Username</th>
                  <th className="text-left py-3 px-4 text-slate-400">Roles</th>
                  <th className="text-left py-3 px-4 text-slate-400">Status</th>
                  <th className="text-left py-3 px-4 text-slate-400">Created</th>
                  <th className="text-left py-3 px-4 text-slate-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-b border-slate-700/50 hover:bg-slate-800/30">
                    <td className="py-3 px-4 text-slate-200 font-medium">{user.username}</td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        {user.roles.map((role) => (
                          <span
                            key={role}
                            className={`px-2 py-1 rounded text-xs font-semibold ${
                              role === 'admin'
                                ? 'bg-red-900/30 text-red-400'
                                : 'bg-blue-900/30 text-blue-400'
                            }`}
                          >
                            {role}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold ${
                          user.enabled ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
                        }`}
                      >
                        {user.enabled ? '✓ Active' : '✗ Disabled'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <button className="text-blue-400 hover:text-blue-300 text-xs font-semibold">
                          Edit
                        </button>
                        <button className="text-red-400 hover:text-red-300 text-xs font-semibold">
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-slate-500 mt-4">
            💡 Tip: User management API endpoints coming soon. Currently, create new users through the database directly.
          </p>
        </div>
      ) : (
        // Create User Form
        <div className="max-w-md">
          <h3 className="text-lg font-semibold text-white mb-4">Create New User</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Username</label>
              <input
                type="text"
                placeholder="Enter username"
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
              <input
                type="password"
                placeholder="Enter password"
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Role</label>
              <select className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500">
                <option value="dashboard">Dashboard (Read-only)</option>
                <option value="admin">Admin (Full access)</option>
              </select>
            </div>

            <button className="w-full bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg font-semibold transition-colors">
              ✓ Create User
            </button>

            <p className="text-xs text-slate-500">
              🔒 User management API coming soon. Contact administrator for user creation.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
