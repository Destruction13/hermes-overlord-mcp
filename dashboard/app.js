const DATA = window.HERMES_DASHBOARD_DATA;

const STORAGE_KEY = 'hermes.user.v1';

const COLORS = {
  ingress: '#526175',
  director: '#246bfe',
  council: '#0f8b8d',
  execution: '#23845c',
  control: '#ad6507',
  output: '#7048b8',
  storage: '#526175',
  auxiliary: '#7b5967',
  healthy: '#23845c',
  partial: '#ad6507',
  gated: '#ad6507',
  failed: '#bd3d3d',
  removed: '#bd3d3d',
  unknown: '#657287',
};

const attentionHealth = new Set(['partial', 'failed', 'gated', 'removed', 'unknown']);
const profiles = DATA.profiles;
const profileById = new Map(profiles.map((profile) => [profile.id, profile]));
const mcpById = new Map(DATA.mcpInventory.map((server) => [`mcp:${server.name}`, server]));
const flowNodeById = new Map(DATA.flow.nodes.map((node) => [node.id, node]));

const DENSITY_SCALE = { compact: 0.82, cozy: 1, comfortable: 1.16 };

const EDGE_STYLES = { neutral: '#748094', brand: '#b98200', phase: '#2563eb', semantic: '#2563eb', severity: '#b45309' };

const THEME_OPTIONS = [
  { id: 'light', name: 'Светлая', note: 'чистая карта' },
  { id: 'dark', name: 'Темная', note: 'ночной пульт' },
  { id: 'sepia', name: 'Теплая', note: 'мягкая бумага' },
  { id: 'graphite', name: 'Графит', note: 'контрастный стенд' },
];

const EDGE_MODE_OPTIONS = [
  { id: 'bezier', name: 'Поток', note: 'мягкие дуги' },
  { id: 'orthogonal', name: 'Маршрут', note: 'ломаные трассы' },
  { id: 'straight', name: 'Прямая', note: 'диагностика' },
];

const EDGE_COLOR_OPTIONS = [
  { id: 'semantic', name: 'Смысл', note: 'входы, работа, контроль, выход' },
  { id: 'phase', name: 'Фазы', note: 'цвет источника' },
  { id: 'severity', name: 'Риски', note: 'акцент на проблемах' },
  { id: 'brand', name: 'Бренд', note: 'единый цвет' },
  { id: 'neutral', name: 'Спокойно', note: 'минимум шума' },
];

const EDGE_KIND_COLORS = {
  input: '#2563eb',
  orchestration: '#0f766e',
  dispatch: '#7c3aed',
  execution: '#16803d',
  control: '#b45309',
  storage: '#64748b',
  output: '#be185d',
  mcp: '#0891b2',
  disabled: '#94a3b8',
};

const PROJECT_BOARD = 'overlord';
const PROJECT_POLL_MS = 2500;
const PROJECT_LOG_POLL_MS = 2000;
const PROJECT_LOG_DEFAULT_TAIL_BYTES = 120_000;
const PROJECT_NODE_W = 250;
const PROJECT_NODE_H = 124;
const PROJECT_ACTIVE_STATUSES = new Set(['ready', 'running', 'blocked', 'review']);
const PROJECT_STATUS_LABELS = {
  live: 'делает',
  running: 'делает',
  ready: 'очередь',
  pending: 'очередь',
  review: 'проверка',
  blocked: 'стоп',
  stale: 'нет сигнала',
  done: 'готово',
  used: 'участвовал',
  handoff: 'передано',
  received: 'получено',
  waiting: 'ждет',
  missing: 'нет следа',
  mounted: 'память',
  archived: 'закрыто',
  triage: 'очередь',
  todo: 'запланировано',
  idle: 'тихо',
};

function projectApiBase() {
  if (window.HERMES_PROJECT_API) return String(window.HERMES_PROJECT_API).replace(/\/$/, '');
  return window.location.protocol === 'file:' ? 'http://127.0.0.1:8787' : '';
}

const INITIAL_QUERY = new URLSearchParams(window.location.search || '');
const INITIAL_MODE = ['flow', 'projects', 'mcp'].includes(INITIAL_QUERY.get('mode')) ? INITIAL_QUERY.get('mode') : (userConfig.mode || 'flow');
const INITIAL_PROJECT_VIEW = INITIAL_QUERY.get('view') === 'archive' ? 'archive' : 'active';
const INITIAL_PROJECT_ID = INITIAL_QUERY.get('project_id') || null;

const HEALTH_ICON = { healthy: '●', partial: '◐', failed: '⊘', gated: '⌧', removed: '⊘', unknown: '—' };

const MCP_TAGS = {
  filesystem: ['files', 'core', 'write'], github: ['code', 'repo', 'review'], mem0: ['memory', 'context'], 'sequential-thinking': ['reasoning', 'planning'], deepcontext: ['code-analysis', 'context'], serena: ['code-analysis', 'lsp'], codegraph: ['code-analysis', 'graph'], codegraphcontext: ['code-analysis', 'graph'],
  context7: ['docs', 'reference'], 'ref-tools': ['docs', 'reference'], openaiDeveloperDocs: ['docs', 'openai'], exa: ['web-search', 'research'], tavily: ['web-search', 'research'],
  obsidian: ['notes', 'knowledge'], notion: ['workspace', 'knowledge'], linear: ['tasks', 'product'],
  'chrome-devtools': ['browser', 'debug'], playwright: ['browser', 'testing'], magic: ['ui', 'components'], shadcn: ['ui', 'components'], vercel: ['deploy', 'frontend'], canva: ['design', 'assets'], 'canva-dev': ['design', 'api'], browserstack: ['testing', 'devices'], storybook: ['ui', 'catalog'],
  prisma: ['database', 'backend'], semgrep: ['security', 'static-analysis'], socket: ['security', 'supply-chain'], trivy: ['security', 'containers'], gitguardian: ['security', 'secrets'],
  'docker-gateway': ['runtime', 'mcp'], 'cloudflare-api': ['deploy', 'platform'],
};

const PROFILE_TAGS = {
  overlord: ['orchestration', 'director'], olproduct: ['product', 'scope'], olarchitect: ['architecture', 'contracts'], olresearcher: ['research', 'evidence'], olrisk: ['risk', 'security'], olux: ['ux', 'design'], olfrontend: ['frontend', 'ui'], olbackend: ['backend', 'api'], olautomation: ['automation', 'ops'], olwatchdog: ['monitoring', 'ops'], olreviewer: ['review', 'qa'], olsynth: ['synthesis', 'docs'], nerood: ['auxiliary'], diana: ['auxiliary'],
};

DATA.mcpInventory.forEach((server) => {
  server.tags = [...new Set([...(server.tags || []), ...(MCP_TAGS[server.name] || ['mcp'])])];
});
profiles.forEach((profile) => {
  profile.tags = [...new Set([...(profile.tags || []), ...(PROFILE_TAGS[profile.id] || [profile.phase])])];
});

const MCP_CATEGORIES = {
  'Ядро / память': ['filesystem', 'github', 'mem0', 'sequential-thinking', 'deepcontext', 'serena', 'codegraph', 'codegraphcontext'],
  'Документы / ресерч': ['context7', 'ref-tools', 'openaiDeveloperDocs', 'exa', 'tavily'],
  'Product / workspace': ['obsidian', 'notion', 'linear'],
  'Frontend / UX': ['chrome-devtools', 'playwright', 'magic', 'shadcn', 'vercel', 'canva', 'canva-dev', 'browserstack', 'storybook'],
  'Backend / risk': ['prisma', 'semgrep', 'socket', 'trivy', 'gitguardian'],
  'Платформа / runtime': ['docker-gateway', 'cloudflare-api'],
};

const MCP_CATEGORY_PHASE = {
  'Ядро / память': 'storage',
  'Документы / ресерч': 'council',
  'Product / workspace': 'director',
  'Frontend / UX': 'execution',
  'Backend / risk': 'control',
  'Платформа / runtime': 'auxiliary',
};

const categoryByMcp = new Map();
Object.entries(MCP_CATEGORIES).forEach(([category, names]) => names.forEach((name) => categoryByMcp.set(name, category)));
const categoryNames = Object.keys(MCP_CATEGORIES);
const categoryOf = (name) => categoryByMcp.get(name) || 'Платформа / runtime';

const PHASE_ICONS = {
  ingress: '↘',
  director: '◆',
  council: '●',
  execution: '■',
  control: '▲',
  output: '◇',
  storage: '▣',
  auxiliary: '○',
};

const SHORT_ROLE = {
  user: 'Постановщик задачи',
  cli: 'CLI-вход',
  telegram: 'Telegram-вход',
  gateway: 'Внешний шлюз',
  kanban: 'Очередь задач',
  vault: 'Долгая память',
  memory: 'Контекст',
  overlord: 'Генеральный директор',
  olproduct: 'Продуктовый стратег',
  olarchitect: 'Архитектор',
  olresearcher: 'Исследователь',
  olrisk: 'Риск-офицер',
  olux: 'UX-офицер',
  olfrontend: 'Фронтенд',
  olbackend: 'Бэкенд',
  olautomation: 'Automation / Ops',
  olwatchdog: 'Мониторинг',
  olreviewer: 'Ревьюер',
  olsynth: 'Синтезатор',
  nerood: 'Легкий оркестратор',
  diana: 'Общий профиль',
};

const EDGE_COLORS = {
  user: '#475569',
  cli: '#334155',
  telegram: '#229ed9',
  gateway: '#0f766e',
  kanban: '#7c3aed',
  overlord: '#2563eb',
  olproduct: '#0284c7',
  olarchitect: '#7c3aed',
  olresearcher: '#0891b2',
  olrisk: '#dc2626',
  olux: '#db2777',
  olfrontend: '#16a34a',
  olbackend: '#d97706',
  olautomation: '#0d9488',
  olwatchdog: '#64748b',
  olreviewer: '#9333ea',
  olsynth: '#111827',
  nerood: '#7f1d1d',
  diana: '#9f1239',
};

const BUILTIN_PRESETS = [
  { id: 'executive', name: 'Executive', mode: 'flow', appMode: 'present', density: 'comfortable', theme: 'light', edgeColor: 'brand', showLabels: false },
  { id: 'engineer', name: 'Engineer', mode: 'flow', appMode: 'view', density: 'cozy', theme: 'light', edgeColor: 'neutral', showLabels: true },
  { id: 'risk-audit', name: 'Risk audit', mode: 'mcp', appMode: 'view', density: 'compact', theme: 'graphite', edgeColor: 'severity', attentionOnly: true },
  { id: 'mcp-map', name: 'MCP map', mode: 'mcp', appMode: 'view', density: 'cozy', theme: 'light', mcpView: 'map', edgeColor: 'neutral' },
  { id: 'onboarding', name: 'Onboarding', mode: 'flow', appMode: 'view', density: 'comfortable', theme: 'sepia', edgeColor: 'phase', selectedId: 'overlord' },
];

function defaultUserConfig() {
  return {
    version: 1,
    theme: 'light',
    brand: '#B58900',
    density: 'cozy',
    appMode: 'view',
    mcpView: 'map',
    edgeMode: 'bezier',
    edgeColor: 'semantic',
    showGrid: true,
    snap: true,
    lock: false,
    auxiliaryOpen: false,
    tagFilter: '',
    hiddenNodes: [],
    nodes: {},
    viewNodes: {},
    transforms: {},
    edges: {},
    mcp: {},
    lanes: [],
    presets: [],
  };
}

function readUserConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultUserConfig();
    const parsed = JSON.parse(raw);
    return { ...defaultUserConfig(), ...parsed, version: 1 };
  } catch (_error) {
    return defaultUserConfig();
  }
}

let userConfig = readUserConfig();
applyStoredMcpAssignments();
const undoStack = [];
const redoStack = [];

function applyStoredMcpAssignments() {
  Object.entries(userConfig.mcp || {}).forEach(([name, config]) => {
    (config.enabledProfilesAdd || []).forEach((profileId) => {
      const profile = profileById.get(profileId);
      const inventory = mcpById.get(`mcp:${name}`);
      if (!profile || !inventory || profile.mcp.some((server) => server.name === name)) return;
      profile.mcp.push({ name, enabled: true, transport: inventory.transports?.[0] || 'unknown', health: inventory.health, note: inventory.note, humanNote: inventory.humanNote, tags: inventory.tags || [] });
      if (!inventory.enabledProfiles.includes(profileId)) inventory.enabledProfiles.push(profileId);
      if (!inventory.profiles.includes(profileId)) inventory.profiles.push(profileId);
    });
  });
}

const state = {
  mode: INITIAL_MODE,
  selectedId: 'overlord',
  selectedTab: 'overview',
  appMode: userConfig.appMode,
  mcpView: userConfig.mcpView,
  density: userConfig.density,
  catalogCategory: 'all',
  catalogHealth: 'all',
  tagFilter: userConfig.tagFilter || '',
  search: '',
  showLabels: true,
  attentionOnly: false,
  showAllMcpEdges: false,
  transform: { x: 60, y: 80, scale: 0.78 },
  transformScope: null,
  dragging: null,
  nodeDrag: null,
  suppressClick: false,
  previousNodeIds: new Set(),
  lastSoulTrigger: null,
  graph: { nodes: [], edges: [], lanes: [], width: 3000, height: 900 },
  projects: {
    board: INITIAL_QUERY.get('board') || PROJECT_BOARD,
    view: INITIAL_PROJECT_VIEW,
    selectedProjectId: INITIAL_PROJECT_ID,
    data: null,
    error: null,
    loading: false,
    poller: null,
    railScrollLeft: 0,
    logTaskId: null,
    logNodeId: null,
    logData: null,
    logError: null,
    logPoller: null,
    logTailBytes: PROJECT_LOG_DEFAULT_TAIL_BYTES,
    logFollow: true,
    logScrollTop: 0,
    inspectorScrollTop: 0,
    requestSeq: 0,
  },
};

const viewport = document.getElementById('boardViewport');
const canvas = document.getElementById('boardCanvas');
const edgeLayer = document.getElementById('edgeLayer');
const laneLayer = document.getElementById('laneLayer');
const nodeLayer = document.getElementById('nodeLayer');
const minimap = document.getElementById('minimap');

function phaseLabel(phase) {
  return DATA.phases[phase]?.label || phase;
}

function phaseName(phase) {
  return {
    ingress: 'вход',
    director: 'директор',
    council: 'совет',
    execution: 'исполнение',
    control: 'контроль',
    output: 'итог',
    storage: 'память/системы',
    auxiliary: 'вспомогательный',
  }[phase] || phase;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function enabledMcp(profile) {
  return profile.mcp.filter((server) => server.enabled);
}

function disabledMcp(profile) {
  return profile.mcp.filter((server) => !server.enabled);
}

function shortText(text, max = 34) {
  if (!text) return '';
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function problemMcpCount() {
  return DATA.mcpInventory.filter((server) => attentionHealth.has(server.health)).length;
}

function setTooltip(node, text) {
  if (!text) return;
  node.classList.add('has-tooltip');
  node.dataset.tooltip = text;
  node.setAttribute('aria-label', text);
}

function roleSubtitle(id, fallback = '') {
  return SHORT_ROLE[id] || fallback || id;
}

function layoutScope() {
  if (state.mode === 'flow') return 'flow';
  if (state.mode === 'projects') return 'projects';
  if (state.mcpView !== 'map') return `mcp:${state.mcpView}`;
  if (state.showAllMcpEdges) return 'mcp:map:all';
  if (state.selectedId?.startsWith('mcp:')) return 'mcp:map:selected-mcp';
  return 'mcp:map:selected-profile';
}

function transformScope() {
  if (state.mode === 'mcp') return `mcp:${state.mcpView}`;
  if (state.mode === 'projects') return 'projects';
  return 'flow';
}

function defaultTransformForScope(scope = transformScope()) {
  if (scope === 'flow') return { x: 60, y: 80, scale: 0.78 };
  if (scope === 'projects') return { x: 44, y: 70, scale: 0.86 };
  if (scope === 'mcp:map') return { x: 60, y: 80, scale: 0.72 };
  return { x: 0, y: 0, scale: 0.78 };
}

function activateTransformScope() {
  const scope = transformScope();
  if (state.transformScope === scope) return;
  saveTransform(true);
  state.transformScope = scope;
  state.transform = { ...defaultTransformForScope(scope), ...(userConfig.transforms?.[scope] || {}) };
}

function saveTransform(write = true) {
  if (!state.transformScope) return;
  userConfig.transforms = userConfig.transforms || {};
  userConfig.transforms[state.transformScope] = {
    x: Math.round(state.transform.x),
    y: Math.round(state.transform.y),
    scale: Number(state.transform.scale.toFixed(3)),
  };
  if (write) localStorage.setItem(STORAGE_KEY, JSON.stringify(userConfig));
}

function scopedNodeConfig(id, create = false) {
  const scope = layoutScope();
  userConfig.viewNodes = userConfig.viewNodes || {};
  if (create && !userConfig.viewNodes[scope]) userConfig.viewNodes[scope] = {};
  return userConfig.viewNodes[scope]?.[id];
}

function edgeKind(edge) {
  if (edge.enabled === false || edge.label === 'off') return 'disabled';
  if (edge.label === 'uses') return 'mcp';
  if (['verdict', 'gate', 'heartbeat'].includes(edge.label)) return 'control';
  if (['scope', 'architecture', 'research', 'risk', 'ux', 'dispatch'].includes(edge.label)) return edge.label === 'dispatch' ? 'dispatch' : 'orchestration';
  if (['execute', 'automate', 'build'].includes(edge.label)) return 'execution';
  if (['memory', 'vault', 'persist', 'queue'].includes(edge.label) || ['kanban', 'vault', 'memory'].includes(edge.to)) return 'storage';
  if (['final', 'synth', 'output'].includes(edge.label) || edge.to === 'olsynth') return 'output';
  if (['user', 'cli', 'telegram', 'gateway'].includes(edge.from)) return 'input';
  return profileById.get(edge.from)?.phase === 'control' ? 'control' : 'orchestration';
}

function edgeColor(source, edge = null) {
  const kind = edge ? edgeKind(edge) : 'orchestration';
  if (userConfig.edgeColor === 'brand') return userConfig.brand || EDGE_STYLES.brand;
  if (userConfig.edgeColor === 'phase') return COLORS[profileById.get(source)?.phase] || COLORS.storage;
  if (userConfig.edgeColor === 'severity') return kind === 'control' || kind === 'disabled' ? EDGE_KIND_COLORS.control : EDGE_KIND_COLORS.storage;
  if (userConfig.edgeColor === 'semantic') return EDGE_KIND_COLORS[kind] || EDGE_STYLES.semantic;
  return EDGE_STYLES.neutral;
}

function markerId(source, color = '') {
  return `arrow-${String(source).replace(/[^a-zA-Z0-9_-]/g, '-')}-${String(color).replace(/[^a-zA-Z0-9_-]/g, '')}`;
}

function appendArrowMarker(defs, id, color) {
  const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
  marker.setAttribute('id', id);
  marker.setAttribute('viewBox', '0 0 10 10');
  marker.setAttribute('refX', '8');
  marker.setAttribute('refY', '5');
  marker.setAttribute('markerWidth', '8');
  marker.setAttribute('markerHeight', '8');
  marker.setAttribute('orient', 'auto-start-reverse');
  const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  arrow.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
  arrow.setAttribute('fill', color);
  marker.append(arrow);
  defs.append(marker);
}

function persistConfig(pushUndo = false) {
  if (pushUndo) {
    undoStack.push(JSON.stringify(userConfig));
    if (undoStack.length > 100) undoStack.shift();
    redoStack.length = 0;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(userConfig));
  applyUserConfig();
}

function restoreConfig(snapshot) {
  userConfig = { ...defaultUserConfig(), ...JSON.parse(snapshot), version: 1 };
  state.appMode = userConfig.appMode;
  state.mcpView = userConfig.mcpView;
  state.density = userConfig.density;
  state.tagFilter = userConfig.tagFilter || '';
  localStorage.setItem(STORAGE_KEY, JSON.stringify(userConfig));
  applyUserConfig();
  refreshGraph();
}

function applyUserConfig() {
  document.documentElement.dataset.theme = userConfig.theme || 'light';
  document.body.dataset.mode = state.appMode || 'view';
  document.body.dataset.density = userConfig.density || 'cozy';
  document.body.classList.toggle('presentation-mode', state.appMode === 'present');
  document.body.classList.toggle('constructor-mode', state.appMode === 'constructor');
  document.body.classList.toggle('hide-grid', !userConfig.showGrid);
  document.documentElement.style.setProperty('--brand', userConfig.brand || '#B58900');
}

function saveNodePosition(id, x, y) {
  const scope = layoutScope();
  userConfig.viewNodes = userConfig.viewNodes || {};
  userConfig.viewNodes[scope] = userConfig.viewNodes[scope] || {};
  userConfig.viewNodes[scope][id] = { ...(userConfig.viewNodes[scope][id] || {}), position: { x: Math.round(x), y: Math.round(y) } };
  persistConfig(true);
}

function applyNodeOverrides(node) {
  const legacy = state.mode === 'flow' ? userConfig.nodes?.[node.id] : null;
  const override = { ...(legacy || {}), ...(scopedNodeConfig(node.id) || {}) };
  if (override?.position) {
    node.x = override.position.x;
    node.y = override.position.y;
  }
  if (override?.label) node.label = override.label;
  if (override?.role) node.subtitle = override.role;
  if (override?.accent) node.accent = override.accent;
  if (userConfig.hiddenNodes.includes(node.id)) node.hidden = true;
  return node;
}

function allTags() {
  const counts = new Map();
  [...profiles, ...DATA.mcpInventory].forEach((item) => (item.tags || []).forEach((tag) => counts.set(tag, (counts.get(tag) || 0) + 1)));
  return [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

function initials(id) {
  return id.replace(/^ol/, '').slice(0, 2).toUpperCase();
}

function addMcpToProfile(mcpName, profileId) {
  const profile = profileById.get(profileId);
  const inventory = mcpById.get(`mcp:${mcpName}`);
  if (!profile || !inventory) return false;
  if (!profile.mcp.some((server) => server.name === mcpName)) {
    profile.mcp.push({ name: mcpName, enabled: true, transport: inventory.transports?.[0] || 'unknown', health: inventory.health, note: inventory.note, humanNote: inventory.humanNote, tags: inventory.tags || [] });
  }
  if (!inventory.enabledProfiles.includes(profileId)) inventory.enabledProfiles.push(profileId);
  if (!inventory.profiles.includes(profileId)) inventory.profiles.push(profileId);
  userConfig.mcp[mcpName] = userConfig.mcp[mcpName] || {};
  const additions = new Set(userConfig.mcp[mcpName].enabledProfilesAdd || []);
  additions.add(profileId);
  userConfig.mcp[mcpName].enabledProfilesAdd = [...additions];
  persistConfig(true);
  refreshGraph();
  return true;
}

function selectedEntity() {
  return profileById.get(state.selectedId)
    || mcpById.get(state.selectedId)
    || flowNodeById.get(state.selectedId)
    || state.graph.nodes.find((node) => node.id === state.selectedId)
    || profileById.get('overlord');
}

function entityLabel(id) {
  if (id.startsWith('mcp:')) return id.slice(4);
  const graphNode = state.graph.nodes.find((node) => node.id === id);
  return profileById.get(id)?.id || flowNodeById.get(id)?.label || graphNode?.label || graphNode?.taskTitle || id;
}

function profileMatches(profile) {
  if (state.tagFilter && !(profile.tags || []).includes(state.tagFilter)) return false;
  if (!state.search) return true;
  const haystack = [
    profile.id,
    profile.title,
    profile.responsibility,
    profile.phase,
    profile.model,
    profile.ru?.summary,
    profile.ru?.does,
    profile.ru?.responsible,
    profile.ru?.communicates,
    ...(profile.tags || []),
    ...profile.owns,
    ...profile.mcp.map((server) => server.name),
  ].join(' ').toLowerCase();
  return haystack.includes(state.search);
}

function mcpMatches(server) {
  if (state.attentionOnly && !attentionHealth.has(server.health)) return false;
  if (state.tagFilter && !(server.tags || []).includes(state.tagFilter)) return false;
  if (!state.search) return true;
  return [server.name, server.health, server.note, server.humanNote, ...(server.tags || []), ...server.enabledProfiles, ...server.disabledProfiles]
    .join(' ')
    .toLowerCase()
    .includes(state.search);
}

function buildFlowGraph() {
  const nodes = [];
  const add = (id, x, y, w = 178, h = 82) => {
    const profile = profileById.get(id);
    const raw = flowNodeById.get(id) || profile;
    if (!raw) return;
    nodes.push({
      id,
      type: profile ? 'profile' : (raw.type || 'system'),
      phase: profile?.phase || raw.phase,
      label: profile?.id || raw.label || id,
      subtitle: roleSubtitle(id, raw.ru?.summary || profile?.ru?.summary || profile?.title || raw.summary || raw.type || phaseLabel(raw.phase)),
      x,
      y,
      w,
      h,
      health: 'healthy',
    });
  };

  add('user', 60, 170, 150, 72);
  add('cli', 300, 80, 160, 72);
  add('telegram', 300, 250, 160, 72);
  add('gateway', 540, 170, 170, 72);
  add('kanban', 800, 170, 170, 72);
  add('overlord', 1060, 170, 190, 88);

  ['olproduct', 'olarchitect', 'olresearcher', 'olrisk', 'olux'].forEach((id, index) => add(id, 1380, 40 + index * 122, 190, 84));
  ['olfrontend', 'olbackend', 'olautomation'].forEach((id, index) => add(id, 1740, 115 + index * 132, 190, 84));
  ['olwatchdog', 'olreviewer'].forEach((id, index) => add(id, 2090, 150 + index * 145, 190, 84));
  add('olsynth', 2400, 220, 190, 84);
  add('vault', 2670, 80, 170, 72);
  add('memory', 2670, 210, 170, 72);
  if (userConfig.auxiliaryOpen) {
    add('nerood', 1050, 520, 180, 78);
    add('diana', 1050, 640, 180, 78);
  } else {
    nodes.push({ id: 'auxiliary-group', type: 'system', phase: 'auxiliary', label: 'Auxiliary (2)', subtitle: 'Nerood + Diana', x: 1050, y: 560, w: 190, h: 76, health: 'healthy' });
  }

  const visibleNodes = nodes.map(applyNodeOverrides).filter((node) => !node.hidden);
  const validIds = new Set(visibleNodes.map((node) => node.id));
  const edges = DATA.flow.edges
    .filter(([from, to]) => validIds.has(from) && validIds.has(to))
    .map(([from, to, label]) => ({ from, to, label }));

  return {
    width: 2920,
    height: 790,
    nodes: visibleNodes,
    edges,
    lanes: [
      ['Ingress', 30, 30, 720, 340, 'ingress'],
      ['Director', 1010, 30, 280, 280, 'director'],
      ['Council', 1330, 15, 290, 660, 'council'],
      ['Execution', 1690, 60, 300, 470, 'execution'],
      ['Control', 2040, 95, 300, 370, 'control'],
      ['Output', 2350, 150, 280, 250, 'output'],
      ['Memory / Systems', 2630, 30, 270, 360, 'storage'],
      ['Auxiliary', 1010, 460, 280, 300, 'auxiliary'],
    ],
  };
}

function buildProjectGraph() {
  const payload = state.projects.data;
  if (!payload || !payload.nodes || !payload.nodes.length) {
    return {
      width: 980,
      height: 560,
      nodes: [{
        id: 'project-empty', type: 'system', phase: 'storage', label: state.projects.error ? 'Нет live-соединения' : 'Нет активных проектов',
        subtitle: state.projects.error || (state.projects.view === 'archive' ? 'В архиве пока нет закрытых слепков.' : 'В активе только реальные задачи в работе.'), x: 80, y: 130, w: 300, h: 112, health: state.projects.error ? 'gated' : 'healthy',
      }],
      edges: [],
      lanes: [['Live projects', 40, 50, 880, 360, state.projects.error ? 'control' : 'storage']],
    };
  }

  const groups = new Map();
  payload.nodes.forEach((node) => {
    const depth = Number(node.depth || 0);
    if (!groups.has(depth)) groups.set(depth, []);
    groups.get(depth).push(node);
  });
  const nodes = [];
  const lanes = [];
  const depths = [...groups.keys()].sort((a, b) => a - b);
  let maxRows = 1;
  depths.forEach((depth) => {
    const group = groups.get(depth).slice().sort((a, b) => {
      if (a.is_running !== b.is_running) return a.is_running ? -1 : 1;
      if ((a.status || '') !== (b.status || '')) return String(a.status || '').localeCompare(String(b.status || ''));
      return Number(a.created_at || 0) - Number(b.created_at || 0);
    });
    maxRows = Math.max(maxRows, group.length);
    const x = 68 + depth * (PROJECT_NODE_W + 118);
    group.forEach((task, index) => {
      const y = 100 + index * (PROJECT_NODE_H + 42);
      nodes.push({
        ...task,
        id: task.id,
        type: 'project-task',
        phase: task.phase || 'execution',
        label: task.assignee || 'unassigned',
        taskTitle: task.title || task.task_id,
        subtitle: task.latest_activity || task.subtitle || 'waiting',
        x,
        y,
        w: PROJECT_NODE_W,
        h: PROJECT_NODE_H,
        health: task.is_stale ? 'gated' : task.liveness === 'pending' ? 'partial' : task.status === 'blocked' ? 'failed' : task.is_running ? 'healthy' : PROJECT_ACTIVE_STATUSES.has(task.status) ? 'partial' : 'unknown',
      });
    });
    const laneLabel = group.find((node) => node.stage_label)?.stage_label || phaseLabel(group[0]?.phase || 'storage');
    lanes.push([laneLabel, x - 28, 44, PROJECT_NODE_W + 58, Math.max(250, 92 + group.length * (PROJECT_NODE_H + 42)), group[0]?.phase || 'storage']);
  });

  const validIds = new Set(nodes.map((node) => node.id));
  const edges = (payload.edges || [])
    .filter((edge) => validIds.has(edge.from) && validIds.has(edge.to))
    .map((edge) => ({ from: edge.from, to: edge.to, label: edge.label || 'handoff', enabled: edge.active !== false, active: Boolean(edge.active), kind: edge.kind || 'handoff' }));
  return {
    width: Math.max(1080, 160 + depths.length * (PROJECT_NODE_W + 118)),
    height: Math.max(620, 150 + maxRows * (PROJECT_NODE_H + 42)),
    nodes,
    edges,
    lanes,
  };
}

function projectStatusLabel(node) {
  const key = node.liveness === 'live' ? 'live' : node.liveness === 'stale' ? 'stale' : node.liveness === 'pending' ? 'pending' : (node.status || 'todo');
  return PROJECT_STATUS_LABELS[key] || key;
}

async function loadProjectGraph(options = {}) {
  if (state.projects.loading && options.quiet) return;
  state.projects.loading = true;
  const hadNodes = Boolean(state.projects.data?.nodes?.length);
  const requestSeq = ++state.projects.requestSeq;
  const requestView = state.projects.view;
  const params = new URLSearchParams({ board: state.projects.board, view: requestView });
  if (state.projects.selectedProjectId) params.set('project_id', state.projects.selectedProjectId);
  try {
    const response = await fetch(`${projectApiBase()}/api/live/projects?${params.toString()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (requestSeq !== state.projects.requestSeq) return;
    if (payload.error) throw new Error(payload.error);
    state.projects.view = payload.view === 'archive' ? 'archive' : requestView;
    state.projects.data = payload;
    state.projects.error = null;
    state.projects.selectedProjectId = payload.project?.id || null;
    if (state.mode === 'projects') {
      const hasSelected = payload.nodes?.some((node) => node.id === state.selectedId);
      let selectedChanged = false;
      if (!hasSelected) {
        const running = payload.nodes?.find((node) => node.is_running);
        state.selectedId = (running || payload.nodes?.[0])?.id || 'project-empty';
        selectedChanged = true;
      }
      const preserveScroll = state.selectedId?.startsWith('task:');
      if (preserveScroll) captureProjectLogScroll();
      refreshGraph();
      if (preserveScroll) restoreProjectLogScroll();
      if (!options.quiet && (selectedChanged || !hadNodes)) focusSelection(state.selectedId);
    } else {
      renderStatus();
    }
  } catch (error) {
    if (requestSeq !== state.projects.requestSeq) return;
    state.projects.error = `Live API недоступен: ${error.message || error}`;
    if (state.mode === 'projects') refreshGraph(); else renderStatus();
  } finally {
    if (requestSeq === state.projects.requestSeq) state.projects.loading = false;
  }
}

function ensureProjectPolling() {
  if (state.mode === 'projects' && !state.projects.poller) {
    loadProjectGraph({ quiet: Boolean(state.projects.data) });
    state.projects.poller = window.setInterval(() => loadProjectGraph({ quiet: true }), PROJECT_POLL_MS);
  }
  if (state.mode !== 'projects' && state.projects.poller) {
    window.clearInterval(state.projects.poller);
    state.projects.poller = null;
  }
}

function captureProjectLogScroll() {
  const body = document.getElementById('inspectorBody');
  const log = body?.querySelector('.project-live-log');
  if (body) state.projects.inspectorScrollTop = body.scrollTop;
  if (!log) return;
  const gap = log.scrollHeight - log.scrollTop - log.clientHeight;
  state.projects.logFollow = gap < 28;
  state.projects.logScrollTop = log.scrollTop;
}

function restoreProjectLogScroll() {
  window.requestAnimationFrame(() => {
    const body = document.getElementById('inspectorBody');
    const log = body?.querySelector('.project-live-log');
    if (body && !state.projects.logFollow) body.scrollTop = state.projects.inspectorScrollTop;
    if (!log) return;
    if (state.projects.logFollow) {
      log.scrollTop = log.scrollHeight;
    } else {
      log.scrollTop = Math.min(state.projects.logScrollTop, log.scrollHeight);
    }
  });
}

async function loadProjectLog(taskId, nodeId = state.projects.logNodeId) {
  if (!taskId) return;
  state.projects.logTailBytes = PROJECT_LOG_DEFAULT_TAIL_BYTES;
  const params = new URLSearchParams({ board: state.projects.board, task_id: taskId, tail: String(PROJECT_LOG_DEFAULT_TAIL_BYTES) });
  const shouldRender = state.mode === 'projects' && state.selectedId === (nodeId || `task:${taskId}`);
  try {
    const response = await fetch(`${projectApiBase()}/api/live/log?${params.toString()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (shouldRender) captureProjectLogScroll();
    state.projects.logData = await response.json();
    state.projects.logError = null;
  } catch (error) {
    if (shouldRender) captureProjectLogScroll();
    state.projects.logData = null;
    state.projects.logError = `Лог недоступен: ${error.message || error}`;
  }
  if (shouldRender) {
    renderInspector();
    restoreProjectLogScroll();
  }
}

function ensureProjectLogPolling(taskId, nodeId = `task:${taskId}`) {
  if (state.projects.logTaskId === taskId && state.projects.logNodeId === nodeId && state.projects.logPoller) return;
  if (state.projects.logPoller) window.clearInterval(state.projects.logPoller);
  state.projects.logTaskId = taskId;
  state.projects.logNodeId = nodeId;
  state.projects.logData = null;
  state.projects.logError = null;
  state.projects.logFollow = true;
  state.projects.logScrollTop = 0;
  state.projects.inspectorScrollTop = 0;
  if (!taskId) return;
  loadProjectLog(taskId, nodeId);
  state.projects.logPoller = window.setInterval(() => loadProjectLog(taskId, nodeId), PROJECT_LOG_POLL_MS);
}

function buildMcpGraph() {
  const nodes = [];
  const edges = [];
  const profileOrder = ['overlord', 'olproduct', 'olarchitect', 'olresearcher', 'olrisk', 'olux', 'olfrontend', 'olbackend', 'olautomation', 'olwatchdog', 'olreviewer', 'olsynth', 'nerood', 'diana'];

  const mcpSubtitle = (server) => {
    const usedBy = server.enabledProfiles.slice(0, 5).join(', ');
    return server.humanNote || (usedBy ? `используют: ${usedBy}${server.enabledProfiles.length > 5 ? ` +${server.enabledProfiles.length - 5}` : ''}` : 'нет активных агентов');
  };
  const filteredInventory = DATA.mcpInventory.filter(mcpMatches);

  const selectedProfile = profileById.get(state.selectedId);
  if (selectedProfile && !state.showAllMcpEdges) {
    nodes.push({
      id: selectedProfile.id,
      type: 'profile',
      phase: selectedProfile.phase,
      label: selectedProfile.id,
      subtitle: roleSubtitle(selectedProfile.id, selectedProfile.ru?.summary || selectedProfile.title),
      x: 70,
      y: 350,
      w: 286,
      h: 132,
      health: 'healthy',
    });

    const grouped = new Map(categoryNames.map((category) => [category, []]));
    selectedProfile.mcp.forEach((profileServer) => {
      const inventory = mcpById.get(`mcp:${profileServer.name}`) || {
        name: profileServer.name,
        health: profileServer.health || 'unknown',
        note: profileServer.note || '',
        enabledProfiles: profileServer.enabled ? [selectedProfile.id] : [],
        disabledProfiles: profileServer.enabled ? [] : [selectedProfile.id],
        transports: [profileServer.transport].filter(Boolean),
      };
      if (!mcpMatches(inventory)) return;
      grouped.get(categoryOf(profileServer.name)).push({ profileServer, inventory });
    });

    const columns = categoryNames.map((category, index) => ({
      category,
      x: 455 + index * 260,
      y: 70,
      row: 0,
      phase: MCP_CATEGORY_PHASE[category] || 'auxiliary',
    }));
    const lanes = [['Выбранный агент', 38, 280, 360, 292, selectedProfile.phase]];
    let maxHeight = 720;
    columns.forEach((slot) => {
      const servers = grouped.get(slot.category).sort((a, b) => a.profileServer.name.localeCompare(b.profileServer.name));
      if (!servers.length) {
        nodes.push({
          id: `empty:${slot.category}`,
          type: 'empty',
          phase: slot.phase,
          label: 'нет MCP',
          subtitle: `В этой категории у ${selectedProfile.id} пусто`,
          x: slot.x,
          y: slot.y,
          w: 222,
          h: 82,
          health: 'unknown',
          category: slot.category,
        });
        slot.row += 1;
        lanes.push([slot.category, slot.x - 24, 22, 244, 190, slot.phase]);
        return;
      }
      servers.forEach(({ profileServer, inventory }) => {
        const y = slot.y + slot.row * 150;
        slot.row += 1;
        maxHeight = Math.max(maxHeight, y + 174);
        nodes.push({
          id: `mcp:${profileServer.name}`,
          type: 'mcp',
          phase: slot.phase,
          label: profileServer.name,
          subtitle: mcpSubtitle(inventory),
          x: slot.x,
          y,
          w: 222,
          h: 126,
          health: inventory.health || profileServer.health || 'unknown',
          category: slot.category,
        });
        edges.push({ from: selectedProfile.id, to: `mcp:${profileServer.name}`, label: profileServer.enabled ? 'uses' : 'off', enabled: profileServer.enabled });
      });
      lanes.push([slot.category, slot.x - 24, 22, 244, Math.max(190, 82 + slot.row * 150), slot.phase]);
    });

    return {
      width: 455 + columns.length * 260,
      height: maxHeight,
      nodes,
      edges,
      lanes,
    };
  }

  const selectedMcp = mcpById.get(state.selectedId);
  if (selectedMcp && !state.showAllMcpEdges) {
    const users = [
      ...selectedMcp.enabledProfiles.map((id) => ({ id, enabled: true })),
      ...selectedMcp.disabledProfiles.map((id) => ({ id, enabled: false })),
    ]
      .sort((a, b) => profileOrder.indexOf(a.id) - profileOrder.indexOf(b.id))
      .filter(({ id }) => {
        const profile = profileById.get(id);
        return profile && profileMatches(profile);
      });
    users.forEach(({ id, enabled }, index) => {
      const profile = profileById.get(id);
      const col = index % 2;
      const row = Math.floor(index / 2);
      const preview = enabledMcp(profile).slice(0, 3).map((server) => server.name).join(', ');
      nodes.push({
        id,
        type: 'profile',
        phase: profile.phase,
        label: profile.id,
        subtitle: roleSubtitle(id, preview || profile.ru?.summary || profile.title),
        x: 70 + col * 280,
        y: 78 + row * 138,
        w: 238,
        h: 112,
        health: enabled ? 'healthy' : 'gated',
      });
      edges.push({ from: id, to: `mcp:${selectedMcp.name}`, label: enabled ? 'uses' : 'off', enabled });
    });
    const hubY = Math.max(220, 78 + Math.floor(Math.max(0, users.length - 1) / 2) * 69);
    nodes.push({
      id: `mcp:${selectedMcp.name}`,
      type: 'mcp',
      phase: MCP_CATEGORY_PHASE[categoryOf(selectedMcp.name)] || 'storage',
      label: selectedMcp.name,
      subtitle: selectedMcp.note,
      x: 760,
      y: hubY,
      w: 286,
      h: 132,
      health: selectedMcp.health || 'unknown',
      category: categoryOf(selectedMcp.name),
    });
    const height = Math.max(720, 130 + Math.ceil(users.length / 2) * 138);
    return {
      width: 1120,
      height,
      nodes,
      edges,
      lanes: [
        ['Агенты, где подключен MCP', 36, 24, 600, height - 70, 'director'],
        ['Выбранный MCP', 710, Math.max(36, hubY - 74), 380, 286, MCP_CATEGORY_PHASE[categoryOf(selectedMcp.name)] || 'storage'],
      ],
    };
  }

  profileOrder.forEach((id, index) => {
    const profile = profileById.get(id);
    if (!profile || !profileMatches(profile)) return;
    const preview = enabledMcp(profile).slice(0, 4).map((server) => server.name).join(', ');
    nodes.push({
      id,
      type: 'profile',
      phase: profile.phase,
      label: profile.id,
      subtitle: roleSubtitle(id, preview || profile.ru?.summary || profile.title),
      x: 64,
      y: 72 + index * 132,
      w: 238,
      h: 110,
      health: 'healthy',
    });
  });

  const visibleProfiles = new Set(nodes.filter((node) => node.type === 'profile').map((node) => node.id));
  const categoryLayout = Object.fromEntries(categoryNames.map((category, index) => [category, {
    x: 430 + index * 258,
    y: 72,
    row: 0,
    phase: MCP_CATEGORY_PHASE[category] || 'auxiliary',
  }]));
  filteredInventory.forEach((server) => {
    const category = categoryOf(server.name);
    const slot = categoryLayout[category];
    const y = slot.y + slot.row * 132;
    slot.row += 1;
    nodes.push({
      id: `mcp:${server.name}`,
      type: 'mcp',
      phase: 'storage',
      label: server.name,
      subtitle: mcpSubtitle(server),
      x: slot.x,
      y,
      w: 222,
      h: 112,
      health: server.health || 'unknown',
      category,
    });
  });

  const visibleMcp = new Set(nodes.filter((node) => node.type === 'mcp').map((node) => node.id));
  profiles.forEach((profile) => {
    if (!visibleProfiles.has(profile.id)) return;
    profile.mcp.forEach((server) => {
      const target = `mcp:${server.name}`;
      if (!visibleMcp.has(target)) return;
      const selectedProfile = state.selectedId === profile.id;
      const selectedMcp = state.selectedId === target;
      edges.push({ from: profile.id, to: target, label: server.enabled ? 'uses' : 'off', enabled: server.enabled });
    });
  });

  return {
    width: 430 + categoryNames.length * 258,
    height: Math.max(1080, 130 + Math.max(profileOrder.length, ...Object.values(categoryLayout).map((slot) => slot.row)) * 132),
    nodes,
    edges,
    lanes: [
      ['Агенты', 32, 24, 306, Math.max(1010, 80 + profileOrder.length * 132), 'director'],
      ...Object.entries(categoryLayout).map(([category, slot]) => [category, slot.x - 24, 24, 244, Math.max(190, 82 + Math.max(1, slot.row) * 132), slot.phase]),
    ],
  };
}

function refreshGraph() {
  activateTransformScope();
  document.body.dataset.mapMode = state.mode;
  state.graph = state.mode === 'flow' ? buildFlowGraph() : state.mode === 'projects' ? buildProjectGraph() : buildMcpGraph();
  state.graph.nodes = state.graph.nodes.map(applyNodeOverrides).filter((node) => !node.hidden);
  const visibleIds = new Set(state.graph.nodes.map((node) => node.id));
  if (state.mode === 'projects' && !visibleIds.has(state.selectedId)) {
    state.selectedId = state.graph.nodes[0]?.id || 'project-empty';
  }
  state.graph.edges = state.graph.edges.filter((edge) => visibleIds.has(edge.from) && visibleIds.has(edge.to));
  canvas.style.width = `${state.graph.width}px`;
  canvas.style.height = `${state.graph.height}px`;
  edgeLayer.setAttribute('width', state.graph.width);
  edgeLayer.setAttribute('height', state.graph.height);
  edgeLayer.setAttribute('viewBox', `0 0 ${state.graph.width} ${state.graph.height}`);
  const graphVisible = state.mode !== 'mcp' || state.mcpView === 'map';
  document.getElementById('mcpPanel').hidden = graphVisible;
  viewport.hidden = !graphVisible;
  document.querySelector('.minimap-wrap').hidden = !graphVisible || state.mode === 'projects';
  document.querySelector('.legend-wrap').hidden = !graphVisible || state.mode === 'projects';
  if (graphVisible) {
    renderLanes();
    renderEdges();
    renderNodes();
  } else {
    laneLayer.innerHTML = '';
    edgeLayer.innerHTML = '';
    nodeLayer.innerHTML = '';
    renderMcpPanel();
  }
  applyTransform();
  renderNavigator();
  renderInspector();
  renderMinimap();
  renderMobileList();
  renderProjectRail();
  renderStatus();
  document.getElementById('mcpViewSwitch').hidden = state.mode !== 'mcp';
  updateMcpViewButtons();
  document.getElementById('boardTitle').textContent = state.mode === 'flow'
    ? 'Поток задач'
    : state.mode === 'projects'
      ? (state.projects.view === 'archive' ? 'Архив задач' : 'Живая линия задачи')
      : state.mcpView === 'matrix' ? 'MCP-матрица' : state.mcpView === 'catalog' ? 'Каталог MCP' : 'Карта агент -> MCP';
  document.getElementById('boardHint').textContent = state.mode === 'flow'
    ? 'Перетаскивай поле, крути колесо для масштаба, кликай ноду для деталей.'
    : state.mode === 'projects'
      ? 'User -> Codex -> Hermes -> Overlord -> реальные участники -> итог.'
      : 'Кликни агента или MCP: карта покажет только его реальные связи без паутины.';
  ensureProjectPolling();
}

function renderProjectRail() {
  const rail = document.getElementById('projectRail');
  if (!rail) return;
  rail.hidden = state.mode !== 'projects';
  if (state.mode !== 'projects') {
    rail.innerHTML = '';
    return;
  }
  const previousRailScroll = rail.querySelector('.project-rail-chips')?.scrollLeft ?? state.projects.railScrollLeft ?? 0;
  rail.innerHTML = '';
  const payload = state.projects.data;
  const projects = payload?.projects || [];
  const summary = el('div', 'project-rail-summary');
  const current = payload?.project;
  const viewSwitch = el('div', 'project-view-switch');
  [
    ['active', 'Актив'],
    ['archive', 'Архив'],
  ].forEach(([view, label]) => {
    const button = el('button', state.projects.view === view ? 'active' : '', label);
    button.type = 'button';
    button.addEventListener('click', () => {
      if (state.projects.view === view) return;
      state.projects.view = view;
      state.projects.selectedProjectId = null;
      state.selectedId = 'project-empty';
      loadProjectGraph();
    });
    viewSwitch.append(button);
  });
  summary.append(viewSwitch);
  summary.append(el('strong', null, current ? shortText(current.title || current.id, 72) : (state.projects.view === 'archive' ? 'Архив пуст' : 'Сейчас ничего не идет')));
  summary.append(el('span', null, state.projects.error || (current ? shortText(current.summary || 'Линия выполнения открыта', 96) : (state.projects.view === 'archive' ? 'Здесь будут закрытые слепки.' : 'В активе только реальные задачи.'))));
  rail.append(summary);
  if (!projects.length) {
    rail.append(el('div', 'project-empty-note', state.projects.error ? 'Live API недоступен.' : (state.projects.view === 'archive' ? 'Закрытых слепков пока нет.' : 'Активных задач сейчас нет.')));
    return;
  }
  const chips = el('div', 'project-rail-chips');
  chips.scrollLeft = previousRailScroll;
  chips.addEventListener('scroll', () => { state.projects.railScrollLeft = chips.scrollLeft; });
  projects.forEach((project) => {
    const active = payload?.project?.id === project.id;
    const button = el('button', `project-chip${active ? ' active' : ''}`);
    button.type = 'button';
    button.title = project.title || project.id;
    button.append(el('strong', null, shortText(project.title || project.id, 54)));
    button.append(el('span', null, shortText(project.summary || 'в работе', 84)));
    button.addEventListener('click', () => {
      state.projects.selectedProjectId = project.id;
      state.selectedId = 'project-empty';
      loadProjectGraph();
    });
    chips.append(button);
  });
  rail.append(chips);
  window.requestAnimationFrame(() => { chips.scrollLeft = previousRailScroll; });
}

function renderLanes() {
  laneLayer.innerHTML = '';
  state.graph.lanes.forEach(([label, x, y, w, h, phase]) => {
    const lane = el('div', 'lane');
    lane.style.left = `${x}px`;
    lane.style.top = `${y}px`;
    lane.style.width = `${w}px`;
    lane.style.height = `${h}px`;
    lane.style.borderColor = `${COLORS[phase]}44`;
    const count = state.graph.nodes.filter((node) => node.phase === phase && node.x >= x - 20 && node.x <= x + w + 20).length;
    const text = el('div', 'lane-label', state.mode === 'projects' ? label : `${label} (${count})`);
    text.style.color = COLORS[phase] || COLORS.storage;
    if (phase === 'auxiliary') {
      text.setAttribute('role', 'button');
      text.setAttribute('tabindex', '0');
      text.addEventListener('click', () => {
        userConfig.auxiliaryOpen = !userConfig.auxiliaryOpen;
        persistConfig(true);
        refreshGraph();
      });
    }
    lane.append(text);
    laneLayer.append(lane);
  });
}

function renderEdges() {
  const nodeMap = new Map(state.graph.nodes.map((node) => [node.id, node]));
  const selectedEdges = relatedEdgeIds(state.selectedId);
  const isHot = (edge) => edge.from === state.selectedId || edge.to === state.selectedId || selectedEdges.has(`${edge.from}->${edge.to}`);
  const visibleEdges = state.graph.edges.filter((edge) => {
    const override = userConfig.edges[`${edge.from}->${edge.to}`];
    if (override?.hidden) return false;
    if (state.mode === 'flow' && state.selectedId) {
      if (state.selectedId === 'overlord') return edge.from === state.selectedId;
      return edge.from === state.selectedId || edge.to === state.selectedId;
    }
    return true;
  });
  edgeLayer.innerHTML = '';
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  const markerColors = new Map();
  visibleEdges.forEach((edge, edgeIndex) => {
    const override = userConfig.edges[`${edge.from}->${edge.to}`] || {};
    const color = override.color || (edge.enabled === false ? EDGE_KIND_COLORS.disabled : edgeColor(edge.from, edge));
    markerColors.set(markerId(edge.from, color), color);
  });
  markerColors.forEach((color, id) => appendArrowMarker(defs, id, color));
  appendArrowMarker(defs, 'arrow-off', '#94a3b8');
  appendArrowMarker(defs, 'arrow-brand', userConfig.brand || EDGE_STYLES.brand);
  edgeLayer.append(defs);
  const targetOrder = new Map();
  visibleEdges.forEach((edge, edgeIndex) => {
    const list = targetOrder.get(edge.to) || [];
    list.push(edge);
    targetOrder.set(edge.to, list);
  });
  visibleEdges.forEach((edge, edgeIndex) => {
    const from = nodeMap.get(edge.from);
    const to = nodeMap.get(edge.to);
    if (!from || !to) return;
    const hot = isHot(edge);
    const dim = state.selectedId && !hot && state.mode === 'mcp' && state.showAllMcpEdges;
    const siblings = targetOrder.get(edge.to) || [edge];
    const route = { index: siblings.indexOf(edge), total: siblings.length };
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const kind = edgeKind(edge);
    path.setAttribute('class', `edge-path edge-${kind}${hot ? ' hot' : ''}${dim ? ' dim' : ''}${edge.active ? ' live' : ''}`);
    const d = edgePath(from, to, route, edge);
    path.setAttribute('d', d);
    const pathId = `edge-path-${edgeIndex}`;
    path.setAttribute('id', pathId);
    const override = userConfig.edges[`${edge.from}->${edge.to}`] || {};
    const color = override.color || (edge.enabled === false ? EDGE_KIND_COLORS.disabled : edgeColor(edge.from, edge));
    path.style.setProperty('--edge-color', color);
    path.setAttribute('marker-end', edge.enabled === false ? 'url(#arrow-off)' : `url(#${markerId(edge.from, color)})`);
    if (override.style === 'dashed') path.setAttribute('stroke-dasharray', '8 7');
    if (override.style === 'dotted') path.setAttribute('stroke-dasharray', '2 7');
    path.dataset.edgeId = `${edge.from}->${edge.to}`;
    path.style.pointerEvents = state.appMode === 'constructor' ? 'stroke' : 'none';
    if (state.appMode === 'constructor') {
      path.addEventListener('click', (event) => {
        event.stopPropagation();
        openEdgePopover(edge, event.clientX, event.clientY);
      });
    }
    if (edge.enabled === false) {
      path.setAttribute('stroke-dasharray', '7 6');
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = 'MCP отключен у профиля';
      path.append(title);
    }
    edgeLayer.append(path);
    if (state.mode === 'projects' && edge.active) {
      const packet = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      packet.setAttribute('class', 'edge-packet');
      packet.style.setProperty('--edge-color', color);
      const file = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      file.setAttribute('d', 'M -7 -8 H 3 L 8 -3 V 8 H -7 Z M 3 -8 V -3 H 8');
      const motion = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
      motion.setAttribute('dur', '1.8s');
      motion.setAttribute('repeatCount', 'indefinite');
      motion.setAttribute('rotate', 'auto');
      motion.setAttribute('path', d);
      packet.append(file, motion);
      edgeLayer.append(packet);
    }
    if (state.showLabels && state.transform.scale >= 0.55 && hot) {
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('class', `edge-label${dim ? ' dim' : ''}`);
      const mid = edgeMidpoint(from, to, route);
      label.setAttribute('x', mid.x);
      label.setAttribute('y', mid.y - 4);
      label.style.setProperty('--edge-color', color);
      label.textContent = override.label || edge.label;
      edgeLayer.append(label);
    }
  });
}

function edgePath(from, to, route = { index: 0, total: 1 }, edge = null) {
  const spread = (route.index - (route.total - 1) / 2) * 8;
  const forward = to.x >= from.x;
  const startX = forward ? from.x + from.w : from.x;
  const startY = from.y + from.h / 2 + spread;
  const endX = forward ? to.x : to.x + to.w;
  const endY = to.y + to.h / 2 - spread * 0.55;
  if (userConfig.edgeMode === 'straight') return `M ${startX} ${startY} L ${forward ? endX - 8 : endX + 8} ${endY}`;
  if (userConfig.edgeMode === 'orthogonal') {
    const sourcePhase = from.phase || profileById.get(edge?.from)?.phase || 'storage';
    const targetPhase = to.phase || profileById.get(edge?.to)?.phase || 'storage';
    const sourceOrder = DATA.phases[sourcePhase]?.order ?? 0;
    const targetOrder = DATA.phases[targetPhase]?.order ?? 0;
    const backward = targetOrder < sourceOrder || !forward;
    const corridor = backward
      ? Math.max(from.y + from.h + 42, to.y + to.h + 42) + route.index * 6
      : Math.min(from.y, to.y) - 32 - route.index * 6;
    const midX = startX + (endX - startX) * 0.5;
    return `M ${startX} ${startY} L ${midX} ${startY} L ${midX} ${corridor} L ${forward ? endX - 10 : endX + 10} ${corridor} L ${forward ? endX - 10 : endX + 10} ${endY}`;
  }
  const dx = Math.max(96, Math.abs(endX - startX) * 0.42);
  const layer = spread * 2.2;
  if (forward) return `M ${startX} ${startY} C ${startX + dx} ${startY + layer}, ${endX - dx} ${endY - layer}, ${endX - 8} ${endY}`;
  return `M ${startX} ${startY} C ${startX - dx} ${startY + layer}, ${endX + dx} ${endY - layer}, ${endX + 8} ${endY}`;
}

function edgeMidpoint(from, to, route = { index: 0, total: 1 }) {
  const spread = (route.index - (route.total - 1) / 2) * 8;
  const forward = to.x >= from.x;
  const startX = forward ? from.x + from.w : from.x;
  const endX = forward ? to.x : to.x + to.w;
  return { x: (startX + endX) / 2 - 24, y: (from.y + from.h / 2 + to.y + to.h / 2) / 2 + spread };
}

function relatedEdgeIds(id) {
  const ids = new Set();
  state.graph.edges.forEach((edge) => {
    if (edge.from === id || edge.to === id) ids.add(`${edge.from}->${edge.to}`);
  });
  return ids;
}

function renderNodes() {
  nodeLayer.innerHTML = '';
  const related = relatedNodeIds(state.selectedId);
  const nextNodeIds = new Set(state.graph.nodes.map((node) => node.id));
  state.graph.nodes.forEach((node) => {
    const card = el('button', `node-card ${node.type} ${node.phase || ''} ${node.health || ''}${node.semantic ? ' semantic' : ''}${node.is_running ? ' running' : ''}${node.is_active ? ' live-active' : ''}${state.previousNodeIds.has(node.id) ? ' no-animate' : ''}`);
    card.type = 'button';
    card.style.left = `${node.x}px`;
    card.style.top = `${node.y}px`;
    card.style.width = `${node.w}px`;
    card.style.minHeight = `${node.h}px`;
    card.style.height = `${node.h}px`;
    card.style.setProperty('--node-accent', node.accent || (node.type === 'mcp'
      ? (COLORS[node.health] || COLORS[node.phase] || COLORS.storage)
      : (COLORS[node.phase] || EDGE_COLORS[node.id] || COLORS.storage)));
    card.dataset.nodeId = node.id;
    if (node.semantic_role) card.dataset.semanticRole = node.semantic_role;
    card.setAttribute('aria-label', `${node.type === 'mcp' ? 'MCP' : node.type === 'profile' ? 'агент' : 'узел'}: ${node.label}, фаза ${phaseName(node.phase)}, ${node.subtitle || ''}`);
    card.setAttribute('draggable', 'false');
    if (!(state.appMode === 'constructor' && node.type === 'mcp')) card.addEventListener('dragstart', (event) => event.preventDefault());
    if (state.appMode === 'constructor' && node.type === 'mcp') {
      card.setAttribute('draggable', 'true');
      card.addEventListener('dragstart', (event) => {
        event.dataTransfer.setData('text/hermes-mcp', node.label);
        event.dataTransfer.effectAllowed = 'copy';
      });
    }
    if (state.appMode === 'constructor' && node.type === 'profile') {
      card.addEventListener('dragover', (event) => {
        if ([...event.dataTransfer.types].includes('text/hermes-mcp')) event.preventDefault();
      });
      card.addEventListener('drop', (event) => {
        const mcpName = event.dataTransfer.getData('text/hermes-mcp');
        if (mcpName) {
          event.preventDefault();
          addMcpToProfile(mcpName, node.id);
        }
      });
    }
    if (node.id === state.selectedId) card.classList.add('active');
    const focusedMode = state.selectedId && (state.mode === 'flow' || (state.mode === 'mcp' && !state.showAllMcpEdges));
    if (focusedMode && !related.has(node.id) && node.id !== state.selectedId) card.classList.add('dim');
    if (state.search && !nodeMatchesSearch(node)) card.classList.add('dim');
    if (node.type === 'empty') {
      card.disabled = true;
    } else {
      card.addEventListener('click', (event) => {
        if (state.suppressClick) {
          event.preventDefault();
          event.stopPropagation();
          state.suppressClick = false;
          return;
        }
        event.stopPropagation();
        selectNode(node.id);
      });
    }
    if (state.appMode === 'constructor' && node.type !== 'empty') {
      const handle = el('span', 'drag-handle', '⠿');
      handle.setAttribute('aria-hidden', 'true');
      handle.addEventListener('pointerdown', (event) => startNodeDrag(event, node));
      card.append(handle);
    }
    if (node.type !== 'empty') {
      card.append(el('span', 'node-port node-port-in'));
      card.append(el('span', 'node-port node-port-out'));
    }
    const kicker = el('div', 'node-kicker');
    kicker.append(el('span', `phase-icon ${node.phase || ''}`, PHASE_ICONS[node.phase] || '•'));
    if (node.type !== 'project-task') kicker.append(el('span', null, node.type === 'mcp' ? node.health : phaseLabel(node.phase)));
    card.append(kicker);
    if (node.type === 'project-task') {
      const statusText = projectStatusLabel(node);
      const statusClass = node.liveness && node.liveness !== 'idle' ? node.liveness : (node.status || 'todo');
      const status = el('span', `project-status ${statusClass}`, statusText);
      kicker.append(status);
      card.append(el('div', 'node-title project-agent', node.label));
      const taskTitle = String(node.taskTitle || node.title || node.task_id || '');
      if (taskTitle && taskTitle.toLowerCase() !== String(node.label || '').toLowerCase()) {
        card.append(el('div', 'project-task-title', shortText(taskTitle, 74)));
      }
      card.append(el('div', 'node-subtitle', shortText(node.subtitle, 78)));
    } else {
      card.append(el('div', 'node-title', node.label));
      const subtitleLimit = state.mode === 'flow' ? 30 : node.type === 'mcp' ? 56 : 38;
      card.append(el('div', 'node-subtitle', shortText(node.subtitle, subtitleLimit)));
    }
    const badges = el('div', 'node-badges');
    if (node.type === 'project-task') {
      (node.public_tools || []).slice(0, 2).forEach((name) => badges.append(el('span', 'pill tiny', name)));
    } else if (node.type === 'profile') {
      const profile = profileById.get(node.id);
      badges.append(el('span', 'pill', `${enabledMcp(profile).length}/${profile.mcp.length} MCP`));
      if (state.mode === 'mcp') {
        enabledMcp(profile).slice(0, 2).forEach((server) => {
          const pill = el('span', 'pill tiny', server.name);
          const inventory = mcpById.get(`mcp:${server.name}`);
          setTooltip(pill, inventory?.humanNote || server.humanNote);
          badges.append(pill);
        });
        if (enabledMcp(profile).length > 2) badges.append(el('span', 'pill tiny', `+${enabledMcp(profile).length - 2}`));
      }
    } else if (node.type === 'mcp') {
      const server = mcpById.get(node.id);
      badges.append(el('span', `pill ${server.health}`, server.health));
      badges.append(el('span', 'pill', `${server.enabledProfiles.length} агентов`));
      if (server.disabledProfiles.length) badges.append(el('span', 'pill tiny', `${server.disabledProfiles.length} выкл`));
    } else if (node.type === 'empty') {
      badges.append(el('span', 'pill tiny', 'пусто'));
    } else {
      badges.append(el('span', `pill ${node.phase}`, phaseLabel(node.phase)));
    }
    if ((state.mode === 'mcp' || state.mode === 'projects') && node.type !== 'empty') card.append(badges);
    if (state.mode === 'mcp') {
      const mini = el('div', 'node-mini-list');
      if (node.type === 'profile') {
        const profile = profileById.get(node.id);
        mini.textContent = enabledMcp(profile).slice(0, 5).map((server) => server.name).join(' · ') || 'MCP не настроены';
      } else if (node.type === 'mcp') {
        const server = mcpById.get(node.id);
        mini.textContent = server.enabledProfiles.slice(0, 6).join(' · ') || 'Нет активных агентов';
      }
      if (mini.textContent) card.append(mini);
    }
    nodeLayer.append(card);
  });
  state.previousNodeIds = nextNodeIds;
}

function nodeMatchesSearch(node) {
  if (!state.search) return true;
  const entity = profileById.get(node.id) || mcpById.get(node.id) || flowNodeById.get(node.id) || node;
  const text = JSON.stringify(entity || node).toLowerCase();
  return text.includes(state.search);
}

function relatedNodeIds(id) {
  const ids = new Set([id]);
  state.graph.edges.forEach((edge) => {
    if (edge.from === id) ids.add(edge.to);
    if (edge.to === id) ids.add(edge.from);
  });
  return ids;
}

function startNodeDrag(event, node) {
  if (userConfig.lock) return;
  event.preventDefault();
  event.stopPropagation();
  state.nodeDrag = {
    id: node.id,
    x: event.clientX,
    y: event.clientY,
    startX: node.x,
    startY: node.y,
    phase: node.phase,
  };
  document.body.classList.add('node-dragging');
  event.currentTarget.setPointerCapture?.(event.pointerId);
}

function moveDraggedNode(event) {
  if (!state.nodeDrag) return false;
  event.preventDefault();
  const dx = (event.clientX - state.nodeDrag.x) / state.transform.scale;
  const dy = (event.clientY - state.nodeDrag.y) / state.transform.scale;
  let x = state.nodeDrag.startX + dx;
  let y = state.nodeDrag.startY + dy;
  if (userConfig.snap) {
    x = Math.round(x / 16) * 16;
    y = Math.round(y / 16) * 16;
  }
  const lane = state.graph.lanes.find(([, lx, ly, lw, lh, phase]) => phase === state.nodeDrag.phase && x >= lx - 20 && x <= lx + lw + 20);
  if (lane) {
    const [, lx, ly, lw, lh] = lane;
    const node = state.graph.nodes.find((item) => item.id === state.nodeDrag.id);
    if (node) {
      x = clamp(x, lx + 18, lx + lw - node.w - 18);
      y = clamp(y, ly + 44, ly + lh - node.h - 18);
    }
  }
  const node = state.graph.nodes.find((item) => item.id === state.nodeDrag.id);
  if (!node) return true;
  node.x = x;
  node.y = y;
  const card = nodeLayer.querySelector(`[data-node-id="${CSS.escape(node.id)}"]`);
  if (card) {
    card.style.left = `${x}px`;
    card.style.top = `${y}px`;
  }
  renderEdges();
  renderMinimap();
  return true;
}

function finishNodeDrag() {
  if (!state.nodeDrag) return false;
  const node = state.graph.nodes.find((item) => item.id === state.nodeDrag.id);
  if (node) saveNodePosition(node.id, node.x, node.y);
  state.nodeDrag = null;
  document.body.classList.remove('node-dragging');
  return true;
}

function selectNode(id) {
  state.selectedId = id;
  if (state.mode === 'mcp' && !state.showAllMcpEdges) {
    refreshGraph();
    focusSelection(id);
    return;
  }
  renderEdges();
  renderNodes();
  renderNavigator();
  renderInspector();
  renderMinimap();
}

function applyTransform() {
  const { x, y, scale } = state.transform;
  canvas.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
  document.getElementById('zoomLabel').textContent = `${Math.round(scale * 100)}%`;
  renderMinimap();
}

function zoomAt(clientX, clientY, factor) {
  const rect = viewport.getBoundingClientRect();
  const before = screenToBoard(clientX - rect.left, clientY - rect.top);
  state.transform.scale = clamp(state.transform.scale * factor, 0.18, 2.2);
  state.transform.x = clientX - rect.left - before.x * state.transform.scale;
  state.transform.y = clientY - rect.top - before.y * state.transform.scale;
  applyTransform();
  saveTransform();
  renderEdges();
}

function screenToBoard(x, y) {
  return {
    x: (x - state.transform.x) / state.transform.scale,
    y: (y - state.transform.y) / state.transform.scale,
  };
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function fitBoard() {
  const rect = viewport.getBoundingClientRect();
  const scale = Math.min(rect.width / state.graph.width, rect.height / state.graph.height) * 0.92;
  state.transform.scale = clamp(scale, 0.55, 1.0);
  state.transform.x = (rect.width - state.graph.width * state.transform.scale) / 2;
  state.transform.y = (rect.height - state.graph.height * state.transform.scale) / 2;
  applyTransform();
  saveTransform();
  renderEdges();
}

function resetView() {
  state.transform = defaultTransformForScope(state.transformScope || transformScope());
  applyTransform();
  saveTransform();
  renderEdges();
}

function focusNode(id) {
  const node = state.graph.nodes.find((item) => item.id === id);
  if (!node) return;
  const rect = viewport.getBoundingClientRect();
  state.transform.x = rect.width / 2 - (node.x + node.w / 2) * state.transform.scale;
  state.transform.y = rect.height / 2 - (node.y + node.h / 2) * state.transform.scale;
  applyTransform();
  saveTransform();
}

function focusSelection(id = state.selectedId) {
  if (state.mode === 'mcp' && !state.showAllMcpEdges) {
    const node = state.graph.nodes.find((item) => item.id === id);
    if (!node) return;
    const rect = viewport.getBoundingClientRect();
    if (id.startsWith('mcp:')) {
      const scale = clamp(Math.min(rect.width / state.graph.width, rect.height / state.graph.height) * 0.86, 0.44, 0.78);
      state.transform.scale = scale;
      state.transform.x = Math.max(28, (rect.width - state.graph.width * scale) / 2);
      state.transform.y = Math.max(28, (rect.height - state.graph.height * scale) / 2);
      applyTransform();
      saveTransform();
      renderEdges();
      return;
    }
    const scale = rect.width < 620 ? 0.52 : 0.64;
    state.transform.scale = scale;
    state.transform.x = rect.width < 760 ? 24 : 42;
    state.transform.y = rect.height / 2 - (node.y + node.h / 2) * scale;
    applyTransform();
    saveTransform();
    renderEdges();
    return;
  }
  focusNode(id);
}

function renderMinimap() {
  const ctx = minimap.getContext('2d');
  const w = minimap.width;
  const h = minimap.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg-1').trim() || '#ffffff';
  ctx.fillRect(0, 0, w, h);
  const sx = w / state.graph.width;
  const sy = h / state.graph.height;
  state.graph.nodes.forEach((node) => {
    ctx.fillStyle = node.id === state.selectedId ? (userConfig.brand || '#B58900') : (COLORS[node.health] || COLORS[node.phase] || '#8a96a8');
    ctx.globalAlpha = node.id === state.selectedId ? 1 : 0.65;
    ctx.fillRect(node.x * sx, node.y * sy, Math.max(3, node.w * sx), Math.max(3, node.h * sy));
  });
  ctx.globalAlpha = 1;
  const rect = viewport.getBoundingClientRect();
  const viewX = -state.transform.x / state.transform.scale;
  const viewY = -state.transform.y / state.transform.scale;
  const viewW = rect.width / state.transform.scale;
  const viewH = rect.height / state.transform.scale;
  ctx.fillStyle = 'rgba(181, 137, 0, 0.18)';
  ctx.fillRect(viewX * sx, viewY * sy, viewW * sx, viewH * sy);
  ctx.strokeStyle = userConfig.brand || '#B58900';
  ctx.lineWidth = 2;
  ctx.strokeRect(viewX * sx, viewY * sy, viewW * sx, viewH * sy);
}

function renderStatus() {
  const row = document.getElementById('statusRow');
  row.innerHTML = '';
  const activeProjects = state.projects.data ? (state.projects.data.projects || []).filter((project) => project.is_active).length : 0;
  const status = state.mode === 'projects'
    ? [
      ['Hermes', state.projects.error ? 'нет связи' : 'ok', state.projects.error ? 'warn' : 'ok'],
      ['Проекты', String(activeProjects), activeProjects ? 'ok' : 'warn'],
    ]
    : [
      ['Агенты', String(profiles.length), 'ok'],
      ['MCP', String(DATA.mcpInventory.length), problemMcpCount() ? 'warn' : 'ok'],
      ['Gateway', String(DATA.runtime.gateway || '').includes('stop') ? 'stop' : 'ok', String(DATA.runtime.gateway || '').includes('stop') ? 'warn' : 'ok'],
      ['TG', DATA.runtime.telegramConfigured ? 'ok' : 'off', DATA.runtime.telegramConfigured ? 'ok' : 'bad'],
      ['Kanban', String(DATA.runtime.overlordBoardTasks ?? 0), (DATA.runtime.overlordBoardTasks ?? 0) ? 'ok' : 'warn'],
      ['Projects', state.projects.data ? String(activeProjects) : 'off', state.projects.error ? 'warn' : state.projects.data ? 'ok' : 'warn'],
    ];
  status.forEach(([label, value, health]) => row.append(statusPill(label, value, health)));
  const date = new Date(DATA.generatedAt || Date.now());
  document.getElementById('breadcrumb').textContent = state.mode === 'projects' ? 'Hermes / Live' : `Hermes / Constellation / generated ${DATA.generatedAt || 'unknown'}`;
  document.getElementById('updatedLabel').textContent = state.mode === 'projects' ? 'Live' : `Updated: ${relativeTime(date)}`;
  const attentionCount = document.getElementById('attentionCount');
  if (attentionCount) attentionCount.textContent = `(${problemMcpCount()})`;
}

function relativeTime(date) {
  const diff = Math.max(0, Date.now() - date.getTime());
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return 'сейчас';
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} ч назад`;
  return date.toLocaleDateString('ru-RU');
}

function renderMobileList() {
  const root = document.getElementById('mobileList');
  if (!root) return;
  root.innerHTML = '';
  if (state.mode === 'projects') {
    const details = el('details', 'mobile-phase');
    details.open = true;
    details.append(el('summary', null, 'Активный проект'));
    state.graph.nodes.filter((node) => node.type === 'project-task').forEach((node) => {
      const button = el('button', 'mobile-node', node.label);
      button.type = 'button';
      button.append(el('span', null, `${projectStatusLabel(node)} · ${node.current_action || node.subtitle || node.taskTitle}`));
      button.addEventListener('click', () => {
        selectNode(node.id);
        state.selectedTab = 'overview';
        renderInspector();
      });
      details.append(button);
    });
    if (!details.querySelector('.mobile-node')) details.append(el('div', 'empty-state', state.projects.error || 'Активных процессов нет.'));
    root.append(details);
    return;
  }
  const groups = new Map();
  profiles.filter(profileMatches).forEach((profile) => {
    const phase = phaseLabel(profile.phase);
    if (!groups.has(phase)) groups.set(phase, []);
    groups.get(phase).push(profile);
  });
  groups.forEach((items, phase) => {
    const details = el('details', 'mobile-phase');
    details.open = phase === phaseLabel('director') || phase === phaseLabel('council');
    details.append(el('summary', null, phase));
    items.forEach((profile) => {
      const button = el('button', 'mobile-node', profile.id);
      button.type = 'button';
      button.append(el('span', null, profile.ru?.summary || profile.title));
      button.addEventListener('click', () => {
        selectNode(profile.id);
        state.selectedTab = 'overview';
        renderInspector();
      });
      details.append(button);
    });
    root.append(details);
  });
}

function statusPill(label, value, health = 'ok') {
  const pill = el('span', `status-chip ${health}`);
  pill.textContent = `${label}: ${value}`;
  return pill;
}

function renderNavigator() {
  const title = document.getElementById('navigatorTitle');
  const count = document.getElementById('navigatorCount');
  const list = document.getElementById('navigatorList');
  list.innerHTML = '';
  if (state.mode === 'projects') {
    const payload = state.projects.data;
    const projects = payload?.projects || [];
    title.textContent = state.projects.view === 'archive' ? 'Архив' : 'Сейчас';
    count.textContent = payload ? `${projects.length} ${state.projects.view === 'archive' ? 'закр.' : 'активн.'}` : 'Live API';
    const projectItems = projects.map((project) => ({
      id: `project:${project.id}`,
      title: shortText(project.title || project.id, 46),
      meta: state.projects.view === 'archive' ? 'слепок' : (project.running_count ? 'делает' : 'идет'),
      subtitle: shortText(project.summary || project.id, 82),
      phase: payload?.project?.id === project.id ? 'director' : 'storage',
    }));
    list.append(navigatorGroup('Проекты', projectItems, true));
    const taskItems = state.graph.nodes
      .filter((node) => node.type === 'project-task')
      .filter(nodeMatchesSearch)
      .map((node) => ({ id: node.id, title: node.label, meta: projectStatusLabel(node), subtitle: node.current_action || node.subtitle || node.taskTitle, phase: node.phase }));
    list.append(navigatorGroup('Линия', taskItems, true));
    if (!projects.length && !state.projects.error) list.append(el('div', 'empty-state', state.projects.view === 'archive' ? 'Архив пуст.' : 'Активных задач нет.'));
    if (state.projects.error) list.append(el('div', 'empty-state bad', state.projects.error));
    return;
  }
  const items = profiles.filter(profileMatches).map((profile) => ({ id: profile.id, title: roleSubtitle(profile.id), meta: profile.id, subtitle: state.mode === 'mcp' ? `${enabledMcp(profile).length}/${profile.mcp.length} MCP` : profile.ru?.summary || profile.title, phase: profile.phase }));
  title.textContent = state.mode === 'flow' ? 'Агенты' : 'Агенты + MCP';
  const systemCount = DATA.flow.nodes.filter((node) => node.type !== 'profile').length;
  count.textContent = state.mode === 'flow'
    ? `Агенты: ${profiles.length} / Системы: ${systemCount}`
    : `Агенты: ${profiles.length} / MCP: ${DATA.mcpInventory.length}`;

  const byPhase = new Map();
  items.forEach((item) => {
    const phase = phaseLabel(item.phase);
    if (!byPhase.has(phase)) byPhase.set(phase, []);
    byPhase.get(phase).push(item);
  });
  byPhase.forEach((phaseItems, phase) => list.append(navigatorGroup(phase, phaseItems)));

  if (state.mode === 'flow') {
    const systems = DATA.flow.nodes
      .filter((node) => node.type !== 'profile')
      .filter((node) => !state.search || JSON.stringify(node).toLowerCase().includes(state.search))
      .map((node) => ({ id: node.id, title: roleSubtitle(node.id), meta: node.label, subtitle: node.ru?.summary || node.summary, phase: node.phase }));
    list.append(navigatorGroup(`Системы`, systems, false));
  }

  if (state.mode === 'mcp') {
    const mcpItems = DATA.mcpInventory.filter(mcpMatches).map((server) => ({ id: `mcp:${server.name}`, title: server.name, meta: server.health, subtitle: `${server.enabledProfiles.length} агентов`, phase: server.health }));
    list.append(navigatorGroup('MCP', mcpItems, false));
  }

  const tagItems = allTags().map(([tag, tagCount]) => ({ id: `tag:${tag}`, title: tag, meta: `${tagCount}`, subtitle: 'tag', phase: state.tagFilter === tag ? 'director' : 'storage' }));
  list.append(navigatorGroup('Теги', tagItems, false));
  if (!list.children.length) list.append(el('div', 'empty-state', 'Ничего не найдено.'));
}

function navigatorGroup(title, items, open = true) {
  const details = el('details', 'nav-group');
  details.open = open;
  details.append(el('summary', null, `${title} (${items.length})`));
  if (!items.length) {
    details.append(el('div', 'empty-state compact', 'пусто'));
    return details;
  }
  items.forEach((item) => details.append(navigatorItem(item)));
  return details;
}

function navigatorItem(item) {
  const active = item.id === state.selectedId || (item.id.startsWith('tag:') && state.tagFilter === item.id.slice(4));
  const button = el('button', `nav-item${active ? ' active' : ''}`);
  button.type = 'button';
  const top = el('div', 'nav-title');
  top.append(el('span', null, item.title));
  top.append(el('span', `pill ${item.phase}`, item.meta || phaseLabel(item.phase)));
  button.append(top);
  button.append(el('div', 'nav-subtitle', item.subtitle));
  button.addEventListener('click', () => {
    if (item.id.startsWith('tag:')) {
      state.tagFilter = state.tagFilter === item.id.slice(4) ? '' : item.id.slice(4);
      userConfig.tagFilter = state.tagFilter;
      persistConfig(true);
      refreshGraph();
      return;
    }
    if (item.id.startsWith('project:')) {
      state.projects.selectedProjectId = item.id.slice('project:'.length);
      state.selectedId = 'project-empty';
      loadProjectGraph();
      return;
    }
    selectNode(item.id);
    focusSelection(item.id);
  });
  if (state.appMode === 'constructor' && profileById.has(item.id)) {
    button.addEventListener('dragover', (event) => {
      if ([...event.dataTransfer.types].includes('text/hermes-mcp')) event.preventDefault();
    });
    button.addEventListener('drop', (event) => {
      const mcpName = event.dataTransfer.getData('text/hermes-mcp');
      if (mcpName) {
        event.preventDefault();
        addMcpToProfile(mcpName, item.id);
      }
    });
  }
  return button;
}

function mcpSummary(items = DATA.mcpInventory.filter(mcpMatches)) {
  return {
    total: items.length,
    healthy: items.filter((server) => server.health === 'healthy').length,
    attention: items.filter((server) => attentionHealth.has(server.health)).length,
    links: items.reduce((sum, server) => sum + server.enabledProfiles.length, 0),
  };
}

function summaryTile(label, value, tone = 'neutral') {
  const tile = el('div', `summary-tile ${tone}`);
  tile.append(el('span', null, label), el('strong', null, String(value)));
  return tile;
}

function renderMcpSummary(panel, title, subtitle, items = DATA.mcpInventory.filter(mcpMatches)) {
  const stats = mcpSummary(items);
  const summary = el('section', 'mcp-summary');
  const copy = el('div', 'mcp-summary-copy');
  copy.append(el('h2', null, title), el('p', null, subtitle));
  const metrics = el('div', 'summary-metrics');
  metrics.append(
    summaryTile('MCP', stats.total),
    summaryTile('Здоровые', stats.healthy, 'ok'),
    summaryTile('Требуют внимания', stats.attention, stats.attention ? 'warn' : 'ok'),
    summaryTile('Связи агент-MCP', stats.links, 'info'),
  );
  summary.append(copy, metrics);
  panel.append(summary);
}

function renderMcpPanel() {
  const panel = document.getElementById('mcpPanel');
  panel.innerHTML = '';
  if (state.mcpView === 'matrix') renderMcpMatrix(panel);
  if (state.mcpView === 'catalog') renderMcpCatalog(panel);
}

function renderMcpMatrix(panel) {
  const visibleServers = DATA.mcpInventory.filter(mcpMatches);
  renderMcpSummary(panel, 'MCP-матрица', 'Кто чем реально пользуется: полный кружок — включено, полукружок — назначено, но выключено.', visibleServers);
  const tableWrap = el('div', 'matrix-wrap');
  const table = el('table', 'mcp-matrix');
  table.append(el('caption', null, 'Покрытие агентов по MCP-серверам'));
  const thead = el('thead');
  const headRow = el('tr');
  headRow.append(el('th', 'sticky-col', 'Агент / MCP'));
  visibleServers.forEach((server) => {
    const th = el('th', `matrix-head ${server.health}`);
    th.append(el('span', 'matrix-health', HEALTH_ICON[server.health] || HEALTH_ICON.unknown), el('span', 'matrix-server', server.name));
    th.append(el('small', null, categoryOf(server.name)));
    setTooltip(th, `${server.name}: ${server.humanNote || server.note || (server.tags || []).join(', ')}`);
    headRow.append(th);
  });
  thead.append(headRow);
  table.append(thead);
  const tbody = el('tbody');
  const rows = profiles.filter(profileMatches);
  rows.forEach((profile) => {
    const tr = el('tr');
    const agent = el('th', 'sticky-col row-agent');
    agent.append(el('strong', null, roleSubtitle(profile.id)), el('span', null, profile.id));
    tr.append(agent);
    visibleServers.forEach((server) => {
      const configured = profile.mcp.find((item) => item.name === server.name);
      const td = el('td', configured?.enabled ? 'enabled' : configured ? 'disabled' : 'empty', configured?.enabled ? '●' : configured ? '◐' : '');
      td.dataset.agent = profile.id;
      td.dataset.mcp = server.name;
      setTooltip(td, configured ? `${profile.id} ${configured.enabled ? 'использует' : 'имеет выключенным'} ${server.name}` : `${profile.id}: ${server.name} не назначен`);
      tr.append(td);
    });
    tbody.append(tr);
  });
  table.append(tbody);
  tableWrap.append(table);
  panel.append(tableWrap);
}

function renderMcpCatalog(panel) {
  const catalogItems = DATA.mcpInventory
    .filter(mcpMatches)
    .filter((server) => state.catalogCategory === 'all' || categoryOf(server.name) === state.catalogCategory)
    .filter((server) => state.catalogHealth === 'all' || server.health === state.catalogHealth);
  renderMcpSummary(panel, 'Каталог MCP', 'Карточки показывают назначение сервера, здоровье, транспорты и агентов, которым он нужен.', catalogItems);
  const toolbar = el('div', 'catalog-toolbar');
  const category = el('select', 'select-control');
  category.append(el('option', null, 'Все категории'));
  category.firstChild.value = 'all';
  categoryNames.forEach((name) => {
    const option = el('option', null, name);
    option.value = name;
    category.append(option);
  });
  category.value = state.catalogCategory;
  category.addEventListener('change', () => { state.catalogCategory = category.value; renderMcpPanel(); });
  const health = el('select', 'select-control');
  ['all', 'healthy', 'partial', 'failed', 'gated', 'unknown'].forEach((name) => {
    const option = el('option', null, name === 'all' ? 'Любой health' : name);
    option.value = name;
    health.append(option);
  });
  health.value = state.catalogHealth;
  health.addEventListener('change', () => { state.catalogHealth = health.value; renderMcpPanel(); });
  toolbar.append(category, health);
  const tags = el('div', 'catalog-tags');
  allTags().forEach(([tag, count]) => {
    const chip = el('button', `tag-chip${state.tagFilter === tag ? ' active' : ''}`, `${tag} ${count}`);
    chip.type = 'button';
    chip.addEventListener('click', () => {
      state.tagFilter = state.tagFilter === tag ? '' : tag;
      userConfig.tagFilter = state.tagFilter;
      persistConfig(true);
      refreshGraph();
    });
    tags.append(chip);
  });
  toolbar.append(tags);
  panel.append(toolbar);

  const grid = el('div', 'catalog-grid');
  catalogItems.forEach((server) => grid.append(mcpCatalogCard(server)));
  if (!grid.children.length) grid.append(el('div', 'empty-state', 'MCP по этим фильтрам не найдены.'));
  panel.append(grid);
}

function mcpCatalogCard(server) {
  const card = el('button', `catalog-card ${server.health}`);
  card.type = 'button';
  if (state.appMode === 'constructor') {
    card.draggable = true;
    card.addEventListener('dragstart', (event) => {
      event.dataTransfer.setData('text/hermes-mcp', server.name);
      event.dataTransfer.effectAllowed = 'copy';
    });
  }
  const head = el('div', 'catalog-card-head');
  head.append(el('span', 'health-icon', HEALTH_ICON[server.health] || HEALTH_ICON.unknown));
  const title = el('div', 'catalog-title');
  title.append(el('strong', null, server.name), el('span', null, categoryOf(server.name)));
  head.append(title, el('span', `pill ${server.health}`, server.health));
  card.append(head);
  card.append(el('p', null, server.humanNote || server.note));
  const meta = el('div', 'catalog-meta');
  meta.append(el('span', null, `${server.enabledProfiles.length} активных`));
  if (server.disabledProfiles.length) meta.append(el('span', null, `${server.disabledProfiles.length} выкл.`));
  if (server.transports?.length) meta.append(el('span', null, server.transports.slice(0, 2).join(' / ')));
  card.append(meta);
  const agents = el('div', 'avatar-row');
  server.enabledProfiles.slice(0, 4).forEach((id) => agents.append(el('span', 'avatar', initials(id))));
  if (server.enabledProfiles.length > 4) agents.append(el('span', 'avatar more', `+${server.enabledProfiles.length - 4}`));
  card.append(agents);
  const tags = el('div', 'node-tags');
  (server.tags || []).slice(0, 3).forEach((tag) => tags.append(el('span', 'tag-chip small', tag)));
  card.append(tags);
  card.addEventListener('click', () => openMcpDrawer(server));
  return card;
}

function renderInspector() {
  const entity = selectedEntity();
  const isProfile = profileById.has(state.selectedId);
  const isMcp = state.selectedId.startsWith('mcp:');
  const isProjectTask = entity?.type === 'project-task';
  if (state.selectedTab === 'properties' && state.appMode !== 'constructor') state.selectedTab = 'overview';
  const hiddenTabs = new Set(isProjectTask ? (entity.hide_tabs || []) : []);
  if (hiddenTabs.has(state.selectedTab)) state.selectedTab = 'overview';
  const phase = isMcp ? entity.health : (entity.phase || 'storage');
  document.getElementById('inspectorKind').textContent = isProjectTask ? 'Линия задачи' : isProfile ? 'Агент' : isMcp ? 'MCP' : 'Система';
  document.getElementById('inspectorTitle').textContent = isProjectTask ? (entity.label || entity.assignee || entity.task_id) : isMcp ? entity.name : (entity.id || entity.label);
  const phasePill = document.getElementById('inspectorPhase');
  phasePill.className = `pill ${phase}`;
  phasePill.textContent = isProjectTask ? projectStatusLabel(entity) : isMcp ? entity.health : phaseLabel(phase);
  document.querySelectorAll('.tab-btn').forEach((button) => {
    if (button.classList.contains('constructor-only')) button.hidden = state.appMode !== 'constructor';
    if (!button.classList.contains('constructor-only')) button.hidden = hiddenTabs.has(button.dataset.tab);
    const active = button.dataset.tab === state.selectedTab;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
    button.setAttribute('tabindex', active ? '0' : '-1');
  });
  const body = document.getElementById('inspectorBody');
  body.innerHTML = '';
  if (isProjectTask) renderProjectTaskInspector(body, entity);
  else if (isProfile) renderProfileInspector(body, entity);
  else if (isMcp) renderMcpInspector(body, entity);
  else renderSystemInspector(body, entity);
}

function renderProjectTaskInspector(body, task) {
  ensureProjectLogPolling(task.log?.task_id || task.task_id, task.id);
  if (state.selectedTab === 'properties') {
    renderPropertiesPanel(body, task.id, 'project-task');
    return;
  }

  if (state.selectedTab === 'mcp') {
    const tools = (task.public_tools || []).length ? task.public_tools : (task.tool_signals || []).map((signal) => signal.name).slice(0, 6);
    body.append(el('p', 'summary-text lead', tools.length ? tools.join(' · ') : 'Инструментов для этого шага не видно.'));
    return;
  }

  if (state.selectedTab === 'flow') {
    flowSection(body, task.id);
    return;
  }

  const overviewText = task.overview || task.taskTitle || task.title || task.task_id;
  const overviewClass = task.semantic_role === 'user' ? 'summary-text lead project-user-prompt' : 'summary-text lead';
  body.append(el('p', overviewClass, overviewText));

  const evidence = el('div', 'project-evidence-grid');
  evidence.append(projectEvidenceBlock('Получил', task.received || overviewText || 'Нет данных.'));
  evidence.append(projectEvidenceBlock('Сделал', task.did || task.current_action || task.latest_activity || 'Нет данных.'));
  evidence.append(projectEvidenceBlock('Инструменты', projectEvidenceChips(task.tools_used || [], 'Инструментов не видно.')));
  evidence.append(projectEvidenceBlock('MCP', projectEvidenceChips(task.mcp_used || [], 'MCP-вызовов не видно.')));
  evidence.append(projectEvidenceBlock('Передал', task.handoff || 'Передачи дальше не видно.'));
  body.append(evidence);

  const activity = el('section', 'project-now-card');
  activity.append(el('span', `project-now-dot ${task.is_running ? 'live' : ''}`));
  const copy = el('div', null);
  copy.append(el('strong', null, task.is_running ? 'Сейчас делает' : 'Состояние'));
  copy.append(el('p', null, task.current_action || task.latest_activity || task.subtitle || 'Нет активности.'));
  activity.append(copy);
  body.append(activity);

  if (task.outcome) {
    const outcome = el('section', 'project-now-card quiet');
    outcome.append(el('span', 'project-now-dot'));
    const text = el('div', null);
    text.append(el('strong', null, 'Итог'));
    text.append(el('p', null, task.outcome));
    outcome.append(text);
    body.append(outcome);
  }

  const logWrap = el('section', 'project-log-block');
  const head = el('div', 'project-log-head');
  head.append(el('h3', null, 'Журнал'));
  logWrap.append(head);
  if (state.projects.logError) logWrap.append(el('div', 'empty-state bad', state.projects.logError));
  const log = state.projects.logData;
  if (log?.content) {
    const logNode = el('pre', 'project-live-log', log.content);
    logNode.addEventListener('scroll', () => {
      const gap = logNode.scrollHeight - logNode.scrollTop - logNode.clientHeight;
      state.projects.logFollow = gap < 28;
      state.projects.logScrollTop = logNode.scrollTop;
    });
    logWrap.append(logNode);
    logWrap.append(el('div', 'project-log-meta', log.truncated ? 'Показан короткий хвост журнала' : 'Журнал целиком'));
  } else if (!state.projects.logError) {
    logWrap.append(el('div', 'empty-state', 'Журнал пока пуст.'));
  }
  body.append(logWrap);
}

function projectEvidenceBlock(title, content) {
  const block = el('section', 'project-evidence-item');
  block.append(el('h3', null, title));
  if (content instanceof Node) block.append(content);
  else block.append(el('p', null, content || 'Нет данных.'));
  return block;
}

function projectEvidenceChips(items, emptyText) {
  const chips = el('div', 'project-evidence-chips');
  if (!items || !items.length) {
    chips.append(el('span', 'pill tiny muted', emptyText));
    return chips;
  }
  items.slice(0, 8).forEach((item) => {
    const name = typeof item === 'string' ? item : item.name;
    const count = typeof item === 'string' ? 1 : Number(item.count || 1);
    chips.append(el('span', 'pill tiny', count > 1 ? `${name} ×${count}` : name));
  });
  return chips;
}

function renderProfileInspector(body, profile) {
  if (state.selectedTab === 'overview') {
    body.append(el('p', 'summary-text lead', profile.ru?.summary || profile.responsibility));
    const roleGrid = el('div', 'role-grid');
    roleGrid.append(roleBlock('Что делает', profile.ru?.does || profile.responsibility));
    roleGrid.append(roleBlock('За что отвечает', profile.ru?.responsible || profile.owns.join(', ')));
    roleGrid.append(roleBlock('Как коммуницирует', profile.ru?.communicates || `${profile.receivesFrom.join(', ')} -> ${profile.handsTo.join(', ')}`));
    body.append(roleGrid);
    body.append(inspectorActions(profile));
    const stats = el('div', 'stat-grid');
    stats.append(stat('Модель', profile.model || 'не настроена'));
    stats.append(stat('Провайдер', profile.provider || 'не настроен'));
    stats.append(stat('Reasoning', profile.reasoningEffort || 'default'));
    stats.append(stat('MCP', `${enabledMcp(profile).length}/${profile.mcp.length} включено`));
    stats.append(stat('Auth', authSummary(profile)));
    stats.append(stat('Max turns', profile.maxTurns ?? 'profile default'));
    body.append(stats);
    chipSection(body, 'Зоны владения', profile.owns);
    chipSection(body, 'Входы', profile.receivesFrom);
    chipSection(body, 'Выходы', profile.handsTo);
  }
  if (state.selectedTab === 'mcp') {
    const list = el('div', 'mcp-list');
    profile.mcp.forEach((server) => {
      const inventory = mcpById.get(`mcp:${server.name}`);
      list.append(mcpRow(server.name, server.health, inventory?.humanNote || server.humanNote || server.note, !server.enabled));
    });
    if (!profile.mcp.length) list.append(el('div', 'empty-state', 'MCP не настроены.'));
    body.append(list);
  }
  if (state.selectedTab === 'flow') {
    flowSection(body, profile.id);
  }
  if (state.selectedTab === 'properties') {
    renderPropertiesPanel(body, profile.id, 'profile');
  }
}

function inspectorActions(profile) {
  const actions = el('div', 'inspector-actions');
  const soulAction = el('button', 'soul-open-btn', 'Открыть SOUL');
  soulAction.type = 'button';
  soulAction.addEventListener('click', () => openSoulModal(profile));
  const neighbors = el('button', 'tool-btn', 'Соседи');
  neighbors.type = 'button';
  neighbors.addEventListener('click', () => { state.selectedTab = 'flow'; renderInspector(); });
  const map = el('button', 'tool-btn', 'На карте');
  map.type = 'button';
  map.addEventListener('click', () => focusSelection(profile.id));
  const copy = el('button', 'tool-btn', 'Копировать ID');
  copy.type = 'button';
  copy.addEventListener('click', () => navigator.clipboard?.writeText(profile.id));
  actions.append(soulAction, neighbors, map, copy);
  return actions;
}

function renderPropertiesPanel(body, id, type) {
  const node = state.graph.nodes.find((item) => item.id === id) || { id, label: id, subtitle: roleSubtitle(id) };
  const override = userConfig.nodes[id] || {};
  const form = el('div', 'properties-form');
  form.append(propertyInput('Label override', override.label || node.label, (value) => updateNodeOverride(id, 'label', value)));
  form.append(propertyInput('RU role', override.role || node.subtitle || roleSubtitle(id), (value) => updateNodeOverride(id, 'role', value)));
  form.append(propertyInput('Accent color', override.accent || '', (value) => updateNodeOverride(id, 'accent', value), 'color'));
  form.append(propertyInput('Tags', (type === 'profile' ? profileById.get(id)?.tags : mcpById.get(id)?.tags || []).join(', '), (value) => {
    if (type === 'profile' && profileById.has(id)) profileById.get(id).tags = value.split(',').map((tag) => tag.trim()).filter(Boolean);
    if (type === 'mcp' && mcpById.has(id)) mcpById.get(id).tags = value.split(',').map((tag) => tag.trim()).filter(Boolean);
    persistConfig(true);
    refreshGraph();
  }));
  const hide = el('button', 'tool-btn danger', userConfig.hiddenNodes.includes(id) ? 'Показать на карте' : 'Скрыть на карте');
  hide.type = 'button';
  hide.addEventListener('click', () => {
    if (userConfig.hiddenNodes.includes(id)) userConfig.hiddenNodes = userConfig.hiddenNodes.filter((item) => item !== id);
    else userConfig.hiddenNodes.push(id);
    persistConfig(true);
    refreshGraph();
  });
  form.append(hide);
  body.append(form);
}

function propertyInput(label, value, onChange, type = 'text') {
  const wrap = el('label', 'property-field');
  wrap.append(el('span', null, label));
  const input = document.createElement('input');
  input.type = type;
  input.value = type === 'color' ? (value || '#B58900') : value;
  input.addEventListener('change', () => onChange(input.value));
  wrap.append(input);
  return wrap;
}

function updateNodeOverride(id, key, value) {
  userConfig.nodes[id] = { ...(userConfig.nodes[id] || {}), [key]: value };
  persistConfig(true);
  refreshGraph();
}

function roleBlock(title, text) {
  const block = el('section', 'role-block');
  block.append(el('h3', null, title));
  block.append(el('p', null, text || 'Не описано.'));
  return block;
}

function renderMcpInspector(body, server) {
  if (state.selectedTab === 'properties') {
    renderPropertiesPanel(body, `mcp:${server.name}`, 'mcp');
    return;
  }
  body.append(el('p', 'summary-text lead', server.humanNote || server.note));
  if (server.note && server.note !== server.humanNote) body.append(el('p', 'mcp-note-detail', server.note));
  const stats = el('div', 'stat-grid');
  stats.append(stat('Health', server.health));
  stats.append(stat('Transports', server.transports.join(', ') || 'unknown'));
  stats.append(stat('Включен у', server.enabledProfiles.length));
  stats.append(stat('Выключен у', server.disabledProfiles.length));
  body.append(stats);
  chipSection(body, 'Используют', server.enabledProfiles);
  chipSection(body, 'Выключен у', server.disabledProfiles);
  flowSection(body, `mcp:${server.name}`);
}

function openMcpDrawer(server) {
  const drawer = document.getElementById('mcpDrawer');
  const title = document.getElementById('mcpDrawerTitle');
  const body = document.getElementById('mcpDrawerBody');
  title.textContent = server.name;
  body.innerHTML = '';
  body.append(el('p', 'summary-text lead', server.humanNote || server.note));
  const stats = el('div', 'definition-list');
  stats.append(definitionRow('Health', `${HEALTH_ICON[server.health] || '—'} ${server.health}`));
  stats.append(definitionRow('Категория', categoryOf(server.name)));
  stats.append(definitionRow('Transport', server.transports.join(', ') || 'unknown'));
  stats.append(definitionRow('Используют', `${server.enabledProfiles.length} агентов`));
  body.append(stats);
  chipSection(body, 'Теги', server.tags || []);
  chipSection(body, 'Используют', server.enabledProfiles);
  const actions = el('div', 'drawer-actions');
  const open = el('button', 'tool-btn primary', 'Открыть на карте');
  open.type = 'button';
  open.addEventListener('click', () => {
    drawer.hidden = true;
    state.mode = 'mcp';
    state.mcpView = 'map';
    state.selectedId = `mcp:${server.name}`;
    userConfig.mcpView = 'map';
    persistConfig();
    updateModeButtons();
    refreshGraph();
    focusSelection(state.selectedId);
  });
  const copy = el('button', 'tool-btn', 'Copy config');
  copy.type = 'button';
  copy.addEventListener('click', () => navigator.clipboard?.writeText(JSON.stringify(server, null, 2)));
  actions.append(open, copy);
  body.append(actions);
  drawer.hidden = false;
}

function definitionRow(label, value) {
  const row = el('div', 'definition-row');
  row.append(el('span', null, label));
  row.append(el('strong', null, String(value)));
  return row;
}

function renderSystemInspector(body, node) {
  if (state.selectedTab === 'properties') {
    renderPropertiesPanel(body, node.id, 'system');
    return;
  }
  body.append(el('p', 'summary-text', node.ru?.summary || node.summary || 'Системный компонент'));
  flowSection(body, node.id);
}

function stat(label, value) {
  const block = el('div', 'stat-box');
  block.append(el('span', null, label));
  block.append(el('strong', null, String(value)));
  return block;
}

function authSummary(profile) {
  const parts = [];
  if (profile.auth.env) parts.push('.env');
  if (profile.auth.authJson) parts.push('auth');
  if (profile.auth.mcpTokens) parts.push('mcp-tokens');
  if (profile.auth.skills) parts.push('skills');
  return parts.join(', ') || 'не найдено';
}

function chipSection(body, title, values) {
  body.append(el('h3', null, title));
  const chips = el('div', 'chip-list');
  if (!values || !values.length) chips.append(el('span', 'pill', 'нет'));
  (values || []).forEach((value) => chips.append(el('span', 'pill', value)));
  body.append(chips);
}

function mcpRow(name, health, note, off = false) {
  const row = el('div', `mcp-row${off ? ' off' : ''}`);
  const text = el('div');
  text.append(el('div', 'mcp-name', name));
  text.append(el('div', 'mcp-note', note));
  row.append(text);
  row.append(el('span', `pill ${health}`, off ? 'выкл' : health));
  setTooltip(row, note);
  row.addEventListener('click', () => {
    state.mode = 'mcp';
    updateModeButtons();
    state.selectedId = `mcp:${name}`;
    refreshGraph();
    focusSelection(state.selectedId);
  });
  return row;
}

function localizedEdgeLabel(label) {
  return { uses: 'использует', off: 'выключено' }[label] || label;
}

function flowSection(body, id) {
  if (id.startsWith('mcp:')) {
    const incoming = state.graph.edges.filter((edge) => edge.to === id);
    body.append(el('h3', null, 'Вызывают'));
    groupedFlowList(body, incoming.map((edge) => ({ id: edge.from, label: entityLabel(edge.from), meta: localizedEdgeLabel(edge.label) })));
    body.append(el('h3', null, 'Исходящие'));
    body.append(flowList([], 'Этот MCP вызывают агенты, сам он никого не вызывает.'));
    return;
  }
  const incoming = state.graph.edges.filter((edge) => edge.to === id).map((edge) => ({ id: edge.from, label: entityLabel(edge.from), meta: localizedEdgeLabel(edge.label) }));
  const outgoing = state.graph.edges.filter((edge) => edge.from === id).map((edge) => ({ id: edge.to, label: entityLabel(edge.to), meta: localizedEdgeLabel(edge.label) }));
  body.append(el('h3', null, 'Входящие'));
  body.append(flowList(incoming, 'Этот узел только отдает результат, входящих ребер нет.'));
  body.append(el('h3', null, 'Исходящие'));
  body.append(flowList(outgoing, 'Этот узел только принимает запросы, исходящих ребер нет.'));
}

function groupedFlowList(body, items) {
  if (!items.length) {
    body.append(flowList([], 'Для выбранного фильтра вызовов нет.'));
    return;
  }
  const groups = new Map();
  items.forEach((item) => {
    const phase = profileById.get(item.id)?.phase || 'storage';
    const label = phaseLabel(phase);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(item);
  });
  groups.forEach((groupItems, label) => {
    body.append(el('div', 'flow-group-title', label));
    body.append(flowList(groupItems, ''));
  });
}

function flowList(items, emptyText = 'В этом режиме видимых связей нет.') {
  const list = el('div', 'flow-list');
  if (!items.length && emptyText) list.append(el('div', 'empty-state', emptyText));
  items.forEach((item) => {
    const chip = el('div', 'flow-item chip-flow');
    chip.append(el('span', 'flow-arrow', '→'));
    chip.append(el('strong', null, item.label));
    chip.append(el('span', null, item.meta));
    list.append(chip);
  });
  return list;
}

function openSoulModal(profile) {
  const modal = document.getElementById('soulModal');
  const title = document.getElementById('soulModalTitle');
  const content = document.getElementById('soulModalContent');
  title.textContent = `${profile.id} / ${profile.title}`;
  content.textContent = profile.soul?.full || profile.soul?.excerpt || 'SOUL.md не найден.';
  content.scrollTop = 0;
  state.lastSoulTrigger = document.activeElement;
  modal.hidden = false;
  document.body.classList.add('modal-open');
  document.getElementById('closeSoulModal').focus();
}

function openEdgePopover(edge, x, y) {
  const popover = document.getElementById('edgePopover');
  const id = `${edge.from}->${edge.to}`;
  const override = userConfig.edges[id] || {};
  popover.innerHTML = '';
  popover.style.left = `${x}px`;
  popover.style.top = `${y}px`;
  popover.append(el('strong', null, `${entityLabel(edge.from)} → ${entityLabel(edge.to)}`));
  popover.append(propertyInput('Label', override.label || edge.label || '', (value) => {
    userConfig.edges[id] = { ...(userConfig.edges[id] || {}), label: value };
    edge.label = value;
    persistConfig(true);
    renderEdges();
  }));
  popover.append(propertyInput('Color', override.color || userConfig.brand || '#B58900', (value) => {
    userConfig.edges[id] = { ...(userConfig.edges[id] || {}), color: value };
    persistConfig(true);
    renderEdges();
  }, 'color'));
  const styles = el('div', 'edge-style-row');
  const styleLabels = { solid: 'сплошная', dashed: 'пунктир', dotted: 'точки' };
  ['solid', 'dashed', 'dotted'].forEach((style) => {
    const button = el('button', `tool-btn${(override.style || 'solid') === style ? ' active' : ''}`, styleLabels[style]);
    button.type = 'button';
    button.addEventListener('click', () => {
      userConfig.edges[id] = { ...(userConfig.edges[id] || {}), style };
      persistConfig(true);
      openEdgePopover(edge, x, y);
      renderEdges();
    });
    styles.append(button);
  });
  popover.append(styles);
  const hide = el('button', 'tool-btn danger', override.hidden ? 'Показать' : 'Скрыть');
  hide.type = 'button';
  hide.addEventListener('click', () => {
    userConfig.edges[id] = { ...(userConfig.edges[id] || {}), hidden: !override.hidden };
    persistConfig(true);
    popover.hidden = true;
    renderEdges();
  });
  popover.append(hide);
  popover.hidden = false;
}

function closeSoulModal() {
  const modal = document.getElementById('soulModal');
  modal.hidden = true;
  document.body.classList.remove('modal-open');
  if (state.lastSoulTrigger?.focus) state.lastSoulTrigger.focus();
}

function setAppMode(mode) {
  state.appMode = mode;
  userConfig.appMode = mode;
  if (mode !== 'constructor' && state.selectedTab === 'properties') state.selectedTab = 'overview';
  persistConfig(true);
  updateModeButtons();
  renderInspector();
  renderEdges();
  renderNodes();
}

function setDensity(density) {
  state.density = density;
  userConfig.density = density;
  persistConfig(true);
  updateModeButtons();
}

function undo() {
  const snapshot = undoStack.pop();
  if (!snapshot) return;
  redoStack.push(JSON.stringify(userConfig));
  restoreConfig(snapshot);
}

function redo() {
  const snapshot = redoStack.pop();
  if (!snapshot) return;
  undoStack.push(JSON.stringify(userConfig));
  restoreConfig(snapshot);
}

function autoLayout() {
  const scope = layoutScope();
  userConfig.nodes = state.mode === 'flow' ? {} : userConfig.nodes;
  if (userConfig.viewNodes?.[scope]) delete userConfig.viewNodes[scope];
  persistConfig(true);
  refreshGraph();
  focusSelection(state.selectedId);
}

function exportConfig() {
  const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '');
  const blob = new Blob([JSON.stringify(userConfig, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `hermes-config-${stamp}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function importConfig(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  file.text().then((text) => {
    const parsed = JSON.parse(text);
    if (!parsed.version || typeof parsed !== 'object') throw new Error('Bad config');
    userConfig = { ...defaultUserConfig(), ...parsed, version: 1 };
    state.appMode = userConfig.appMode;
    state.mcpView = userConfig.mcpView;
    state.density = userConfig.density;
    persistConfig(true);
    refreshGraph();
  }).catch(() => alert('Не удалось импортировать JSON конфигурации.'));
}

function showPresetMenu() {
  const name = prompt(`Пресет: ${BUILTIN_PRESETS.map((preset) => preset.name).join(', ')}`, 'Engineer');
  if (!name) return;
  const preset = BUILTIN_PRESETS.find((item) => item.name.toLowerCase() === name.toLowerCase() || item.id === name.toLowerCase());
  if (!preset) return;
  if (!confirm(`Применить «${preset.name}»? Текущие правки останутся в undo-стеке.`)) return;
  Object.assign(userConfig, preset);
  state.mode = preset.mode || state.mode;
  state.appMode = preset.appMode || state.appMode;
  state.mcpView = preset.mcpView || state.mcpView;
  state.density = preset.density || state.density;
  if (preset.selectedId) state.selectedId = preset.selectedId;
  state.showLabels = preset.showLabels ?? state.showLabels;
  state.attentionOnly = preset.attentionOnly ?? state.attentionOnly;
  persistConfig(true);
  updateModeButtons();
  refreshGraph();
}

function renderThemeDrawer() {
  const drawer = document.getElementById('themeDrawer');
  const body = document.getElementById('themeDrawerBody');
  body.innerHTML = '';
  const themes = el('div', 'theme-section');
  themes.append(el('h3', null, 'Тема'));
  THEME_OPTIONS.forEach((theme) => {
    const button = el('button', `theme-option theme-${theme.id}${userConfig.theme === theme.id ? ' active' : ''}`);
    button.type = 'button';
    button.append(el('strong', null, theme.name), el('span', null, theme.note));
    button.addEventListener('click', () => { userConfig.theme = theme.id; persistConfig(true); renderThemeDrawer(); });
    themes.append(button);
  });
  body.append(themes);
  body.append(propertyInput('Акцентный цвет', userConfig.brand || '#B58900', (value) => { userConfig.brand = value; persistConfig(true); renderThemeDrawer(); }, 'color'));
  const edgeMode = el('div', 'theme-section');
  edgeMode.append(el('h3', null, 'Форма линий'));
  EDGE_MODE_OPTIONS.forEach((mode) => {
    const button = el('button', `theme-option compact${userConfig.edgeMode === mode.id ? ' active' : ''}`);
    button.type = 'button';
    button.append(el('strong', null, mode.name), el('span', null, mode.note));
    button.addEventListener('click', () => { userConfig.edgeMode = mode.id; persistConfig(true); renderEdges(); renderThemeDrawer(); });
    edgeMode.append(button);
  });
  body.append(edgeMode);
  const edgeColorMode = el('div', 'theme-section');
  edgeColorMode.append(el('h3', null, 'Цвет линий'));
  EDGE_COLOR_OPTIONS.forEach((mode) => {
    const button = el('button', `theme-option compact${userConfig.edgeColor === mode.id ? ' active' : ''}`);
    button.type = 'button';
    button.append(el('strong', null, mode.name), el('span', null, mode.note));
    button.addEventListener('click', () => { userConfig.edgeColor = mode.id; persistConfig(true); renderEdges(); renderThemeDrawer(); });
    edgeColorMode.append(button);
  });
  body.append(edgeColorMode);
  const grid = el('button', `tool-btn${userConfig.showGrid ? ' active' : ''}`, 'Сетка');
  grid.type = 'button';
  grid.addEventListener('click', () => { userConfig.showGrid = !userConfig.showGrid; persistConfig(true); renderThemeDrawer(); });
  const reset = el('button', 'tool-btn danger', 'Сбросить локальные правки');
  reset.type = 'button';
  reset.addEventListener('click', () => { userConfig = defaultUserConfig(); persistConfig(true); refreshGraph(); renderThemeDrawer(); });
  body.append(grid, reset);
  drawer.hidden = false;
}

function setupEvents() {
  document.querySelectorAll('.seg-btn').forEach((button) => {
    button.addEventListener('click', () => {
      state.mode = button.dataset.mode;
      userConfig.mode = state.mode;
      if (state.mode === 'flow' && state.selectedId.startsWith('mcp:')) state.selectedId = 'overlord';
      if (state.mode === 'flow' && state.selectedId.startsWith('task:')) state.selectedId = 'overlord';
      if (state.mode === 'mcp' && !state.selectedId.startsWith('mcp:') && !profileById.has(state.selectedId)) state.selectedId = 'overlord';
      if (state.mode === 'projects' && !state.selectedId.startsWith('task:')) state.selectedId = state.projects.data?.nodes?.[0]?.id || 'project-empty';
      const hadTransform = Boolean(userConfig.transforms?.[transformScope()]);
      updateModeButtons();
      persistConfig(true);
      refreshGraph();
      if (state.mode === 'mcp' && !hadTransform) focusSelection(state.selectedId);
      if (state.mode === 'projects' && !hadTransform) focusSelection(state.selectedId);
    });
  });
  document.querySelectorAll('.tab-btn').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedTab = button.dataset.tab;
      renderInspector();
    });
    button.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      const tabs = [...document.querySelectorAll('.tab-btn:not([hidden])')];
      const index = tabs.indexOf(button);
      const next = tabs[(index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
      next.focus();
      state.selectedTab = next.dataset.tab;
      renderInspector();
    });
  });
  document.getElementById('searchInput').addEventListener('input', (event) => {
    state.search = event.target.value.trim().toLowerCase();
    refreshGraph();
  });
  document.getElementById('labelsToggle').addEventListener('click', (event) => {
    state.showLabels = !state.showLabels;
    event.currentTarget.classList.toggle('active', state.showLabels);
    event.currentTarget.setAttribute('aria-pressed', String(state.showLabels));
    renderEdges();
  });
  document.getElementById('attentionToggle').addEventListener('click', (event) => {
    state.attentionOnly = !state.attentionOnly;
    event.currentTarget.classList.toggle('active', state.attentionOnly);
    event.currentTarget.setAttribute('aria-pressed', String(state.attentionOnly));
    refreshGraph();
  });
  document.getElementById('allMcpEdgesToggle').addEventListener('click', (event) => {
    state.showAllMcpEdges = !state.showAllMcpEdges;
    event.currentTarget.classList.toggle('active', state.showAllMcpEdges);
    event.currentTarget.setAttribute('aria-pressed', String(state.showAllMcpEdges));
    refreshGraph();
  });
  document.querySelectorAll('.mode-btn').forEach((button) => {
    button.addEventListener('click', () => setAppMode(button.dataset.appMode));
  });
  document.querySelectorAll('.density-btn').forEach((button) => {
    button.addEventListener('click', () => setDensity(button.dataset.density));
  });
  document.querySelectorAll('.mcp-view-btn').forEach((button) => {
    button.addEventListener('click', () => {
      state.mcpView = button.dataset.mcpView;
      userConfig.mcpView = state.mcpView;
      const hadTransform = Boolean(userConfig.transforms?.[transformScope()]);
      persistConfig(true);
      refreshGraph();
      if (state.mcpView === 'map' && !hadTransform) focusSelection(state.selectedId);
    });
  });
  document.getElementById('legendBtn').addEventListener('click', () => {
    const panel = document.getElementById('legendPanel');
    const open = panel.hidden;
    panel.hidden = !open;
    document.getElementById('legendBtn').setAttribute('aria-expanded', String(open));
  });
  document.getElementById('fitBtn').addEventListener('click', fitBoard);
  document.getElementById('resetBtn').addEventListener('click', resetView);
  document.getElementById('zoomInBtn').addEventListener('click', () => zoomAt(viewport.getBoundingClientRect().left + viewport.clientWidth / 2, viewport.getBoundingClientRect().top + viewport.clientHeight / 2, 1.18));
  document.getElementById('zoomOutBtn').addEventListener('click', () => zoomAt(viewport.getBoundingClientRect().left + viewport.clientWidth / 2, viewport.getBoundingClientRect().top + viewport.clientHeight / 2, 0.84));
  document.getElementById('presentToggleBtn').addEventListener('click', () => setAppMode(state.appMode === 'present' ? 'view' : 'present'));
  document.getElementById('undoBtn').addEventListener('click', undo);
  document.getElementById('redoBtn').addEventListener('click', redo);
  document.getElementById('autoLayoutBtn').addEventListener('click', autoLayout);
  document.getElementById('lockBtn').addEventListener('click', () => { userConfig.lock = !userConfig.lock; persistConfig(true); updateModeButtons(); });
  document.getElementById('snapBtn').addEventListener('click', () => { userConfig.snap = !userConfig.snap; persistConfig(true); updateModeButtons(); });
  document.getElementById('themeBtn').addEventListener('click', renderThemeDrawer);
  document.getElementById('closeThemeDrawer').addEventListener('click', () => { document.getElementById('themeDrawer').hidden = true; });
  document.getElementById('closeMcpDrawer').addEventListener('click', () => { document.getElementById('mcpDrawer').hidden = true; });
  document.getElementById('exportBtn').addEventListener('click', exportConfig);
  document.getElementById('importBtn').addEventListener('click', () => document.getElementById('importInput').click());
  document.getElementById('importInput').addEventListener('change', importConfig);
  document.getElementById('presetBtn').addEventListener('click', showPresetMenu);
  document.getElementById('closeSoulModal').addEventListener('click', closeSoulModal);
  document.getElementById('soulModal').addEventListener('click', (event) => {
    if (event.target.id === 'soulModal') closeSoulModal();
  });
  window.addEventListener('keydown', (event) => {
    const modal = document.getElementById('soulModal');
    if (event.key === 'Tab' && !modal.hidden) {
      const focusable = [...modal.querySelectorAll('button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])')].filter((node) => !node.disabled);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
      return;
    }
    if (event.key === 'Escape' && !modal.hidden) {
      closeSoulModal();
      return;
    }
    if (event.key === 'Escape') {
      document.getElementById('edgePopover').hidden = true;
      document.getElementById('themeDrawer').hidden = true;
      document.getElementById('mcpDrawer').hidden = true;
      if (state.appMode === 'present') setAppMode('view');
    }
    if (event.target.matches('input, textarea')) {
      if (event.key === 'Escape' && event.target.id === 'searchInput') {
        event.target.value = '';
        state.search = '';
        event.target.blur();
        refreshGraph();
      }
      return;
    }
    if (event.key === 'f' || event.key === 'F') fitBoard();
    if (event.key === '+' || event.key === '=') zoomAt(viewport.getBoundingClientRect().left + viewport.clientWidth / 2, viewport.getBoundingClientRect().top + viewport.clientHeight / 2, 1.16);
    if (event.key === '-' || event.key === '_') zoomAt(viewport.getBoundingClientRect().left + viewport.clientWidth / 2, viewport.getBoundingClientRect().top + viewport.clientHeight / 2, 0.86);
    if (event.key === '0') resetView();
    if (event.key === '/') {
      event.preventDefault();
      document.getElementById('searchInput').focus();
    }
    if (event.key === 'm' || event.key === 'M') {
      const modes = ['flow', 'projects', 'mcp'];
      state.mode = modes[(modes.indexOf(state.mode) + 1) % modes.length] || 'flow';
      if (state.mode === 'flow' && state.selectedId.startsWith('mcp:')) state.selectedId = 'overlord';
      if (state.mode === 'flow' && state.selectedId.startsWith('task:')) state.selectedId = 'overlord';
      if (state.mode === 'projects' && !state.selectedId.startsWith('task:')) state.selectedId = state.projects.data?.nodes?.[0]?.id || 'project-empty';
      updateModeButtons();
      resetView();
      refreshGraph();
      focusSelection(state.selectedId);
    }
    if (event.key === 'e' || event.key === 'E') setAppMode(state.appMode === 'constructor' ? 'view' : 'constructor');
    if (event.key === 'g' || event.key === 'G') { userConfig.showGrid = !userConfig.showGrid; persistConfig(true); }
    if (event.key === 'a' || event.key === 'A') autoLayout();
    if (event.key === 'l' || event.key === 'L') { userConfig.lock = !userConfig.lock; persistConfig(true); updateModeButtons(); }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
      event.preventDefault();
      if (event.shiftKey) redo(); else undo();
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'e') {
      event.preventDefault();
      exportConfig();
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      showPresetMenu();
    }
    if (event.key === 'Delete' && state.appMode === 'constructor' && state.selectedId) {
      if (!userConfig.hiddenNodes.includes(state.selectedId)) userConfig.hiddenNodes.push(state.selectedId);
      persistConfig(true);
      refreshGraph();
    }
  });

  viewport.addEventListener('wheel', (event) => {
    event.preventDefault();
    zoomAt(event.clientX, event.clientY, event.deltaY < 0 ? 1.08 : 0.92);
  }, { passive: false });
  viewport.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    window.getSelection()?.removeAllRanges();
    const node = event.target.closest('.node-card');
    state.dragging = {
      x: event.clientX,
      y: event.clientY,
      tx: state.transform.x,
      ty: state.transform.y,
      nodeId: node?.dataset.nodeId || null,
      moved: false,
    };
    viewport.classList.add('dragging');
    document.body.classList.add('map-dragging');
    viewport.setPointerCapture(event.pointerId);
  });
  viewport.addEventListener('pointermove', (event) => {
    if (moveDraggedNode(event)) return;
    if (!state.dragging) return;
    event.preventDefault();
    window.getSelection()?.removeAllRanges();
    const dx = event.clientX - state.dragging.x;
    const dy = event.clientY - state.dragging.y;
    if (Math.hypot(dx, dy) > 3) state.dragging.moved = true;
    state.transform.x = state.dragging.tx + dx;
    state.transform.y = state.dragging.ty + dy;
    applyTransform();
  });
  viewport.addEventListener('pointerup', (event) => {
    if (finishNodeDrag()) return;
    if (state.dragging?.moved) saveTransform();
    if (state.dragging?.moved) state.suppressClick = true;
    if (state.dragging?.nodeId && !state.dragging.moved) selectNode(state.dragging.nodeId);
    state.dragging = null;
    viewport.classList.remove('dragging');
    document.body.classList.remove('map-dragging');
    window.getSelection()?.removeAllRanges();
  });
  viewport.addEventListener('pointercancel', () => {
    finishNodeDrag();
    if (state.dragging?.moved) saveTransform();
    state.dragging = null;
    viewport.classList.remove('dragging');
    document.body.classList.remove('map-dragging');
    window.getSelection()?.removeAllRanges();
  });
  const panFromMinimap = (event) => {
    const rect = minimap.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * state.graph.width;
    const y = ((event.clientY - rect.top) / rect.height) * state.graph.height;
    const viewRect = viewport.getBoundingClientRect();
    state.transform.x = viewRect.width / 2 - x * state.transform.scale;
    state.transform.y = viewRect.height / 2 - y * state.transform.scale;
    applyTransform();
    saveTransform();
  };
  minimap.addEventListener('click', panFromMinimap);
  minimap.addEventListener('pointerdown', (event) => {
    panFromMinimap(event);
    minimap.setPointerCapture(event.pointerId);
  });
  minimap.addEventListener('pointermove', (event) => {
    if (event.buttons === 1) panFromMinimap(event);
  });
  minimap.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      focusSelection(state.selectedId);
    }
  });
  window.addEventListener('resize', () => {
    renderMinimap();
  });
  window.addEventListener('pointermove', moveDraggedNode);
  window.addEventListener('pointerup', finishNodeDrag);
}

function updateModeButtons() {
  document.querySelectorAll('.seg-btn').forEach((button) => {
    const active = button.dataset.mode === state.mode;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  document.querySelectorAll('.mode-btn').forEach((button) => {
    const active = button.dataset.appMode === state.appMode;
    button.classList.toggle('active', active);
    button.setAttribute('aria-checked', String(active));
  });
  document.querySelectorAll('.density-btn').forEach((button) => {
    const active = button.dataset.density === state.density;
    button.classList.toggle('active', active);
    button.setAttribute('aria-checked', String(active));
  });
  document.getElementById('constructorToolbar').hidden = state.appMode !== 'constructor';
  document.getElementById('lockBtn')?.classList.toggle('active', userConfig.lock);
  document.getElementById('lockBtn')?.setAttribute('aria-pressed', String(userConfig.lock));
  document.getElementById('snapBtn')?.classList.toggle('active', userConfig.snap);
  document.getElementById('snapBtn')?.setAttribute('aria-pressed', String(userConfig.snap));
  applyUserConfig();
}

function updateMcpViewButtons() {
  document.querySelectorAll('.mcp-view-btn').forEach((button) => {
    const active = button.dataset.mcpView === state.mcpView;
    button.classList.toggle('active', active);
    button.setAttribute('aria-checked', String(active));
  });
}

function init() {
  applyUserConfig();
  renderStatus();
  setupEvents();
  updateModeButtons();
  resetView();
  refreshGraph();
  focusSelection('overlord');
  maybeShowOnboarding();
}

function maybeShowOnboarding() {
  return;
  if (localStorage.getItem('hermes-onboarded')) return;
  const card = el('div', 'onboarding-card');
  card.append(el('strong', null, 'Быстрый старт'));
  card.append(el('p', null, 'Переключай Поток/Проекты/MCP, кликай ноды, смотри live-логи в инспекторе. Горячие клавиши: F, /, M, +, -, 0.'));
  const button = el('button', 'icon-btn', 'Понял');
  button.type = 'button';
  button.addEventListener('click', () => {
    localStorage.setItem('hermes-onboarded', '1');
    card.remove();
  });
  card.append(button);
  document.body.append(card);
}

init();
