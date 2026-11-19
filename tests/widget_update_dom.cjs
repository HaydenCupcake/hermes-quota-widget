// Offline real-Chromium update flow. Run with NODE_PATH=C:/Users/xstah/harnessing-agents/node_modules node tests/widget_update_dom.cjs
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require('@playwright/test');
const reactDir = process.env.QUOTA_REACT_NODE_MODULES || 'C:/Users/xstah/tcg-vendor-book/apps/web/node_modules';
const react = fs.readFileSync(path.join(reactDir, 'react/umd/react.development.js'), 'utf8');
const reactDom = fs.readFileSync(path.join(reactDir, 'react-dom/umd/react-dom.development.js'), 'utf8');
const src = fs.readFileSync(path.join(__dirname, '../desktop/plugin.js'), 'utf8')
  .replace(/^import[\s\S]*?from ["'][^"']+["'];/gm, '').replace('export default {', 'const plugin = {');
const shim = `
const {useEffect,useMemo,useRef,useState} = React;
const jsx=(type,props)=>React.createElement(type,props), jsxs=jsx;
const atom=v=>({get:()=>v,set:x=>{v=x},subscribe:()=>()=>{}});
const cn=(...x)=>x.filter(Boolean).join(' '), fmtDayTime=new Intl.DateTimeFormat('en-US');
const useValue=a=>a.get();
let translations={}; const usePluginI18n=()=> (k,...a)=>typeof translations[k]==='function'?translations[k](...a):(translations[k]||k);
const host={state:{focusedSessionOwner:atom({connectionId:'local',profile:'test'})},profileRoutes:async()=>[{connectionId:'local',profile:'test',targetProfile:'test'}],requestProfile:async(r,m,p)=>{window.cliCalls.push(p.argv);return p.argv.includes('status')?{code:0,output:JSON.stringify(window.fixture)}:window.cliResult}};
const listeners=new Set();
const useQuery=o=>{const [state,setState]=useState({data:o.placeholderData,isLoading:!!o.enabled,isError:false});useEffect(()=>{let alive=true;const run=async()=>{try{const data=await o.queryFn();if(alive)setState({data,isLoading:false,isError:false})}catch(e){if(alive)setState({isError:true,isLoading:false})}};if(o.enabled)run();listeners.add(run);return()=>{alive=false;listeners.delete(run)}},[JSON.stringify(o.queryKey),o.enabled]);return state};
const useQueryClient=()=>({invalidateQueries:x=>{window.invalidated.push(x.queryKey);for(const f of listeners)f();return Promise.resolve()}});
const useMutation=()=>({mutate:()=>{},isPending:false});
const Input='input',Switch=()=>null,SegmentedControl=()=>null,StatusDot='span';
const Tooltip=({children})=>children,TooltipProvider=Tooltip,TooltipTrigger=Tooltip,TooltipContent=Tooltip;
const icons={RefreshCw:()=>null},PANES_AREA='',ROUTES_AREA='',SIDEBAR_NAV_AREA='',STATUSBAR_AREAS={right:''};
window.fetch=async()=>{window.fetchCount++; if(window.offline)throw Error('offline');return {ok:true,json:async()=>window.latest}};
`;
const boot = `
const storage={}; const ctx={storage:{get:k=>storage[k],set:(k,v)=>storage[k]=v,remove:k=>delete storage[k]},i18n:{register:v=>translations=v.en},register:()=>()=>{}};
plugin.register(ctx); window.storage=storage; window.refreshFixture=()=>{for(const f of listeners)f()}; window.root=ReactDOM.createRoot(document.getElementById('root')); window.mount=()=>window.root.render(jsx(QuotaPane,{})); window.mount();
`;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 let count=0;
 async function test(name, fn){try{await fn();console.log('PASS '+name);count++;}catch(e){console.error('FAIL '+name+'\n'+e.stack);throw e;}}
 async function pageFor(opts={}){
  const p=await browser.newPage(); await p.route('**/*',r=>r.abort());
  await p.setContent('<div id="root"></div>');
  await p.evaluate(o=>{window.fixture={providers:{},plugin_version:'2.11.0',installed_sha:'old',installed_date:'2026-01-01T00:00:00Z',...o.fixture};window.latest=o.latest||{sha:'new',commit:{committer:{date:'2026-02-01T00:00:00Z'}}};window.offline=!!o.offline;window.fetchCount=0;window.invalidated=[];window.cliCalls=[];window.cliResult={code:0,output:JSON.stringify({updated:true,widget_synced:true,...(o.result||{backend_changed:false})})};window.restarts=[];if(!o.noRecycle)window.hermesDesktop={recycleBackend:async p=>window.restarts.push(p)};},opts);
  await p.addScriptTag({content:react}); await p.addScriptTag({content:reactDom}); await p.addScriptTag({content:shim+'\n'+src+'\n'+boot}); return p;
 }
 try{
  await test('newer banner opens and focuses update settings',async()=>{const p=await pageFor();try{let b=p.getByRole('button',{name:'⬆ New version available — open settings to update'});await b.waitFor({timeout:3000});await b.click();await p.getByRole('button',{name:'Check for update'}).waitFor();assert.equal(await p.evaluate(()=>document.activeElement.id),'quota-update-section');}finally{await p.close()}});
  for(const [name,fixture,latest] of [
   ['older commit',{},{sha:'new',commit:{committer:{date:'2025-12-31T23:59:59Z'}}}],
   ['equal commit time',{},{sha:'new',commit:{committer:{date:'2026-01-01T00:00:00Z'}}}],
   ['same sha with newer time',{},{sha:'old',commit:{committer:{date:'2026-02-01T00:00:00Z'}}}],
  ]) await test(name+' is not an update',async()=>{const p=await pageFor({fixture,latest});try{await p.getByRole('button',{name:'Settings'}).click();await p.getByText('No newer version available.').waitFor();assert.equal(await p.getByRole('button',{name:'Update now'}).count(),0);assert.equal(await p.getByRole('button',{name:/⬆ New version/}).count(),0)}finally{await p.close()}});
  for(const fixture of [{installed_sha:null},{installed_date:null},{installed_date:'bad'}]) await test('missing or invalid stamp is not stamped '+JSON.stringify(fixture),async()=>{const p=await pageFor({fixture});try{await p.getByRole('button',{name:'Settings'}).click();await p.getByText(/Installation not stamped/).waitFor();assert.equal(await p.evaluate(()=>window.fetchCount),0);assert.equal(await p.getByRole('button',{name:'Update now'}).count(),0)}finally{await p.close()}});
  for(const opts of [{offline:true},{latest:{sha:'new',commit:{committer:{date:'not a date'}}}},{latest:{sha:'new',commit:{committer:{date:'2026-02-30T00:00:00Z'}}}}]) await test('network or invalid commit shows an error '+JSON.stringify(opts),async()=>{const p=await pageFor(opts);try{await p.getByRole('button',{name:'Settings'}).click();await p.getByText(/Could not check for updates/).waitFor({timeout:3000});assert.equal(await p.getByRole('button',{name:'Update now'}).count(),0)}finally{await p.close()}});
  await test('force check bypasses cache and renders changed latest metadata',async()=>{const p=await pageFor();try{await p.getByRole('button',{name:/⬆ New version/}).click();assert.match(await p.locator('#quota-update-section').innerText(),/Latest SHA: new/);assert.equal(await p.evaluate(()=>window.fetchCount),1);await p.evaluate(()=>{window.latest={sha:'old',commit:{committer:{date:'2026-02-01T00:00:00Z'}}}});await p.getByRole('button',{name:'Check for update'}).click();await p.getByText('No newer version available.').waitFor();assert.equal(await p.evaluate(()=>window.fetchCount),2);assert.match(await p.locator('#quota-update-section').innerText(),/Latest SHA: old/)}finally{await p.close()}});
  await test('cache is keyed by sha and installed date',async()=>{const p=await pageFor();try{await p.getByRole('button',{name:/⬆ New version/}).waitFor();await p.evaluate(()=>{window.root.render(null)});await p.waitForTimeout(100);await p.evaluate(()=>window.mount());await p.getByRole('button',{name:/⬆ New version/}).waitFor();assert.equal(await p.evaluate(()=>window.fetchCount),1);await p.evaluate(()=>{window.fixture.installed_date='2026-03-01T00:00:00Z';window.refreshFixture()});await p.getByRole('button',{name:'Settings'}).click();await p.getByText('No newer version available.').waitFor();assert.equal(await p.evaluate(()=>window.fetchCount),2)}finally{await p.close()}});
  await test('expired cache and changed sha trigger fresh requests',async()=>{const p=await pageFor();try{await p.getByRole('button',{name:/⬆ New version/}).waitFor();await p.evaluate(()=>{const c=JSON.parse(window.storage.updateCheck);c.at=Date.now()-3600001;window.storage.updateCheck=JSON.stringify(c);window.root.render(null)});await p.waitForTimeout(100);await p.evaluate(()=>window.mount());await p.getByRole('button',{name:/⬆ New version/}).waitFor();assert.equal(await p.evaluate(()=>window.fetchCount),2);await p.evaluate(()=>{window.fixture.installed_sha='other';window.refreshFixture()});await p.waitForFunction(()=>window.fetchCount===3)}finally{await p.close()}});
  for(const backendChanged of [false,true]) await test('apply backend_changed='+backendChanged+' and explicit restart',async()=>{const p=await pageFor({result:{success:true,backend_changed:backendChanged}});try{await p.getByRole('button',{name:/⬆ New version/}).click();await p.getByRole('button',{name:'Update now'}).click();await p.getByText(backendChanged?/Update installed. Restart the backend/:/no backend restart needed/).waitFor();assert.deepEqual(await p.evaluate(()=>window.restarts),[]);assert.deepEqual(await p.evaluate(()=>window.cliCalls.filter(x=>x.includes('self-update'))),[['--profile','test','quota','self-update']]);assert.deepEqual(await p.evaluate(()=>window.invalidated),[['quota','widget','local','test']]);assert.equal(await p.evaluate(()=>window.storage.updateCheck),undefined);const restart=p.getByRole('button',{name:'Restart backend to finish update'});assert.equal(await restart.count(),backendChanged?1:0);if(backendChanged){await p.getByText(/interrupts all sessions/).waitFor();await restart.click();await p.getByText('Backend restart requested.').waitFor();assert.deepEqual(await p.evaluate(()=>window.restarts),['test'])}}finally{await p.close()}});
  await test('missing restart capability provides manual Desktop fallback',async()=>{const p=await pageFor({noRecycle:true,result:{success:true,backend_changed:true}});try{await p.getByRole('button',{name:/⬆ New version/}).click();await p.getByRole('button',{name:'Update now'}).click();await p.getByText(/Restart Hermes Desktop to finish/).waitFor();assert.equal(await p.getByRole('button',{name:'Restart backend to finish update'}).count(),0)}finally{await p.close()}});
  await test('installed widget version and short SHA stay honest during skew',async()=>{const p=await pageFor({fixture:{plugin_version:'1.0.0',installed_sha:'0123456789abcdef'}});try{await p.getByRole('button',{name:'Settings'}).click();await p.getByText('Installed version: 2.11.0').waitFor();await p.getByText('Installed SHA: 0123456').waitFor()}finally{await p.close()}});
  await test('missing stamp gives actionable guidance',async()=>{const p=await pageFor({fixture:{installed_date:null}});try{await p.getByRole('button',{name:'Settings'}).click();await p.getByText(/reinstall.*fork/i).waitFor()}finally{await p.close()}});
  await test('no-op update reports no change rather than claiming installation',async()=>{const p=await pageFor({result:{updated:false,backend_changed:false}});try{await p.getByRole('button',{name:/⬆ New version/}).click();await p.getByRole('button',{name:'Update now'}).click();await p.getByText('Already up to date; no update was installed.').waitFor({timeout:3000});assert.equal(await p.getByRole('button',{name:'Restart backend to finish update'}).count(),0)}finally{await p.close()}});
  await test('unsynced widget does not report success',async()=>{const p=await pageFor({result:{widget_synced:false,backend_changed:false}});try{await p.getByRole('button',{name:/⬆ New version/}).click();await p.getByRole('button',{name:'Update now'}).click();await p.getByText(/Update failed:/).waitFor({timeout:3000})}finally{await p.close()}});
  await test('structured update failure is shown and does not restart',async()=>{const p=await pageFor({result:{success:false,error:'synthetic update failure'}});try{await p.getByRole('button',{name:/⬆ New version/}).click();await p.getByRole('button',{name:'Update now'}).click();await p.getByText('Update failed: synthetic update failure').waitFor({timeout:3000});assert.deepEqual(await p.evaluate(()=>window.restarts),[])}finally{await p.close()}});
 }finally{await browser.close();} console.log(`TOTAL ${count} passed`);
})().catch(e=>{process.exitCode=1});
