import re

with open('src/graph.ts', 'r') as f:
    content = f.read()

# Replace the buildStylesheet function
stylesheet_new = """function buildStylesheet(): any[] {
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
}"""

content = re.sub(r'function buildStylesheet\(\): any\[\] \{.*?(?=const LAYOUT_OPTIONS)', stylesheet_new + "\n\n", content, flags=re.DOTALL)

# Add logic for determining node shape in update()
update_old = """      cyNodes.push({
        data: {
          id: n.id,
          label: n.label,
          displayLabel: `${n.label}\\n[${n.health}]`,
          health: n.health,
          connector: n.connector ?? 'generic',
          stage: n.stage ?? '',
          parent: parent,
          bg: colors.bg,
          borderColor: colors.border,
          textColor: colors.text,
          iconUri: getSvgIconUri(n.connector ?? 'generic', colors.border),
        },
      });"""

update_new = """      const isHub = ['github_actions', 'kubernetes', 'prometheus'].includes(n.connector ?? '');
      const shape = isHub ? 'ellipse' : 'hexagon';
      const iconFill = isHub ? '#ffffff' : colors.border;
      
      cyNodes.push({
        data: {
          id: n.id,
          label: n.label,
          displayLabel: `${n.label}\\n[${n.health}]`,
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
      });"""

content = content.replace(update_old, update_new)

with open('src/graph.ts', 'w') as f:
    f.write(content)
