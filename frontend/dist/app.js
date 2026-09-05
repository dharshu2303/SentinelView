const state = {
  customers: [],
  currentCustomerId: null,
  transactions: [],
  report: null,
  highlighted: new Set(),
};

const customerListEl = document.getElementById('customerList');
const customerTitleEl = document.getElementById('customerTitle');
const customerMetaEl = document.getElementById('customerMeta');
const txBodyEl = document.getElementById('txBody');
const timelineEl = document.getElementById('timeline');
const investigateBtn = document.getElementById('investigateBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const firstFindingEl = document.getElementById('firstFinding');
const summaryEl = document.getElementById('summary');
const claimsEl = document.getElementById('claims');
const fallbackNoticeEl = document.getElementById('fallbackNotice');

function currency(v) {
  return `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function badgeClass(level) {
  return level === 'clean' ? 'clean' : 'risk';
}

function renderCustomers() {
  customerListEl.innerHTML = state.customers.map((c) => `
    <div class="customer-item ${c.id === state.currentCustomerId ? 'active' : ''}" data-id="${c.id}">
      <strong>${c.name}</strong><span class="badge ${badgeClass(c.risk_level)}">${c.risk_level}</span>
      <div class="muted">${c.id} · ${c.transaction_count} tx</div>
    </div>
  `).join('');

  customerListEl.querySelectorAll('.customer-item').forEach((item) => {
    item.addEventListener('click', async () => selectCustomer(item.dataset.id));
  });
}

function renderTransactions() {
  const flagged = new Set(state.report?.flagged_transaction_ids || []);
  txBodyEl.innerHTML = state.transactions.map((tx) => {
    const highlight = state.highlighted.has(tx.transaction_id) ? 'highlighted' : '';
    const flaggedClass = flagged.has(tx.transaction_id) ? 'flagged' : '';
    return `
      <tr id="row-${tx.transaction_id}" class="${highlight} ${flaggedClass}">
        <td>${tx.transaction_id}</td>
        <td>${new Date(tx.date).toLocaleString()}</td>
        <td>${tx.payee}</td>
        <td>${currency(tx.amount)}</td>
        <td>${tx.channel}</td>
        <td>${tx.category}</td>
        <td>${tx.region}</td>
      </tr>
    `;
  }).join('');
}

function renderTimeline() {
  if (!state.transactions.length) {
    timelineEl.innerHTML = '';
    return;
  }
  const flagged = new Set(state.report?.flagged_transaction_ids || []);
  const sorted = [...state.transactions].sort((a, b) => new Date(a.date) - new Date(b.date));
  const minDate = new Date(sorted[0].date).getTime();
  const maxDate = new Date(sorted[sorted.length - 1].date).getTime();
  const maxAmount = Math.max(...sorted.map((t) => Number(t.amount)));
  const width = 1000;
  const height = 140;
  const x = (d) => 20 + ((d - minDate) / Math.max(1, (maxDate - minDate))) * (width - 40);
  const y = (a) => height - 15 - (Number(a) / Math.max(1, maxAmount)) * (height - 30);

  const points = sorted.map((tx) => {
    const cls = flagged.has(tx.transaction_id) ? 'dot-flagged' : '';
    const color = flagged.has(tx.transaction_id) ? '#ffb020' : '#6aa0ff';
    return `<circle class="${cls}" cx="${x(new Date(tx.date).getTime())}" cy="${y(tx.amount)}" r="${flagged.has(tx.transaction_id) ? 4.3 : 2.8}" fill="${color}" />`;
  }).join('');

  timelineEl.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <rect x="0" y="0" width="${width}" height="${height}" fill="#0a1220" />
      <line x1="20" y1="${height-15}" x2="${width-20}" y2="${height-15}" stroke="#28406b" stroke-width="1" />
      ${points}
    </svg>
  `;
}

function renderReport() {
  const report = state.report;
  if (!report) {
    firstFindingEl.innerHTML = '<p class="muted">Run an investigation to generate findings.</p>';
    summaryEl.innerHTML = '';
    claimsEl.innerHTML = '';
    fallbackNoticeEl.innerHTML = '';
    return;
  }

  const clean = report.status === 'clean' || report.status === 'no_data';
  firstFindingEl.innerHTML = `<h4 class="first ${clean ? 'clean' : 'risk'}">${report.first_finding}</h4>`;
  summaryEl.innerHTML = `<p>${report.narrative?.summary || ''}</p>`;

  const claims = report.narrative?.claims || [];
  claimsEl.innerHTML = claims.length
    ? claims.map((claim, i) => `
      <div class="claim" data-ids="${claim.transaction_ids.join(',')}">
        <strong>${i + 1}. ${claim.title}</strong>
        <p>${claim.explanation}</p>
        <p class="muted">Rule: ${claim.rule_id} · Tx: ${claim.transaction_ids.join(', ')}</p>
        <p class="muted">Check first: ${claim.investigator_next_step}</p>
      </div>
    `).join('')
    : '<p class="muted">No flagged claims for this customer.</p>';

  claimsEl.querySelectorAll('.claim').forEach((claimEl) => {
    claimEl.addEventListener('click', () => {
      state.highlighted = new Set(claimEl.dataset.ids.split(',').filter(Boolean));
      renderTransactions();
      const firstId = [...state.highlighted][0];
      const row = firstId ? document.getElementById(`row-${firstId}`) : null;
      if (row) row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });

  fallbackNoticeEl.innerHTML = report.fallback_mode
    ? `<p class="muted">AI narrative unavailable — showing rule-engine findings directly. (${report.gemini_error || 'no details'})</p>`
    : '';
}

async function selectCustomer(customerId) {
  state.currentCustomerId = customerId;
  state.report = null;
  state.highlighted = new Set();

  const customer = state.customers.find((c) => c.id === customerId);
  customerTitleEl.textContent = `${customer.name} (${customer.id})`;
  customerMetaEl.textContent = `${customer.transaction_count} transactions · ${customer.date_range.start} to ${customer.date_range.end}`;

  const txRes = await fetch(`/api/customers/${customerId}/transactions`);
  const txData = await txRes.json();
  state.transactions = txData.transactions || [];

  renderCustomers();
  renderTransactions();
  renderTimeline();
  renderReport();
}

async function runInvestigation() {
  if (!state.currentCustomerId) return;
  loadingOverlay.classList.remove('hidden');
  state.highlighted = new Set();
  renderTransactions();

  try {
    const res = await fetch(`/api/customers/${state.currentCustomerId}/investigate`, { method: 'POST' });
    state.report = await res.json();
  } catch (error) {
    state.report = {
      status: 'error',
      first_finding: 'Needs attention: investigation service error.',
      narrative: { summary: String(error), claims: [] },
      fallback_mode: true,
      gemini_error: String(error),
      flagged_transaction_ids: [],
    };
  }

  loadingOverlay.classList.add('hidden');
  renderTransactions();
  renderTimeline();
  renderReport();
}

async function boot() {
  const res = await fetch('/api/customers');
  state.customers = await res.json();
  if (!state.customers.length) return;
  state.currentCustomerId = state.customers[0].id;
  renderCustomers();
  await selectCustomer(state.currentCustomerId);
}

investigateBtn.addEventListener('click', runInvestigation);
boot();
