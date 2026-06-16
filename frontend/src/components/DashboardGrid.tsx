import React, { useState, useEffect, useRef } from 'react';
import GridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import AgentHealthPanel from './widgets/AgentHealthPanel';
import CapacityPanel from './widgets/CapacityPanel';
import LocksPanel from './widgets/LocksPanel';
import DatabaseSummaryPanel from './widgets/DatabaseSummaryPanel';
import InsightsAlerts from './widgets/InsightsAlerts';
import ActivityFeed from './widgets/ActivityFeed';
import PerformanceMetrics from './widgets/PerformanceMetrics';
import ChatBot from './ChatBot';
import ChatbotInfoBox from './ChatbotInfoBox';
import PrismaAirsToggle from './PrismaAirsToggle';

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
    { x: 0, y: 0, w: 2, h: 1, i: 'capacity', static: false },
    { x: 2, y: 0, w: 2, h: 1, i: 'locks', static: false },
    { x: 4, y: 0, w: 2, h: 1, i: 'database', static: false },
    { x: 0, y: 1, w: 2, h: 1, i: 'insights', static: false },
    { x: 2, y: 1, w: 4, h: 1, i: 'activity', static: false },
    { x: 0, y: 2, w: 6, h: 1, i: 'performance', static: false },
  ]);
  const [isEditMode, setIsEditMode] = useState(false);
  const [containerWidth, setContainerWidth] = useState(1200);
  const [rowHeight, setRowHeight] = useState(250);
  const [prismaAirsEnabled, setPrismaAirsEnabled] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const metricsContainerRef = useRef<HTMLDivElement>(null);

  // Load layout from localStorage and measure container
  useEffect(() => {
    const savedLayout = localStorage.getItem('dashboard-layout');
    if (savedLayout) {
      try {
        setLayout(JSON.parse(savedLayout));
      } catch (e) {
        console.error('Failed to load saved layout:', e);
      }
    }

    // Measure container width on mount
    if (containerRef.current) {
      setContainerWidth(containerRef.current.offsetWidth);
    }
  }, []);

  // Scroll to top when tab changes
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [activeTab]);

  // Handle window resize - update width and calculate row height
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth);
      }

      // Calculate available height for the metrics grid
      if (metricsContainerRef.current) {
        const header = document.querySelector('header') as HTMLElement;
        const tabNav = document.querySelector('.tab-nav') as HTMLElement;
        const headerHeight = header?.offsetHeight || 72;
        const tabHeight = tabNav?.offsetHeight || 52;
        const paddingAndMargins = 48 + 32; // p-6 (24*2) + grid margins (16*2)

        const availableHeight = window.innerHeight - headerHeight - tabHeight - paddingAndMargins;
        // Grid has 3 rows (3 x rowHeight) with 2 gaps of 16px = 32px
        // availableHeight = 3 * rowHeight + 32
        const calculatedRowHeight = Math.max(150, (availableHeight - 32) / 3);
        setRowHeight(calculatedRowHeight);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleLayoutChange = (newLayout: any[]) => {
    setLayout(newLayout);
    localStorage.setItem('dashboard-layout', JSON.stringify(newLayout));
  };

  const tabs = [
    { id: 'metrics', label: 'Metrics' },
    { id: 'chatbot', label: 'Assistant' },
    { id: 'health', label: 'Agent Health' },
  ] as const;

  return (
    <div className="h-full flex flex-col bg-slate-900">
      {/* Tab Navigation */}
      <div className="border-b border-slate-700 bg-slate-900/50 backdrop-blur z-40 flex-shrink-0 tab-nav">
        <div className="px-6 flex gap-8 items-center">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-0 py-4 text-sm font-medium transition-all border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
          {activeTab === 'metrics' && (
            <>
              <div className="flex-1" />
              <button
                onClick={() => setIsEditMode(!isEditMode)}
                className={`px-3 py-2 text-xs font-medium rounded transition-colors ${
                  isEditMode
                    ? 'bg-green-600/30 text-green-400 hover:bg-green-600/40'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                {isEditMode ? 'Done Editing' : 'Edit Layout'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tab Content - Metrics and Health */}
      {(activeTab === 'metrics' || activeTab === 'health') && (
        <div ref={containerRef} className="p-6 max-w-full overflow-x-hidden flex flex-col flex-1 min-h-0">
          {/* Metrics Tab */}
          {activeTab === 'metrics' && (
            <div ref={metricsContainerRef} style={{ width: containerWidth, flex: 1, minHeight: 0 }}>
              {React.createElement(GridLayout as any, {
                className: 'layout',
                layout,
                onLayoutChange: handleLayoutChange,
                cols: 6,
                rowHeight: rowHeight,
                width: containerWidth,
                isDraggable: isEditMode,
                isResizable: isEditMode,
                containerPadding: [0, 0],
                margin: [16, 16],
                compactType: 'vertical',
                preventCollision: false,
              } as any,
                <div key="capacity" className="grid-item">
                  <CapacityPanel insights={insightsPending?.capacity} />
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
                </div>,
                <div key="performance" className="grid-item">
                  <PerformanceMetrics />
                </div>
              )}
            </div>
          )}

          {/* Agent Health Tab */}
          {activeTab === 'health' && (
            <div className="w-full flex-1 min-h-0 flex flex-col gap-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-shrink-0">
                {/* Agent Status */}
                <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6 shadow-lg overflow-hidden flex flex-col h-96">
                  <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wide flex-shrink-0">Agent Status</h2>
                  <div className="flex-1 min-h-0 overflow-hidden">
                    <AgentHealthPanel agentStatus={agentStatus} healthData={healthData} />
                  </div>
                </div>

                {/* System Status */}
                <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6 shadow-lg flex flex-col h-96">
                  <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wide flex-shrink-0">System Status</h2>
                  <div className="space-y-4 flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">Orchestrator</span>
                      <span className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                        healthData?.orchestrator_running
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-red-900/30 text-red-400'
                      }`}>
                        {healthData?.orchestrator_running ? 'Running' : 'Stopped'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">Database Connection</span>
                      <span className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                        healthData?.db_connected
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-red-900/30 text-red-400'
                      }`}>
                        {healthData?.db_connected ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">Overall Status</span>
                      <span className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                        healthData?.status === 'ok' || healthData?.status === 'healthy'
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-yellow-900/30 text-yellow-400'
                      }`}>
                        {healthData?.status?.toUpperCase() || 'UNKNOWN'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Domain Execution */}
              <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-lg p-6 shadow-lg flex-shrink-0">
                <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wide">Domain Execution</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Last Cycle</p>
                    <p className="text-sm font-mono text-slate-200">
                      {agentStatus?.last_cycle ? new Date(agentStatus.last_cycle).toLocaleTimeString() : 'Unknown'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Active Domains</p>
                    <p className="text-sm text-slate-200">{agentStatus?.domains_executed?.join(', ') || 'None'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">Pending Actions</p>
                    <p className="text-sm font-semibold text-cyan-400">{agentStatus?.queue_size || 0}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Chatbot Tab - With Info Box */}
      {activeTab === 'chatbot' && (
        <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
          <div className="p-6 flex gap-6 flex-1 min-h-0">
            {/* Chatbot - Takes 70% of space */}
            <div className="flex-1 min-w-0">
              <ChatBot />
            </div>
            {/* Info Box and Controls - Takes 30% of space */}
            <div className="w-56 flex-shrink-0 flex flex-col gap-4 min-h-0">
              {/* Prisma AIRS Toggle Button */}
              <PrismaAirsToggle
                enabled={prismaAirsEnabled}
                onToggle={setPrismaAirsEnabled}
              />
              {/* Info Box */}
              <div className="flex-1 min-h-0 overflow-hidden">
                <ChatbotInfoBox />
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        :global(.react-grid-layout) {
          background: transparent;
          width: 100%;
          height: 100%;
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
