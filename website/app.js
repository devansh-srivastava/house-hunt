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
      </div>
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
      // Re-render current config quotes with updated status
      const activePill = document.querySelector('.config-pill.active');
      if (activePill) {
        document.getElementById('quotes-container').innerHTML = renderQuotes(quotes, activePill.dataset.configId);
        attachQuoteEvents(quotes);
      }
    });
  });
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
