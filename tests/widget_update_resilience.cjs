// Real React Query + Chromium; only the host RPC and GitHub are simulated.
// NODE_PATH=C:/Users/xstah/tcg-vendor-book-pre-prod/apps/web/node_modules node tests/widget_update_resilience.cjs
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require('playwright-core');
const desktop = 'C:/Users/xstah/AppData/Local/hermes/hermes-agent/apps/desktop';
const esbuild = require(require.resolve('esbuild', {paths:[desktop]}));
const file = process.env.QUOTA_WIDGET_SOURCE || path.join(__dirname, '../desktop/plugin.js');
const source = fs.readFileSync(file, 'utf8').replace(/^import[\s\S]*?from ["'][^"']+["'];/gm, '').replace('export default {', 'const plugin = {');
const shim = `
const React = require('react');
const ReactDOM = require('react-dom/client');
const {QueryClient,QueryClientProvider,useQuery,useQueryClient,useMutation,focusManager,onlineManager}=require('@tanstack/react-query');
const {useEffect,useMemo,useRef,useState,useSyncExternalStore}=React;
const jsx=(type,props)=>React.createElement(type,props),jsxs=jsx;
const atom=initial=>{let value=initial;const listeners=new Set();return {get:()=>value,set:v=>{value=v;for(const f of listeners)f()},subscribe:f=>{listeners.add(f);return()=>listeners.delete(f)}}};
const useValue=a=>useSyncExternalStore(a.subscribe,a.get,a.get);
const cn=(...x)=>x.filter(Boolean).join(' '),fmtDayTime=new Intl.DateTimeFormat('en-US');
let translations={};const usePluginI18n=()=> (k,...a)=>typeof translations[k]==='function'?translations[k](...a):(translations[k]||k);
const host={state:{focusedSessionOwner:atom({connectionId:'local',profile:'test'})},profileRoutes:async()=>[{connectionId:'local',profile:'test',targetProfile:'test'}],requestProfile:async(r,m,p,timeout)=>{
 window.calls.push({argv:p.argv,timeout,childTimeout:p.timeout});
 if(p.argv.includes('self-update')){window.applyCount++;if(window.behavior==='hold' || (window.behavior==='timeout-then-hold' && window.applyCount>1))return new Promise((resolve,reject)=>window.pending={resolve,reject});if((window.behavior==='timeout-once' || window.behavior==='timeout-then-hold') && window.applyCount===1 || window.behavior==='always-timeout')throw Error('cli.exec: timeout');if(window.behavior==='refusal')return {code:-1,blocked:true,hint:'Update refused: tracked files are dirty.'};if(window.behavior==='forever')return new Promise(()=>{});return {code:0,output:JSON.stringify({updated:true,widget_synced:true,backend_changed:false})}}
 return {code:0,output:JSON.stringify(window.fixture)};
}};
const Input='input',Switch=()=>null,SegmentedControl=()=>null,StatusDot='span';
const Tooltip=({children})=>children,TooltipProvider=Tooltip,TooltipTrigger=Tooltip,TooltipContent=Tooltip;
const icons={RefreshCw:()=>null},PANES_AREA='',ROUTES_AREA='',SIDEBAR_NAV_AREA='',STATUSBAR_AREAS={right:''};
window.fetch=async()=>({ok:true,json:async()=>({sha:'newsha',commit:{committer:{date:'2026-02-01T00:00:00Z'}}})});
`;
const boot = `
const storage={}; const ctx={storage:{get:k=>storage[k],set:(k,v)=>storage[k]=v,remove:k=>delete storage[k]},i18n:{register:v=>translations=v.en},register:()=>()=>{}};
plugin.register(ctx); const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:Infinity}}});
window.focusToggle=()=>{focusManager.setFocused(false);focusManager.setFocused(true)};
window.onlineToggle=()=>{onlineManager.setOnline(false);onlineManager.setOnline(true)};
window.extraMount=()=>{const div=document.createElement('div');document.body.append(div);ReactDOM.createRoot(div).render(jsx(QueryClientProvider,{client,children:jsx(StatusBar,{})}))};
ReactDOM.createRoot(document.getElementById('root')).render(jsx(QueryClientProvider,{client,children:jsx(QuotaPane,{})}));
`;
async function main(){
 const bundle=await esbuild.build({stdin:{contents:shim+'\n'+source+'\n'+boot,resolveDir:desktop,loader:'js'},bundle:true,platform:'browser',format:'iife',write:false});
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 let passed=0;
 async function test(name,fn){try{await fn();console.log('PASS '+name);passed++}catch(e){console.error('FAIL '+name+'\n'+e.stack);throw e}}
 async function pageFor(behavior){const p=await browser.newPage();await p.clock.install({time:new Date('2026-03-01T00:00:00Z')});await p.setContent('<div id="root"></div>');await p.evaluate(behavior=>{window.fixture={providers:{},plugin_version:'2.11.0',installed_sha:'oldsha',installed_date:'2026-01-01T00:00:00Z',age_s:0};window.behavior=behavior;window.calls=[];window.applyCount=0;},behavior);await p.addScriptTag({content:bundle.outputFiles[0].text});await p.getByRole('button',{name:/New version available/}).click();return p}
 const statusCount=p=>p.evaluate(()=>window.calls.filter(c=>c.argv.includes('status')).length);
 try{
 await test('deferred update shows ticking progress and yields interval, focus, reconnect and mount',async()=>{const p=await pageFor('hold');try{await p.getByRole('button',{name:'Update now'}).click();await p.waitForFunction(()=>window.applyCount===1);await p.clock.runFor(2200);assert.match(await p.locator('#quota-update-section').innerText(),/waiting for backend queue/i);assert.match(await p.locator('#quota-update-section').innerText(),/[12]\s*s/i);const before=await statusCount(p);await p.evaluate(()=>{window.focusToggle();window.onlineToggle();window.extraMount()});await p.clock.runFor(65000);assert.equal(await statusCount(p),before,'status calls must not start while apply is unresolved');await p.evaluate(()=>window.pending.resolve({code:0,output:JSON.stringify({updated:true,widget_synced:true,backend_changed:false})}));await p.clock.runFor(100);await p.getByText(/no backend restart needed/).waitFor();await p.clock.runFor(100);assert.ok(await statusCount(p)>before,'poll resumes after apply settles')}finally{await p.close()}});
 await test('gateway timeout is retried once and succeeds',async()=>{const p=await pageFor('timeout-once');try{await p.getByRole('button',{name:'Update now'}).click();await p.getByText(/no backend restart needed/).waitFor();assert.equal(await p.evaluate(()=>window.applyCount),2);assert.ok((await p.evaluate(()=>window.calls.filter(c=>c.argv.includes('self-update')).every(c=>c.childTimeout<=90))))}finally{await p.close()}});
 await test('applying phase is visible after gateway responds and retry is pending',async()=>{const p=await pageFor('timeout-then-hold');try{await p.getByRole('button',{name:'Update now'}).click();await p.waitForFunction(()=>window.applyCount===2);await p.clock.runFor(1100);await p.getByText(/applying…/i).waitFor();await p.evaluate(()=>window.pending.resolve({code:0,output:JSON.stringify({updated:true,widget_synced:true,backend_changed:false})}));await p.getByText(/no backend restart needed/).waitFor()}finally{await p.close()}});
 await test('repeated gateway timeouts stop after one retry and three cached reads',async()=>{const p=await pageFor('always-timeout');try{await p.getByRole('button',{name:'Update now'}).click();await p.clock.runFor(91000);await p.getByRole('button',{name:'Retry'}).waitFor();assert.equal(await p.evaluate(()=>window.applyCount),2);const calls=await p.evaluate(()=>window.calls.filter(c=>c.argv.includes('--cached')));assert.equal(calls.length,3);assert.ok(calls.every(c=>c.childTimeout<=30))}finally{await p.close()}});
 await test('renderer deadline recovers confirmed receipt and restart requirement',async()=>{const p=await pageFor('forever');try{await p.getByRole('button',{name:'Update now'}).click();await p.waitForFunction(()=>window.applyCount===1);await p.evaluate(()=>{window.fixture.installed_sha='newsha';window.fixture.update_receipt={from_sha:'oldsha',to_sha:'newsha',widget_synced:true,backend_changed:true}});await p.clock.runFor(241000);await p.getByText(/update applied.*UI caught up/i).waitFor({timeout:3000});assert.equal(await p.getByRole('button',{name:'Restart backend to finish update'}).count(),0);await p.getByText(/Restart Hermes Desktop to finish/).waitFor();assert.ok(await statusCount(p)<=4)}finally{await p.close()}});
 await test('advanced stamp without receipt is not claimed as completed',async()=>{const p=await pageFor('forever');try{await p.getByRole('button',{name:'Update now'}).click();await p.waitForFunction(()=>window.applyCount===1);await p.evaluate(()=>window.fixture.installed_sha='newsha');await p.clock.runFor(340000);await p.getByText(/stamp.*newsha/i).waitFor();assert.match(await p.locator('#quota-update-section').innerText(),/confirm|unconfirmed/i);assert.equal(await p.getByText(/update applied.*UI caught up/i).count(),0)}finally{await p.close()}});
 await test('refusal is visible and retry can succeed',async()=>{const p=await pageFor('refusal');try{await p.getByRole('button',{name:'Update now'}).click();await p.clock.runFor(91000);await p.getByRole('alert').getByText(/tracked files are dirty/).waitFor();await p.evaluate(()=>window.behavior='success');await p.getByRole('button',{name:'Retry'}).click();await p.getByText(/no backend restart needed/).waitFor()}finally{await p.close()}});
 await test('unresolved calls end in error and a retry affordance',async()=>{const p=await pageFor('forever');try{await p.getByRole('button',{name:'Update now'}).click();await p.waitForFunction(()=>window.applyCount===1);await p.clock.runFor(340000);await p.getByRole('alert').getByText(/timeout/i).waitFor({timeout:3000});assert.equal(await p.getByRole('button',{name:'Retry'}).count(),1);assert.equal(await p.getByText(/Updating…/).count(),0)}finally{await p.close()}});
 await test('unresolved request cannot be duplicated by Retry',async()=>{const p=await pageFor('forever');try{await p.getByRole('button',{name:'Update now'}).click();await p.waitForFunction(()=>window.applyCount===1);await p.clock.runFor(340000);await p.getByRole('button',{name:'Retry'}).click();await p.clock.runFor(100);assert.equal(await p.evaluate(()=>window.applyCount),1,'timed-out renderer must not launch another writer while the gateway request is unresolved');await p.getByRole('alert').getByText(/previous.*pending/i).waitFor()}finally{await p.close()}});
 }finally{await browser.close()};console.log('TOTAL '+passed+' passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
