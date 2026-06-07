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
  const [layout, setLayout] = useState<any[]>([
    { x: 0, y: 0, w: 2, h: 2, i: 'health', static: false },
    { x: 2, y: 0, w: 2, h: 2, i: 'capacity', static: false },
    { x: 4, y: 0, w: 2, h: 2, i: 'performance', static: false },
    { x: 0, y: 2, w: 2, h: 2, i: 'locks', static: false },
    { x: 2, y: 2, w: 2, h: 2, i: 'database', static: false },
    { x: 4, y: 2, w: 2, h: 2, i: 'insights', static: false },
    { x: 0, y: 4, w: 6, h: 3, i: 'chatbot', static: false },
    { x: 0, y: 7, w: 6, h: 2, i: 'activity', static: false },
  ]);
  const [isEditMode, setIsEditMode] = useState(false);

  // Load layout from localStorage or user profile
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

  const handleLayoutChange = (newLayout: any[]) => {
    setLayout(newLayout);
    localStorage.setItem('dashboard-layout', JSON.stringify(newLayout));
  };

  return (
    <div className="min-h-screen bg-slate-900 p-4">
      <div className="mb-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <button
          onClick={() => setIsEditMode(!isEditMode)}
          className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
            isEditMode
              ? 'bg-green-600 hover:bg-green-500 text-white'
              : 'bg-slate-700 hover:bg-slate-600 text-slate-100'
          }`}
        >
          {isEditMode ? '✓ Done Editing' : '✏️ Customize Layout'}
        </button>
      </div>

      {React.createElement(GridLayout as any, {
        className: 'layout',
        layout,
        onLayoutChange: handleLayoutChange,
        cols: 6,
        rowHeight: 100,
        width: 1200,
        isDraggable: isEditMode,
        isResizable: isEditMode,
      } as any,
        <div key="health" className="grid-item">
          <AgentHealthPanel agentStatus={agentStatus} healthData={healthData} />
        </div>,
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
        <div key="chatbot" className="grid-item">
          <ChatBot />
        </div>,
        <div key="activity" className="grid-item">
          <ActivityFeed activity={activity} />
        </div>
      )}

      <style>{`
        :global(.react-grid-layout) {
          background: transparent;
        }
        :global(.react-grid-item) {
          background: transparent;
          border: none;
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
        :global(.react-grid-item.static) {
          background: #cce;
        }
        :global(.react-grid-item.text) {
          padding: 0;
          font-size: 24px;
          line-height: 1;
        }
        :global(.react-grid-item.no-drag) {
          height: 80px;
          line-height: 80px;
        }
        :global(.react-grid-item.minMax) {
          font-size: 12px;
        }
        :global(.react-grid-item.add) {
          cursor: pointer;
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
