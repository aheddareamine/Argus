// Shared TypeScript types — mirrors the Pydantic models in backend/models/

export type HealthStatus = 'HEALTHY' | 'DEGRADED' | 'FAILING' | 'UNKNOWN';
export type Severity = 'critical' | 'warning';
export type IncidentStatus = 'active' | 'resolved';
export type Scenario = 'healthy' | 'incident' | 'live';
export type ConnectorType = 'github_actions' | 'docker' | 'kubernetes' | 'prometheus' | 'generic';

export interface GraphNode {
  id: string;
  label: string;
  health: HealthStatus;
  // CLI-mode extras (optional — not present in demo mode)
  stage?: string;
  connector?: ConnectorType;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  scenario: Scenario;
  incident_count?: number;
}

// Pipeline layout returned by GET /pipeline/{project_id}
export interface PipelineStage {
  id: string;
  label: string;
  weight: number;
  icon: string;
  connector: ConnectorType;
  services: string[];
  status: string;
}

export interface PipelineResponse {
  project_id: string;
  stages: PipelineStage[];
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ArgusEvent {
  id: string;
  timestamp: string;
  source: string;
  service: string;
  event_type: string;
  status: string;
  details: Record<string, unknown>;
}

export interface Incident {
  id: string;
  service: string;
  severity: Severity;
  status: IncidentStatus;
  start_time: string;
  possible_cause: string;
  evidence: string[];
  explanation: string;
  events: ArgusEvent[];
}
