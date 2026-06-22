import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AdminPageTabbed from './pages/AdminPageTabbed';
import DashboardGrid from './components/DashboardGrid';
import Login from './components/Login';
import Header from './components/Header';
import {
  fetchHealth,
  fetchAgentStatus,
  fetchDatabaseSummary,
  fetchInsightsPending,
  fetchActivity,
  forceSignOut,
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
  status,
}: {
  healthData: HealthResponse | null;
  agentStatus: AgentStatusResponse | null;
  dbSummary: DatabaseSummaryResponse | null;
  insightsPending: InsightsPendingResponse | null;
  activity: ActivityEvent[];
  isRunning: boolean;
  status: string;
}) {
  return (
    <div className="h-screen flex flex-col bg-slate-900 text-slate-100 overflow-hidden">
      <Header
        status={status}
        lastCycle={agentStatus?.last_cycle ?? ''}
        isRunning={isRunning}
      />

      <main className="flex-1 min-h-0 overflow-hidden">
        <DashboardGrid
          healthData={healthData}
          agentStatus={agentStatus}
          dbSummary={dbSummary}
          insightsPending={insightsPending}
          activity={activity}
        />
      </main>
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
  status: string;
  onLoginSuccess: () => void;
}) {

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
            status={status}
          />
        }
      />
      <Route path="/admin" element={<AdminPageTabbed />} />
    </Routes>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(() => !!localStorage.getItem('access_token'));
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatusResponse | null>(null);
  const [dbSummary, setDbSummary] = useState<DatabaseSummaryResponse | null>(null);
  const [insightsPending, setInsightsPending] = useState<InsightsPendingResponse | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);

  const handleLoginSuccess = () => {
    setAuthenticated(true);
  };

  // Reflect forced sign-outs (session expiry, inactivity) in React state so the
  // Login page is shown immediately, even while sitting on the dashboard ("/").
  useEffect(() => {
    const onSignout = () => setAuthenticated(false);
    window.addEventListener('app:signout', onSignout);
    return () => window.removeEventListener('app:signout', onSignout);
  }, []);

  // Auto sign-out after 20 minutes of inactivity. Any user activity resets the
  // timer; only genuine inactivity triggers the logout and returns to Sign In.
  useEffect(() => {
    if (!authenticated) return;
    const INACTIVITY_MS = 20 * 60 * 1000;
    let timer: number;
    const signOut = () =>
      forceSignOut('You were signed out after 20 minutes of inactivity.');
    const resetTimer = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(signOut, INACTIVITY_MS);
    };
    // Throttle resets so frequent events (mousemove) don't thrash the timer.
    let lastReset = 0;
    const onActivity = () => {
      const now = Date.now();
      if (now - lastReset > 1000) {
        lastReset = now;
        resetTimer();
      }
    };
    const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    resetTimer();
    return () => {
      window.clearTimeout(timer);
      events.forEach((e) => window.removeEventListener(e, onActivity));
    };
  }, [authenticated]);

  // Browser tab: keep "Sign In" (neutral) on the auth page; show the SELECTer
  // name + logo only after login so the brand isn't exposed on the public login page.
  useEffect(() => {
    document.title = authenticated ? 'SELECTer' : 'Sign In';

    let icon = document.querySelector<HTMLLinkElement>("link[rel='icon']");
    if (!icon) {
      icon = document.createElement('link');
      icon.rel = 'icon';
      document.head.appendChild(icon);
    }
    icon.type = 'image/svg+xml';
    icon.href = authenticated ? '/selecter.svg' : '/vite.svg';
  }, [authenticated]);

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
        status={status}
        onLoginSuccess={handleLoginSuccess}
      />
    </BrowserRouter>
  );
}
