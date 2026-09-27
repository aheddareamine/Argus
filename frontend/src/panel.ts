import type { Incident, HealthStatus } from './types';

// ── Lazy DOM refs ─────────────────────────────────────────────────────────────
function getRefs() {
  return {
    elEmpty:         document.getElementById('detail-empty')!,
    elContent:       document.getElementById('detail-content')!,
    elServiceInfo:   document.getElementById('detail-service-info')!,
    elServiceName:   document.getElementById('detail-service-name')!,
    elServiceStatus: document.getElementById('detail-service-status')!,
    elCause:         document.getElementById('detail-cause')!,
    elEvidence:      document.getElementById('detail-evidence')!,
    elTimeline:      document.getElementById('detail-timeline')!,
    elAiBlock:       document.getElementById('detail-ai-block')!,
    elAiText:        document.getElementById('detail-ai')!,
    elNodeName:      document.getElementById('detail-node-name')!,
    elNodeStatus:    document.getElementById('detail-node-status')!,
  };
}

const STATUS_LABELS: Record<HealthStatus, string> = {
  HEALTHY:  '● HEALTHY',
  DEGRADED: '● DEGRADED',
  FAILING:  '● FAILING',
  UNKNOWN:  '○ UNKNOWN',
};

const EVENT_ICONS: Record<string, string> = {
  DEPLOY_FAILED:            '✕',
  DEPLOY_SUCCESS:           '✓',
  BUILD_FAILED:             '✕',
  BUILD_SUCCESS:            '✓',
  TEST_FAILED:              '✕',
  TEST_SUCCESS:             '✓',
  POD_FAILED:               '✕',
  POD_STARTED:              '✓',
  POD_RESTARTED:            '↺',
  APPLICATION_ERROR:        '⚠',
  DATABASE_CONNECTION_ERROR:'⚠',
  HIGH_ERROR_RATE:          '↑',
  HIGH_LATENCY:             '↑',
  HIGH_CPU:                 '↑',
  HIGH_MEMORY:              '↑',
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return iso;
  }
}

function statusClass(health: HealthStatus): string {
  return `status--${health.toLowerCase()}`;
}

export function showEmpty(): void {
  const refs = getRefs();
  refs.elEmpty.style.display = '';
  refs.elContent.style.display = 'none';
  refs.elServiceInfo.style.display = 'none';
}

export function showServiceInfo(nodeId: string, health: HealthStatus): void {
  const refs = getRefs();
  refs.elEmpty.style.display = 'none';
  refs.elContent.style.display = 'none';
  refs.elServiceInfo.style.display = '';

  refs.elNodeName.textContent = nodeId.toUpperCase();
  refs.elNodeStatus.textContent = STATUS_LABELS[health];
  refs.elNodeStatus.className = `detail-service__status ${statusClass(health)}`;
}

export function showIncident(incident: Incident): void {
  const refs = getRefs();
  refs.elEmpty.style.display = 'none';
  refs.elServiceInfo.style.display = 'none';
  refs.elContent.style.display = '';

  const health: HealthStatus = incident.severity === 'critical' ? 'FAILING' : 'DEGRADED';

  refs.elServiceName.textContent = incident.service.toUpperCase();
  refs.elServiceStatus.textContent = STATUS_LABELS[health];
  refs.elServiceStatus.className = `detail-service__status ${statusClass(health)}`;

  refs.elCause.textContent = incident.possible_cause;

  refs.elEvidence.innerHTML = '';
  incident.evidence.forEach((item) => {
    const li = document.createElement('li');
    li.className = 'evidence-item';
    li.innerHTML = `<span class="evidence-check">✓</span>${item}`;
    refs.elEvidence.appendChild(li);
  });

  refs.elTimeline.innerHTML = '';
  incident.events.forEach((ev, idx) => {
    const icon = EVENT_ICONS[ev.event_type] ?? '•';
    const isLast = idx === incident.events.length - 1;

    const row = document.createElement('div');
    row.className = `timeline-row${isLast ? ' timeline-row--last' : ''}`;
    row.innerHTML = `
      <div class="timeline-col timeline-col--time">${formatTime(ev.timestamp)}</div>
      <div class="timeline-col timeline-col--line">
        <span class="timeline-dot ${ev.status === 'critical' ? 'timeline-dot--critical' : 'timeline-dot--ok'}">${icon}</span>
        ${!isLast ? '<div class="timeline-connector"></div>' : ''}
      </div>
      <div class="timeline-col timeline-col--body">
        <div class="timeline-type">${ev.event_type.replace(/_/g, ' ')}</div>
        <div class="timeline-service">${ev.source} / ${ev.service}</div>
      </div>
    `;
    refs.elTimeline.appendChild(row);
  });

  if (incident.explanation) {
    refs.elAiBlock.style.display = '';
    refs.elAiText.textContent = incident.explanation;
  } else {
    refs.elAiBlock.style.display = 'none';
  }
}
