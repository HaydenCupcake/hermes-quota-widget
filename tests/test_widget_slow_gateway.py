"""Quota must tolerate slow profile discovery without orphaning CLI workers."""
import json
import subprocess
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
class SlowDesktopRoutingTests(unittest.TestCase):
 def test_slow_profile_discovery_and_bounded_backend_command(self):
  script = r'''
const fs=require('fs');const src=fs.readFileSync(process.argv[1],'utf8');
let now=0; const scope={connectionId:'local',profile:'hermes-agent'};let call;
const host={profileRoutes:async()=>{now+=22000;return [{...scope,targetProfile:'hermes-agent'}]},requestProfile:async(route,method,params,timeout)=>{call={route,method,params,timeout};return {code:0,output:'{}'}}};
const start=src.indexOf('const QUOTA_QUERY_KEY =');const end=src.indexOf('\nfunction useQuota()',start);
const api=new Function('host','CTX','Date','setTimeout','clearTimeout',src.slice(start,end)+'; return {quotaCli};')(host,{}, {now:()=>now},()=>1,()=>{});
(async()=>{try{await api.quotaCli(scope,['quota','status','--json','--cached']);console.log(JSON.stringify({call}));}catch(e){console.log(JSON.stringify({error:String(e)}));}})();
'''
  result=subprocess.run(['node','-e',script,str(ROOT/'desktop/plugin.js')],capture_output=True,text=True,timeout=90)
  self.assertEqual(result.returncode,0,result.stderr)
  data=json.loads(result.stdout)
  self.assertNotIn('error',data,'22-second profile discovery must not make fresh quota unreachable')
  self.assertGreater(data['call']['timeout'],0)
  self.assertGreater(data['call']['params'].get('timeout',0),0,'CLI child must have an explicit bounded lifetime')
  self.assertLess(data['call']['params']['timeout']*1000,data['call']['timeout'])
if __name__=='__main__':unittest.main()
