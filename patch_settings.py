import sys

with open('final_front_end/components/argus-dashboard.tsx', 'r') as f:
    content = f.read()

target4 = '<button className="icon-button" aria-label="Settings"><Settings2 size={17} /></button>'
replacement4 = '''<Dialog>
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
</Dialog>'''

content = content.replace(target4, replacement4)

with open('final_front_end/components/argus-dashboard.tsx', 'w') as f:
    f.write(content)
