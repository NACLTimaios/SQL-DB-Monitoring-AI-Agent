export interface HealthResponse {
  status: string;
  orchestrator_running: boolean;
  db_connected: boolean;
  timestamp: string;
}

export interface AgentStatusResponse {
  last_cycle: string;
  domains_executed: string[];
  tools_executed: string[];
  queue_size: number;
  status: string;
}

export interface DatabaseSummaryResponse {
  db_id: string;
  connections: number;
  connections_max: number;
  connections_pct: number;
  query_latency_ms: {
    p50: number;
    p95: number;
    p99: number;
  };
  disk_size_gb: number;
  disk_free_gb: number;
  disk_trend_gb_per_day: number;
  ram_pct: number;
}

export interface InsightsPendingResponse {
  capacity: any[];
  performance: any[];
  locks: any[];
  total_pending: number;
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  type: string;
  title: string;
  description: string;
}
