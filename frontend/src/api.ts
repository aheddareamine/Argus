// API client — all typed fetch wrappers for Argus backend endpoints

import type { GraphResponse, Incident, PipelineResponse, Scenario } from './types';

const BASE = import.meta.env.VITE_API_URL ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status} on ${path}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** GET /graph — nodes, edges, health status */
  getGraph(): Promise<GraphResponse> {
    return request<GraphResponse>('/graph');
  },

  /** GET /incidents — all active incidents */
  getIncidents(): Promise<Incident[]> {
    return request<Incident[]>('/incidents');
  },

  /** GET /incidents/:id — single incident detail */
  getIncident(id: string): Promise<Incident> {
    return request<Incident>(`/incidents/${id}`);
  },

  /** POST /demo/:scenario — switch demo state, returns updated graph */
  switchDemo(scenario: Scenario): Promise<GraphResponse> {
    return request<GraphResponse>(`/demo/${scenario}`, { method: 'POST' });
  },

  /** POST /sync — pull real data from connectors */
  sync(): Promise<GraphResponse> {
    return request<GraphResponse>('/sync', { method: 'POST' });
  },

  /** GET /pipeline/:projectId — dynamic topology from CLI */
  getPipeline(projectId = 'default'): Promise<PipelineResponse> {
    return request<PipelineResponse>(`/pipeline/${projectId}`);
  },
};
