import React, { useState, useEffect } from 'react';
import GridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import AgentHealthPanel from './widgets/AgentHealthPanel';
import CapacityPanel from './widgets/CapacityPanel';
import PerformancePanel from './widgets/PerformancePanel';
import LocksPanel from './widgets/LocksPanel';
import DatabaseSummaryPanel from './widgets/DatabaseSummaryPanel';
import InsightsAlerts from './widgets/InsightsAlerts';
import ActivityFeed from './widgets/ActivityFeed';
import ChatBot from './ChatBot';

interface DashboardGridProps {
  healthData: any;
  agentStatus: any;
  dbSummary: any;
  insightsPending: any;
  activity: any;
}

export default function DashboardGrid({
  healthData,
  agentStatus,
  dbSummary,
  insightsPending,
  activity,
}: DashboardGridProps) {
  const [activeTab, setActiveTab] = useState<'metrics' | 'chatbot' | 'health'>('metrics');
  const [layout, setLayout] = useState<any[]>([
    { x: 0, y: 0, w: 2, h: 2, i: 'capacity', static: false },
    { x: 2, y: 0, w: 2, h: 2, i: 'performance', static: false },
    { x: 4, y: 0, w: 2, h: 2, i: 'locks', static: false },
    { x: 0, y: 2, w: 2, h: 2, i: 'database', static: false },
    { x: 2, y: 2, w: 2, h: 2, i: 'insights', static: false },
    { x: 4, y: 2, w: 2, h: 2, i: 'activity', static: false },
  ]);
  const [isEditMode, setIsEditMode] = useState(false);
  const [containerWidth, setContainerWidth] = useState(window.innerWidth - 32);

  // Load layout from localStorage
  useEffect(() => {
    const savedLayout = localStorage.getItem('dashboard-layout');
    if (savedLayout) {
      try {
        setLayout(JSON.parse(savedLayout));
      } catch (e) {
        console.error('Failed to load saved layout:', e);
      }
    }
  }, []);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      setContainerWidth(window.innerWidth - 32);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleLayoutChange = (newLayout: any[]) => {
    setLayout(newLayout);
    localStorage.setItem('dashboard-layout', JSON.stringify(newLayout));
  };

  const tabs = [
    { id: 'metrics', label: '📊 Metrics', icon: '📊' },
    { id: 'chatbot', label: '💬 Assistant', icon: '💬' },
    { id: 'health', label: '❤️ Agent Health', icon: '❤️' },
  ] as const;

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Tab Navigation */}
      <div className="border-b border-slate-700 bg-slate-900/50 backdrop-blur sticky top-20 z-40">
        <div className="px-4 flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-4 font-medium transition-all border-b-2 ${
                activeTab === tab.id
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
          <div className="flex-1" />
          {activeTab === 'metrics' && (
            <button
              onClick={() => setIsEditMode(!isEditMode)}
              className={`px-4 py-4 text-sm font-semibold transition-colors ${
                isEditMode
                  ? 'bg-green-600/20 text-green-400 hover:bg-green-600/30'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              {isEditMode ? '✓ Done' : '✏️ Edit'}
            </button>
          )}
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-4">
        {/* Metrics Tab */}
        {activeTab === 'metrics' && (
          <div>
            {React.createElement(GridLayout as any, {
              className: 'layout',
              layout,
              onLayoutChange: handleLayoutChange,
              cols: 6,
              rowHeight: 100,
              width: containerWidth,
              isDraggable: isEditMode,
              isResizable: isEditMode,
              containerPadding: [0, 0],
              margin: [16, 16],
            } as any,
              <div key="capacity" className="grid-item">
                <CapacityPanel insights={insightsPending?.capacity} />
              </div>,
              <div key="performance" className="grid-item">
                <PerformancePanel insights={insightsPending?.performance} />
              </div>,
              <div key="locks" className="grid-item">
                <LocksPanel insights={insightsPending?.locks} />
              </div>,
              <div key="database" className="grid-item">
                <DatabaseSummaryPanel summary={dbSummary} />
              </div>,
              <div key="insights" className="grid-item">
                <InsightsAlerts insights={insightsPending} />
              </div>,
              <div key="activity" className="grid-item">
                <ActivityFeed activity={activity} />
              </div>
            )}
          </div>
        )}

        {/* Chatbot Tab */}
        {activeTab === 'chatbot' && (
          <div className="max-w-6xl mx-auto">
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-lg" style={{ minHeight: 'calc(100vh - 250px)' }}>
              <ChatBot />
            </div>
          </div>
        )}

        {/* Agent Health Tab */}
        {activeTab === 'health' && (
          <div className="max-w-6xl mx-auto space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-6 shadow-lg">
                <h2 className="text-lg font-semibold text-slate-200 mb-4">Agent Status</h2>
                <AgentHealthPanel agentStatus={agentStatus} healthData={healthData} />
              </div>

              <div className="space-y-4">
                <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-6 shadow-lg">
                  <h2 className="text-lg font-semibold text-slate-200 mb-4">System Status</h2>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Orchestrator</span>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        healthData?.orchestrator_running
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-red-900/30 text-red-400'
                      }`}>
                        {healthData?.orchestrator_running ? '✓ Running' : '✗ Stopped'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Database Connection</span>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        healthData?.db_connected
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-red-900/30 text-red-400'
                      }`}>
                        {healthData?.db_connected ? '✓ Connected' : '✗ Disconnected'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Overall Status</span>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        healthData?.status === 'ok' || healthData?.status === 'healthy'
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-yellow-900/30 text-yellow-400'
                      }`}>
                        {healthData?.status?.toUpperCase() || 'UNKNOWN'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl p-6 shadow-lg">
                  <h2 className="text-lg font-semibold text-slate-200 mb-4">Domain Execution</h2>
                  <div className="space-y-2 text-sm text-slate-400">
                    <p>Last cycle: <span className="text-slate-200 font-mono text-xs">{agentStatus?.last_cycle ? new Date(agentStatus.last_cycle).toLocaleTimeString() : 'Unknown'}</span></p>
                    <p>Domains: <span className="text-slate-200">{agentStatus?.domains_executed?.join(', ') || 'None'}</span></p>
                    <p>Pending actions: <span className="text-slate-200 font-semibold">{agentStatus?.queue_size || 0}</span></p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        :global(.react-grid-layout) {
          background: transparent;
          width: 100%;
        }
        :global(.react-grid-item) {
          background: transparent;
          border: none;
          overflow: hidden;
        }
        :global(.react-grid-item > div) {
          width: 100%;
          height: 100%;
          overflow: hidden;
        }
        :global(.react-grid-item.react-grid-placeholder) {
          background: rgba(34, 197, 94, 0.2);
          border: 2px dashed rgba(34, 197, 94, 0.5);
          border-radius: 8px;
        }
        :global(.react-grid-item > .resizing) {
          opacity: 0.9;
          z-index: 3;
        }
        :global(.dragging) {
          opacity: 0.3;
          background: rgba(59, 130, 246, 0.1);
          z-index: 3;
        }
        :global(.react-grid-placeholder) {
          background: rgba(59, 130, 246, 0.2);
          opacity: 0.2;
          border-radius: 3px;
          z-index: 2;
          border: none;
        }
      `}</style>
    </div>
  );
}
