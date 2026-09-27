import cytoscape from 'cytoscape';
import { getSvgIconUri } from './icons';
// ── Theme constants ──────────────────────────────────────────────────────────
const HEALTH_COLORS = {
    HEALTHY: { bg: '#0d3320', border: '#22c55e', text: '#22c55e' },
    DEGRADED: { bg: '#3a2500', border: '#f59e0b', text: '#f59e0b' },
    FAILING: { bg: '#3a0a0a', border: '#ef4444', text: '#ef4444' },
    UNKNOWN: { bg: '#1c1c2e', border: '#6b7280', text: '#6b7280' },
};
// Map specific nodes to parents for compound node groupings
function getParentGroup(nodeId) {
    if (nodeId.includes('build') || nodeId.includes('test'))
        return 'group-ci';
    if (nodeId.includes('docker'))
        return 'group-build';
    if (nodeId.includes('backend') || nodeId.includes('database'))
        return 'group-k8s';
    if (nodeId.includes('prometheus'))
        return 'group-monitoring';
    return undefined;
}
function getGroupLabel(groupId) {
    switch (groupId) {
        case 'group-ci': return 'CI PIPELINE';
        case 'group-build': return 'IMAGE BUILD';
        case 'group-k8s': return 'KUBERNETES CLUSTER (HUB)';
        case 'group-monitoring': return 'SYSTEM MONITORING';
        default: return groupId.toUpperCase();
    }
}
// ── Cytoscape stylesheet ─────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildStylesheet() {
    return [
        {
            selector: 'node',
            style: {
                'width': 80,
                'height': 80,
                'shape': 'data(shape)',
                'background-color': 'data(bg)',
                'border-color': 'data(borderColor)',
                'border-width': 3,
                'background-image': 'data(iconUri)',
                'background-fit': 'contain',
                'background-width': '50%',
                'background-height': '50%',
                'label': 'data(displayLabel)',
                'color': '#f8fafc',
                'font-size': '11px',
                'font-family': '"JetBrains Mono", "Fira Code", monospace',
                'font-weight': 600,
                'text-valign': 'bottom',
                'text-margin-y': 8,
                'text-wrap': 'wrap',
                'text-max-width': '100px',
                'cursor': 'pointer',
                'transition-property': 'border-color, background-color, border-width',
                'transition-duration': 300,
                'shadow-blur': 25,
                'shadow-color': 'data(borderColor)',
                'shadow-opacity': 0.6,
            },
        },
        {
            selector: 'node:parent',
            style: {
                'shape': 'roundrectangle',
                'background-color': 'rgba(15, 23, 42, 0.2)',
                'border-color': '#334155',
                'border-width': 1.5,
                'border-style': 'solid',
                'padding': 35,
                'label': 'data(label)',
                'color': '#94a3b8',
                'font-size': '12px',
                'text-valign': 'bottom',
                'text-halign': 'center',
                'text-margin-y': 12,
                'font-weight': 700,
                'background-image': 'none',
                'shadow-opacity': 0,
            },
        },
        {
            selector: 'node:selected',
            style: {
                'border-width': 4,
                'underlay-color': '#ffffff',
                'underlay-padding': 4,
                'underlay-opacity': 0.1,
            },
        },
        {
            selector: 'node.pulsing',
            style: {
                'border-width': 5,
                'shadow-blur': 35,
                'shadow-opacity': 1,
            },
        },
        {
            selector: 'edge',
            style: {
                'width': 2.5,
                'line-color': '#22c55e',
                'target-arrow-color': '#22c55e',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'arrow-scale': 1.2,
                'opacity': 0.5,
                'transition-property': 'line-color, target-arrow-color',
                'transition-duration': 400,
            },
        },
        {
            selector: 'edge.failing',
            style: {
                'line-color': '#ef4444',
                'target-arrow-color': '#ef4444',
                'width': 3.5,
                'opacity': 0.9,
            },
        },
    ];
}
const LAYOUT_OPTIONS = {
    name: 'breadthfirst',
    directed: true,
    padding: 60,
    spacingFactor: 1.8,
    animate: true,
    animationDuration: 500,
    fit: true,
};
export class ArgusGraph {
    constructor(container, onNodeSelect) {
        Object.defineProperty(this, "cy", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "onNodeSelect", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        this.onNodeSelect = onNodeSelect;
        this.cy = cytoscape({
            container,
            elements: [],
            layout: { name: 'preset' },
            userZoomingEnabled: true,
            userPanningEnabled: true,
            boxSelectionEnabled: false,
        });
        this.cy.style(buildStylesheet());
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            if (node.isParent())
                return; // ignore clicks on parent container
            this.onNodeSelect(node.id(), node.data('health'));
        });
        this.cy.on('tap', (evt) => {
            if (evt.target === this.cy) {
                this.cy.$(':selected').unselect();
            }
        });
    }
    update(nodes, edges) {
        const prevHealthMap = new Map();
        this.cy.nodes().forEach((n) => {
            prevHealthMap.set(n.id(), n.data('health'));
        });
        const cyNodes = [];
        const parentGroups = new Set();
        nodes.forEach((n) => {
            const colors = HEALTH_COLORS[n.health] ?? HEALTH_COLORS.UNKNOWN;
            const parent = getParentGroup(n.id);
            if (parent)
                parentGroups.add(parent);
            const isHub = ['github_actions', 'kubernetes', 'prometheus'].includes(n.connector ?? '');
            const shape = isHub ? 'ellipse' : 'hexagon';
            const iconFill = isHub ? '#ffffff' : colors.border;
            cyNodes.push({
                data: {
                    id: n.id,
                    label: n.label,
                    displayLabel: `${n.label}\n[${n.health}]`,
                    health: n.health,
                    connector: n.connector ?? 'generic',
                    stage: n.stage ?? '',
                    parent: parent,
                    shape: shape,
                    bg: isHub ? '#1e293b' : colors.bg,
                    borderColor: isHub ? '#f1f5f9' : colors.border,
                    textColor: colors.text,
                    iconUri: getSvgIconUri(n.connector ?? 'generic', iconFill),
                },
            });
        });
        // Add parent nodes
        parentGroups.forEach(groupId => {
            cyNodes.push({
                data: {
                    id: groupId,
                    label: getGroupLabel(groupId),
                }
            });
        });
        const cyEdges = edges.map((e, i) => ({
            data: {
                id: `edge-${i}`,
                source: e.source,
                target: e.target,
            },
        }));
        // Re-layout if topology changed
        const prevNodeIds = new Set(this.cy.nodes().filter(n => !n.isParent()).map((n) => n.id()));
        const newNodeIds = new Set(nodes.map((n) => n.id));
        const topologyChanged = prevNodeIds.size !== newNodeIds.size ||
            [...newNodeIds].some((id) => !prevNodeIds.has(id));
        if (this.cy.elements().length === 0 || topologyChanged) {
            this.cy.elements().remove();
            this.cy.add([...cyNodes, ...cyEdges]);
            this.cy.layout(LAYOUT_OPTIONS).run();
        }
        else {
            cyNodes.forEach((n) => {
                const existing = this.cy.getElementById(n.data.id);
                if (existing.length > 0)
                    existing.data(n.data);
                else
                    this.cy.add({ group: 'nodes', data: n.data });
            });
            nodes.forEach((n) => {
                const prev = prevHealthMap.get(n.id);
                if (n.health === 'FAILING' && prev !== 'FAILING') {
                    this.pulseNode(n.id);
                }
            });
        }
        this.cy.edges().forEach((edge) => {
            const target = this.cy.getElementById(edge.data('target'));
            if (target.data('health') === 'FAILING')
                edge.addClass('failing');
            else
                edge.removeClass('failing');
        });
    }
    resize() {
        this.cy.resize();
        this.cy.fit(undefined, 60);
    }
    pulseNode(id) {
        const node = this.cy.getElementById(id);
        if (!node.length)
            return;
        node.addClass('pulsing');
        let count = 0;
        const interval = setInterval(() => {
            node.toggleClass('pulsing');
            count++;
            if (count >= 6) {
                clearInterval(interval);
                node.addClass('pulsing');
            }
        }, 250);
    }
}
