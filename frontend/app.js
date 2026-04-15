// ABOUTME: Main application logic for Agent Board — loads session data, renders chat messages,
// ABOUTME: and manages sidebar navigation, agent roster filtering, and search.

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────
  const state = {
    agentTypes: {},             // type → {color, label}
    index: null,                // project index data
    sessionCache: {},           // sessionId → session.json data
    currentMeeting: null,       // currently loaded meeting data
    currentSessionId: null,
    agentFilter: null,          // agentId to filter by, or null
    searchQuery: '',            // current search text
    rosterVisible: false,
    sidebarCollapsed: false,
  };

  // ── DOM references ─────────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const app = $('#app');
  const projectTree = $('#project-tree');
  const chatMessages = $('#chat-messages');
  const chatHeader = $('#meeting-title');
  const searchInput = $('#search-input');
  const rosterPanel = $('#roster-panel');
  const agentRoster = $('#agent-roster');
  const toggleRoster = $('#toggle-roster');
  const closeRoster = $('#close-roster');
  const toggleSidebar = $('#toggle-sidebar');
  const refreshBtn = $('#refresh-data');
  const renderProgress = $('#render-progress');
  const progressFill = $('#progress-fill');
  const progressText = $('#progress-text');

  // ── Initialization ─────────────────────────────────────
  async function init() {
    bindEvents();
    try {
      const [indexData, typesData] = await Promise.all([
        fetchJSON('/data/index.json'),
        fetchJSON('/data/agent-types.json'),
      ]);
      state.index = indexData;
      state.agentTypes = typesData;
      renderSidebar();
    } catch (err) {
      showError('Failed to load application data: ' + err.message);
    }
  }

  function bindEvents() {
    toggleRoster.addEventListener('click', () => {
      state.rosterVisible = !state.rosterVisible;
      rosterPanel.classList.toggle('hidden', !state.rosterVisible);
      app.classList.toggle('roster-open', state.rosterVisible);
    });

    closeRoster.addEventListener('click', () => {
      state.rosterVisible = false;
      rosterPanel.classList.add('hidden');
      app.classList.remove('roster-open');
    });

    toggleSidebar.addEventListener('click', () => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      app.classList.toggle('sidebar-collapsed', state.sidebarCollapsed);
    });

    refreshBtn.addEventListener('click', refreshData);

    let searchDebounce = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        state.searchQuery = searchInput.value.trim().toLowerCase();
        applyFilters();
      }, 150);
    });
  }

  // ── Fetch helper ───────────────────────────────────────
  async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
    return resp.json();
  }

  // ── Sidebar rendering ─────────────────────────────────
  const SESSION_CAP = 20;

  function buildSessionEl(session) {
    const sessionEl = createEl('div', 'tree-session');
    sessionEl.dataset.sessionId = session.id;

    const sLabelEl = createEl('div', 'tree-label');
    const timeStr = formatDate(session.startTime);
    const agentMeta = session.agentCount >= 2
      ? `<span class="session-meta">${session.agentCount}a</span>`
      : '';
    sLabelEl.innerHTML = `<span class="chevron">&#x25B8;</span><span>${timeStr}</span>${agentMeta}`;
    sessionEl.appendChild(sLabelEl);

    sLabelEl.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleSession(sessionEl, session.id);
    });

    return sessionEl;
  }

  function renderSidebar() {
    projectTree.innerHTML = '';
    if (!state.index || !state.index.projects) return;

    state.index.projects.forEach((project) => {
      const projectEl = createEl('div', 'tree-project');
      const labelEl = createEl('div', 'tree-label');
      const sessionCount = project.sessions ? project.sessions.length : 0;
      const countBadge = sessionCount > 0
        ? `<span class="project-count">(${sessionCount})</span>`
        : '';
      labelEl.innerHTML =
        `<span class="chevron">&#x25B8;</span><span>${esc(project.displayName)}</span>${countBadge}`;
      projectEl.appendChild(labelEl);

      const childrenEl = createEl('div', 'tree-children');

      // Sort sessions by startTime descending; null startTime sorts last
      const sorted = (project.sessions || []).slice().sort((a, b) => {
        if (!a.startTime && !b.startTime) return 0;
        if (!a.startTime) return 1;
        if (!b.startTime) return -1;
        return b.startTime < a.startTime ? -1 : b.startTime > a.startTime ? 1 : 0;
      });

      const visible = sorted.slice(0, SESSION_CAP);
      const hidden = sorted.slice(SESSION_CAP);

      visible.forEach((session) => {
        childrenEl.appendChild(buildSessionEl(session));
      });

      if (hidden.length > 0) {
        const showAllEl = createEl('div', 'tree-show-all');
        showAllEl.textContent = `Show all ${sorted.length} sessions\u2026`;
        showAllEl.addEventListener('click', (e) => {
          e.stopPropagation();
          hidden.forEach((session) => {
            childrenEl.insertBefore(buildSessionEl(session), showAllEl);
          });
          showAllEl.remove();
        });
        childrenEl.appendChild(showAllEl);
      }

      projectEl.appendChild(childrenEl);

      labelEl.addEventListener('click', () => {
        projectEl.classList.toggle('expanded');
      });

      projectTree.appendChild(projectEl);
    });
  }

  async function toggleSession(sessionEl, sessionId) {
    // Highlight active session
    document.querySelectorAll('.tree-session.active').forEach((el) => el.classList.remove('active'));
    sessionEl.classList.add('active');

    state.currentSessionId = sessionId;
    state.agentFilter = null;
    state.searchQuery = '';
    searchInput.value = '';

    showLoading();

    try {
      const [sessionData, messages] = await Promise.all([
        fetchJSON(`/data/sessions/${sessionId}/session.json`),
        fetchJSON(`/data/sessions/${sessionId}/messages.json`),
      ]);
      state.sessionCache[sessionId] = sessionData;
      state.currentMeeting = { messages, agents: sessionData.agents || [] };
      chatHeader.textContent = formatDate(sessionData.startTime) || 'Session';
      renderRoster(sessionData.agents || []);
      renderMessages(state.currentMeeting);
    } catch (err) {
      showError('Failed to load session: ' + err.message);
    }
  }

  // ── Roster rendering ──────────────────────────────────
  function renderRoster(agents) {
    agentRoster.innerHTML = '';
    if (!agents || agents.length === 0) return;

    // Group agents by type, summing message counts
    const byType = {};
    agents.forEach((a) => {
      if (!byType[a.type]) {
        byType[a.type] = { type: a.type, messageCount: 0, agentIds: [] };
      }
      byType[a.type].messageCount += a.messageCount;
      byType[a.type].agentIds.push(a.agentId);
    });

    Object.values(byType)
      .sort((a, b) => b.messageCount - a.messageCount)
      .forEach((group) => {
        const el = createEl('div', 'roster-agent');
        el.dataset.agentType = group.type;

        const color = getAgentColor(group.type);
        const label = getAgentLabel(group.type);
        const instanceCount = group.agentIds.length > 1 ? ` <span class="roster-id-suffix">×${group.agentIds.length}</span>` : '';

        el.innerHTML =
          `<span class="roster-dot" style="background:${color}"></span>` +
          `<span class="roster-name">${esc(label)}${instanceCount}</span>` +
          `<span class="roster-count">${group.messageCount}</span>`;

        el.addEventListener('click', () => {
          if (state.agentFilter === group.type) {
            state.agentFilter = null;
            el.classList.remove('active-filter');
          } else {
            document.querySelectorAll('.roster-agent.active-filter').forEach((e) => e.classList.remove('active-filter'));
            state.agentFilter = group.type;
            el.classList.add('active-filter');
          }
          applyFilters();
        });

        agentRoster.appendChild(el);
      });

    // Auto-open roster when meeting loads (only if there are agents to show)
    if (!state.rosterVisible && agents.length > 0) {
      state.rosterVisible = true;
      rosterPanel.classList.remove('hidden');
      app.classList.add('roster-open');
    }
  }

  // ── Message rendering (batched with rAF) ──────────────
  function renderMessages(meeting) {
    chatMessages.innerHTML = '';

    if (!meeting.messages || meeting.messages.length === 0) {
      chatMessages.innerHTML = '<div class="empty-state"><div class="empty-icon">∅</div><div class="empty-text">No messages in this session.</div></div>';
      hideProgress();
      return;
    }

    // Filter out empty messages (tool result plumbing with no content or tools)
    const messages = meeting.messages.filter(
      (msg) => (msg.content && msg.content.trim()) || (msg.toolUse && msg.toolUse.length > 0)
    );
    const total = messages.length;
    const BATCH_SIZE = 50;

    // Skip per-message animation for large meetings to avoid jank
    chatMessages.classList.toggle('batch-rendered', total > BATCH_SIZE);
    let index = 0;

    showProgress(0, total);

    function renderBatch() {
      const fragment = document.createDocumentFragment();
      const end = Math.min(index + BATCH_SIZE, total);
      for (let i = index; i < end; i++) {
        fragment.appendChild(buildMessageEl(messages[i]));
      }
      chatMessages.appendChild(fragment);
      index = end;

      updateProgress(index, total);

      if (index < total) {
        requestAnimationFrame(renderBatch);
      } else {
        hideProgress();
        applyFilters();
        // Scroll to top after render
        chatMessages.scrollTop = 0;
      }
    }

    requestAnimationFrame(renderBatch);
  }

  function buildMessageEl(msg) {
    const el = createEl('div', 'message');
    el.dataset.agentId = msg.agentId || '';
    el.dataset.agentType = msg.agentType || '';
    el.dataset.uuid = msg.uuid || '';

    const color = getAgentColor(msg.agentType);
    el.style.borderLeftColor = color;

    // Header
    const header = createEl('div', 'message-header');

    // Agent badge
    const badge = createEl('span', 'agent-badge');
    badge.innerHTML = `<span class="agent-dot" style="background:${color}"></span>${esc(getAgentLabel(msg.agentType))}`;
    header.appendChild(badge);

    // Role pill
    const rolePill = createEl('span', 'role-pill');
    rolePill.textContent = msg.role || 'unknown';
    header.appendChild(rolePill);

    // Dispatched by
    if (msg.sender) {
      const dispatch = createEl('span', 'msg-dispatch');
      dispatch.innerHTML = `dispatched by: <span class="sender-name">${esc(msg.sender)}</span>`;
      header.appendChild(dispatch);
    }

    // Summary (task description)
    if (msg.summary) {
      const summaryEl = createEl('span', 'msg-dispatch');
      summaryEl.textContent = '· ' + msg.summary;
      header.appendChild(summaryEl);
    }

    // Timestamp
    const ts = createEl('span', 'msg-timestamp');
    ts.textContent = formatTime(msg.timestamp);
    header.appendChild(ts);

    el.appendChild(header);

    // Content
    if (msg.content && msg.content.trim()) {
      const body = createEl('div', 'message-body');
      body.innerHTML = renderMarkdown(msg.content);
      el.appendChild(body);
    }

    // Tool use blocks
    if (msg.toolUse && msg.toolUse.length > 0) {
      const toolBlock = createEl('div', 'tool-block');
      msg.toolUse.forEach((tool) => {
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.innerHTML =
          `<span class="tool-icon">⚙</span>` +
          `<span class="tool-name">${esc(tool.tool)}</span>` +
          `<span class="tool-summary">${esc(tool.summary || '')}</span>`;
        details.appendChild(summary);

        if (tool.input) {
          const inputEl = createEl('div', 'tool-input');
          inputEl.textContent = JSON.stringify(tool.input, null, 2);
          details.appendChild(inputEl);
        }

        toolBlock.appendChild(details);
      });
      el.appendChild(toolBlock);
    }

    return el;
  }

  // ── Filtering ──────────────────────────────────────────
  function applyFilters() {
    const messages = chatMessages.querySelectorAll('.message');
    const query = state.searchQuery;
    const filterType = state.agentFilter;

    messages.forEach((el) => {
      let visible = true;

      if (filterType && el.dataset.agentType !== filterType) {
        visible = false;
      }

      if (visible && query) {
        const text = el.textContent.toLowerCase();
        if (!text.includes(query)) {
          visible = false;
        }
      }

      el.classList.toggle('filtered-out', !visible);
    });
  }

  // ── Markdown rendering ─────────────────────────────────
  function renderMarkdown(raw) {
    try {
      const html = marked.parse(raw, { breaks: true, gfm: true });
      return DOMPurify.sanitize(html);
    } catch {
      return DOMPurify.sanitize(raw);
    }
  }

  // ── Agent colors/labels ────────────────────────────────
  function getAgentColor(type) {
    if (state.agentTypes[type]) return state.agentTypes[type].color;
    return '#6a7080';
  }

  function getAgentLabel(type) {
    if (state.agentTypes[type]) return state.agentTypes[type].label;
    if (!type) return 'Unknown';
    // Fallback: title-case the type
    return type.split('-').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  }

  // ── UI state helpers ───────────────────────────────────
  function showLoading() {
    chatMessages.innerHTML = '<div class="loading-state"><div class="spinner"></div><div>Loading session…</div></div>';
  }

  function showError(msg) {
    chatMessages.innerHTML = `<div class="error-state"><div class="error-icon">⚠</div><div class="error-msg">${esc(msg)}</div></div>`;
  }

  function showProgress(current, total) {
    renderProgress.classList.remove('hidden');
    updateProgress(current, total);
  }

  function updateProgress(current, total) {
    const pct = Math.round((current / total) * 100);
    progressFill.style.width = pct + '%';
    progressText.textContent = `${current} / ${total} messages`;
  }

  function hideProgress() {
    renderProgress.classList.add('hidden');
  }

  // ── Refresh ────────────────────────────────────────────
  async function refreshData() {
    refreshBtn.disabled = true;
    refreshBtn.classList.add('refreshing');
    try {
      const resp = await fetch('/api/refresh', { method: 'POST' });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${resp.status}`);
      }
      // Reload index and agent types
      const [indexData, typesData] = await Promise.all([
        fetchJSON('/data/index.json'),
        fetchJSON('/data/agent-types.json'),
      ]);
      state.index = indexData;
      state.agentTypes = typesData;
      state.sessionCache = {};
      renderSidebar();

      // Reload current session if one is selected
      if (state.currentSessionId) {
        const sessionEl = projectTree.querySelector(
          `.tree-session[data-session-id="${state.currentSessionId}"]`
        );
        if (sessionEl) {
          toggleSession(sessionEl, state.currentSessionId);
        }
      }
    } catch (err) {
      showError('Refresh failed: ' + err.message);
    } finally {
      refreshBtn.disabled = false;
      refreshBtn.classList.remove('refreshing');
    }
  }

  // ── Utilities ──────────────────────────────────────────
  function createEl(tag, className) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    return el;
  }

  function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  // ── Boot ───────────────────────────────────────────────
  init();
})();
