// API client — all typed fetch wrappers for Argus backend endpoints
const BASE = import.meta.env.VITE_API_URL ?? '';
async function request(path, init) {
    const res = await fetch(`${BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...init,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API ${res.status} on ${path}: ${text}`);
    }
    return res.json();
}
export const api = {
    /** GET /graph — nodes, edges, health status */
    getGraph() {
        return request('/graph');
    },
    /** GET /incidents — all active incidents */
    getIncidents() {
        return request('/incidents');
    },
    /** GET /incidents/:id — single incident detail */
    getIncident(id) {
        return request(`/incidents/${id}`);
    },
    /** POST /demo/:scenario — switch demo state, returns updated graph */
    switchDemo(scenario) {
        return request(`/demo/${scenario}`, { method: 'POST' });
    },
    /** POST /sync — pull real data from connectors */
    sync() {
        return request('/sync', { method: 'POST' });
    },
    /** GET /pipeline/:projectId — dynamic topology from CLI */
    getPipeline(projectId = 'default') {
        return request(`/pipeline/${projectId}`);
    },
};
