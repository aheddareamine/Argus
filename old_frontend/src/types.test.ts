// Unit tests for TypeScript types and API client shape

import { describe, it, expect } from 'vitest';
import type { GraphResponse, Incident, HealthStatus } from './types';

// ── Type guard helpers ────────────────────────────────────────────────────────
function isHealthStatus(val: unknown): val is HealthStatus {
  return ['HEALTHY', 'DEGRADED', 'FAILING', 'UNKNOWN'].includes(val as string);
}

function isGraphResponse(obj: unknown): obj is GraphResponse {
  if (typeof obj !== 'object' || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.nodes) &&
    Array.isArray(o.edges) &&
    typeof o.scenario === 'string'
  );
}

function isIncident(obj: unknown): obj is Incident {
  if (typeof obj !== 'object' || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === 'string' &&
    typeof o.service === 'string' &&
    typeof o.severity === 'string' &&
    typeof o.status === 'string' &&
    typeof o.possible_cause === 'string' &&
    Array.isArray(o.evidence) &&
    Array.isArray(o.events)
  );
}

// ── Type tests ────────────────────────────────────────────────────────────────
describe('HealthStatus type', () => {
  it('accepts all four valid values', () => {
    const values: HealthStatus[] = ['HEALTHY', 'DEGRADED', 'FAILING', 'UNKNOWN'];
    values.forEach(v => expect(isHealthStatus(v)).toBe(true));
  });

  it('rejects invalid values', () => {
    expect(isHealthStatus('OK')).toBe(false);
    expect(isHealthStatus('CRITICAL')).toBe(false);
    expect(isHealthStatus('')).toBe(false);
    expect(isHealthStatus(null)).toBe(false);
  });
});

describe('GraphResponse shape', () => {
  it('validates a correct graph response', () => {
    const resp: GraphResponse = {
      nodes: [{ id: 'backend', label: 'Backend', health: 'HEALTHY' }],
      edges: [{ source: 'deploy', target: 'backend' }],
      scenario: 'healthy',
    };
    expect(isGraphResponse(resp)).toBe(true);
  });

  it('rejects missing nodes', () => {
    expect(isGraphResponse({ edges: [], scenario: 'healthy' })).toBe(false);
  });

  it('rejects missing scenario', () => {
    expect(isGraphResponse({ nodes: [], edges: [] })).toBe(false);
  });
});

describe('Incident shape', () => {
  it('validates a correct incident', () => {
    const inc: Incident = {
      id: 'inc-001',
      service: 'backend',
      severity: 'critical',
      status: 'active',
      start_time: '2026-09-25T14:20:00',
      possible_cause: 'Deploy failure',
      evidence: ['Deployment failed', 'Pod crashed'],
      explanation: '',
      events: [],
    };
    expect(isIncident(inc)).toBe(true);
  });

  it('requires all mandatory fields', () => {
    expect(isIncident({ id: 'x' })).toBe(false);
    expect(isIncident(null)).toBe(false);
    expect(isIncident({})).toBe(false);
  });
});
