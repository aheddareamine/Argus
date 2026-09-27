// main.ts — app entry point: wires graph, panel, polling, and controls
import './style.css';
import { api } from './api';
import { ArgusGraph } from './graph';
import { showEmpty, showIncident, showServiceInfo } from './panel';
// ── DOM refs ──────────────────────────────────────────────────────────────────
const cyContainer = document.getElementById('cy');
const btnHealthy = document.getElementById('btn-healthy');
const btnIncident = document.getElementById('btn-incident');
const btnSync = document.getElementById('btn-sync');
const scenarioBadge = document.getElementById('scenario-badge');
const lastUpdated = document.getElementById('last-updated');
const incidentBadge = document.getElementById('incident-count-badge');
// ── State ─────────────────────────────────────────────────────────────────────
let graph = null;
let pollingTimer = null;
let incidents = [];
let currentPipeline = null;
const POLL_INTERVAL_MS = 3000;
const PROJECT_ID = new URLSearchParams(window.location.search).get('project') ?? 'default';
// ── Boot ──────────────────────────────────────────────────────────────────────
async function boot() {
    graph = new ArgusGraph(cyContainer, handleNodeSelect);
    // Try to load dynamic pipeline first (CLI mode)
    try {
        currentPipeline = await api.getPipeline(PROJECT_ID);
    }
    catch {
        currentPipeline = null;
    }
    await refresh();
    startPolling();
    window.addEventListener('resize', () => graph?.resize());
}
// ── Polling ───────────────────────────────────────────────────────────────────
function startPolling() {
    if (pollingTimer !== null)
        clearInterval(pollingTimer);
    pollingTimer = setInterval(async () => {
        await refresh();
    }, POLL_INTERVAL_MS);
}
// ── Core refresh: fetch graph + incidents, update UI ─────────────────────────
async function refresh() {
    try {
        const [graphData, incidentList] = await Promise.all([
            api.getGraph(),
            api.getIncidents(),
        ]);
        incidents = incidentList;
        // Merge pipeline node metadata (connector, stage) onto graph nodes when in CLI mode
        let nodes = graphData.nodes;
        let edges = graphData.edges;
        if (currentPipeline && currentPipeline.nodes.length > 0) {
            // Re-fetch pipeline on every cycle so topology changes are reflected
            try {
                currentPipeline = await api.getPipeline(PROJECT_ID);
            }
            catch { /* keep stale */ }
            const pipelineNodeMap = new Map(currentPipeline.nodes.map((n) => [n.id, n]));
            // Enrich graph nodes with pipeline metadata
            nodes = nodes.map((gn) => {
                const pn = pipelineNodeMap.get(gn.id);
                return pn ? { ...gn, stage: pn.stage, connector: pn.connector } : gn;
            });
            // If pipeline has nodes the health graph doesn't know about, add them
            currentPipeline.nodes.forEach((pn) => {
                if (!nodes.find((n) => n.id === pn.id)) {
                    nodes.push({ ...pn });
                }
            });
            // Use pipeline edges (dynamic topology)
            if (currentPipeline.edges.length > 0) {
                edges = currentPipeline.edges;
            }
        }
        graph?.update(nodes, edges);
        updateTopBar(graphData.scenario, incidentList.length);
        updateLastUpdated();
    }
    catch (err) {
        console.error('[Argus] refresh failed:', err);
        setStatusError();
    }
}
// ── Node click handler ────────────────────────────────────────────────────────
function handleNodeSelect(nodeId, health) {
    // Find incident involving this service
    const incident = incidents.find((i) => i.service === nodeId || i.events.some((e) => e.service === nodeId));
    if (incident) {
        showIncident(incident);
    }
    else {
        showServiceInfo(nodeId, health);
    }
}
// ── Demo controls ─────────────────────────────────────────────────────────────
async function switchScenario(scenario) {
    setButtonLoading(scenario, true);
    try {
        await api.switchDemo(scenario);
        await refresh();
        showEmpty();
    }
    finally {
        setButtonLoading(scenario, false);
    }
}
async function syncLive() {
    btnSync.textContent = '⟳ Syncing…';
    btnSync.setAttribute('disabled', 'true');
    try {
        await api.sync();
        await refresh();
        showEmpty();
    }
    catch (err) {
        console.warn('[Argus] sync failed (no real connector configured?):', err);
    }
    finally {
        btnSync.textContent = '⟳ Sync';
        btnSync.removeAttribute('disabled');
    }
}
// ── UI helpers ────────────────────────────────────────────────────────────────
function updateTopBar(scenario, incidentCount) {
    const isHealthy = incidentCount === 0;
    scenarioBadge.textContent = isHealthy ? '● HEALTHY' : `● ${incidentCount} INCIDENT${incidentCount > 1 ? 'S' : ''}`;
    scenarioBadge.className = `badge ${isHealthy ? 'badge--healthy' : 'badge--failing'}`;
    if (incidentCount > 0) {
        incidentBadge.textContent = `${incidentCount} active`;
        incidentBadge.className = 'badge badge--failing';
        incidentBadge.style.display = '';
    }
    else {
        incidentBadge.style.display = 'none';
    }
    // Highlight active button
    btnHealthy.classList.toggle('btn--active', scenario === 'healthy');
    btnIncident.classList.toggle('btn--active', scenario === 'incident');
}
function updateLastUpdated() {
    lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
}
function setStatusError() {
    scenarioBadge.textContent = '○ OFFLINE';
    scenarioBadge.className = 'badge badge--unknown';
}
function setButtonLoading(scenario, loading) {
    const btn = scenario === 'healthy' ? btnHealthy : btnIncident;
    btn.toggleAttribute('disabled', loading);
    if (loading)
        btn.textContent = `${scenario === 'healthy' ? '⬤ Healthy' : '⬤ Incident'} …`;
    else
        btn.textContent = scenario === 'healthy' ? '⬤ Healthy' : '⬤ Incident';
}
// ── Event listeners ───────────────────────────────────────────────────────────
btnHealthy.addEventListener('click', () => switchScenario('healthy'));
btnIncident.addEventListener('click', () => switchScenario('incident'));
btnSync.addEventListener('click', () => syncLive());
// ── Start ─────────────────────────────────────────────────────────────────────
boot();
