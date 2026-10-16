"""Status-bar-only refresh must return fresh data in one bounded request."""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = r'''
const fs=require('fs');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('const QUOTA_QUERY_KEY =');
const end=source.indexOf('\n// Statusbar tips',start);
let now=1000000,calls=[],payload={age_s:180,fetched_at:'old-cache',providers:{copilot:{windows:[{label:'Monthly',used_percent:70}]}}};
const fresh={age_s:0,fetched_at:'new-snapshot',providers:{copilot:{windows:[{label:'Monthly',used_percent:12}]}}};
const scope={connectionId:'local',profile:'hermes-agent'};
const host={state:{focusedSessionOwner:scope},profileRoutes:async()=>[{...scope,targetProfile:'hermes-agent'}],requestProfile:async(route,method,params,timeout)=>{
 calls.push({route,method,params,timeout});
 if(params.argv.includes('--max-age'))payload=fresh;
 if(params.argv.includes('refresh')){payload=fresh;return {code:0,output:'refreshed'};}
 return {code:0,output:JSON.stringify(payload)};
}};
const interval={};
const create=new Function('host','CTX','Date','setTimeout','clearTimeout','refreshIntervalAtom','useValue','useQueryClient','useQuery',source.slice(start,end)+';return {useQuota,quotaCli};');
const api=create(host,{storage:{get:()=>null,set:()=>{}}},{now:()=>now},()=>1,()=>{},interval,a=>a===interval?60:scope,()=>({invalidateQueries:()=>{}}),o=>o);
(async()=>{const options=api.useQuota();const data=await options.queryFn();await new Promise(r=>setImmediate(r));
const cadence=typeof options.refetchInterval==='function'?options.refetchInterval({state:{data:{age_s:10},dataUpdatedAt:now-20000,status:'success'}}):options.refetchInterval;
const retryCadence=typeof options.refetchInterval==='function'?options.refetchInterval({state:{data:{age_s:180},dataUpdatedAt:now,status:'error'}}):options.refetchInterval;
console.log(JSON.stringify({data,calls,cadence,retryCadence,background:options.refetchIntervalInBackground}));})().catch(e=>{console.error(e);process.exitCode=1;});
'''

def run():
    result=subprocess.run(['node','-e',SCRIPT,str(ROOT/'desktop/plugin.js')],capture_output=True,text=True,timeout=20)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)

class StatusBarAutoRefreshTests(unittest.TestCase):
    def test_first_background_request_returns_new_data_not_a_stale_snapshot(self):
        result=run()
        self.assertEqual(result['data']['fetched_at'],'new-snapshot')
        self.assertEqual(len(result['calls']),1,'Do not chain cache read, refresh, and another cache read')
        self.assertIn('--max-age',result['calls'][0]['params']['argv'])
        self.assertTrue(result['background'])

    def test_refresh_deadline_uses_snapshot_age_not_last_read_completion(self):
        result=run()
        self.assertEqual(result['cadence'],30000,'10-second cache age plus 20 seconds elapsed leaves 30 seconds, not a new 60-second wait')
        self.assertEqual(result['retryCadence'],60000,'Errors must back off rather than spin')

    def test_bounded_child_allows_startup_plus_provider_sweep(self):
        result=run()
        call=result['calls'][0]
        self.assertGreaterEqual(call['params']['timeout'],60,'The command budget must allow interpreter startup plus the bounded 20-second provider sweep')
        self.assertLess(call['params']['timeout']*1000,call['timeout'])

if __name__=='__main__':unittest.main()
