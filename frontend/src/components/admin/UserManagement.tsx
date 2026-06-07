import { useState, useEffect } from 'react';
import axios from 'axios';

interface User {
  id: number;
  username: string;
  enabled: boolean;
  roles: string[];
  created_at?: string;
}

export default function UserManagement() {
  const [activeSubTab, setActiveSubTab] = useState<'view' | 'create'>('view');
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Form state
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    role: 'dashboard',
  });
  const [creating, setCreating] = useState(false);

  // Fetch users on mount and when tab changes
  useEffect(() => {
    if (activeSubTab === 'view') {
      fetchUsers();
    }
  }, [activeSubTab]);

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('/api/users', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setUsers(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleCreateUser = async () => {
    setCreating(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.post('/api/users', formData, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setSuccess(`✓ User '${response.data.username}' created successfully`);
      setFormData({ username: '', password: '', role: 'dashboard' });

      // Refresh users list
      setTimeout(() => {
        fetchUsers();
        setActiveSubTab('view');
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create user');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteUser = async (userId: number, username: string) => {
    if (!confirm(`Are you sure you want to delete user '${username}'?`)) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      await axios.delete(`/api/users/${userId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setSuccess(`✓ User '${username}' deleted successfully`);
      fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete user');
    }
  };

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

      {/* Error/Success Messages */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-400 text-sm">
          ❌ {error}
        </div>
      )}
      {success && (
        <div className="bg-green-900/30 border border-green-700 rounded-lg p-3 text-green-400 text-sm">
          {success}
        </div>
      )}

      {activeSubTab === 'view' ? (
        // View Users
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">System Users</h3>
          {loading ? (
            <div className="text-slate-400">Loading users...</div>
          ) : users.length === 0 ? (
            <div className="text-slate-400">No users found</div>
          ) : (
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
                        {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          <button className="text-blue-400 hover:text-blue-300 text-xs font-semibold">
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteUser(user.id, user.username)}
                            className="text-red-400 hover:text-red-300 text-xs font-semibold"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-xs text-slate-500 mt-4">
            💡 Tip: Use the "Create User" tab to add new users to the system.
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
                name="username"
                placeholder="Enter username"
                value={formData.username}
                onChange={handleInputChange}
                disabled={creating}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
              <input
                type="password"
                name="password"
                placeholder="Enter password"
                value={formData.password}
                onChange={handleInputChange}
                disabled={creating}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Role</label>
              <select
                name="role"
                value={formData.role}
                onChange={handleInputChange}
                disabled={creating}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
              >
                <option value="dashboard">Dashboard (Read-only)</option>
                <option value="admin">Admin (Full access)</option>
              </select>
            </div>

            <button
              onClick={handleCreateUser}
              disabled={creating || !formData.username || !formData.password}
              className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg font-semibold transition-colors"
            >
              {creating ? '⏳ Creating...' : '✓ Create User'}
            </button>

            <p className="text-xs text-slate-500">
              🔒 All passwords are securely hashed with Argon2 encryption.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
