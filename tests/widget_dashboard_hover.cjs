// Actual plugin + actual Hermes SDK Tip/Radix, mounted in Chromium.
// Data transport is synthetic/offline. Styling uses the installed host CSS.
// node widget_dashboard_hover.cjs DESKTOP_DIR OUTPUT_DIR THEME_CAPTURE_JSON
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const assert = require('node:assert/strict');
const desktop = path.resolve(process.argv[2]);
const out = path.resolve(process.argv[3]);
const theme = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
const req = createRequire(path.join(desktop, 'package.json'));
const {build} = req('esbuild');
const {chromium} = req('playwright');
const fixture = {age_s:0, fetched_at:new Date().toISOString(), providers:{}};
for (const pid of ['anthropic','antigravity','commandcode','copilot','cursor','deepseek','experientiallabs','gemini','grok','kimi','minimax','nous','ollama','openai-codex','opencode-go','openrouter','zai']) fixture.providers[pid]={unavailable_reason:'no-credentials',windows:[]};
fixture.providers['openai-codex']={accounts:[52,83,100,97].map((remaining,index)=>({label:`QA account ${index+1}`,plan:index===3?'Plus':'Team',windows:[{label:'Session',used_percent:100-remaining,reset_at:new Date(Date.now()+3*3600000).toISOString()},{label:'Weekly',used_percent:25+index,reset_at:new Date(Date.now()+6*86400000).toISOString()}]}))};
fixture.providers.copilot={plan:'Individual',windows:[{label:'Premium requests',used_percent:0,reset_at:new Date(Date.now()+18*86400000).toISOString()}]};
fixture.providers.nous={plan:'Tier 2',details:['Spend this period: $8.49 (no cap reported)','Rate limits: 400 RPM · 4M TPM · 16.8k RPH']};
fixture.providers.openrouter={account_balances:[{currency:'USD',total_balance:-0.2}],details:[]};
const sdk = `
import React from 'react';
export {Tip,Tooltip,TooltipContent,TooltipProvider,TooltipTrigger} from ${JSON.stringify(path.join(desktop,'src/components/ui/tooltip.tsx'))};
export const atom=value=>({get:()=>value,set:v=>{value=v}});
export const useValue=a=>a.get();
let snapshot=${JSON.stringify(fixture)},listeners=new Set();
window.quotaSetData=data=>{snapshot=data;listeners.forEach(l=>l(data));};
window.quotaFixture=JSON.parse(JSON.stringify(snapshot));
export const useQuery=()=>{const [data,setData]=React.useState(snapshot);React.useEffect(()=>{listeners.add(setData);return()=>listeners.delete(setData);},[]);return {data,isError:false,isPlaceholderData:false};};
export const useQueryClient=()=>({invalidateQueries:()=>{}}),useMutation=()=>({});
export const usePluginI18n=()=>key=>key,cn=(...a)=>a.filter(Boolean).join(' ');
export const fmtDayTime=new Intl.DateTimeFormat('en-US');
export const host={state:{focusedSessionOwner:atom(null)},navigate:p=>{window.navigated=p}};
export const Input='input',Switch='input',SegmentedControl='span',StatusDot='span';
export const icons={Activity:props=>React.createElement('svg',{...props,width:14,height:14,'data-graph-icon':true,viewBox:'0 0 24 24'},React.createElement('path',{d:'M3 12h4l3-8 4 16 3-8h4',fill:'none',stroke:'currentColor',strokeWidth:2}))};
export const PANES_AREA='',ROUTES_AREA='',SIDEBAR_NAV_AREA='',STATUSBAR_AREAS={right:''};`;
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const plugin=path.resolve(__dirname,'../desktop/plugin.js'),source=fs.readFileSync(plugin,'utf8');
 await build({stdin:{contents:`import React from 'react';import {createRoot} from 'react-dom/client';import {StatusBar} from 'quota-under-test';createRoot(document.getElementById('root')).render(React.createElement(StatusBar));`,resolveDir:desktop,loader:'jsx'},bundle:true,format:'iife',outfile:path.join(out,'hover.js'),jsx:'automatic',nodePaths:[path.join(desktop,'node_modules'),path.resolve(desktop,'../../node_modules')],plugins:[{name:'offline-boundaries',setup(b){
 b.onResolve({filter:/^quota-under-test$/},()=>({path:plugin,namespace:'quota'}));
 b.onLoad({filter:/.*/,namespace:'quota'},()=>({contents:source+'\nexport {StatusBar};',resolveDir:desktop,loader:'js'}));
 b.onResolve({filter:/^@hermes\/plugin-sdk$/},()=>({path:'sdk',namespace:'fixture'}));
 b.onLoad({filter:/.*/,namespace:'fixture'},()=>({contents:sdk,resolveDir:desktop,loader:'js'}));
 b.onResolve({filter:/^@\/(i18n|lib\/keybinds\/use-keybind-hint)$/},()=>({path:'hooks',namespace:'hooks'}));
 b.onLoad({filter:/.*/,namespace:'hooks'},()=>({contents:'export const useI18n=()=>({});export const useKeybindHint=()=>null;'}));
 b.onResolve({filter:/^@\//},a=>({path:path.join(desktop,'src',a.path.slice(2)+'.ts')}));
 } }]});
 let css='';
 for(const href of theme.stylesheets.filter(h=>h.startsWith('file:')&&(/index-|tooltip-/.test(h)))) css+=fs.readFileSync(require('node:url').fileURLToPath(href),'utf8')+'\n';
 fs.writeFileSync(path.join(out,'host.css'),css);
 fs.writeFileSync(path.join(out,'index.html'),'<!doctype html><html><head><link rel="stylesheet" href="host.css"><link rel="stylesheet" href="hover.css"><style>body{margin:0;font-family:system-ui,sans-serif;background:var(--ui-editor-surface-background);color:var(--ui-text-primary)}#root{position:fixed;bottom:0;left:0;right:0;height:28px;display:flex;align-items:center}</style></head><body><div id="root"></div><script src="hover.js"></script></body></html>');
 const browser=await chromium.launch({headless:true,channel:'chrome'}),results=[];
 try{
  for(const mode of ['dark','light']) for(const width of [1200,460,360]){
   const page=await browser.newPage({viewport:{width,height:900}}),errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   await page.route('**/*',route=>{const u=new URL(route.request().url()),name=u.pathname==='/'?'index.html':u.pathname.slice(1);if(u.origin==='http://quota.test'&&['index.html','hover.js','hover.css','host.css'].includes(name))return route.fulfill({path:path.join(out,name),contentType:name.endsWith('.js')?'application/javascript':name.endsWith('.css')?'text/css':'text/html'});return route.abort();});
   await page.goto('http://quota.test/');
   const tokens=mode==='dark'?theme.tokens:{...theme.tokens,'--ui-editor-surface-background':'#ffffff','--ui-text-primary':'#18202b','--ui-text-secondary':'#465365','--ui-text-tertiary':'#586575','--ui-stroke-secondary':'#e0e5ec','--ui-stroke-primary':'#c7d0dc','--ui-bg-card':'#f6f8fa','--ui-accent':'#1769c2','--ui-red':'#c53030','--ui-yellow':'#946500'};
   await page.evaluate(tokens=>{for(const[k,v]of Object.entries(tokens))document.documentElement.style.setProperty(k,v);},tokens);
   const button=page.getByRole('button');await button.waitFor();assert.equal(await button.count(),1);assert.equal((await button.innerText()).trim(),'Quota');
   assert.equal(await page.locator('[data-graph-icon]').count(),1);
   await button.hover();const bubble=page.locator('[data-slot="tooltip-content"]');await bubble.waitFor({state:'visible',timeout:4000});
   assert.equal(await bubble.locator('[data-quota-mini-provider]').count(),17,'Every provider represented');
   assert.equal(await bubble.locator('[data-quota-mini-provider="openai-codex"]').count(),1,'Codex has one shared header');
   assert.equal(await bubble.locator('[data-quota-mini-provider="openai-codex"] [data-quota-mini-account]').count(),4);
   assert.equal(await bubble.getByRole('progressbar').count(),9,'Every account window and provider category has a bar');
   const geometry=await bubble.evaluate(el=>{const r=el.getBoundingClientRect(),d=el.querySelector('[data-quota-mini]'),w=d.parentElement;const g=el.querySelector('[data-quota-mini-accounts="openai-codex"]');return {width:r.width,height:r.height,x:r.x,y:r.y,scrollHeight:w.scrollHeight,clientHeight:w.clientHeight,columns:getComputedStyle(g).gridTemplateColumns,overflow:d.scrollWidth>d.clientWidth+1,background:getComputedStyle(el).backgroundColor,color:getComputedStyle(d).color};});
   assert.equal(geometry.overflow,false,'No horizontal dashboard overflow');assert.ok(geometry.x>=0&&geometry.x+geometry.width<=width+1);
   if(width>=460){assert.ok(geometry.height<660,'All providers and four accounts fit a condensed dashboard');assert.equal(geometry.scrollHeight,geometry.clientHeight,'No clipping at desktop width');}
   if(width===360){
    await page.mouse.move(geometry.x+geometry.width/2,geometry.y+geometry.height/2);
    await page.mouse.wheel(0,600);
    assert.ok(await bubble.isVisible(),'Dashboard must stay open when moving into it to scroll');
    await page.waitForFunction(()=>document.querySelector('[data-slot="tooltip-label"] > div')?.scrollTop>0,{},{timeout:2000});
   }
   const updated=JSON.parse(JSON.stringify(fixture));updated.providers['openai-codex'].accounts[0].windows[0].used_percent=22;
   await page.evaluate(data=>window.quotaSetData(data),updated);
   await page.waitForFunction(()=>document.querySelector('[data-quota-mini-provider="openai-codex"] [role="progressbar"]').getAttribute('aria-valuenow')==='78');
   assert.ok(await bubble.isVisible(),'Updates while hovering without reopening');
   await page.screenshot({path:path.join(out,`${mode}-${width}.png`)});
   await page.mouse.move(width-20,40,{steps:8});await bubble.waitFor({state:'hidden',timeout:3000});
   await button.click();assert.equal(await page.evaluate(()=>window.navigated),'/quota');
   assert.deepEqual(errors,[]);results.push({mode,viewportWidth:width,...geometry,reactiveUpdate:true,scrollVerified:width===360,errors});await page.close();
  }
 }finally{await browser.close();}
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
