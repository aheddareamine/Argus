import sys

with open('final_front_end/components/argus-dashboard.tsx', 'r') as f:
    content = f.read()

target = '<div className="top-actions"><div className="status-pill"><span className="status-light" />{activeCount} ACTIVE INCIDENT{activeCount === 1 ? \'\' : \'S\'}</div><Dialog>'
replacement = '''<div className="top-actions">
  <div className="status-pill"><span className="status-light" />{activeCount} ACTIVE INCIDENT{activeCount === 1 ? '' : 'S'}</div>
  <button className="icon-button" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} aria-label="Toggle theme">
    {theme === 'light' ? <Moon size={17} /> : <Sun size={17} />}
  </button>
  <Dialog>'''

content = content.replace(target, replacement)

with open('final_front_end/components/argus-dashboard.tsx', 'w') as f:
    f.write(content)
