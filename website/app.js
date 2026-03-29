// ── Config ──
// Frontend config comes from config.js so the public key lives in one place.
// Leave values empty to use built-in demo data.
const runtimeConfig = window.HOUSE_HUNT_CONFIG || {};
const SUPABASE_URL = runtimeConfig.supabaseUrl || '';
const SUPABASE_KEY = runtimeConfig.supabaseKey || '';

// ── Demo Data ──
const DEMO = {
  societies: [
    { id: '1', name: 'Ace Aspire', location: 'Greater Noida West', created_at: '2025-03-20' },
    { id: '2', name: 'Prateek Grand City', location: 'Siddharth Vihar', created_at: '2025-03-18' },
    { id: '3', name: 'Gaur City 2', location: 'Greater Noida West', created_at: '2025-03-15' },
    { id: '4', name: 'Supertech Capetown', location: 'Noida Sector 74', created_at: '2025-03-10' },
    { id: '5', name: 'ATS Pristine', location: 'Noida Sector 150', created_at: '2025-03-08' },
  ],
  configurations: [
    { id: 'c1', society_id: '1', type: '3BHK', area_sqft: 1250 },
    { id: 'c2', society_id: '1', type: '2BHK', area_sqft: 950 },
    { id: 'c3', society_id: '2', type: '3BHK', area_sqft: 1400 },
    { id: 'c4', society_id: '3', type: '2BHK', area_sqft: 1050 },
    { id: 'c5', society_id: '3', type: '3BHK', area_sqft: 1350 },
    { id: 'c6', society_id: '3', type: '2.5BHK', area_sqft: 1150 },
    { id: 'c7', society_id: '4', type: '3BHK', area_sqft: 1500 },
    { id: 'c8', society_id: '5', type: '4BHK', area_sqft: 2200 },
  ],
  quotes: [
    { id: 'q1', config_id: 'c1', broker_name: 'Ramesh', broker_phone: '919876543210', price_lakh: 85, floor: '4th', facing: 'East', availability: 'Ready to move', notes: null, added_on: '2025-03-24', status: 'interested' },
    { id: 'q2', config_id: 'c1', broker_name: 'Sunil', broker_phone: '919876543211', price_lakh: 82, floor: '6th', facing: 'West', availability: 'Under construction', notes: 'Possession Dec 2025', added_on: '2025-03-20', status: null },
    { id: 'q3', config_id: 'c2', broker_name: 'Ramesh', broker_phone: '919876543210', price_lakh: 62, floor: '3rd', facing: 'North', availability: 'Ready to move', notes: null, added_on: '2025-03-22', status: null },
    { id: 'q4', config_id: 'c3', broker_name: 'Vikram', broker_phone: '919876543212', price_lakh: 95, floor: '8th', facing: 'South', availability: 'Ready to move', notes: 'Corner flat', added_on: '2025-03-22', status: 'interested' },
    { id: 'q5', config_id: 'c4', broker_name: 'Anil', broker_phone: '919876543213', price_lakh: 55, floor: '2nd', facing: 'East', availability: 'Ready to move', notes: null, added_on: '2025-03-19', status: 'not-interested' },
    { id: 'q6', config_id: 'c5', broker_name: 'Anil', broker_phone: '919876543213', price_lakh: 72, floor: '5th', facing: 'West', availability: 'Under construction', notes: 'Possession Mar 2026', added_on: '2025-03-18', status: null },
    { id: 'q7', config_id: 'c7', broker_name: 'Deepak', broker_phone: '919876543214', price_lakh: 110, floor: '12th', facing: 'East', availability: 'Ready to move', notes: 'Well maintained', added_on: '2025-03-15', status: 'interested' },
    { id: 'q8', config_id: 'c8', broker_name: 'Mohit', broker_phone: '919876543215', price_lakh: 180, floor: '15th', facing: 'North', availability: 'Ready to move', notes: 'Premium flat', added_on: '2025-03-12', status: 'not-interested' },
  ],
};

// ── State ──
let supabase = null;
let allSocieties = [];
let allConfigs = [];
let currentSearch = '';

// ── Notes (localStorage) ──
const NOTES_KEY = 'house_hunt_notes';
function getAllNotes() {
  try { return JSON.parse(localStorage.getItem(NOTES_KEY) || '{}'); } catch { return {}; }
}
function getNotes(quoteId) { return getAllNotes()[quoteId] || []; }
function addNote(quoteId, text) {
  const all = getAllNotes();
  if (!all[quoteId]) all[quoteId] = [];
  all[quoteId].push({ text, at: new Date().toISOString() });
  localStorage.setItem(NOTES_KEY, JSON.stringify(all));
}
function deleteNote(quoteId, index) {
  const all = getAllNotes();
  if (all[quoteId]) { all[quoteId].splice(index, 1); localStorage.setItem(NOTES_KEY, JSON.stringify(all)); }
}

// ── Init ──
async function init() {
  if (SUPABASE_URL && SUPABASE_KEY) {
    const { createClient } = await import('https://esm.sh/@supabase/supabase-js@2');
    supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
  }
  setupEvents();
  await route();
}

// ── Data Loading ──
async function loadHome() {
  if (!supabase) {
    allSocieties = DEMO.societies;
    allConfigs = DEMO.configurations;
    return;
  }
  const [s, c] = await Promise.all([
    supabase.from('societies').select('*'),
    supabase.from('configurations').select('*'),
  ]);
  allSocieties = s.data || [];
  allConfigs = c.data || [];
}

async function loadDetail(id) {
  if (!supabase) {
    const society = DEMO.societies.find(s => s.id === id);
    const configs = DEMO.configurations.filter(c => c.society_id === id);
    const quotes = DEMO.quotes.filter(q => configs.some(c => c.id === q.config_id));
    return { society, configs, quotes };
  }
  const [sRes, cRes] = await Promise.all([
    supabase.from('societies').select('*').eq('id', id).single(),
    supabase.from('configurations').select('*').eq('society_id', id),
  ]);
  const configs = cRes.data || [];
  const configIds = configs.map(c => c.id);
  const qRes = configIds.length
    ? await supabase.from('broker_quotes').select('*').in('config_id', configIds).order('added_on', { ascending: false })
    : { data: [] };
  return { society: sRes.data, configs, quotes: qRes.data || [] };
}

// ── Delete Quote ──
let pendingDeleteId = null;
let pendingDeleteQuotes = null;

function showDeleteModal(quoteId, quotes) {
  pendingDeleteId = quoteId;
  pendingDeleteQuotes = quotes;
  document.getElementById('delete-modal').style.display = 'flex';
}

function hideDeleteModal() {
  pendingDeleteId = null;
  pendingDeleteQuotes = null;
  document.getElementById('delete-modal').style.display = 'none';
}

async function confirmDelete() {
  const quoteId = pendingDeleteId;
  const quotes = pendingDeleteQuotes;
  if (!quoteId) return;
  hideDeleteModal();

  if (supabase) {
    await supabase.from('broker_quotes').delete().eq('id', quoteId);
  } else {
    const idx = DEMO.quotes.findIndex(q => q.id === quoteId);
    if (idx !== -1) DEMO.quotes.splice(idx, 1);
  }
  // Remove from local quotes array used by detail view
  const qi = quotes.findIndex(q => q.id === quoteId);
  if (qi !== -1) quotes.splice(qi, 1);

  // Re-render
  const activePill = document.querySelector('.config-pill.active');
  if (activePill) {
    document.getElementById('quotes-container').innerHTML = renderQuotes(quotes, activePill.dataset.configId);
    attachQuoteEvents(quotes);
  }
}

async function saveQuoteStatus(quoteId, status, quotes) {
  // Use local cache for toggle logic — avoids an extra round-trip and keeps
  // the UI snappy even when the DB write is slow or fails.
  const localQuote = (supabase ? quotes : DEMO.quotes).find(q => q.id === quoteId);
  const newStatus = localQuote?.status === status ? null : status;
  if (localQuote) localQuote.status = newStatus;
  if (!supabase) return newStatus;
  await supabase.from('broker_quotes').update({ status: newStatus }).eq('id', quoteId);
  return newStatus;
}

// ── Render: Home ──
function renderHome() {
  const list = document.getElementById('society-list');
  const empty = document.getElementById('empty');

  let items = allSocieties.slice();

  if (currentSearch) {
    const q = currentSearch.toLowerCase();
    items = items.filter(s => s.name.toLowerCase().includes(q) || (s.location || '').toLowerCase().includes(q));
  }

  // Sort alphabetically
  items.sort((a, b) => a.name.localeCompare(b.name));

  if (!items.length) {
    list.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  list.innerHTML = items.map((s, i) => {
    const configs = allConfigs.filter(c => c.society_id === s.id);
    const color = (i % 7) + 1;
    return `<div class="society-card" data-id="${s.id}" data-color="${color}" style="animation-delay:${i * 40}ms">
      <div class="society-name">${esc(s.name)}</div>
      ${s.location ? `<div class="society-location">${esc(s.location)}</div>` : ''}
      <div class="society-meta">
        <div class="config-tags">${configs.map(c => `<span class="config-tag">${esc(c.type)}</span>`).join('')}</div>
        <span class="society-count">${configs.length} config${configs.length !== 1 ? 's' : ''}</span>
      </div>
    </div>`;
  }).join('');
}

// ── Render: Detail ──
function renderDetail(data) {
  const { society, configs, quotes } = data;
  const el = document.getElementById('detail-content');

  if (!society) { el.innerHTML = '<div class="empty">society not found</div>'; return; }

  el.innerHTML = `
    <div class="detail-header">
      <div class="detail-name">${esc(society.name)}</div>
      ${society.location ? `<div class="detail-location">${esc(society.location)}</div>` : ''}
    </div>
    ${configs.length ? `
      <div class="config-pills" id="config-pills">
        ${configs.map((c, i) => `<button class="config-pill${i === 0 ? ' active' : ''}" data-config-id="${c.id}">${esc(c.type)}${c.area_sqft ? ` · ${c.area_sqft} sqft` : ''}</button>`).join('')}
      </div>
      <div id="quotes-container">${renderQuotes(quotes, configs[0]?.id)}</div>
    ` : '<div class="no-quotes">no configurations yet</div>'}
  `;

  document.getElementById('config-pills')?.addEventListener('click', (e) => {
    const pill = e.target.closest('.config-pill');
    if (!pill) return;
    document.querySelectorAll('.config-pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    document.getElementById('quotes-container').innerHTML = renderQuotes(quotes, pill.dataset.configId);
    attachQuoteEvents(quotes);
  });

  attachQuoteEvents(quotes);
}

function renderQuotes(quotes, configId) {
  const filtered = quotes
    .filter(q => q.config_id === configId)
    .sort((a, b) => new Date(b.added_on) - new Date(a.added_on));

  if (!filtered.length) return '<div class="no-quotes">no quotes yet</div>';

  return `<div class="quote-list">${filtered.map((q, i) => {
    const phone = safePhone(q.broker_phone);
    const status = q.status || '';
    const cardClass = status ? ` ${status}` : '';
    const details = [
      q.price_lakh ? `₹${q.price_lakh}L` : null,
      q.floor ? `${q.floor} floor` : null,
      q.facing ? `${q.facing} facing` : null,
    ].filter(Boolean).join(' · ');

    return `<div class="quote-card${cardClass}" data-quote-id="${q.id}" style="animation-delay:${i * 40}ms">
      <div class="quote-broker">${esc(q.broker_name)}${phone ? ` · ${fmtPhone(phone)}` : ''}</div>
      ${details ? `<div class="quote-details">${details}</div>` : ''}
      ${q.availability ? `<div class="quote-availability">${esc(q.availability)}</div>` : ''}
      ${q.notes ? `<div class="quote-notes">${esc(q.notes)}</div>` : ''}
      ${q.added_on ? `<div class="quote-date">${fmtDate(q.added_on)}</div>` : ''}
      <div class="quote-actions">
        <button class="status-btn${status === 'interested' ? ' active-interested' : ''}" data-quote-id="${q.id}" data-status="interested">👍 interested</button>
        <button class="status-btn${status === 'not-interested' ? ' active-not-interested' : ''}" data-quote-id="${q.id}" data-status="not-interested">👎 pass</button>
        ${phone ? `<a href="https://wa.me/${phone}" target="_blank" rel="noopener noreferrer" class="whatsapp-btn">💬</a>` : ''}
        <button class="delete-btn" data-quote-id="${q.id}">🗑️</button>
      </div>
      ${renderNotesSection(q.id)}
    </div>`;
  }).join('')}</div>`;
}

function attachQuoteEvents(quotes) {
  document.querySelectorAll('.status-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const quoteId = btn.dataset.quoteId;
      const status = btn.dataset.status;
      await saveQuoteStatus(quoteId, status, quotes);
      const activePill = document.querySelector('.config-pill.active');
      if (activePill) {
        document.getElementById('quotes-container').innerHTML = renderQuotes(quotes, activePill.dataset.configId);
        attachQuoteEvents(quotes);
      }
    });
  });
  document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      showDeleteModal(btn.dataset.quoteId, quotes);
    });
  });
}

function renderNotesSection(quoteId, open = false) {
  const notes = getNotes(quoteId);
  const count = notes.length;
  return `<div class="notes-section" data-quote-id="${quoteId}">
    <button class="notes-toggle${open ? ' open' : ''}" data-quote-id="${quoteId}">
      📝 ${count ? `${count} note${count !== 1 ? 's' : ''}` : 'add note'}
    </button>
    <div class="notes-body"${open ? '' : ' style="display:none"'}>
      ${notes.map((n, i) => `<div class="note-item">
        <div class="note-text">${esc(n.text)}</div>
        <div class="note-meta">
          <span class="note-time">${fmtNoteDate(n.at)}</span>
          <button class="note-delete" data-quote-id="${quoteId}" data-index="${i}">×</button>
        </div>
      </div>`).join('')}
      <div class="note-input-row">
        <textarea class="note-input" data-quote-id="${quoteId}" placeholder="type a note…" rows="2"></textarea>
        <button class="note-add" data-quote-id="${quoteId}">Add</button>
      </div>
    </div>
  </div>`;
}

function fmtNoteDate(iso) {
  const d = new Date(iso);
  const diff = Date.now() - d;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  if (Math.floor(hrs / 24) === 1) return 'yesterday';
  if (hrs < 168) return `${Math.floor(hrs / 24)}d ago`;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

// ── Router ──
async function route() {
  const hash = location.hash || '#/';
  const homeView = document.getElementById('home-view');
  const detailView = document.getElementById('detail-view');

  if (hash.startsWith('#/society/')) {
    const id = decodeURIComponent(hash.split('#/society/')[1]);
    homeView.style.display = 'none';
    detailView.style.display = 'block';
    const data = await loadDetail(id);
    renderDetail(data);
  } else {
    detailView.style.display = 'none';
    homeView.style.display = 'block';
    await loadHome();
    renderHome();
  }
}

// ── Events ──
function setupEvents() {
  document.getElementById('search').addEventListener('input', (e) => {
    currentSearch = e.target.value;
    renderHome();
  });

  document.getElementById('society-list').addEventListener('click', (e) => {
    const card = e.target.closest('.society-card');
    if (!card) return;
    location.hash = `#/society/${card.dataset.id}`;
  });

  window.addEventListener('hashchange', route);

  // Delete modal
  document.getElementById('modal-cancel').addEventListener('click', hideDeleteModal);
  document.getElementById('modal-confirm').addEventListener('click', confirmDelete);
  document.getElementById('delete-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) hideDeleteModal();
  });

  // Notes delegation
  document.getElementById('detail-view').addEventListener('click', (e) => {
    const toggle = e.target.closest('.notes-toggle');
    const addBtn  = e.target.closest('.note-add');
    const delBtn  = e.target.closest('.note-delete');
    if (toggle) {
      const section = toggle.closest('.notes-section');
      const body    = section.querySelector('.notes-body');
      const open    = body.style.display === 'none';
      body.style.display = open ? 'block' : 'none';
      toggle.classList.toggle('open', open);
      if (open) section.querySelector('.note-input')?.focus();
    } else if (addBtn) {
      const qid     = addBtn.dataset.quoteId;
      const section = document.querySelector(`.notes-section[data-quote-id="${qid}"]`);
      const input   = section.querySelector('.note-input');
      const text    = input.value.trim();
      if (!text) return;
      addNote(qid, text);
      section.outerHTML = renderNotesSection(qid, true);
    } else if (delBtn) {
      const qid   = delBtn.dataset.quoteId;
      const index = parseInt(delBtn.dataset.index);
      deleteNote(qid, index);
      document.querySelector(`.notes-section[data-quote-id="${qid}"]`).outerHTML = renderNotesSection(qid, true);
    }
  });
  document.getElementById('detail-view').addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      const input = e.target.closest('.note-input');
      if (!input) return;
      const qid  = input.dataset.quoteId;
      const text = input.value.trim();
      if (!text) return;
      addNote(qid, text);
      document.querySelector(`.notes-section[data-quote-id="${qid}"]`).outerHTML = renderNotesSection(qid, true);
    }
  });
}

// ── Helpers ──
function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtDate(str) {
  return new Date(str).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function fmtPhone(phone) {
  return phone.startsWith('91') && phone.length === 12 ? phone.slice(2) : phone;
}

function safePhone(phone) {
  return phone ? phone.replace(/\D/g, '') : '';
}

// ── Start ──
init();
