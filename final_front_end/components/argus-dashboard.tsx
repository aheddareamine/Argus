'use client'

import { useEffect, useMemo, useState } from 'react'
import { useTheme } from 'next-themes'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Activity, AlertTriangle, Box, Check, Clock3, Code2, GitBranch, Layers3, Network, Radio, RefreshCw, Settings2, ShieldCheck, Terminal, TriangleAlert, X, Moon, Sun } from 'lucide-react'

type Health = 'HEALTHY' | 'DEGRADED' | 'FAILING' | 'UNKNOWN'
type TopologyNode = { id: string; label: string; stage: string; connector: string }
type Topology = { nodes: TopologyNode[]; edges: { source: string; target: string }[] }
type IncidentEvent = { id: string; timestamp: string; source: string; service: string; event_type: string; status: string }
type Incident = { id: string; service: string; severity: string; status: string; start_time: string; possible_cause: string; evidence: string[]; explanation: string; events: IncidentEvent[] }
type GraphNode = { id: string; label: string; health: Health }
type Pod = { name: string; role: string; health: Health; restarts: number; image: string }

const kubernetesPods: Pod[] = [
  { name: 'argus-api-7d8f9', role: 'Backend API', health: 'FAILING', restarts: 6, image: 'argus/api:v2.1.8' },
  { name: 'argus-worker-54c2a', role: 'Queue Worker', health: 'HEALTHY', restarts: 0, image: 'argus/worker:v2.1.8' },
  { name: 'argus-web-6b91d', role: 'Frontend', health: 'HEALTHY', restarts: 0, image: 'argus/web:v2.1.8' },
]

function uniqueEdges(edges: Topology['edges']) {
  const seen = new Set<string>()
  return edges.filter((edge) => {
    const key = `${edge.source}->${edge.target}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8090'

const fallbackTopology: Topology = {
  nodes: [
    { id: 'github', label: 'GitHub Actions', stage: 'source', connector: 'github_actions' },
    { id: 'build', label: 'Build', stage: 'build', connector: 'github_actions' },
    { id: 'test', label: 'Tests', stage: 'build', connector: 'github_actions' },
    { id: 'kubernetes', label: 'Kubernetes', stage: 'orchestration', connector: 'kubernetes' },
    { id: 'backend', label: 'Backend API', stage: 'orchestration', connector: 'kubernetes' },
    { id: 'database', label: 'Database', stage: 'data', connector: 'prometheus' },
  ],
  edges: [
    { source: 'github', target: 'build' },
    { source: 'build', target: 'test' },
    { source: 'test', target: 'kubernetes' },
    { source: 'kubernetes', target: 'backend' },
    { source: 'backend', target: 'database' },
  ],
}

const fallbackGraph: GraphNode[] = [
  { id: 'github', label: 'GitHub Actions', health: 'HEALTHY' }, { id: 'build', label: 'Build', health: 'HEALTHY' }, { id: 'test', label: 'Tests', health: 'HEALTHY' }, { id: 'kubernetes', label: 'Kubernetes', health: 'DEGRADED' }, { id: 'backend', label: 'Backend API', health: 'FAILING' }, { id: 'database', label: 'Database', health: 'FAILING' },
]

const fallbackIncident: Incident = {
  id: 'inc-8f72a', service: 'backend', severity: 'critical', status: 'active', start_time: '2026-09-27T12:00:00Z', possible_cause: 'ConnectionRefusedError: db.production.internal', evidence: ["Deployment 'v2.1.8' failed", 'Backend error logs spiked'], explanation: 'The backend pod crashed repeatedly after the recent v2.1.8 deployment.', events: [
    { id: 'evt-01', timestamp: '2026-09-27T11:58:00Z', source: 'github_actions', service: 'backend', event_type: 'DEPLOY_FAILED', status: 'critical' },
    { id: 'evt-02', timestamp: '2026-09-27T11:59:12Z', source: 'kubernetes', service: 'backend', event_type: 'POD_CRASH_LOOP', status: 'critical' },
    { id: 'evt-03', timestamp: '2026-09-27T12:00:03Z', source: 'prometheus', service: 'backend', event_type: 'ERROR_RATE_SPIKE', status: 'critical' },
  ],
}

function healthColor(health: Health) { return health === 'FAILING' ? '#ff4d68' : health === 'DEGRADED' ? '#f7b955' : health === 'UNKNOWN' ? '#718096' : '#56e39f' }
function formatTime(timestamp: string) { return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
function connectorAsset(nodeId: string, connector: string) {
  const assets: Record<string, string> = { github: '/assets/github.svg', build: '/assets/Docker.svg', kubernetes: '/assets/kubernetes.svg', database: '/assets/Prometheus.svg' }
  return assets[nodeId] ?? (connector === 'kubernetes' ? '/assets/kubernetes.svg' : '/assets/github.svg')
}

export default function ArgusDashboard() {
  const [topology, setTopology] = useState<Topology>(fallbackTopology)
  const [graph, setGraph] = useState<GraphNode[]>(fallbackGraph)
  const [incident, setIncident] = useState<Incident | null>(fallbackIncident)
  const [lastUpdated, setLastUpdated] = useState(new Date())
  const [connected, setConnected] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [incidentOpen, setIncidentOpen] = useState(true)
  const { setTheme, theme } = useTheme()

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setIsRefreshing(true)
      try {
        const [topologyResponse, graphResponse, incidentsResponse] = await Promise.all([fetch(`${BASE_URL}/pipeline/default`), fetch(`${BASE_URL}/graph`), fetch(`${BASE_URL}/incidents`)] )
        if (!topologyResponse.ok || !graphResponse.ok || !incidentsResponse.ok) throw new Error('API unavailable')
        const nextTopology = await topologyResponse.json(); const nextGraph = await graphResponse.json(); const nextIncidents = await incidentsResponse.json()
        if (!cancelled) {
          const normalizedTopology: Topology = {
            nodes: Array.isArray(nextTopology?.nodes) && nextTopology.nodes.length ? nextTopology.nodes : fallbackTopology.nodes,
            edges: Array.isArray(nextTopology?.edges) && nextTopology.edges.length ? uniqueEdges(nextTopology.edges) : fallbackTopology.edges,
          }
          setTopology(normalizedTopology)
          setGraph(Array.isArray(nextGraph?.nodes) && nextGraph.nodes.length ? nextGraph.nodes : fallbackGraph)
          setIncident(nextIncidents[0] ?? null)
          setConnected(true)
          setLastUpdated(new Date())
        }
      } catch { if (!cancelled) setConnected(false) } finally { if (!cancelled) setIsRefreshing(false) }
    }
    load(); const interval = window.setInterval(load, 5000)
    return () => { cancelled = true; window.clearInterval(interval) }
  }, [])

  const healthById = useMemo(() => new Map(graph.map((node) => [node.id, node.health])), [graph])
  const graphEdges = useMemo(() => {
    const nodeIds = new Set(topology.nodes.map((node) => node.id))
    const canonicalEdges = [
      { source: 'github', target: 'build' },
      { source: 'build', target: 'test' },
      { source: 'test', target: 'kubernetes' },
      { source: 'kubernetes', target: 'backend' },
      { source: 'backend', target: 'database' },
    ].filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    if (canonicalEdges.length) return canonicalEdges
    return uniqueEdges(topology.edges).filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  }, [topology.edges, topology.nodes])
  const staticConnections = [
    { id: 'github-build', d: 'M 14 50 C 19 50, 21 50, 26 50', color: '#56e39f' },
    { id: 'build-test', d: 'M 34 50 C 39 50, 41 50, 46 50', color: '#56e39f' },
    { id: 'test-kubernetes', d: 'M 54 50 C 59 50, 61 50, 66 50', color: '#56e39f' },
    { id: 'kubernetes-backend', d: 'M 74 50 C 78 50, 79 36, 86 36', color: '#ff4d68' },
    { id: 'backend-database', d: 'M 90 43 C 93 48, 93 52, 90 57', color: '#ff4d68' },
  ]
  const activeCount = graph.filter((node) => node.health === 'FAILING').length > 0 ? 1 : 0

  return <main className="argus-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Network size={19} strokeWidth={2.4} /></div><div><div className="brand-name">ARGUS</div><div className="brand-subtitle">SYSTEM HEALTH MAP</div></div></div>
      <div className="topbar-center"><span className="live-dot" /> LIVE MONITORING <span className="divider" /> <span className="muted">PROJECT / DEFAULT</span></div>
      <div className="top-actions">
  <div className="status-pill"><span className="status-light" />{activeCount} ACTIVE INCIDENT{activeCount === 1 ? '' : 'S'}</div>
  <button className="icon-button" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} aria-label="Toggle theme">
    {theme === 'light' ? <Moon size={17} /> : <Sun size={17} />}
  </button>
  <Dialog>
  <DialogTrigger asChild>
    <button className="icon-button" aria-label="Settings"><Settings2 size={17} /></button>
  </DialogTrigger>
  <DialogContent className="sm:max-w-[400px] bg-[#0b1421] border-[#273147] text-[#d6deeb]">
    <DialogHeader>
      <DialogTitle className="text-[#56e39f] font-mono text-sm tracking-widest uppercase">Global Settings</DialogTitle>
    </DialogHeader>
    <div className="flex flex-col gap-4 py-4">
      <div className="flex items-center justify-between">
        <div className="flex flex-col"><span className="text-sm font-semibold">Enable AI Agent</span><span className="text-xs text-[#7d8da5]">Auto-analyze incidents using IBM Bob</span></div>
        <div className="w-9 h-5 bg-[#56e39f] rounded-full relative"><div className="w-4 h-4 bg-white rounded-full absolute right-0.5 top-0.5"></div></div>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex flex-col"><span className="text-sm font-semibold">Auto-Remediation</span><span className="text-xs text-[#7d8da5]">Automatically trigger runbooks</span></div>
        <div className="w-9 h-5 bg-[#273147] rounded-full relative"><div className="w-4 h-4 bg-[#7d8da5] rounded-full absolute left-0.5 top-0.5"></div></div>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex flex-col"><span className="text-sm font-semibold">Sound Alerts</span><span className="text-xs text-[#7d8da5]">Play sound on new incidents</span></div>
        <div className="w-9 h-5 bg-[#56e39f] rounded-full relative"><div className="w-4 h-4 bg-white rounded-full absolute right-0.5 top-0.5"></div></div>
      </div>
    </div>
  </DialogContent>
</Dialog><div className="avatar">AG</div></div>
    </header>

    <div className="workspace">
      <section className="map-panel">
        <div className="panel-heading"><div><div className="eyebrow">OBSERVABILITY / TOPOLOGY</div><h1>Pipeline Overview</h1></div><div className="map-tools"><button className="tool-button"><Box size={14} /> AUTO LAYOUT</button><button className="tool-button" onClick={() => fetch(BASE_URL + '/demo/incident', { method: 'POST' }).then(() => window.location.reload())}><AlertTriangle size={14} /> SIMULATE FAILURE</button>
<button className="tool-button" onClick={() => window.location.reload()}><RefreshCw className={isRefreshing ? 'spin' : ''} size={14} /> REFRESH</button></div></div>
        <div className={`graph-wrap ${selectedNode === 'kubernetes' ? 'pods-open' : ''}`}>
          <div className="stage-label source-label">SOURCE CONTROL</div><div className="stage-label build-label">BUILD PIPELINE</div><div className="stage-label orchestration-label">ORCHESTRATION</div><div className="stage-label data-label">DATA LAYER</div>
          <svg className="topology-connections" aria-hidden="true" preserveAspectRatio="none" viewBox="0 0 100 100">
            {staticConnections.map((line) => <g key={line.id}><path id={`topology-${line.id}`} d={line.d} fill="none" stroke={line.color} strokeWidth="0.55" strokeLinecap="round" opacity="1" vectorEffect="non-scaling-stroke" style={{ filter: `drop-shadow(0 0 8px ${line.color}cc)` }} /><circle r="0.34" fill={line.color}><animateMotion dur="1.5s" repeatCount="indefinite"><mpath href={`#topology-${line.id}`} /></animateMotion></circle></g>)}
          </svg>
          <div className="topology-layout" aria-label="Pipeline topology connections">
            {topology.nodes.map((node) => <div key={node.id} className={`flow-node ${node.id} ${(healthById.get(node.id) ?? 'UNKNOWN').toLowerCase()} ${selectedNode === node.id ? 'selected' : ''}`} style={{ '--node-color': healthColor(healthById.get(node.id) ?? 'UNKNOWN') } as React.CSSProperties}>
              <button type="button" onClick={() => setSelectedNode(selectedNode === node.id ? null : node.id)} aria-label={`${node.label}, ${healthById.get(node.id) ?? 'UNKNOWN'}`}>
                <span className="node-shape"><img className="technology-icon" src={connectorAsset(node.id, node.connector)} alt="" aria-hidden="true" /><span className="node-pulse" /></span><span className="node-label">{node.label}</span><span className="node-health"><span className="health-dot" />{healthById.get(node.id) ?? 'UNKNOWN'}</span>
              </button>
            </div>)}
          </div>
          {selectedNode === 'kubernetes' && <section className="pod-inspector" aria-label="Kubernetes pods"><div className="pod-inspector-header"><div><span className="eyebrow">KUBERNETES / CLUSTER</span><h2>Running pods</h2></div><button type="button" className="pod-close" onClick={() => setSelectedNode(null)} aria-label="Close pod inspector"><X size={14} /></button></div><div className="pod-summary"><span className="pod-summary-dot" />{kubernetesPods.length} pods · {kubernetesPods.filter((pod) => pod.health === 'HEALTHY').length} healthy</div><div className="pod-list">{kubernetesPods.map((pod) => <div className="pod-row" key={pod.name}><div className="pod-icon"><Box size={14} /></div><div className="pod-copy"><strong>{pod.name}</strong><span>{pod.role} · {pod.image}</span></div><div className={`pod-state ${pod.health.toLowerCase()}`}><span />{pod.health}<small>{pod.restarts} restarts</small></div></div>)}</div></section>}
          <div className="graph-legend"><div><span className="legend-dot healthy" />HEALTHY</div><div><span className="legend-dot degraded" />DEGRADED</div><div><span className="legend-dot failing" />FAILING</div></div>
          <div className="scanline" />
        </div>
        <div className="map-footer"><div className="footer-stat"><span className="stat-icon green"><Check size={14} /></span><div><strong>{graph.filter(n => n.health === 'HEALTHY').length}</strong><span>Healthy services</span></div></div><div className="footer-stat"><span className="stat-icon amber"><TriangleAlert size={14} /></span><div><strong>{graph.filter(n => n.health === 'DEGRADED').length}</strong><span>Degraded services</span></div></div><div className="footer-stat"><span className="stat-icon red"><AlertTriangle size={14} /></span><div><strong>{graph.filter(n => n.health === 'FAILING').length}</strong><span>Failing services</span></div></div><div className="last-updated"><Radio size={12} /> LAST SYNC {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} <span className={connected ? 'api-ok' : 'api-demo'}>{connected ? 'API CONNECTED' : 'DEMO DATA'}</span></div></div>
      </section>

      <aside className="incident-panel">
        <div className="incident-header"><div><div className="eyebrow red-text"><span className="incident-pulse" />ACTIVE INCIDENT</div><h2>Incident details</h2></div><button className="close-button" aria-label="Close incident panel" onClick={() => setIncidentOpen(false)}><X size={17} /></button></div>
        {incident && incidentOpen ? <><div className="incident-title-row"><div><div className="incident-service">{incident.service.toUpperCase()} / {incident.id}</div><h3>Backend service failing</h3></div><span className="severity-badge"><span />{incident.severity.toUpperCase()}</span></div><p className="incident-explanation">{incident.explanation}</p><div className="cause-box"><div className="cause-label"><Terminal size={13} />POSSIBLE CAUSE</div><code>{incident.possible_cause}</code></div><div className="evidence"><div className="section-label"><ShieldCheck size={14} />EVIDENCE <span>({incident.evidence.length})</span></div>{incident.evidence.map((item) => <div className="evidence-item" key={item}><Check size={13} />{item}</div>)}</div><div className="timeline"><div className="section-label"><Clock3 size={14} />EVENT TIMELINE <span>CHRONOLOGICAL</span></div>{incident.events.map((event, index) => { const Icon = event.source === 'github_actions' ? GitBranch : event.source === 'kubernetes' ? Layers3 : Activity; return <div className="timeline-item" key={event.id}><div className="timeline-line"><div className="timeline-dot" /><span className="timeline-connector" /></div><div className="timeline-content"><div className="event-meta"><span>{formatTime(event.timestamp)}</span><span className="event-source"><Icon size={12} />{event.source.replace('_', ' ')}</span></div><strong>{event.event_type.replaceAll('_', ' ')}</strong><span className="event-service">{event.service} service</span></div></div> })}</div><div className="incident-actions"><Dialog>
  <DialogTrigger asChild>
    <button className="primary-action"><Code2 size={14} /> VIEW LOGS</button>
  </DialogTrigger>
  <DialogContent className="sm:max-w-[700px] bg-[#0b1421] border-[#273147] text-[#d6deeb]">
    <DialogHeader>
      <DialogTitle className="text-[#56e39f] font-mono text-sm tracking-widest uppercase">System Logs & Traces</DialogTitle>
    </DialogHeader>
    <div className="bg-black p-5 rounded-md font-mono text-[10px] text-[#a7b2c3] max-h-[450px] overflow-y-auto whitespace-pre-wrap leading-relaxed border border-[#1b2b3c]">
      {incident.events.map((event, i) => (
         <div key={i} className="mb-3">
           <span className="text-[#5f6f86]">{`[${formatTime(event.timestamp)}] `}</span>
           <span className="text-[#7587a2] uppercase">{`[${event.source}] `}</span>
           <span className={event.status === 'critical' ? 'text-[#ff4d68]' : 'text-[#56e39f]'}>{event.event_type}</span>
           <br />
           <span className="text-[#64738b] ml-4">{`> Trace: ${incident.evidence[i] || 'Event registered successfully'}`}</span>
         </div>
      ))}
      <div className="mt-4 pt-4 border-t border-[#1b2b3c] text-[#ff7286]">
        {`[FATAL] Incident escalated at ${formatTime(incident.start_time)}\n> Cause: ${incident.possible_cause}`}
      </div>
    </div>
  </DialogContent>
</Dialog><Dialog>
  <DialogTrigger asChild>
    <button className="secondary-action"><GitBranch size={14} /> OPEN RUNBOOK</button>
  </DialogTrigger>
  <DialogContent className="sm:max-w-[500px] bg-[#0b1421] border-[#273147] text-[#d6deeb]">
    <DialogHeader>
      <DialogTitle className="text-[#56e39f] font-mono text-sm tracking-widest uppercase">Remediation Runbook</DialogTitle>
    </DialogHeader>
    <div className="bg-black p-5 rounded-md text-xs text-[#a7b2c3] border border-[#1b2b3c] flex flex-col gap-3">
      <p>Follow these steps to remediate the incident on <strong>{incident.service}</strong>:</p>
      <ul className="list-decimal pl-5 flex flex-col gap-2">
        <li>Acknowledge the incident and notify the on-call engineer.</li>
        <li>Rollback the recent deployment if metrics indicate an immediate failure.</li>
        <li>Restart the crashing pods in the {incident.service} namespace.</li>
        <li>Verify the database connection strings are correct.</li>
      </ul>
      <div className="flex gap-2 mt-4">
        <button className="primary-action w-full" onClick={() => fetch(BASE_URL + '/demo/healthy', { method: 'POST' }).then(() => window.location.reload())}>
          <Check size={14} /> RESOLVE INCIDENT
        </button>
      </div>
    </div>
  </DialogContent>
</Dialog></div></> : <div className="empty-incident"><Check size={27} /><strong>All systems operational</strong><span>No active incidents detected.</span></div>}
      </aside>
    </div>
  </main>
}

export { ArgusDashboard }

