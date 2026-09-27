export function getSvgIconUri(type, color = '#f8fafc') {
    let svg = '';
    switch (type.toLowerCase()) {
        case 'github_actions':
            svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}">
        <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.379.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.161 22 16.416 22 12c0-5.523-4.477-10-10-10z"/>
      </svg>`;
            break;
        case 'docker':
            svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}">
        <path d="M11.98 2.02c-5.51 0-10 4.49-10 10s4.49 10 10 10 10-4.49 10-10-4.49-10-10-10zm-3 12.5H6.5v-2H9v2zm3 0H9.5v-2h2.5v2zm3 0H12v-2h2.5v2zm2-2.5h-8.5v-2H17v2zm-2.5-3.5H12v-2h2.5v2zm-3 0H9.5v-2H12v2zm-3 0H6.5v-2H9v2z"/>
      </svg>`;
            break;
        case 'kubernetes':
            svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}">
        <path d="M12 2L3 7v10l9 5 9-5V7l-9-5zm0 2.5l6 3.3v6.7l-6 3.4-6-3.4v-6.7l6-3.3zm0 2L8 8.8v4.5l4 2.2 4-2.2V8.8L12 6.5z"/>
      </svg>`;
            break;
        case 'prometheus':
            svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
      </svg>`;
            break;
        case 'test':
            svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}">
        <path d="M19 19.5v-1l-5-7V5h1V3H9v2h1v6.5l-5 7v1h14zM10.8 12.5h2.4l3.6 5H7.2l3.6-5z"/>
      </svg>`;
            break;
        default:
            svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}">
        <circle cx="12" cy="12" r="8"/>
      </svg>`;
    }
    // Base64 encode the SVG to use it directly as an image URI in Cytoscape
    return 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg.trim())));
}
