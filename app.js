const themeLabels = {
  'distributed-systems': 'Distributed systems',
  'developer-tooling': 'Developer tooling',
  'data-and-ml': 'Data and ML',
  'product-and-ui': 'Product and UI',
  'runtime-and-languages': 'Runtime and languages',
  'performance-and-ops': 'Performance and ops',
};

const storageKey = 'aosa_progress_v2';
const themeStorageKey = 'aosa_theme_v1';
const themeOrder = ['dark', 'light', 'teal', 'reader'];
const themeLabel = {
  dark: 'Dark',
  light: 'Light',
  teal: 'Teal',
  reader: 'Reader',
};

const defaultProgress = {
  completed: [],
  bookmarked: [],
  notes: {},
  completionLog: {},
  readerVisits: [],
};

const achievementsCatalog = [
  {
    id: 'first-blood',
    name: 'First Blood',
    description: 'Complete your first mission.',
    icon: '01',
    unlocked: (state) => state.completed.length >= 1,
  },
  {
    id: 'systems-tour',
    name: 'Systems Tour',
    description: 'Finish 10 missions across any collections.',
    icon: '10',
    unlocked: (state) => state.completed.length >= 10,
  },
  {
    id: 'polyglot-operator',
    name: 'Polyglot Operator',
    description: 'Complete at least one session in every collection.',
    icon: '4X',
    unlocked: (state, data) => data.collections.every((collection) => collection.sessions.some((session) => state.completed.includes(session.id))),
  },
  {
    id: 'perf-hunter',
    name: 'Perf Hunter',
    description: 'Complete 3 performance-themed missions.',
    icon: 'P3',
    unlocked: (state, data) => data.sessions.filter((session) => session.theme === 'performance-and-ops' && state.completed.includes(session.id)).length >= 3,
  },
  {
    id: 'deep-reader',
    name: 'Deep Reader',
    description: 'Save notes in 5 different sessions.',
    icon: 'N5',
    unlocked: (state) => Object.values(state.notes).filter(Boolean).length >= 5,
  },
  {
    id: 'bookmark-broker',
    name: 'Bookmark Broker',
    description: 'Bookmark 8 missions for later.',
    icon: 'B8',
    unlocked: (state) => state.bookmarked.length >= 8,
  },
  {
    id: 'archive-runner',
    name: 'Archive Runner',
    description: 'Read 25 chapters without leaving the app.',
    icon: 'L25',
    unlocked: (state) => state.readerVisits.length >= 25,
  },
];

const els = {
  authScreen: document.querySelector('#auth-screen'),
  themeToggle: document.querySelector('#theme-toggle'),
  journeyStrip: document.querySelector('#journey-strip'),
  journeyTitle: document.querySelector('#journey-title'),
  journeyBadge: document.querySelector('#journey-badge'),
  journeyCopy: document.querySelector('#journey-copy'),
  journeyFill: document.querySelector('#journey-fill'),
  journeyStep1: document.querySelector('#journey-step-1'),
  journeyStep2: document.querySelector('#journey-step-2'),
  journeyStep3: document.querySelector('#journey-step-3'),
  journeyStep4: document.querySelector('#journey-step-4'),
  dashboardView: document.querySelector('#dashboard-view'),
  readerView: document.querySelector('#reader-view'),
  statTotal: document.querySelector('#stat-total'),
  statCompleted: document.querySelector('#stat-completed'),
  statXp: document.querySelector('#stat-xp'),
  statLevel: document.querySelector('#stat-level'),
  statStreak: document.querySelector('#stat-streak'),
  collectionProgress: document.querySelector('#collection-progress'),
  achievements: document.querySelector('#achievements'),
  sessionGrid: document.querySelector('#session-grid'),
  resultsTitle: document.querySelector('#results-title'),
  resultsSubtitle: document.querySelector('#results-subtitle'),
  searchInput: document.querySelector('#search-input'),
  collectionFilter: document.querySelector('#collection-filter'),
  themeFilter: document.querySelector('#theme-filter'),
  statusFilter: document.querySelector('#status-filter'),
  detailEmpty: document.querySelector('#detail-empty'),
  detailContent: document.querySelector('#detail-content'),
  detailCollection: document.querySelector('#detail-collection'),
  detailTheme: document.querySelector('#detail-theme'),
  detailTitle: document.querySelector('#detail-title'),
  detailMeta: document.querySelector('#detail-meta'),
  detailSummary: document.querySelector('#detail-summary'),
  offlineStats: document.querySelector('#offline-stats'),
  pmFocus: document.querySelector('#pm-focus'),
  headingsList: document.querySelector('#headings-list'),
  activitiesList: document.querySelector('#activities-list'),
  quizList: document.querySelector('#quiz-list'),
  notes: document.querySelector('#session-notes'),
  sourceLink: document.querySelector('#source-link'),
  readOffline: document.querySelector('#read-offline'),
  completeToggle: document.querySelector('#complete-toggle'),
  bookmarkToggle: document.querySelector('#bookmark-toggle'),
  questTitle: document.querySelector('#quest-title'),
  questSummary: document.querySelector('#quest-summary'),
  questMeta: document.querySelector('#quest-meta'),
  questBadge: document.querySelector('#quest-badge'),
  openQuest: document.querySelector('#open-quest'),
  openQuestReader: document.querySelector('#open-quest-reader'),
  randomQuest: document.querySelector('#random-quest'),
  startNext: document.querySelector('#start-next'),
  readerTitle: document.querySelector('#reader-title'),
  readerSubtitle: document.querySelector('#reader-subtitle'),
  readerCollection: document.querySelector('#reader-collection'),
  readerTheme: document.querySelector('#reader-theme'),
  readerSummary: document.querySelector('#reader-summary'),
  readerBack: document.querySelector('#reader-back'),
  readerBookmark: document.querySelector('#reader-bookmark'),
  readerComplete: document.querySelector('#reader-complete'),
  readerSourceLink: document.querySelector('#reader-source-link'),
  readerStats: document.querySelector('#reader-stats'),
  readerToc: document.querySelector('#reader-toc'),
  readerNotes: document.querySelector('#reader-notes'),
  readerLoading: document.querySelector('#reader-loading'),
  readerContent: document.querySelector('#reader-content'),
  toast: document.querySelector('#toast'),
};

const app = {
  data: null,
  state: structuredClone(defaultProgress),
  sessionLookup: new Map(),
  contentCache: new Map(),
  selectedSessionId: null,
  currentView: 'dashboard',
  persistTimer: null,
  toastTimer: null,
};

bindEvents();
bootstrap();

async function bootstrap() {
  applyTheme(loadTheme());
  try {
    const response = await fetch('data/aosa_dataset.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Dataset not found');
    app.data = await response.json();
  } catch (error) {
    if (els.authScreen) {
      els.authScreen.classList.remove('hidden');
      els.authScreen.innerHTML = '<div class="auth-card panel"><p class="eyebrow">Make PM tech again</p><h1 class="auth-title">Dataset not loaded.</h1><p class="hero-text">Serve this app from a web server and keep <code>data/aosa_dataset.json</code> in place.</p></div>';
    }
    return;
  }

  app.state = loadProgress();
  app.sessionLookup = new Map(app.data.sessions.map((session) => [session.id, session]));
  app.selectedSessionId = getInitialSessionId();
  app.currentView = getInitialView();

  showApp();
  populateFiltersOnce();
  render();
  if (app.currentView === 'reader') renderReader();
}

function bindEvents() {
  els.themeToggle?.addEventListener('click', toggleTheme);

  ['input', 'change'].forEach((eventName) => {
    els.searchInput?.addEventListener(eventName, renderSessionGrid);
    els.collectionFilter?.addEventListener(eventName, renderSessionGrid);
    els.themeFilter?.addEventListener(eventName, renderSessionGrid);
    els.statusFilter?.addEventListener(eventName, renderSessionGrid);
  });

  els.completeToggle?.addEventListener('click', () => toggleComplete(app.selectedSessionId));
  els.bookmarkToggle?.addEventListener('click', () => toggleBookmark(app.selectedSessionId));
  els.readOffline?.addEventListener('click', () => openReader(app.selectedSessionId));
  els.notes?.addEventListener('input', (event) => handleNotesInput(app.selectedSessionId, event.target.value));
  els.readerNotes?.addEventListener('input', (event) => handleNotesInput(app.selectedSessionId, event.target.value));
  els.openQuest?.addEventListener('click', () => openSession(getRecommendedSession()));
  els.openQuestReader?.addEventListener('click', () => openReader(getRecommendedSession()?.id));
  els.startNext?.addEventListener('click', () => openSession(getRecommendedSession()));
  els.randomQuest?.addEventListener('click', () => openSession(getRandomSession()));
  els.readerBack?.addEventListener('click', closeReader);
  els.readerBookmark?.addEventListener('click', () => toggleBookmark(app.selectedSessionId));
  els.readerComplete?.addEventListener('click', () => toggleComplete(app.selectedSessionId));
  els.readerContent?.addEventListener('click', handleReaderLinkClick);
  window.addEventListener('popstate', handlePopState);
}

function showApp() {
  els.authScreen?.classList.add('hidden');
  els.journeyStrip?.classList.remove('hidden');
}

function populateFiltersOnce() {
  if (!els.collectionFilter || els.collectionFilter.options.length > 1) return;

  app.data.collections.forEach((collection) => {
    const option = document.createElement('option');
    option.value = collection.id;
    option.textContent = collection.name;
    els.collectionFilter.append(option);
  });

  Object.entries(themeLabels).forEach(([value, label]) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    els.themeFilter.append(option);
  });
}

function render() {
  syncViewVisibility();
  renderStats();
  renderJourney();
  renderQuest();
  renderAchievements();
  renderCollectionProgress();
  renderSessionGrid();
  renderDetail();
}

function syncViewVisibility() {
  const readerMode = app.currentView === 'reader';
  els.dashboardView?.classList.toggle('hidden', readerMode);
  els.readerView?.classList.toggle('hidden', !readerMode);
  els.journeyStrip?.classList.toggle('hidden', readerMode);
}

function renderStats() {
  const completedCount = app.state.completed.length;
  const xp = calculateXp();
  const level = Math.max(1, Math.floor(xp / 550) + 1);
  if (els.statTotal) els.statTotal.textContent = app.data.totalSessions;
  if (els.statCompleted) els.statCompleted.textContent = completedCount;
  if (els.statXp) els.statXp.textContent = xp;
  if (els.statLevel) els.statLevel.textContent = level;
  if (els.statStreak) els.statStreak.textContent = calculateStreak();
}

function renderJourney() {
  const total = app.data.totalSessions || 1;
  const completed = app.state.completed.length;
  const percent = Math.min(100, Math.round((completed / total) * 100));
  const stage = percent >= 75 ? 4 : percent >= 50 ? 3 : percent >= 25 ? 2 : 1;
  const stageNames = ['Scout', 'Builder', 'Operator', 'Architect'];
  const nextName = stage < 4 ? stageNames[stage] : 'Mastery loop';

  if (els.journeyFill) els.journeyFill.style.width = `${percent}%`;
  if (els.journeyTitle) els.journeyTitle.textContent = `${percent}% complete on Make PM tech again (AOSA)`;
  if (els.journeyBadge) els.journeyBadge.textContent = `Stage ${stage}: ${stageNames[stage - 1]}`;
  if (els.journeyCopy) {
    els.journeyCopy.textContent = stage < 4
      ? `${total - completed} missions left. Reach ${nextName} at ${stage * 25}%.`
      : 'All core stages cleared. Use random missions and notes to deepen retention.';
  }

  [els.journeyStep1, els.journeyStep2, els.journeyStep3, els.journeyStep4].forEach((element, index) => {
    if (!element) return;
    const step = index + 1;
    element.classList.toggle('active', step === stage);
    element.classList.toggle('reached', step < stage);
  });
}

function renderQuest() {
  const session = getRecommendedSession();
  if (!session) return;

  if (els.questTitle) els.questTitle.textContent = `${formatSessionCode(session)} · ${session.title}`;
  if (els.questSummary) els.questSummary.textContent = session.summary;
  if (els.questBadge) els.questBadge.textContent = app.state.completed.includes(session.id) ? 'Completed' : 'Next up';
  if (!els.questMeta) return;
  els.questMeta.innerHTML = '';

  [`~${getSessionMinutes(session)} min`, `${themeLabels[session.theme]}`, `${session.offline.imageCount} figures`].forEach((text) => {
    const chip = document.createElement('div');
    chip.className = 'quest-chip';
    chip.innerHTML = `<strong>${text}</strong><span class="muted">${session.collectionName}</span>`;
    els.questMeta.append(chip);
  });
}

function renderAchievements() {
  if (!els.achievements) return;
  els.achievements.innerHTML = '';
  achievementsCatalog.forEach((achievement) => {
    const unlocked = achievement.unlocked(app.state, app.data);
    const card = document.createElement('article');
    card.className = `achievement ${unlocked ? 'unlocked' : ''}`;
    card.innerHTML = `
      <div class="pill ${unlocked ? '' : 'pill-soft'}">${achievement.icon}</div>
      <p class="achievement-name">${achievement.name}</p>
      <p class="muted">${achievement.description}</p>
    `;
    els.achievements.append(card);
  });
}

function renderCollectionProgress() {
  if (!els.collectionProgress) return;
  els.collectionProgress.innerHTML = '';
  app.data.collections.forEach((collection) => {
    const completed = collection.sessions.filter((session) => app.state.completed.includes(session.id)).length;
    const percent = Math.round((completed / collection.sessions.length) * 100);
    const card = document.createElement('article');
    card.className = 'collection-card';
    card.innerHTML = `
      <p class="eyebrow">${collection.tone}</p>
      <strong>${collection.name}</strong>
      <p class="muted">${collection.tagline}</p>
      <p>${completed}/${collection.sessions.length} complete · ${percent}%</p>
      <div class="collection-fill" style="width:${percent}%;"></div>
    `;
    els.collectionProgress.append(card);
  });
}

function renderSessionGrid() {
  const sessions = getFilteredSessions();
  if (!els.sessionGrid) return;
  els.sessionGrid.innerHTML = '';
  if (els.resultsTitle) els.resultsTitle.textContent = `${sessions.length} detailed missions`;
  if (els.resultsSubtitle) els.resultsSubtitle.textContent = `${app.state.completed.length}/${app.data.totalSessions} completed · stored in this browser`;

  sessions.forEach((session) => {
    const card = document.createElement('article');
    card.className = `session-card ${session.id === app.selectedSessionId ? 'active' : ''}`;
    card.addEventListener('click', () => openSession(session));
    const done = app.state.completed.includes(session.id);
    const saved = app.state.bookmarked.includes(session.id);
    const kindLabel = session.sessionKind === 'chapter' ? 'Chapter' : capitalize(session.sessionKind);

    card.innerHTML = `
      <div class="session-topline">
        <span class="pill">${formatSessionCode(session)}</span>
        <div class="session-flags">
          <span class="flag ${done ? 'done' : ''}" title="Completed"></span>
          <span class="flag ${saved ? 'saved' : ''}" title="Bookmarked"></span>
        </div>
      </div>
      <h3>${escapeHtml(session.title)}</h3>
      <p class="muted">${escapeHtml(session.author || 'AOSA contributor')} · ${kindLabel}</p>
      <p class="session-summary">${escapeHtml(session.summary)}</p>
      <div class="session-bottomline">
        <span>${themeLabels[session.theme]}</span>
        <span>~${getSessionMinutes(session)} min · ${session.offline.wordCount.toLocaleString()} words</span>
      </div>
    `;
    els.sessionGrid.append(card);
  });

  if (!sessions.find((session) => session.id === app.selectedSessionId)) {
    app.selectedSessionId = sessions[0]?.id || null;
  }
}

function renderDetail() {
  const session = app.sessionLookup.get(app.selectedSessionId);
  if (!session) {
    els.detailEmpty?.classList.remove('hidden');
    els.detailContent?.classList.add('hidden');
    return;
  }

  els.detailEmpty?.classList.add('hidden');
  els.detailContent?.classList.remove('hidden');
  if (els.detailCollection) els.detailCollection.textContent = `${formatSessionCode(session)} · ${session.collectionName}`;
  if (els.detailTheme) els.detailTheme.textContent = themeLabels[session.theme];
  if (els.detailTitle) els.detailTitle.textContent = session.title;
  if (els.detailMeta) {
    els.detailMeta.textContent = `${session.author || 'AOSA contributor'} · ~${getSessionMinutes(session)} minutes · Difficulty ${'★'.repeat(session.difficulty)} · ${capitalize(session.sessionKind)}`;
  }
  if (els.detailSummary) els.detailSummary.textContent = session.summary;
  if (els.sourceLink) els.sourceLink.href = session.url;
  if (els.completeToggle) els.completeToggle.textContent = app.state.completed.includes(session.id) ? 'Completed ✓' : 'Mark Complete';
  if (els.bookmarkToggle) els.bookmarkToggle.textContent = app.state.bookmarked.includes(session.id) ? 'Bookmarked ★' : 'Bookmark';
  if (els.notes) els.notes.value = app.state.notes[session.id] || '';

  if (els.offlineStats) {
    els.offlineStats.innerHTML = `
      ${renderStatChip('In App', 'available')}
      ${renderStatChip('Figures', String(session.offline.imageCount))}
      ${renderStatChip('Code Blocks', String(session.offline.codeBlockCount))}
      ${renderStatChip('Tables', String(session.offline.tableCount))}
      ${renderStatChip('Words', session.offline.wordCount.toLocaleString())}
    `;
  }
  renderList(els.pmFocus, session.pmFocus);
  renderList(els.headingsList, session.headingAnchors.slice(0, 8).map((item) => item.text));
  renderList(els.activitiesList, createAgenda(session));
  renderList(els.quizList, session.quiz);
}

async function renderReader() {
  const session = app.sessionLookup.get(app.selectedSessionId);
  if (!session) return;

  app.currentView = 'reader';
  syncViewVisibility();
  updateUrl();

  if (!app.state.readerVisits.includes(session.id)) {
    app.state.readerVisits = [...app.state.readerVisits, session.id];
    persistProgress();
    renderAchievements();
  }

  if (els.readerTitle) els.readerTitle.textContent = session.title;
  if (els.readerSubtitle) els.readerSubtitle.textContent = `${session.author} · ${session.collectionName} · ${session.offline.wordCount.toLocaleString()} words`;
  if (els.readerCollection) els.readerCollection.textContent = `${formatSessionCode(session)} · ${session.collectionName}`;
  if (els.readerTheme) els.readerTheme.textContent = themeLabels[session.theme];
  if (els.readerSummary) els.readerSummary.textContent = session.summary;
  if (els.readerSourceLink) els.readerSourceLink.href = session.url;
  if (els.readerNotes) els.readerNotes.value = app.state.notes[session.id] || '';
  if (els.readerBookmark) els.readerBookmark.textContent = app.state.bookmarked.includes(session.id) ? 'Saved ★' : 'Save';
  if (els.readerComplete) els.readerComplete.textContent = app.state.completed.includes(session.id) ? 'Completed ✓' : 'Complete';
  renderReaderStats(session);
  renderReaderToc(session);
  if (els.readerLoading) els.readerLoading.classList.remove('hidden');
  if (els.readerContent) els.readerContent.classList.add('hidden');

  try {
    const html = await loadChapterContent(session);
    if (els.readerContent) els.readerContent.innerHTML = html;
    styleReaderContent();
    if (els.readerLoading) els.readerLoading.classList.add('hidden');
    if (els.readerContent) els.readerContent.classList.remove('hidden');
    jumpToHashIfPresent();
  } catch (error) {
    if (els.readerLoading) els.readerLoading.textContent = 'Failed to load chapter content.';
  }
}

function renderReaderStats(session) {
  if (!els.readerStats) return;
  els.readerStats.innerHTML = `
    ${renderStatChip('Read Time', `~${getSessionMinutes(session)} min`)}
    ${renderStatChip('Figures', String(session.offline.imageCount))}
    ${renderStatChip('Code', String(session.offline.codeBlockCount))}
    ${renderStatChip('Tables', String(session.offline.tableCount))}
    ${renderStatChip('Footnotes', session.offline.hasFootnotes ? 'yes' : 'no')}
  `;
}

function renderReaderToc(session) {
  if (!els.readerToc) return;
  els.readerToc.innerHTML = '';
  session.headingAnchors.slice(0, 18).forEach((heading) => {
    const link = document.createElement('a');
    link.href = `#${heading.id}`;
    link.textContent = heading.text;
    link.className = `toc-link ${heading.level === 'h3' ? 'toc-sub' : ''}`;
    els.readerToc.append(link);
  });
}

function renderList(element, items) {
  if (!element) return;
  element.innerHTML = '';
  items.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    element.append(li);
  });
}

function createAgenda(session) {
  return [
    `Warm-up: read the summary and identify the dominant architectural problem in ${session.title}.`,
    `Read-through: work sections ${session.headingAnchors.slice(0, 3).map((item) => item.text).join(', ')}.`,
    `PM lens: ${session.pmFocus[0]}.`,
    `Artifact: ${session.activities[0]}`,
    'Reflection: answer the boss-battle prompts before marking complete.',
  ];
}

function openSession(session) {
  if (!session) return;
  app.selectedSessionId = session.id;
  app.currentView = 'dashboard';
  updateUrl();
  render();
  document.querySelector('#detail-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function openDashboard() {
  app.currentView = 'dashboard';
  updateUrl();
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function openReader(sessionId) {
  if (!sessionId || !app.sessionLookup.has(sessionId)) return;
  app.selectedSessionId = sessionId;
  render();
  renderReader();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function closeReader() {
  app.currentView = 'dashboard';
  updateUrl();
  syncViewVisibility();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadChapterContent(session) {
  if (app.contentCache.has(session.id)) return app.contentCache.get(session.id);
  const response = await fetch(session.offline.contentPath, { credentials: 'same-origin' });
  if (!response.ok) throw new Error(`Unable to fetch ${session.offline.contentPath}`);
  const html = await response.text();
  app.contentCache.set(session.id, html);
  return html;
}

function styleReaderContent() {
  if (!els.readerContent) return;
  els.readerContent.querySelectorAll('img').forEach((img) => {
    img.loading = 'lazy';
  });
  els.readerContent.querySelectorAll('a').forEach((anchor) => {
    const href = anchor.getAttribute('href') || '';
    if (!href.startsWith('#') && !href.startsWith('?session=')) {
      anchor.target = '_blank';
      anchor.rel = 'noreferrer';
    }
  });
}

function handleReaderLinkClick(event) {
  const anchor = event.target.closest('a[href]');
  if (!anchor) return;
  const href = anchor.getAttribute('href');
  if (!href) return;

  if (href.startsWith('?session=')) {
    event.preventDefault();
    const url = new URL(href, window.location.href);
    const sessionId = url.searchParams.get('session');
    if (sessionId && app.sessionLookup.has(sessionId)) {
      app.selectedSessionId = sessionId;
      app.currentView = url.searchParams.get('view') === 'reader' ? 'reader' : 'dashboard';
      updateUrl(url.hash);
      render();
      if (app.currentView === 'reader') renderReader();
    }
    return;
  }

  if (href.startsWith('#')) {
    event.preventDefault();
    const target = document.getElementById(href.slice(1));
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState({}, '', `?session=${app.selectedSessionId}&view=reader${href}`);
    }
  }
}

function handlePopState() {
  if (!app.data) return;
  app.selectedSessionId = getInitialSessionId();
  app.currentView = getInitialView();
  render();
  if (app.currentView === 'reader') renderReader();
}

function toggleComplete(sessionId) {
  if (!sessionId) return;
  const session = app.sessionLookup.get(sessionId);
  const isComplete = app.state.completed.includes(sessionId);

  if (isComplete) {
    app.state.completed = app.state.completed.filter((id) => id !== sessionId);
    delete app.state.completionLog[sessionId];
    showToast(`Marked ${session.title} as not completed.`);
  } else {
    app.state.completed = [...app.state.completed, sessionId];
    app.state.completionLog[sessionId] = new Date().toISOString().slice(0, 10);
    showToast(`+${session.difficulty * 120} XP for completing ${session.title}.`);
  }

  persistProgress();
  render();
  if (app.currentView === 'reader') renderReader();
}

function toggleBookmark(sessionId) {
  if (!sessionId) return;
  const session = app.sessionLookup.get(sessionId);
  const isBookmarked = app.state.bookmarked.includes(sessionId);
  app.state.bookmarked = isBookmarked
    ? app.state.bookmarked.filter((id) => id !== sessionId)
    : [...app.state.bookmarked, sessionId];
  persistProgress();
  render();
  if (app.currentView === 'reader') renderReader();
  showToast(isBookmarked ? `Removed bookmark for ${session.title}.` : `Bookmarked ${session.title}.`);
}

function handleNotesInput(sessionId, value) {
  if (!sessionId) return;
  app.state.notes[sessionId] = value.trim();
  persistProgress();
  renderAchievements();
}

function persistProgress() {
  window.clearTimeout(app.persistTimer);
  app.persistTimer = window.setTimeout(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(app.state));
    } catch (error) {
      showToast('Unable to save progress in this browser.');
    }
  }, 180);
}

function loadProgress() {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return structuredClone(defaultProgress);
    return normalizeProgress(JSON.parse(raw));
  } catch (error) {
    return structuredClone(defaultProgress);
  }
}

function getFilteredSessions() {
  const search = (els.searchInput?.value || '').trim().toLowerCase();
  const collection = els.collectionFilter?.value || 'all';
  const theme = els.themeFilter?.value || 'all';
  const status = els.statusFilter?.value || 'all';

  return app.data.sessions.filter((session) => {
    const matchesSearch = !search || [
      session.title,
      session.author,
      session.summary,
      themeLabels[session.theme],
      session.searchText,
      ...session.headings,
    ].join(' ').toLowerCase().includes(search);

    const matchesCollection = collection === 'all' || session.collectionId === collection;
    const matchesTheme = theme === 'all' || session.theme === theme;
    const matchesStatus =
      status === 'all' ||
      (status === 'remaining' && !app.state.completed.includes(session.id)) ||
      (status === 'completed' && app.state.completed.includes(session.id)) ||
      (status === 'bookmarked' && app.state.bookmarked.includes(session.id));

    return matchesSearch && matchesCollection && matchesTheme && matchesStatus;
  });
}

function getRecommendedSession() {
  return app.data.sessions.find((session) => !app.state.completed.includes(session.id)) || app.data.sessions[0];
}

function getRandomSession() {
  const pool = getFilteredSessions();
  if (!pool.length) return getRecommendedSession();
  return pool[Math.floor(Math.random() * pool.length)];
}

function calculateXp() {
  return app.state.completed.reduce((sum, sessionId) => {
    const session = app.sessionLookup.get(sessionId);
    return session ? sum + session.difficulty * 120 : sum;
  }, 0);
}

function calculateStreak() {
  const dates = Object.values(app.state.completionLog).sort();
  if (!dates.length) return 0;

  let streak = 1;
  for (let index = dates.length - 1; index > 0; index -= 1) {
    const current = new Date(`${dates[index]}T00:00:00`);
    const previous = new Date(`${dates[index - 1]}T00:00:00`);
    const delta = Math.round((current - previous) / 86400000);
    if (delta === 1) streak += 1;
    else if (delta > 1) break;
  }
  return streak;
}

function getSessionMinutes(session) {
  const words = Number(session?.offline?.wordCount || 0);
  const difficulty = Number(session?.difficulty || 1);
  if (!words) return 20;

  // Friendly estimate: moderate pace + light difficulty adjustment.
  const base = words / 200;
  const adjusted = base * (1 + (difficulty - 1) * 0.08);
  const roundedToFive = Math.round(adjusted / 5) * 5;
  return Math.max(15, Math.min(90, roundedToFive));
}

function getInitialSessionId() {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get('session');
  return app.sessionLookup.has(sessionId) ? sessionId : app.data.sessions[0]?.id || null;
}

function getInitialView() {
  const params = new URLSearchParams(window.location.search);
  const view = params.get('view');
  if (view === 'reader') return 'reader';
  return 'dashboard';
}

function updateUrl(hash = window.location.hash) {
  const params = new URLSearchParams();
  if (app.selectedSessionId) params.set('session', app.selectedSessionId);
  if (app.currentView === 'reader') params.set('view', 'reader');
  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}${hash || ''}`;
  history.replaceState({}, '', nextUrl);
}

function jumpToHashIfPresent() {
  const hash = window.location.hash;
  if (!hash) return;
  const target = document.getElementById(hash.slice(1));
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function normalizeProgress(progress) {
  return {
    ...structuredClone(defaultProgress),
    ...(progress || {}),
    notes: { ...(progress?.notes || {}) },
    completionLog: { ...(progress?.completionLog || {}) },
  };
}

function renderStatChip(label, value) {
  return `<div class="stat-pill"><strong>${value}</strong><span>${label}</span></div>`;
}

function formatSessionCode(session) {
  if (!session) return 'SESSION';
  if (session.id) return String(session.id).toUpperCase();
  if (typeof session.localIndex === 'number') return `S-${String(session.localIndex).padStart(2, '0')}`;
  return 'SESSION';
}

function showToast(message) {
  if (!els.toast) return;
  els.toast.textContent = message;
  els.toast.classList.remove('hidden');
  window.clearTimeout(app.toastTimer);
  app.toastTimer = window.setTimeout(() => {
    els.toast.classList.add('hidden');
  }, 2400);
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1).replace('-', ' ');
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function loadTheme() {
  const stored = localStorage.getItem(themeStorageKey);
  if (themeOrder.includes(stored)) return stored;
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  return prefersDark ? 'dark' : 'light';
}

function applyTheme(theme) {
  document.body.setAttribute('data-theme', theme);
  if (els.themeToggle) {
    els.themeToggle.textContent = `Theme: ${themeLabel[theme] || 'Dark'}`;
  }
}

function toggleTheme() {
  const current = document.body.getAttribute('data-theme') || 'dark';
  const currentIndex = themeOrder.indexOf(current);
  const next = themeOrder[(currentIndex + 1) % themeOrder.length];
  applyTheme(next);
  localStorage.setItem(themeStorageKey, next);
}
