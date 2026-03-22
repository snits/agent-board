// ABOUTME: Main application logic for Agent Board — loads meeting data, renders chat messages,
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
    currentMeetingId: null,
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
  function renderSidebar() {
    projectTree.innerHTML = '';
    if (!state.index || !state.index.projects) return;

    state.index.projects.forEach((project) => {
      const projectEl = createEl('div', 'tree-project');
      const labelEl = createEl('div', 'tree-label');
      labelEl.innerHTML = `<span class="chevron">▸</span><span>${esc(project.displayName)}</span>`;
      projectEl.appendChild(labelEl);

      const childrenEl = createEl('div', 'tree-children');

      project.sessions.forEach((session) => {
        const sessionEl = createEl('div', 'tree-session');
        sessionEl.dataset.sessionId = session.id;

        const sLabelEl = createEl('div', 'tree-label');
        const timeStr = formatDate(session.startTime);
        sLabelEl.innerHTML = `<span class="chevron">▸</span><span>${timeStr}</span>` +
          `<span class="session-meta">${session.meetingCount}m · ${session.agentCount}a</span>`;
        sessionEl.appendChild(sLabelEl);

        const sMeetings = createEl('div', 'tree-children');
        sessionEl.appendChild(sMeetings);

        sLabelEl.addEventListener('click', (e) => {
          e.stopPropagation();
          toggleSession(sessionEl, session.id);
        });

        childrenEl.appendChild(sessionEl);
      });

      projectEl.appendChild(childrenEl);

      labelEl.addEventListener('click', () => {
        projectEl.classList.toggle('expanded');
      });

      projectTree.appendChild(projectEl);
    });
  }

  async function toggleSession(sessionEl, sessionId) {
    if (sessionEl.classList.contains('expanded')) {
      sessionEl.classList.remove('expanded');
      return;
    }

    sessionEl.classList.add('expanded');

    // Lazy-load session data
    if (!state.sessionCache[sessionId]) {
      const meetingsContainer = sessionEl.querySelector('.tree-children');
      meetingsContainer.innerHTML = '<div style="padding: 6px 44px; color: var(--text-muted); font-size: 12px;">Loading…</div>';
      try {
        const data = await fetchJSON(`/data/sessions/${sessionId}/session.json`);
        state.sessionCache[sessionId] = data;
      } catch (err) {
        meetingsContainer.innerHTML = `<div style="padding: 6px 44px; color: var(--accent-red); font-size: 12px;">Failed to load</div>`;
        return;
      }
    }

    renderSessionMeetings(sessionEl, sessionId);
  }

  function renderSessionMeetings(sessionEl, sessionId) {
    const session = state.sessionCache[sessionId];
    const meetingsContainer = sessionEl.querySelector('.tree-children');
    meetingsContainer.innerHTML = '';

    session.meetings.forEach((meeting) => {
      const meetingEl = createEl('div', 'tree-meeting');
      meetingEl.dataset.meetingId = meeting.id;
      meetingEl.dataset.sessionId = sessionId;

      const mLabel = createEl('div', 'tree-label');
      const name = meeting.teamName || 'Unnamed Meeting';
      const truncName = name.length > 22 ? name.slice(0, 22) + '…' : name;
      mLabel.innerHTML = `<span class="meeting-dot"></span><span>${esc(truncName)}</span>` +
        `<span class="meeting-agents">${meeting.agentCount}a</span>`;
      meetingEl.appendChild(mLabel);

      mLabel.addEventListener('click', (e) => {
        e.stopPropagation();
        loadMeeting(sessionId, meeting.id, name);
      });

      meetingsContainer.appendChild(meetingEl);
    });
  }

  // ── Meeting loading ────────────────────────────────────
  async function loadMeeting(sessionId, meetingId, meetingName) {
    // Update active state in sidebar
    document.querySelectorAll('.tree-meeting.active').forEach((el) => el.classList.remove('active'));
    const activeEl = document.querySelector(`.tree-meeting[data-meeting-id="${meetingId}"]`);
    if (activeEl) activeEl.classList.add('active');

    state.currentSessionId = sessionId;
    state.currentMeetingId = meetingId;
    state.agentFilter = null;
    state.searchQuery = '';
    searchInput.value = '';

    chatHeader.textContent = meetingName || 'Meeting';
    showLoading();

    try {
      const data = await fetchJSON(`/data/sessions/${sessionId}/meetings/${meetingId}.json`);
      state.currentMeeting = data;
      renderRoster(data.agents);
      renderMessages(data);
    } catch (err) {
      showError('Failed to load meeting: ' + err.message);
    }
  }

  // ── Roster rendering ──────────────────────────────────
  function renderRoster(agents) {
    agentRoster.innerHTML = '';
    if (!agents || agents.length === 0) return;

    // Detect duplicate types for ID suffix display
    const typeCounts = {};
    agents.forEach((a) => {
      typeCounts[a.type] = (typeCounts[a.type] || 0) + 1;
    });

    agents
      .sort((a, b) => b.messageCount - a.messageCount)
      .forEach((agent) => {
        const el = createEl('div', 'roster-agent');
        el.dataset.agentId = agent.agentId;

        const color = getAgentColor(agent.type);
        const label = getAgentLabel(agent.type);
        const showSuffix = typeCounts[agent.type] > 1;
        const suffix = showSuffix ? agent.agentId.slice(-4) : '';

        el.innerHTML =
          `<span class="roster-dot" style="background:${color}"></span>` +
          `<span class="roster-name">${esc(label)}${suffix ? ` <span class="roster-id-suffix">#${suffix}</span>` : ''}</span>` +
          `<span class="roster-count">${agent.messageCount}</span>`;

        el.addEventListener('click', () => {
          if (state.agentFilter === agent.agentId) {
            state.agentFilter = null;
            el.classList.remove('active-filter');
          } else {
            document.querySelectorAll('.roster-agent.active-filter').forEach((e) => e.classList.remove('active-filter'));
            state.agentFilter = agent.agentId;
            el.classList.add('active-filter');
          }
          applyFilters();
        });

        agentRoster.appendChild(el);
      });

    // Auto-open roster when meeting loads
    if (!state.rosterVisible) {
      state.rosterVisible = true;
      rosterPanel.classList.remove('hidden');
      app.classList.add('roster-open');
    }
  }

  // ── Message rendering (batched with rAF) ──────────────
  function renderMessages(meeting) {
    chatMessages.innerHTML = '';

    if (!meeting.messages || meeting.messages.length === 0) {
      chatMessages.innerHTML = '<div class="empty-state"><div class="empty-icon">∅</div><div class="empty-text">No messages in this meeting.</div></div>';
      hideProgress();
      return;
    }

    const messages = meeting.messages;
    const total = messages.length;
    const BATCH_SIZE = 50;
    let index = 0;

    const fragment = document.createDocumentFragment();

    showProgress(0, total);

    function renderBatch() {
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
    const agentId = state.agentFilter;

    messages.forEach((el) => {
      let visible = true;

      if (agentId && el.dataset.agentId !== agentId) {
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
    chatMessages.innerHTML = '<div class="loading-state"><div class="spinner"></div><div>Loading meeting…</div></div>';
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
