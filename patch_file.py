import sys

with open('final_front_end/components/argus-dashboard.tsx', 'r') as f:
    content = f.read()

target = '<button className="primary-action"><Code2 size={14} /> VIEW LOGS</button>'
replacement = '''<Dialog>
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
        {`[FATAL] Incident escalated at ${formatTime(incident.start_time)}\\n> Cause: ${incident.possible_cause}`}
      </div>
    </div>
  </DialogContent>
</Dialog>'''

content = content.replace(target, replacement)

target2 = '<button className="secondary-action"><GitBranch size={14} /> OPEN RUNBOOK</button>'
replacement2 = '''<Dialog>
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
</Dialog>'''

content = content.replace(target2, replacement2)

target3 = '<button className="tool-button" onClick={() => window.location.reload()}><RefreshCw className={isRefreshing ? \'spin\' : \'\'} size={14} /> REFRESH</button>'
replacement3 = '''<button className="tool-button" onClick={() => fetch(BASE_URL + '/demo/incident', { method: 'POST' }).then(() => window.location.reload())}><AlertTriangle size={14} /> SIMULATE FAILURE</button>
<button className="tool-button" onClick={() => window.location.reload()}><RefreshCw className={isRefreshing ? 'spin' : ''} size={14} /> REFRESH</button>'''

content = content.replace(target3, replacement3)

with open('final_front_end/components/argus-dashboard.tsx', 'w') as f:
    f.write(content)
