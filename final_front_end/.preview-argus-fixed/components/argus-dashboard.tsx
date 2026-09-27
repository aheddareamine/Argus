'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, AlertTriangle, Box, Check, ChevronDown, CircleDot, Clock3, Code2, Database, GitBranch, Layers3, Network, Radio, RefreshCw, Settings2, ShieldCheck, Terminal, TriangleAlert, X } from 'lucide-react'

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

type FracPos = { fx: number; fy: number; kind: 'hub' | 'service' }

// Positions are stored as FRACTIONS of the container's actual measured size
// (0..1), not fixed pixels. This is the fix: the old version placed nodes at
// hardcoded pixel coordinates designed for a 930x390 box, while the edges
// were drawn in an SVG with a hardcoded viewBox of the same size. Whenever
// the real container was a different size (which it almost always was,
// since .graph-wrap is a fluid-width flex/grid panel), the SVG's internal
// scaling and the nodes' raw pixel positions drifted apart, so lines missed
// the icons - worse after dragging, since drag math used real pixels while
// edges stayed in the old fixed coordinate space. Fractions + a live
// ResizeObserver-measured container keep both in the same space always.
const initialPositions: Record<string, FracPos> = {
  github: { fx: 0.113, fy: 0.467, kind: 'hub' },
  build: { fx: 0.317, fy: 0.467, kind: 'service' },
  test: { fx: 0.511, fy: 0.467, kind: 'service' },
  kubernetes: { fx: 0.704, fy: 0.467, kind: 'hub' },
  backend: { fx: 0.882, fy: 0.321, kind: 'service' },
  database: { fx: 0.882, fy: 0.654, kind: 'service' },
}

function healthColor(health: Health) { return health === 'FAILING' ? '#ff4d68' : health === 'DEGRADED' ? '#f7b955' : health === 'UNKNOWN' ? '#718096' : '#56e39f' }
function formatTime(timestamp: string) { return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
function connectorAsset(nodeId: string, connector: string) {
  const assets: Record<string, string> = {
    github: '/assets/github.svg',
    build: '/assets/Docker.svg',
    kubernetes: '/assets/kubernetes.svg',
    database: '/assets/Prometheus.svg',
  }
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
  const [nodePositions, setNodePositions] = useState<Record<string, FracPos>>(initialPositions)
  const dragRef = useRef<{ id: string; offsetX: number; offsetY: number; moved: boolean } | null>(null)
  const suppressClickRef = useRef(false)
  const [incidentOpen, setIncidentOpen] = useState(true)
  const wrapRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 930, height: 390 })

  // Keep `size` in sync with the actual rendered box at all times (initial
  // paint, window resize, sidebar/pod-inspector opening and changing the
  // panel width, etc). Everything below reads pixel positions through
  // pixelPos(), which multiplies the stored fraction by this live size - so
  // node divs and SVG edge paths are always computed from the same numbers.
  useEffect(() => {
    const node = wrapRef.current
    if (!node) return
    const update = () => setSize({ width: node.clientWidth || 930, height: node.clientHeight || 390 })
    update()
    const ro = new ResizeObserver(update)
    ro.observe(node)
    return () => ro.disconnect()
  }, [])

  const pixelPos = (id: string) => {
    const p = nodePositions[id] ?? initialPositions[id]
    if (!p) return { x: 0, y: 0, kind: 'service' as const }
    return { x: p.fx * size.width, y: p.fy * size.height, kind: p.kind }
  }

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setIsRefreshing(true)
      try {
        const [topologyResponse, graphResponse, incidentsResponse] = await Promise.all([fetch(`${BASE_URL}/pipeline/default`), fetch(`${BASE_URL}/graph`), fetch(`${BASE_URL}/incidents`)] )
        if (!topologyResponse.ok || !graphResponse.ok || !incidentsResponse.ok) throw new Error('API unavailable')
        const nextTopology = await topologyResponse.json(); const nextGraph = await graphResponse.json(); const nextIncidents = await incidentsResponse.json()
        if (!cancelled) { setTopology(nextTopology); setGraph(nextGraph.nodes); setIncident(nextIncidents[0] ?? null); setConnected(true); setLastUpdated(new Date()) }
      } catch { if (!cancelled) setConnected(false) } finally { if (!cancelled) setIsRefreshing(false) }
    }
    load(); const interval = window.setInterval(load, 5000)
    return () => { cancelled = true; window.clearInterval(interval) }
  }, [])

  const healthById = useMemo(() => new Map(graph.map((node) => [node.id, node.health])), [graph])
  const graphEdges = useMemo(() => uniqueEdges(topology.edges), [topology.edges])
  const activeCount = graph.filter((node) => node.health === 'FAILING').length > 0 ? 1 : 0

  const handlePointerDown = (event: React.PointerEvent<HTMLButtonElement>, nodeId: string) => {
    const bounds = event.currentTarget.parentElement?.getBoundingClientRect()
    if (!bounds) return
    const position = pixelPos(nodeId)
    event.currentTarget.setPointerCapture(event.pointerId)
    // offsets stay in pixels (relative to the actual box under the pointer
    // right now); they get converted back to fractions on every move below.
    dragRef.current = { id: nodeId, offsetX: event.clientX - bounds.left - position.x, offsetY: event.clientY - bounds.top - position.y, moved: false }
  }

  const handlePointerMove = (event: React.PointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current
    const bounds = event.currentTarget.parentElement?.getBoundingClientRect()
    if (!drag || !bounds || bounds.width === 0 || bounds.height === 0) return
    const margin = 56
    const nextXpx = Math.max(margin, Math.min(bounds.width - margin, event.clientX - bounds.left - drag.offsetX))
    const nextYpx = Math.max(margin, Math.min(bounds.height - margin, event.clientY - bounds.top - drag.offsetY))
    const nextFx = nextXpx / bounds.width
    const nextFy = nextYpx / bounds.height
    const current = nodePositions[drag.id]
    if (current && (Math.abs(nextFx - current.fx) * bounds.width > 2 || Math.abs(nextFy - current.fy) * bounds.height > 2)) drag.moved = true
    setNodePositions((prev) => ({ ...prev, [drag.id]: { ...prev[drag.id], fx: nextFx, fy: nextFy } }))
  }

  const handlePointerUp = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (!dragRef.current) return
    suppressClickRef.current = dragRef.current.moved
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
    dragRef.current = null
  }

  return <main className="argus-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Network size={19} strokeWidth={2.4} /></div><div><div className="brand-name">ARGUS</div><div className="brand-subtitle">SYSTEM HEALTH MAP</div></div></div>
      <div className="topbar-center"><span className="live-dot" /> LIVE MONITORING <span className="divider" /> <span className="muted">PROJECT / DEFAULT</span></div>
      <div className="top-actions"><div className="status-pill"><span className="status-light" />{activeCount} ACTIVE INCIDENT{activeCount === 1 ? '' : 'S'}</div><button className="icon-button" aria-label="Settings"><Settings2 size={17} /></button><div className="avatar">AG</div></div>
    </header>

    <div className="workspace">
      <section className="map-panel">
        <div className="panel-heading"><div><div className="eyebrow">OBSERVABILITY / TOPOLOGY</div><h1>Pipeline Overview</h1></div><div className="map-tools"><button className="tool-button"><Box size={14} /> AUTO LAYOUT</button><button className="tool-button" onClick={() => window.location.reload()}><RefreshCw className={isRefreshing ? 'spin' : ''} size={14} /> REFRESH</button></div></div>
        <div ref={wrapRef} className={`graph-wrap ${selectedNode === 'kubernetes' ? 'pods-open' : ''}`}>
          <div className="stage-label source-label">SOURCE CONTROL</div><div className="stage-label build-label">BUILD PIPELINE</div><div className="stage-label orchestration-label">ORCHESTRATION</div><div className="stage-label data-label">DATA LAYER</div>
          <svg className="edges" viewBox={`0 0 ${size.width} ${size.height}`} role="img" aria-label="Pipeline topology connections">
            <defs>
              <marker id="arrow-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#56e39f" /></marker>
              <marker id="arrow-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#ff4d68" /></marker>
            </defs>
            {graphEdges.map((edge, index) => {
              const from = pixelPos(edge.source)
              const to = pixelPos(edge.target)
              const fromRadius = from.kind === 'hub' ? 48 : 42
              const toRadius = to.kind === 'hub' ? 48 : 42
              const direction = to.x >= from.x ? 1 : -1
              const startX = from.x + direction * fromRadius
              const endX = to.x - direction * toRadius
              const distance = Math.max(48, Math.abs(endX - startX))
              const controlOffset = Math.min(150, Math.max(42, distance * 0.42))
              const failing = healthById.get(edge.source) === 'FAILING' || healthById.get(edge.target) === 'FAILING'
              const path = `M ${startX} ${from.y} C ${startX + direction * controlOffset} ${from.y}, ${endX - direction * controlOffset} ${to.y}, ${endX} ${to.y}`
              return <path key={`${edge.source}-${edge.target}`} d={path} className={failing ? 'edge failing-edge' : 'edge'} markerEnd={`url(#${failing ? 'arrow-red' : 'arrow-green'})`} style={{ animationDelay: `${index * 180}ms` }} />
            })}
          </svg>
          {topology.nodes.map((node) => { const position = pixelPos(node.id); const health = healthById.get(node.id) ?? 'UNKNOWN'; const asset = connectorAsset(node.id, node.connector); return <button key={node.id} type="button" className={`graph-node ${position.kind} ${health.toLowerCase()} ${selectedNode === node.id ? 'selected' : ''}`} style={{ left: `${position.x}px`, top: `${position.y}px`, '--node-color': healthColor(health) } as React.CSSProperties} onPointerDown={(event) => handlePointerDown(event, node.id)} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerCancel={handlePointerUp} onClick={() => { if (suppressClickRef.current) { suppressClickRef.current = false; return }; setSelectedNode(selectedNode === node.id ? null : node.id) }} aria-label={`${node.label}, ${health}`}><span className="node-shape"><img className="technology-icon" src={asset} alt="" aria-hidden="true" /><span className="node-pulse" /></span><span className="node-label">{node.label}</span><span className="node-health"><span className="health-dot" />{health}</span></button> })}
          {selectedNode === 'kubernetes' && <section className="pod-inspector" aria-label="Kubernetes pods"><div className="pod-inspector-header"><div><span className="eyebrow">KUBERNETES / CLUSTER</span><h2>Running pods</h2></div><button type="button" className="pod-close" onClick={() => setSelectedNode(null)} aria-label="Close pod inspector"><X size={14} /></button></div><div className="pod-summary"><span className="pod-summary-dot" />{kubernetesPods.length} pods · {kubernetesPods.filter((pod) => pod.health === 'HEALTHY').length} healthy</div><div className="pod-list">{kubernetesPods.map((pod) => <div className="pod-row" key={pod.name}><div className="pod-icon"><Box size={14} /></div><div className="pod-copy"><strong>{pod.name}</strong><span>{pod.role} · {pod.image}</span></div><div className={`pod-state ${pod.health.toLowerCase()}`}><span />{pod.health}<small>{pod.restarts} restarts</small></div></div>)}</div></section>}
          <div className="graph-legend"><div><span className="legend-dot healthy" />HEALTHY</div><div><span className="legend-dot degraded" />DEGRADED</div><div><span className="legend-dot failing" />FAILING</div></div>
          <div className="scanline" />
        </div>
        <div className="map-footer"><div className="footer-stat"><span className="stat-icon green"><Check size={14} /></span><div><strong>{graph.filter(n => n.health === 'HEALTHY').length}</strong><span>Healthy services</span></div></div><div className="footer-stat"><span className="stat-icon amber"><TriangleAlert size={14} /></span><div><strong>{graph.filter(n => n.health === 'DEGRADED').length}</strong><span>Degraded services</span></div></div><div className="footer-stat"><span className="stat-icon red"><AlertTriangle size={14} /></span><div><strong>{graph.filter(n => n.health === 'FAILING').length}</strong><span>Failing services</span></div></div><div className="last-updated"><Radio size={12} /> LAST SYNC {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} <span className={connected ? 'api-ok' : 'api-demo'}>{connected ? 'API CONNECTED' : 'DEMO DATA'}</span></div></div>
      </section>

      <aside className="incident-panel">
        <div className="incident-header"><div><div className="eyebrow red-text"><span className="incident-pulse" />ACTIVE INCIDENT</div><h2>Incident details</h2></div><button className="close-button" aria-label="Close incident panel" onClick={() => setIncidentOpen(false)}><X size={17} /></button></div>
        {incident && incidentOpen ? <><div className="incident-title-row"><div><div className="incident-service">{incident.service.toUpperCase()} / {incident.id}</div><h3>Backend service failing</h3></div><span className="severity-badge"><span />{incident.severity.toUpperCase()}</span></div><p className="incident-explanation">{incident.explanation}</p><div className="cause-box"><div className="cause-label"><Terminal size={13} />POSSIBLE CAUSE</div><code>{incident.possible_cause}</code></div><div className="evidence"><div className="section-label"><ShieldCheck size={14} />EVIDENCE <span>({incident.evidence.length})</span></div>{incident.evidence.map((item) => <div className="evidence-item" key={item}><Check size={13} />{item}</div>)}</div><div className="timeline"><div className="section-label"><Clock3 size={14} />EVENT TIMELINE <span>CHRONOLOGICAL</span></div>{incident.events.map((event, index) => { const Icon = event.source === 'github_actions' ? GitBranch : event.source === 'kubernetes' ? Layers3 : Activity; return <div className="timeline-item" key={event.id}><div className="timeline-line"><div className="timeline-dot" /><span className="timeline-connector" /></div><div className="timeline-content"><div className="event-meta"><span>{formatTime(event.timestamp)}</span><span className="event-source"><Icon size={12} />{event.source.replace('_', ' ')}</span></div><strong>{event.event_type.replaceAll('_', ' ')}</strong><span className="event-service">{event.service} service</span></div></div> })}</div><div className="incident-actions"><button className="primary-action"><Code2 size={14} /> VIEW LOGS</button><button className="secondary-action"><GitBranch size={14} /> OPEN RUNBOOK</button></div></> : <div className="empty-incident"><Check size={27} /><strong>All systems operational</strong><span>No active incidents detected.</span></div>}
      </aside>
    </div>
  </main>
}

export { ArgusDashboard }

void Database; void CircleDot; void ChevronDown; void AlertTriangle
