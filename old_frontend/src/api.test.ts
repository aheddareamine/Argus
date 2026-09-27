// Unit tests for the API client

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { GraphResponse, Incident } from './types';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Mock import.meta.env
vi.stubGlobal('import', { meta: { env: { VITE_API_URL: 'http://localhost:8000' } } });

function makeGraphResponse(scenario = 'healthy'): GraphResponse {
  return {
    nodes: [
      { id: 'build',    label: 'Build',    health: 'HEALTHY' },
      { id: 'backend',  label: 'Backend',  health: 'FAILING' },
    ],
    edges: [{ source: 'build', target: 'backend' }],
    scenario: scenario as 'healthy' | 'incident',
    incident_count: 1,
  };
}

function makeIncident(): Incident {
  return {
    id: 'inc-001',
    service: 'backend',
    severity: 'critical',
    status: 'active',
    start_time: '2026-09-25T14:20:00',
    possible_cause: 'Deploy failure',
    evidence: ['Deployment failed'],
    explanation: '',
    events: [
      {
        id: 'evt-001',
        timestamp: '2026-09-25T14:20:00',
        source: 'github_actions',
        service: 'deploy',
        event_type: 'DEPLOY_FAILED',
        status: 'critical',
        details: {},
      },
    ],
  };
}

function mockSuccess(data: unknown, status = 200): void {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
}

beforeEach(() => {
  vi.resetModules();
  mockFetch.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('api.getGraph', () => {
  it('calls GET /graph', async () => {
    mockSuccess(makeGraphResponse());
    const { api } = await import('./api');
    await api.getGraph();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/graph'),
      expect.objectContaining({ headers: expect.any(Object) }),
    );
  });

  it('returns typed GraphResponse', async () => {
    const response = makeGraphResponse('incident');
    mockSuccess(response);
    const { api } = await import('./api');
    const result = await api.getGraph();
    expect(result.nodes).toHaveLength(2);
    expect(result.scenario).toBe('incident');
    expect(result.nodes[0].health).toBe('HEALTHY');
  });
});

describe('api.getIncidents', () => {
  it('calls GET /incidents', async () => {
    mockSuccess([makeIncident()]);
    const { api } = await import('./api');
    await api.getIncidents();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/incidents'),
      expect.any(Object),
    );
  });

  it('returns array of incidents', async () => {
    mockSuccess([makeIncident()]);
    const { api } = await import('./api');
    const result = await api.getIncidents();
    expect(Array.isArray(result)).toBe(true);
    expect(result[0].service).toBe('backend');
    expect(result[0].severity).toBe('critical');
  });
});

describe('api.getIncident', () => {
  it('calls GET /incidents/:id', async () => {
    const inc = makeIncident();
    mockSuccess(inc);
    const { api } = await import('./api');
    await api.getIncident('inc-001');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/incidents/inc-001'),
      expect.any(Object),
    );
  });

  it('returns single incident', async () => {
    mockSuccess(makeIncident());
    const { api } = await import('./api');
    const result = await api.getIncident('inc-001');
    expect(result.id).toBe('inc-001');
    expect(result.events).toHaveLength(1);
    expect(result.events[0].event_type).toBe('DEPLOY_FAILED');
  });
});

describe('api.switchDemo', () => {
  it('calls POST /demo/incident', async () => {
    mockSuccess(makeGraphResponse('incident'));
    const { api } = await import('./api');
    await api.switchDemo('incident');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/demo/incident'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('calls POST /demo/healthy', async () => {
    mockSuccess(makeGraphResponse('healthy'));
    const { api } = await import('./api');
    await api.switchDemo('healthy');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/demo/healthy'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('returns updated graph', async () => {
    mockSuccess(makeGraphResponse('incident'));
    const { api } = await import('./api');
    const result = await api.switchDemo('incident');
    expect(result.scenario).toBe('incident');
    expect(result.incident_count).toBe(1);
  });
});

describe('api error handling', () => {
  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal Server Error'),
    });
    const { api } = await import('./api');
    await expect(api.getGraph()).rejects.toThrow('API 500');
  });

  it('throws on 404', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve('Not found'),
    });
    const { api } = await import('./api');
    await expect(api.getIncident('bad-id')).rejects.toThrow('API 404');
  });
});
