// Run the actual uncompiled widget with SDK/hook boundaries stubbed offline.
const fs = require('node:fs');
const vm = require('node:vm');
function renderWidget(options = {}) {
  const jsx = (type, props) => typeof type === 'function' ? type(props || {}) : {type, props: props || {}};
  const atom = value => ({get: () => value, set: v => { value = v; }});
  let translations = {};
  const context = {
    atom, jsx, jsxs: jsx, cn: (...args) => args.filter(Boolean).join(' '),
    useValue: a => a.get(), useEffect: () => {}, useMemo: f => f(),
    useRef: v => ({current: v}), useState: v => [typeof v === 'function' ? v() : v, () => {}],
    usePluginI18n: () => (key, ...args) => typeof translations[key] === 'function' ? translations[key](...args) : translations[key] || key,
    useQuery: () => ({data: options.data, isError: !!options.isError, isPlaceholderData: !!options.isPlaceholderData, isFetching: !!options.isFetching}),
    useQueryClient: () => ({invalidateQueries: () => {}}), useMutation: () => ({}),
    // Keep tooltip labels separate from trigger text/native title. This is a
    // structural test seam, not a simulation of hover (see hover test).
    Tip: props => ({type: 'Tip', props}),
    TooltipProvider: props => props.children,
    TooltipTrigger: props => ({type:'TooltipTrigger',props}),
    TooltipContent: props => ({type:'TooltipContent',props}),
    Tooltip: props => {const [trigger,content]=props.children; return {type:'Tip',props:{...content.props,label:content.props.children,children:trigger.props.children}};},
    StatusDot: ({tone}) => jsx('span', {'data-tone': tone}),
    Input: 'input', Switch: 'input', SegmentedControl: 'span', icons: {},
    // Quota commands route to the focused profile's owner (#26); the pane reads
    // `host.state.focusedSessionOwner` before it can render, so the offline
    // harness has to provide the same read-only atom shape as the SDK.
    host: {state: {focusedSessionOwner: {get: () => null, set: () => {}, subscribe: () => () => {}}}},
    PANES_AREA: '', ROUTES_AREA: '', SIDEBAR_NAV_AREA: '', STATUSBAR_AREAS: {right: ''},
    fmtDayTime: new Intl.DateTimeFormat('en-US'), console,
    Date, Intl, setTimeout, clearTimeout,
  };
  const file = options.source || require('node:path').join(__dirname, '../desktop/plugin.js');
  const source = fs.readFileSync(file, 'utf8').replace(/^import[\s\S]*?from ["'][^"']+["'];/gm, '').replace('export default {', 'const plugin = {');
  vm.createContext(context);
  const storageMap = options.storage || {};
  const testCtx = {
    storage: {get: k => (k in storageMap ? storageMap[k] : undefined), set: (k,v) => {storageMap[k]=v;}, remove: k => {delete storageMap[k];}},
    i18n: {register: v => {translations = v.en;}},
    register: (contrib) => {context.REGISTRATIONS.push(contrib); return () => {const i=context.REGISTRATIONS.indexOf(contrib); if(i>=0) context.REGISTRATIONS.splice(i,1);};},
  };
  context.REGISTRATIONS = [];
  vm.runInContext(source + '\nplugin.register(TEST_CTX); paneDetailAtom.set(TEST_MODE);', Object.assign(context, {
    TEST_MODE: options.mode || 'dense',
    TEST_CTX: testCtx,
  }));
  vm.runInContext('statusbarModeAtom.set(TEST_STATUS_MODE); disabledProvidersAtom.set(TEST_DISABLED);', Object.assign(context, { TEST_STATUS_MODE: options.statusMode || 'all', TEST_DISABLED: options.disabled || [] }));
  context.PROVIDER = options.provider;
  context.WIDGET_ID = options.id || 'deepseek';
  if (options.component === 'registrations') return context.REGISTRATIONS;
  const expression = options.component === 'status' ? 'StatusBar()' : options.component === 'chip' ? 'ProviderChip({pid:WIDGET_ID,provider:PROVIDER})' : options.component === 'row' ? 'ProviderRow({id:WIDGET_ID,provider:PROVIDER})' : options.component === 'worst' ? 'QuotaChipWithBar()' : 'QuotaPane()';
  return vm.runInContext(expression, context);
}
module.exports = {renderWidget};
if (require.main === module) process.stdout.write(JSON.stringify(renderWidget(JSON.parse(fs.readFileSync(0, 'utf8')))));
