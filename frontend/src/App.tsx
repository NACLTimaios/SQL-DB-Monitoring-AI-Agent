import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import AdminPage from './pages/AdminPage';
import ChatBot from './components/ChatBot';
import Login from './components/Login';
import Header from './components/Header';
import AgentHealthPanel from './components/AgentHealthPanel';
import CapacityPanel from './components/CapacityPanel';
import PerformancePanel from './components/PerformancePanel';
import LocksPanel from './components/LocksPanel';
import DatabaseSummaryPanel from './components/DatabaseSummaryPanel';
import InsightsAlerts from './components/InsightsAlerts';
import ActivityFeed from './components/ActivityFeed';
import IncidentsTimeline from './components/IncidentsTimeline';
import HITLApprovalQueue from './components/HITLApprovalQueue';
import {
  fetchHealth,
  fetchAgentStatus,
  fetchDatabaseSummary,
  fetchInsightsPending,
  fetchActivity,
} from './utils/api';
import type {
  HealthResponse,
  AgentStatusResponse,
  DatabaseSummaryResponse,
  InsightsPendingResponse,
  ActivityEvent,
} from './types/api';

function DashboardContent({
  healthData,
  agentStatus,
  dbSummary,
  insightsPending,
  activity,
  isRunning,
  isDbConnected,
  status,
}: {
  healthData: HealthResponse | null;
  agentStatus: AgentStatusResponse | null;
  dbSummary: DatabaseSummaryResponse | null;
  insightsPending: InsightsPendingResponse | null;
  activity: ActivityEvent[];
  isRunning: boolean;
  isDbConnected: boolean;
  status: string;
}) {
  return (
    <div className="min-h-screen bg-[#0a0e1a] text-gray-100 pb-12">
      <Header
        status={status}
        lastCycle={agentStatus?.last_cycle ?? ''}
        isRunning={isRunning}
      />

      <main className="max-w-screen-2xl mx-auto px-4 py-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <AgentHealthPanel
            agentStatus={agentStatus}
            isDbConnected={isDbConnected}
            isOrchestratorRunning={isRunning}
          />
          <CapacityPanel insights={insightsPending?.capacity ?? null} />
          <PerformancePanel insights={insightsPending?.performance ?? null} />
          <LocksPanel insights={insightsPending?.locks ?? null} />
          <DatabaseSummaryPanel summary={dbSummary} />
          <ChatBot />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <InsightsAlerts insights={insightsPending} />
          <ActivityFeed activity={activity} />
        </div>

        <IncidentsTimeline />
      </main>

      <HITLApprovalQueue />
    </div>
  );
}

function AppRoutes({
  authenticated,
  healthData,
  agentStatus,
  dbSummary,
  insightsPending,
  activity,
  isRunning,
  isDbConnected,
  status,
  onLoginSuccess,
}: {
  authenticated: boolean;
  healthData: HealthResponse | null;
  agentStatus: AgentStatusResponse | null;
  dbSummary: DatabaseSummaryResponse | null;
  insightsPending: InsightsPendingResponse | null;
  activity: ActivityEvent[];
  isRunning: boolean;
  isDbConnected: boolean;
  status: string;
  onLoginSuccess: () => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();

  if (!authenticated) {
    return (
      <Routes>
        <Route path="*" element={<Login onLoginSuccess={onLoginSuccess} />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          <DashboardContent
            healthData={healthData}
            agentStatus={agentStatus}
            dbSummary={dbSummary}
            insightsPending={insightsPending}
            activity={activity}
            isRunning={isRunning}
            isDbConnected={isDbConnected}
            status={status}
          />
        }
      />
      <Route path="/admin" element={<AdminPage />} />
    </Routes>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(() => !!localStorage.getItem('token'));
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatusResponse | null>(null);
  const [dbSummary, setDbSummary] = useState<DatabaseSummaryResponse | null>(null);
  const [insightsPending, setInsightsPending] = useState<InsightsPendingResponse | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);

  const handleLoginSuccess = () => {
    setAuthenticated(true);
  };

  const refreshHealth = useCallback(async () => {
    const data = await fetchHealth();
    if (data) setHealthData(data);
  }, []);

  const refreshAgentStatus = useCallback(async () => {
    const data = await fetchAgentStatus();
    if (data) setAgentStatus(data);
  }, []);

  const refreshDbSummary = useCallback(async () => {
    const data = await fetchDatabaseSummary(1);
    if (data) setDbSummary(data);
  }, []);

  const refreshInsights = useCallback(async () => {
    const data = await fetchInsightsPending();
    if (data) setInsightsPending(data);
  }, []);

  const refreshActivity = useCallback(async () => {
    const data = await fetchActivity(30);
    if (data) setActivity(data);
  }, []);

  useEffect(() => {
    if (!authenticated) return;

    refreshHealth();
    refreshAgentStatus();
    refreshInsights();
    refreshActivity();
    refreshDbSummary();

    const healthInterval = setInterval(refreshHealth, 30_000);
    const agentInterval = setInterval(refreshAgentStatus, 30_000);
    const insightsInterval = setInterval(refreshInsights, 10_000);
    const activityInterval = setInterval(refreshActivity, 30_000);
    const dbInterval = setInterval(refreshDbSummary, 60_000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(agentInterval);
      clearInterval(insightsInterval);
      clearInterval(activityInterval);
      clearInterval(dbInterval);
    };
  }, [authenticated, refreshHealth, refreshAgentStatus, refreshInsights, refreshActivity, refreshDbSummary]);

  const isRunning = healthData?.orchestrator_running ?? false;
  const isDbConnected = healthData?.db_connected ?? false;
  const status = healthData?.status ?? 'unknown';

  return (
    <BrowserRouter>
      <AppRoutes
        authenticated={authenticated}
        healthData={healthData}
        agentStatus={agentStatus}
        dbSummary={dbSummary}
        insightsPending={insightsPending}
        activity={activity}
        isRunning={isRunning}
        isDbConnected={isDbConnected}
        status={status}
        onLoginSuccess={handleLoginSuccess}
      />
    </BrowserRouter>
  );
}
