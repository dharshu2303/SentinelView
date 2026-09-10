/**
 * SentinelView - Transaction Risk Investigation Assistant
 * Interactive Client Application
 */

const state = {
  currentTab: 'investigate',
  customers: [],
  currentCustomerId: null,
  currentCustomer: null,
  investigation: null,
  allTransactions: [],
  flaggedTransactions: [],
  displayTransactions: [],
  viewAllMode: false,
  selectedTxnIds: new Set(),
  activeRuleFilter: null,
  theme: localStorage.getItem('sentinel_theme') || 'light',
  customerNotes: JSON.parse(localStorage.getItem('sentinel_notes') || '{}'),
  investigationCache: {}, // In-browser cache for instant 0ms switching!
  dashboardData: null,
  alertsData: [],
  reportsData: [],
};

// DOM Elements
const themeToggleBtn = document.getElementById('themeToggle');
const customerSearchInput = document.getElementById('customerSearch');
const customerListContainer = document.getElementById('customerList');
const customerTotalCountEl = document.getElementById('customerTotalCount');
const riskAlertsBadge = document.getElementById('riskAlertsBadge');

// Customer Panel Toggle Elements
const colCustomersEl = document.getElementById('colCustomers');
const viewInvestigateEl = document.getElementById('view-investigate');
const toggleCustomerPanelBtn = document.getElementById('toggleCustomerPanelBtn');
const collapsedCustomerStrip = document.getElementById('collapsedCustomerStrip');
const mobileCollapsedBanner = document.getElementById('mobileCollapsedBanner');
const collapsedCurrentAvatarEl = document.getElementById('collapsedCurrentAvatar');
const mCurrentAvatarEl = document.getElementById('mCurrentAvatar');
const mCurrentNameEl = document.getElementById('mCurrentName');
const mCurrentIdEl = document.getElementById('mCurrentId');

// Navigation Tabs
const navLinks = document.querySelectorAll('.nav-link');
const tabViews = {
  investigate: document.getElementById('view-investigate'),
  dashboard: document.getElementById('view-dashboard'),
  alerts: document.getElementById('view-alerts'),
  reports: document.getElementById('view-reports'),
  settings: document.getElementById('view-settings'),
  upload: document.getElementById('view-upload'),
};

// Center Column Elements
const customerAvatarEl = document.getElementById('customerAvatar');
const customerNameEl = document.getElementById('customerName');
const customerIdEl = document.getElementById('customerId');
const customerSinceEl = document.getElementById('customerSince');
const lastAnalysedEl = document.getElementById('lastAnalysed');
const customerRiskPillEl = document.getElementById('customerRiskPill');
const customerRiskTextEl = document.getElementById('customerRiskText');

// Extra Customer Details
const customerAccountNoEl = document.getElementById('customerAccountNo');
const customerAccountTypeEl = document.getElementById('customerAccountType');
const customerBranchEl = document.getElementById('customerBranch');
const customerPhoneEl = document.getElementById('customerPhone');

const attentionBannerEl = document.getElementById('attentionBanner');
const attentionTitleEl = document.getElementById('attentionTitle');
const attentionSubtitleEl = document.getElementById('attentionSubtitle');
const riskLevelTagEl = document.getElementById('riskLevelTag');
const riskLevelValueEl = document.getElementById('riskLevelValue');

const keyReasonsGridEl = document.getElementById('keyReasonsGrid');
const flaggedCountBadgeEl = document.getElementById('flaggedCountBadge');
const toggleViewAllBtn = document.getElementById('toggleViewAllBtn');
const txTableBodyEl = document.getElementById('txTableBody');
const selectAllCheckbox = document.getElementById('selectAllCheckbox');

const bTypicalAmountEl = document.getElementById('bTypicalAmount');
const bTypicalSubEl = document.getElementById('bTypicalSub');
const bCurrentAmountEl = document.getElementById('bCurrentAmount');
const bCurrentSubEl = document.getElementById('bCurrentSub');
const bUsualHoursEl = document.getElementById('bUsualHours');
const bUsualSubEl = document.getElementById('bUsualSub');
const bCurrentTimeEl = document.getElementById('bCurrentTime');
const bCurrentTimeSubEl = document.getElementById('bCurrentTimeSub');

const timelineContainerEl = document.getElementById('timelineContainer');
const ruleCardsContainerEl = document.getElementById('ruleCardsContainer');

const briefNarrativeTextEl = document.getElementById('briefNarrativeText');
const briefChecksListEl = document.getElementById('briefChecksList');
const openFullReportBtn = document.getElementById('openFullReportBtn');
const viewFullReportTopBtn = document.getElementById('viewFullReportTopBtn');

const exportReportBtn = document.getElementById('exportReportBtn');
const shareBtn = document.getElementById('shareBtn');
const addNoteBtn = document.getElementById('addNoteBtn');

// Modals
const reportModal = document.getElementById('reportModal');
const modalBodyContent = document.getElementById('modalBodyContent');
const closeModalBtn = document.getElementById('closeModalBtn');
const closeModalFooterBtn = document.getElementById('closeModalFooterBtn');
const printReportBtn = document.getElementById('printReportBtn');
const modalDownloadWordBtn = document.getElementById('modalDownloadWordBtn');

const exportModal = document.getElementById('exportModal');
const closeExportModalBtn = document.getElementById('closeExportModalBtn');
const cancelExportBtn = document.getElementById('cancelExportBtn');
const choiceExportWord = document.getElementById('choiceExportWord');
const choiceExportPdf = document.getElementById('choiceExportPdf');

const noteModal = document.getElementById('noteModal');
const closeNoteModalBtn = document.getElementById('closeNoteModalBtn');
const cancelNoteBtn = document.getElementById('cancelNoteBtn');
const saveNoteBtn = document.getElementById('saveNoteBtn');
const investigatorNoteInput = document.getElementById('investigatorNoteInput');
const appToast = document.getElementById('appToast');

/* ==========================================================================
   Theme Management
   ========================================================================== */

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('sentinel_theme', theme);
  const themeText = themeToggleBtn.querySelector('.theme-text');
  if (themeText) {
    themeText.textContent = theme === 'light' ? 'Light' : 'Dark';
  }
  if (state.investigation) {
    renderTimeline();
  }
}

themeToggleBtn.addEventListener('click', () => {
  const newTheme = state.theme === 'light' ? 'dark' : 'light';
  applyTheme(newTheme);
});

/* ==========================================================================
   Toast Notification
   ========================================================================== */

function showToast(message, duration = 3000) {
  appToast.textContent = message;
  appToast.classList.remove('hidden');
  setTimeout(() => {
    appToast.classList.add('hidden');
  }, duration);
}

/* ==========================================================================
   Date Parsing & Formatting Utilities (Safe from NaN)
   ========================================================================== */

function parseSafeDate(dateStr) {
  if (!dateStr) return new Date();
  if (dateStr instanceof Date) return dateStr;
  if (typeof dateStr === 'string') {
    const iso = dateStr.includes('T') ? dateStr : dateStr.replace(' ', 'T');
    const d = new Date(iso);
    if (!isNaN(d.getTime())) return d;
  }
  const fallback = new Date(dateStr);
  return isNaN(fallback.getTime()) ? new Date() : fallback;
}

function formatInr(num) {
  if (num === null || num === undefined) return '₹0';
  const val = Math.round(Number(num));
  const valStr = String(val);
  if (val < 1000) return `₹${val}`;
  const lastThree = valStr.substring(valStr.length - 3);
  let otherNumbers = valStr.substring(0, valStr.length - 3);
  let res = '';
  while (otherNumbers.length > 2) {
    res = ',' + otherNumbers.substring(otherNumbers.length - 2) + res;
    otherNumbers = otherNumbers.substring(0, otherNumbers.length - 2);
  }
  res = otherNumbers + res;
  return `₹${res},${lastThree}`;
}

function getInitials(name) {
  if (!name) return '??';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getRiskBadgeClass(level) {
  const l = String(level).toUpperCase();
  if (l === 'HIGH') return 'badge-risk-high';
  if (l === 'MEDIUM') return 'badge-risk-medium';
  return 'badge-risk-clean';
}

function getRiskLabel(level) {
  const l = String(level).toUpperCase();
  if (l === 'HIGH') return 'High Risk';
  if (l === 'MEDIUM') return 'Medium Risk';
  return 'No Risk';
}

/* ==========================================================================
   Navigation Tabs Switching
   ========================================================================== */

function switchTab(tabKey) {
  state.currentTab = tabKey;

  navLinks.forEach((link) => {
    if (link.dataset.tab === tabKey) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  Object.keys(tabViews).forEach((k) => {
    const view = tabViews[k];
    if (view) {
      if (k === tabKey) {
        view.classList.remove('hidden');
      } else {
        view.classList.add('hidden');
      }
    }
  });

  // Load content for newly activated tab
  if (tabKey === 'dashboard') {
    loadDashboardView();
  } else if (tabKey === 'alerts') {
    loadAlertsView();
  } else if (tabKey === 'reports') {
    loadReportsView();
  }
}

navLinks.forEach((link) => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const tab = link.dataset.tab;
    if (tab) switchTab(tab);
  });
});

/* ==========================================================================
   Customer List Rendering & Filtering
   ========================================================================== */

function renderCustomerList(filterText = '') {
  const query = filterText.trim().toLowerCase();
  const filtered = state.customers.filter((c) => {
    return (
      c.name.toLowerCase().includes(query) ||
      c.id.toLowerCase().includes(query) ||
      (c.phone && c.phone.includes(query)) ||
      (c.risk_label && c.risk_label.toLowerCase().includes(query))
    );
  });

  customerTotalCountEl.textContent = state.customers.length;

  if (!filtered.length) {
    customerListContainer.innerHTML = `
      <div style="text-align: center; padding: 24px; color: var(--text-muted); font-size: 12px;">
        No matching customers found
      </div>
    `;
    return;
  }

  customerListContainer.innerHTML = filtered.map((c) => {
    const activeClass = c.id === state.currentCustomerId ? 'active' : '';
    const badgeClass = getRiskBadgeClass(c.risk_level);
    const label = getRiskLabel(c.risk_level);
    const initials = getInitials(c.name);

    return `
      <div class="customer-card-item ${activeClass}" data-id="${c.id}">
        <div class="cust-item-left">
          <div class="cust-avatar">${initials}</div>
          <div class="cust-item-info">
            <span class="cust-item-name">${c.name}</span>
            <span class="cust-item-id">${c.id} &bull; ${c.account_number || '•••• 4821'}</span>
          </div>
        </div>
        <span class="badge-pill ${badgeClass}">${label}</span>
      </div>
    `;
  }).join('');

  customerListContainer.querySelectorAll('.customer-card-item').forEach((item) => {
    item.addEventListener('click', () => {
      const cid = item.dataset.id;
      if (cid !== state.currentCustomerId) {
        selectCustomer(cid);
      }
      if (window.innerWidth <= 768) {
        setCustomerPanelCollapsed(true);
      }
    });
  });
}

customerSearchInput.addEventListener('input', (e) => {
  renderCustomerList(e.target.value);
});

/* ==========================================================================
   Customer Panel Collapse / Expand Controls
   ========================================================================== */

function setCustomerPanelCollapsed(collapsed) {
  state.customersCollapsed = collapsed;
  if (!colCustomersEl || !viewInvestigateEl) return;

  if (collapsed) {
    colCustomersEl.classList.add('collapsed');
    viewInvestigateEl.classList.add('customers-collapsed');
    if (toggleCustomerPanelBtn) {
      toggleCustomerPanelBtn.setAttribute('title', 'Expand Customer List');
      toggleCustomerPanelBtn.setAttribute('aria-label', 'Expand customer list');
    }
  } else {
    colCustomersEl.classList.remove('collapsed');
    viewInvestigateEl.classList.remove('customers-collapsed');
    if (toggleCustomerPanelBtn) {
      toggleCustomerPanelBtn.setAttribute('title', 'Minimize Customer List');
      toggleCustomerPanelBtn.setAttribute('aria-label', 'Minimize customer list');
    }
  }
}

function toggleCustomerPanel() {
  const isCollapsed = colCustomersEl ? colCustomersEl.classList.contains('collapsed') : false;
  setCustomerPanelCollapsed(!isCollapsed);
}

if (toggleCustomerPanelBtn) {
  toggleCustomerPanelBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleCustomerPanel();
  });
}

if (collapsedCustomerStrip) {
  collapsedCustomerStrip.addEventListener('click', () => {
    setCustomerPanelCollapsed(false);
  });
}

if (mobileCollapsedBanner) {
  mobileCollapsedBanner.addEventListener('click', () => {
    setCustomerPanelCollapsed(false);
  });
}

/* ==========================================================================
   Select Customer (Instant 0ms with Cache!)
   ========================================================================== */

async function selectCustomer(customerId) {
  state.currentCustomerId = customerId;
  state.currentCustomer = state.customers.find((c) => c.id === customerId);
  state.selectedTxnIds.clear();
  state.activeRuleFilter = null;
  state.viewAllMode = false;

  renderCustomerList(customerSearchInput.value);

  // Update header immediately from known customer metadata
  if (state.currentCustomer) {
    const inits = getInitials(state.currentCustomer.name);
    customerAvatarEl.textContent = inits;
    customerNameEl.textContent = state.currentCustomer.name;
    customerIdEl.textContent = state.currentCustomer.id;
    customerSinceEl.textContent = state.currentCustomer.customer_since || '2 years';
    lastAnalysedEl.textContent = state.currentCustomer.last_analysed || '26 Aug 2025, 14:32';
    customerAccountNoEl.textContent = state.currentCustomer.account_number || '•••• •••• 4821';
    customerAccountTypeEl.textContent = state.currentCustomer.account_type || 'Savings Platinum';
    customerBranchEl.textContent = state.currentCustomer.branch || 'Fort Branch, Mumbai';
    customerPhoneEl.textContent = state.currentCustomer.phone || '+91 98201 44821';

    if (collapsedCurrentAvatarEl) collapsedCurrentAvatarEl.textContent = inits;
    if (mCurrentAvatarEl) mCurrentAvatarEl.textContent = inits;
    if (mCurrentNameEl) mCurrentNameEl.textContent = state.currentCustomer.name;
    if (mCurrentIdEl) mCurrentIdEl.textContent = state.currentCustomer.id;
  }

  // Check in-browser cache first for 0ms instantaneous update!
  if (state.investigationCache[customerId]) {
    applyInvestigationData(state.investigationCache[customerId]);
    return;
  }

  // Otherwise fetch from backend (which is also cached in memory on the server)
  try {
    const res = await fetch(`/api/customers/${customerId}/investigate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await res.json();
    state.investigationCache[customerId] = data;
    applyInvestigationData(data);
  } catch (err) {
    console.error('Failed to load investigation:', err);
    showToast('Error loading customer investigation');
  }
}

function applyInvestigationData(data) {
  state.investigation = data;
  state.allTransactions = data.all_transactions || [];
  state.flaggedTransactions = data.flagged_transactions || [];
  state.displayTransactions = state.flaggedTransactions.length > 0 ? state.flaggedTransactions : state.allTransactions;
  state.viewAllMode = state.flaggedTransactions.length === 0;

  renderInvestigationWorkbench();
}

/* ==========================================================================
   Render Investigation Workbench
   ========================================================================== */

function renderInvestigationWorkbench() {
  const inv = state.investigation;
  if (!inv) return;

  // 1. Customer Header
  const initials = getInitials(inv.customer_name);
  customerAvatarEl.textContent = initials;
  customerNameEl.textContent = inv.customer_name;
  customerIdEl.textContent = inv.customer_id;
  customerSinceEl.textContent = inv.customer_since || '2 years 4 months';
  lastAnalysedEl.textContent = inv.last_analysed || '26 Aug 2025, 14:32';

  customerAccountNoEl.textContent = inv.account_number || '•••• •••• 4821';
  customerAccountTypeEl.textContent = inv.account_type || 'Savings Platinum';
  customerBranchEl.textContent = inv.branch || 'Fort Branch, Mumbai';
  customerPhoneEl.textContent = inv.phone || '+91 98201 44821';

  const riskClass = inv.risk_level === 'HIGH' ? 'risk-high' : (inv.risk_level === 'MEDIUM' ? 'risk-medium' : 'risk-clean');
  customerRiskPillEl.className = `risk-pill-large ${riskClass}`;
  customerRiskTextEl.textContent = inv.risk_level === 'HIGH' ? 'High Risk' : (inv.risk_level === 'MEDIUM' ? 'Medium Risk' : 'No Risk');

  // 2. Attention Banner - Guaranteed non-wrapping Risk Level tag
  const bannerType = inv.risk_level === 'HIGH' ? 'high-risk' : (inv.risk_level === 'MEDIUM' ? 'medium-risk' : 'no-risk');
  attentionBannerEl.className = `attention-banner ${bannerType}`;
  attentionTitleEl.textContent = inv.attention_title || (inv.attention_required ? 'ATTENTION REQUIRED' : 'NO ATTENTION REQUIRED');
  attentionSubtitleEl.textContent = inv.attention_subtitle || (inv.attention_required ? 'Risk signals detected. This activity warrants review.' : 'All transactions align with established baseline.');
  riskLevelTagEl.className = 'risk-level-tag';
  riskLevelValueEl.textContent = inv.risk_level || 'NO RISK';

  // 3. Key Reasons
  renderKeyReasons(inv.key_reasons || []);

  // 4. Flagged Transactions Table
  renderTransactionsTable();

  // 5. Customer Behaviour Analysis
  renderBehaviorAnalysis(inv.behavior_analysis || {});

  // 6. Transaction Timeline (Safe Date Parsing)
  renderTimeline();

  // 7. Detailed Risk Analysis
  renderRiskAnalysisRules(inv.findings || []);

  // 8. Investigator Brief
  renderInvestigatorBrief(inv.narrative || {});
}

/* ==========================================================================
   Key Reasons
   ========================================================================== */

function renderKeyReasons(reasons) {
  if (!reasons || !reasons.length) {
    keyReasonsGridEl.innerHTML = '';
    return;
  }

  keyReasonsGridEl.innerHTML = reasons.map((r) => {
    let iconSvg = '';
    if (r.type === 'amount') {
      iconSvg = `
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="5" width="20" height="14" rx="2"></rect>
          <line x1="2" y1="10" x2="22" y2="10"></line>
        </svg>
      `;
    } else if (r.type === 'payee') {
      iconSvg = `
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
          <circle cx="9" cy="7" r="4"></circle>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
        </svg>
      `;
    } else {
      iconSvg = `
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
      `;
    }

    return `
      <div class="reason-card">
        <div class="reason-icon-wrap">
          ${iconSvg}
        </div>
        <div class="reason-content">
          <span class="reason-val">${r.title}</span>
          <span class="reason-title">${r.subtitle}</span>
          <span class="reason-detail">${r.detail}</span>
        </div>
      </div>
    `;
  }).join('');
}

/* ==========================================================================
   Transactions Table
   ========================================================================== */

function renderTransactionsTable() {
  const flaggedCount = state.flaggedTransactions.length;
  const totalCount = state.allTransactions.length;
  const isClean = flaggedCount === 0;

  const txTableTitleEl = document.getElementById('txTableTitle');
  const txFilterNoticeEl = document.getElementById('txFilterNotice');

  let txs = [];
  let currentTitle = 'Flagged Transactions';
  let currentBadge = `(${flaggedCount})`;
  let toggleText = `View All (${totalCount}) &rarr;`;
  let filterNotice = '';

  if (state.activeRuleFilter) {
    const ruleObj = state.investigation?.findings?.find((f) => f.rule_id === state.activeRuleFilter);
    const ruleNum = ruleObj?.rule_num || '';
    const ruleName = ruleObj?.rule_name || state.activeRuleFilter;

    if (ruleObj && ruleObj.matched_transaction_ids && ruleObj.matched_transaction_ids.length > 0) {
      const allowedIds = new Set(ruleObj.matched_transaction_ids);
      txs = state.allTransactions.filter((t) => allowedIds.has(t.transaction_id));
      currentTitle = `Rule ${ruleNum}: ${ruleName}`;
      currentBadge = `(${txs.length} flagged)`;
      toggleText = '&times; Clear Rule Filter';
      filterNotice = `Filtered by Rule ${ruleNum} (${ruleName}). Showing ${txs.length} triggered transactions.`;
    } else {
      // Rule was NOT triggered (0 violations)
      // DO NOT blank out the table! Show all customer transactions with an explanatory note!
      txs = state.allTransactions;
      currentTitle = `Rule ${ruleNum}: ${ruleName} (Not Triggered)`;
      currentBadge = `(0 violations &bull; showing ${txs.length} baseline)`;
      toggleText = '&times; Clear Filter';
      filterNotice = `Rule ${ruleNum} (${ruleName}) was evaluated and NOT triggered. Showing customer routine transactions below:`;
    }
  } else if (isClean) {
    // Clean customer: 0 flagged transactions (e.g. Rahul Mehta, Karthik R, Sneha Verma)
    // ALWAYS display all reviewed transactions!
    txs = state.allTransactions;
    currentTitle = 'Reviewed Baseline Transactions';
    currentBadge = `(${totalCount} verified &bull; Clean)`;
    toggleText = 'All Baseline Activity';
    filterNotice = 'All transactions align with customer baseline. No risk rules triggered.';
  } else if (state.viewAllMode) {
    // Flagged customer, showing all transactions
    txs = state.allTransactions;
    currentTitle = 'All Customer Transactions';
    currentBadge = `(${totalCount} total &bull; ${flaggedCount} flagged)`;
    toggleText = `&larr; Show Flagged Only (${flaggedCount})`;
    filterNotice = `Displaying all ${totalCount} transactions in customer history. Flagged anomalies highlighted in red.`;
  } else {
    // Flagged customer, showing flagged only
    txs = state.flaggedTransactions;
    currentTitle = 'Flagged Transactions';
    currentBadge = `(${flaggedCount} of ${totalCount})`;
    toggleText = `View All (${totalCount}) &rarr;`;
    filterNotice = `${flaggedCount} transactions triggered risk rules for review.`;
  }

  // Safety fallback: If txs is somehow empty, ALWAYS fallback to state.allTransactions!
  if (!txs || txs.length === 0) {
    txs = state.allTransactions;
    currentTitle = 'All Customer Transactions';
    currentBadge = `(${txs.length})`;
  }

  // Update table header elements
  if (txTableTitleEl) {
    txTableTitleEl.textContent = currentTitle;
  }
  if (flaggedCountBadgeEl) {
    flaggedCountBadgeEl.innerHTML = currentBadge;
  }
  if (toggleViewAllBtn) {
    toggleViewAllBtn.innerHTML = toggleText;
  }
  if (txFilterNoticeEl) {
    txFilterNoticeEl.textContent = filterNotice;
  }

  const flaggedSet = new Set(state.flaggedTransactions.map((t) => t.transaction_id));

  if (!txs.length) {
    txTableBodyEl.innerHTML = `
      <tr>
        <td colspan="9" style="text-align: center; padding: 24px; color: var(--text-muted);">
          No transactions found for this customer.
        </td>
      </tr>
    `;
    return;
  }

  txTableBodyEl.innerHTML = txs.map((tx) => {
    const isFlagged = flaggedSet.has(tx.transaction_id);
    const isChecked = state.selectedTxnIds.has(tx.transaction_id);
    const rowClass = `${isFlagged ? 'row-flagged' : ''} ${isChecked ? 'row-selected' : ''}`;

    const dt = parseSafeDate(tx.date);
    const dateFormatted = dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) + ', ' +
                          dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
    const amountFormatted = tx.amount_formatted || formatInr(tx.amount);

    let ruleBadges = '';
    if (tx.triggered_rules && tx.triggered_rules.length > 0) {
      ruleBadges = tx.triggered_rules.map((r) => {
        let tagCls = 'rule-tag-burst';
        if (r.rule_id === 'R1') tagCls = 'rule-tag-large';
        else if (r.rule_id === 'R3') tagCls = 'rule-tag-hours';
        else if (r.rule_id === 'R4') tagCls = 'rule-tag-break';
        return `<span class="rule-tag ${tagCls}">${r.badge_name}</span>`;
      }).join('');
    } else {
      ruleBadges = `<span class="rule-tag rule-tag-clean">Baseline</span>`;
    }

    return `
      <tr class="${rowClass}" data-id="${tx.transaction_id}">
        <td class="col-check">
          <input type="checkbox" class="row-checkbox" data-id="${tx.transaction_id}" ${isChecked ? 'checked' : ''} />
        </td>
        <td class="tx-id-cell">${tx.transaction_id}</td>
        <td>${dateFormatted}</td>
        <td>${tx.description}</td>
        <td><strong>${tx.payee}</strong></td>
        <td class="tx-amount-cell">${amountFormatted}</td>
        <td>${tx.channel}</td>
        <td>${ruleBadges}</td>
        <td class="tx-chevron" data-id="${tx.transaction_id}">&rsaquo;</td>
      </tr>
    `;
  }).join('');

  txTableBodyEl.querySelectorAll('.row-checkbox').forEach((cb) => {
    cb.addEventListener('change', (e) => {
      const id = e.target.dataset.id;
      if (e.target.checked) {
        state.selectedTxnIds.add(id);
      } else {
        state.selectedTxnIds.delete(id);
      }
      renderTransactionsTable();
      renderTimeline();
    });
  });

  txTableBodyEl.querySelectorAll('.tx-chevron').forEach((ch) => {
    ch.addEventListener('click', () => {
      const id = ch.dataset.id;
      openTxnDetailModal(id);
    });
  });
}

toggleViewAllBtn.addEventListener('click', () => {
  if (state.activeRuleFilter) {
    state.activeRuleFilter = null;
    renderRiskAnalysisRules(state.investigation?.findings || []);
  } else if (state.flaggedTransactions.length === 0) {
    showToast('Customer portfolio: all transactions verify within clean baseline.');
    return;
  } else {
    state.viewAllMode = !state.viewAllMode;
  }
  renderTransactionsTable();
});

selectAllCheckbox.addEventListener('change', (e) => {
  const isChecked = e.target.checked;
  const list = (state.viewAllMode || state.flaggedTransactions.length === 0) ? state.allTransactions : state.flaggedTransactions;
  if (isChecked) {
    list.forEach((t) => state.selectedTxnIds.add(t.transaction_id));
  } else {
    state.selectedTxnIds.clear();
  }
  renderTransactionsTable();
  renderTimeline();
});

/* ==========================================================================
   Customer Behaviour Analysis Cards
   ========================================================================== */

function renderBehaviorAnalysis(b) {
  bTypicalAmountEl.textContent = b.typical_transfer_amount || '₹58,000';
  bTypicalSubEl.textContent = b.typical_transfer_subtitle || '(median, last 90 days)';

  bCurrentAmountEl.textContent = b.current_transfer_amount || '₹2,40,000';
  bCurrentSubEl.textContent = b.current_transfer_subtitle || '(4.1× higher)';

  bUsualHoursEl.textContent = b.usual_active_hours || '9:00 AM – 7:00 PM';
  bUsualSubEl.textContent = b.usual_active_subtitle || '(most activity)';

  bCurrentTimeEl.textContent = b.current_txn_time || '02:13 AM';
  bCurrentTimeSubEl.textContent = b.current_txn_subtitle || '(outside usual hours)';
}

/* ==========================================================================
   Transaction Timeline (24-Hour Behavioral Distribution & Anomaly Mapping)
   ========================================================================== */

function renderTimeline() {
  const txs = state.allTransactions;
  if (!txs || !txs.length) {
    timelineContainerEl.innerHTML = '<div style="color: var(--text-muted); padding: 20px; text-align: center;">No transactions to display on timeline.</div>';
    return;
  }

  const flaggedSet = new Set(state.flaggedTransactions.map((t) => t.transaction_id));
  const isDark = state.theme === 'dark';
  const width = 820;
  const height = 130;
  const paddingX = 50;
  const baselineY = 75;

  // 24-hour cycle starting at 6:00 AM (06:00) to 6:00 AM next day
  const getX = (dateStr) => {
    const dt = parseSafeDate(dateStr);
    const hour = dt.getHours();
    const min = dt.getMinutes();
    let hourOffset = hour + min / 60 - 6; // 6:00 AM is offset 0
    if (hourOffset < 0) hourOffset += 24;
    const pct = hourOffset / 24;
    return paddingX + pct * (width - paddingX * 2);
  };

  const ticks = [
    { label: '9 AM', pct: 3 / 24 },
    { label: '12 PM', pct: 6 / 24 },
    { label: '3 PM', pct: 9 / 24 },
    { label: '6 PM', pct: 12 / 24 },
    { label: '9 PM', pct: 15 / 24 },
    { label: '12 AM', pct: 18 / 24 },
    { label: '3 AM', pct: 21 / 24 },
  ];

  const lineColor = isDark ? '#22385e' : '#cbd5e1';
  const normalColor = '#10b981';
  const flaggedColor = '#ef4444';

  // Highlight band for Usual Active Hours (9:00 AM – 7:00 PM)
  const xActiveStart = paddingX + (3 / 24) * (width - paddingX * 2);
  const xActiveEnd = paddingX + (13 / 24) * (width - paddingX * 2);
  const bandWidth = xActiveEnd - xActiveStart;

  const activeBandSvg = `
    <rect x="${xActiveStart}" y="${baselineY - 26}" width="${bandWidth}" height="42" rx="6"
      fill="${isDark ? 'rgba(16, 185, 129, 0.07)' : 'rgba(16, 185, 129, 0.08)'}"
      stroke="${isDark ? 'rgba(16, 185, 129, 0.25)' : 'rgba(16, 185, 129, 0.3)'}"
      stroke-dasharray="3 3" />
    <text x="${xActiveStart + bandWidth / 2}" y="${baselineY - 14}" text-anchor="middle" font-size="9" font-weight="600"
      fill="${isDark ? '#34d399' : '#059669'}" letter-spacing="0.4" font-family="Inter, sans-serif">
      USUAL ACTIVE HOURS (9 AM &ndash; 7 PM)
    </text>
  `;

  let tickElements = ticks.map((t) => {
    const x = paddingX + t.pct * (width - paddingX * 2);
    return `
      <line x1="${x}" y1="${baselineY - 5}" x2="${x}" y2="${baselineY + 5}" stroke="${lineColor}" stroke-width="1.2" />
      <text x="${x}" y="${baselineY + 20}" text-anchor="middle" font-size="10" font-weight="500" fill="${isDark ? '#7a8ba4' : '#64748b'}" font-family="Inter, sans-serif">${t.label}</text>
    `;
  }).join('');

  // Render normal transactions dots
  let normalDots = '';
  txs.forEach((tx, idx) => {
    if (flaggedSet.has(tx.transaction_id)) return;
    const cx = getX(tx.date);
    const cy = baselineY + ((idx % 3) - 1) * 5;
    const isSelected = state.selectedTxnIds.has(tx.transaction_id);
    const amtFormatted = tx.amount_formatted || formatInr(tx.amount);
    const dt = parseSafeDate(tx.date);
    const timeStr = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });

    normalDots += `
      <circle cx="${cx}" cy="${cy}" r="${isSelected ? 5 : 3.5}" fill="${normalColor}" opacity="${isSelected ? '1' : '0.75'}"
        stroke="${isSelected ? '#ffffff' : 'none'}" stroke-width="${isSelected ? '1.5' : '0'}"
        style="cursor: pointer; transition: all 0.2s;" data-id="${tx.transaction_id}">
        <title>${tx.transaction_id}: ${tx.payee} &bull; ${amtFormatted} at ${timeStr} (${tx.channel})</title>
      </circle>
    `;
  });

  // Render flagged transactions with dots and staggered callout cards
  let flaggedDots = '';
  let callouts = '';
  const flaggedList = txs.filter((t) => flaggedSet.has(t.transaction_id));

  // Sort flagged by x coordinate to handle callout positioning
  flaggedList.sort((a, b) => getX(a.date) - getX(b.date));

  flaggedList.forEach((tx, fIdx) => {
    const cx = getX(tx.date);
    const isSelected = state.selectedTxnIds.has(tx.transaction_id);
    const dt = parseSafeDate(tx.date);
    const timeStr = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
    const amtStr = tx.amount_formatted || formatInr(tx.amount);

    flaggedDots += `
      <circle cx="${cx}" cy="${baselineY}" r="${isSelected ? 7 : 5.5}" fill="${flaggedColor}"
        stroke="#ffffff" stroke-width="2" style="cursor: pointer; filter: drop-shadow(0 2px 4px rgba(239, 68, 68, 0.4));" data-id="${tx.transaction_id}">
        <title>FLAGGED ${tx.transaction_id}: ${amtStr} to ${tx.payee} at ${timeStr}</title>
      </circle>
    `;

    // Stagger callout heights if nearby to prevent overlap
    const calloutY = (fIdx % 2 === 0) ? (baselineY - 46) : (baselineY - 64);
    const calloutWidth = 78;
    const calloutHeight = 28;

    callouts += `
      <g transform="translate(${Math.max(10, Math.min(width - calloutWidth - 10, cx - calloutWidth / 2))}, ${calloutY})"
         style="cursor: pointer;" data-id="${tx.transaction_id}">
        <rect x="0" y="0" width="${calloutWidth}" height="${calloutHeight}" rx="5"
          fill="${isDark ? '#2d1418' : '#fee2e2'}"
          stroke="${flaggedColor}" stroke-width="1.2" />
        <text x="${calloutWidth / 2}" y="11" text-anchor="middle" font-size="9" font-weight="700"
          fill="${isDark ? '#fca5a5' : '#b91c1c'}" font-family="Inter, sans-serif">${timeStr}</text>
        <text x="${calloutWidth / 2}" y="23" text-anchor="middle" font-size="10" font-weight="800"
          fill="${isDark ? '#ffffff' : '#991b1b'}" font-family="'JetBrains Mono', monospace">${amtStr}</text>
        <line x1="${calloutWidth / 2}" y1="${calloutHeight}" x2="${calloutWidth / 2}" y2="${baselineY - calloutY}"
          stroke="${flaggedColor}" stroke-width="1.2" stroke-dasharray="2 2" />
      </g>
    `;
  });

  timelineContainerEl.innerHTML = `
    <svg class="timeline-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: auto; display: block;">
      <!-- Active Hours Band -->
      ${activeBandSvg}
      <!-- Baseline Axis Line -->
      <line x1="${paddingX}" y1="${baselineY}" x2="${width - paddingX}" y2="${baselineY}" stroke="${lineColor}" stroke-width="1.5" />
      <!-- Hour Ticks -->
      ${tickElements}
      <!-- Normal Routine Dots -->
      ${normalDots}
      <!-- Flagged Dots & Callouts -->
      ${flaggedDots}
      ${callouts}
    </svg>
  `;

  // Attach click events
  timelineContainerEl.querySelectorAll('[data-id]').forEach((el) => {
    el.addEventListener('click', () => {
      const id = el.getAttribute('data-id');
      if (id) {
        state.selectedTxnIds.clear();
        state.selectedTxnIds.add(id);
        const isInFlagged = flaggedSet.has(id);
        if (!isInFlagged && !state.viewAllMode) {
          state.viewAllMode = true;
        }
        renderTransactionsTable();
        renderTimeline();
        const row = document.querySelector(`tr[data-id="${id}"]`);
        if (row) {
          row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    });
  });
}

/* ==========================================================================
   Detailed Risk Analysis (Scrollable 4 Rule Cards)
   ========================================================================== */

function renderRiskAnalysisRules(findings) {
  if (!findings || !findings.length) {
    ruleCardsContainerEl.innerHTML = '<div style="color: var(--text-muted); font-size: 12px;">No risk rules evaluated.</div>';
    return;
  }

  ruleCardsContainerEl.innerHTML = findings.map((f) => {
    const isTriggered = f.triggered;
    let badgeClass = 'not-triggered';
    let badgeText = 'Not Triggered';

    if (isTriggered) {
      badgeClass = f.severity === 'High' ? 'triggered-high' : 'triggered-medium';
      badgeText = 'Triggered';
    }

    const sevClass = f.severity === 'High' ? 'sev-high' : (f.severity === 'Medium' ? 'sev-medium' : 'sev-low');
    const isFilterActive = state.activeRuleFilter === f.rule_id;

    return `
      <div class="rule-card ${isFilterActive ? 'active-rule' : ''}" data-rule-id="${f.rule_id}">
        <div class="rule-card-top">
          <span class="rule-card-title">Rule ${f.rule_num || ''}: ${f.rule_name}</span>
          <span class="rule-status-badge ${badgeClass}">${badgeText}</span>
        </div>
        <p class="rule-card-desc">${f.description}</p>
        <div class="rule-card-footer">
          <span class="rule-severity ${sevClass}">Severity: ${f.severity}</span>
          ${isTriggered ? `<span style="color: var(--primary); font-weight: 600;">${f.matched_transaction_ids.length} tx &rsaquo;</span>` : ''}
        </div>
      </div>
    `;
  }).join('');

  ruleCardsContainerEl.querySelectorAll('.rule-card').forEach((card) => {
    card.addEventListener('click', () => {
      const rid = card.dataset.ruleId;
      if (state.activeRuleFilter === rid) {
        state.activeRuleFilter = null;
      } else {
        state.activeRuleFilter = rid;
      }
      renderTransactionsTable();
      renderRiskAnalysisRules(findings);
    });
  });
}

/* ==========================================================================
   Investigator Brief (AI Summary)
   ========================================================================== */

function renderInvestigatorBrief(narrative) {
  briefNarrativeTextEl.textContent = narrative.summary || 'All reviewed activity aligns with this customer’s established baseline.';

  const checks = narrative.recommended_checks || [];
  if (checks.length > 0) {
    briefChecksListEl.innerHTML = checks.map((c) => `<li>${c}</li>`).join('');
  } else {
    briefChecksListEl.innerHTML = `
      <li>Verify customer transaction initiation and authorization details.</li>
      <li>Review authentication/channel information and IP/device telemetry.</li>
    `;
  }
}

/* ==========================================================================
   Full Investigation Dossier Modal
   ========================================================================== */

function openFullReportModal() {
  const inv = state.investigation;
  if (!inv) return;

  const checks = inv.narrative?.recommended_checks || [];
  const findings = inv.findings || [];
  const allTxs = state.allTransactions || [];
  const flaggedTxs = state.flaggedTransactions || [];
  const flaggedSet = new Set(flaggedTxs.map(f => f.transaction_id));

  modalBodyContent.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 12px; border-bottom: 1px solid var(--border-subtle); margin-bottom: 16px;">
      <div>
        <h2 style="font-size: 18px; font-weight: 700;">Customer Risk Investigation Dossier: ${inv.customer_name} (${inv.customer_id})</h2>
        <p style="color: var(--text-muted); font-size: 12px; margin-top: 2px;">
          Account: ${inv.account_number} &bull; ${inv.account_type} &bull; Branch: ${inv.branch}
        </p>
        <p style="color: var(--text-muted); font-size: 12px;">Customer Since: ${inv.customer_since} &bull; Last Analysed: ${inv.last_analysed}</p>
      </div>
      <div style="text-align: right;">
        <span class="badge-pill ${getRiskBadgeClass(inv.risk_level)}" style="font-size: 12px; padding: 4px 12px;">${inv.risk_level}</span>
      </div>
    </div>

    <!-- First Finding & Verdict -->
    <div style="background: var(--bg-card); border-left: 4px solid var(--primary); padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;">
      <h4 style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">Surveillance Verdict &amp; First Finding</h4>
      <p style="font-size: 12px; line-height: 1.5; color: var(--text-main); font-weight: 500;">${inv.first_finding || inv.attention_subtitle}</p>
    </div>

    <!-- AI Brief Summary -->
    <div style="margin-bottom: 16px;">
      <h4 style="font-size: 13px; font-weight: 700; margin-bottom: 6px;">Executive Behavioral Narrative</h4>
      <p style="font-size: 12px; line-height: 1.5; color: var(--text-main);">${inv.narrative?.summary || 'No behavioral anomalies detected.'}</p>
    </div>

    <!-- Rule Breakdown -->
    <div style="margin-bottom: 16px;">
      <h4 style="font-size: 13px; font-weight: 700; margin-bottom: 8px;">Risk Rules Assessment</h4>
      <div style="display: flex; flex-direction: column; gap: 6px;">
        ${findings.map((f) => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--bg-card); border: 1px solid var(--border-main); border-radius: 6px; font-size: 12px;">
            <div>
              <strong>Rule ${f.rule_num}: ${f.rule_name}</strong>
              <div style="color: var(--text-muted); font-size: 11px;">${f.description}</div>
            </div>
            <span class="badge-pill ${f.triggered ? 'badge-risk-high' : 'badge-gray-bg'}" style="font-size: 10px;">
              ${f.triggered ? 'TRIGGERED' : 'NOT TRIGGERED'}
            </span>
          </div>
        `).join('')}
      </div>
    </div>

    <!-- Actionable Investigator Protocol -->
    <div style="margin-bottom: 16px;">
      <h4 style="font-size: 13px; font-weight: 700; margin-bottom: 6px;">Actionable Investigator Protocol Checklist</h4>
      <ol style="padding-left: 20px; font-size: 12px; line-height: 1.5; color: var(--text-main);">
        ${checks.map((c) => `<li style="margin-bottom: 4px;">${c}</li>`).join('')}
      </ol>
    </div>

    <!-- Complete Transaction History Table (All Records) -->
    <div style="margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <h4 style="font-size: 13px; font-weight: 700; margin: 0;">Comprehensive Transaction Audit Ledger (${allTxs.length} Total Records)</h4>
        <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">${flaggedTxs.length} Flagged &bull; ${allTxs.length - flaggedTxs.length} Baseline</span>
      </div>
      <div style="border: 1px solid var(--border-main); border-radius: 6px; overflow: visible;">
        <table style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left;">
          <thead>
            <tr style="background: var(--bg-card); border-bottom: 1px solid var(--border-main);">
              <th style="padding: 6px 8px;">Txn ID</th>
              <th style="padding: 6px 8px;">Date &amp; Time</th>
              <th style="padding: 6px 8px;">Description</th>
              <th style="padding: 6px 8px;">Payee</th>
              <th style="padding: 6px 8px;">Amount</th>
              <th style="padding: 6px 8px;">Channel</th>
              <th style="padding: 6px 8px;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${allTxs.map((t) => {
              const isFlagged = flaggedSet.has(t.transaction_id);
              const dt = parseSafeDate(t.date);
              const dateStr = dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) + ', ' +
                              dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
              const amtStr = t.amount_formatted || formatInr(t.amount);
              return `
                <tr style="border-bottom: 1px solid var(--border-subtle); background: ${isFlagged ? 'rgba(239, 68, 68, 0.08)' : 'transparent'};">
                  <td style="padding: 5px 8px; font-family: monospace; font-weight: 600;">${t.transaction_id}</td>
                  <td style="padding: 5px 8px;">${dateStr}</td>
                  <td style="padding: 5px 8px;">${t.description || '-'}</td>
                  <td style="padding: 5px 8px; font-weight: 600;">${t.payee || '-'}</td>
                  <td style="padding: 5px 8px; font-family: monospace; font-weight: 700;">${amtStr}</td>
                  <td style="padding: 5px 8px;">${t.channel || 'Online'}</td>
                  <td style="padding: 5px 8px;">
                    ${isFlagged ? '<span style="color: #dc2626; font-weight: 700;">● FLAGGED</span>' : '<span style="color: #16a34a; font-weight: 600;">✓ Baseline</span>'}
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Compliance Disclaimer -->
    <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); padding: 10px 14px; border-radius: 6px; font-size: 11px; color: var(--text-muted);">
      <strong>Bank Fraud Desk Regulatory Notice:</strong> This report identifies deviations against customer behavioral baselines. It does not state fraud has occurred. Final adjudication rests with designated compliance authorities.
    </div>
  `;

  reportModal.classList.remove('hidden');
}

openFullReportBtn.addEventListener('click', openFullReportModal);
viewFullReportTopBtn.addEventListener('click', openFullReportModal);
closeModalBtn.addEventListener('click', () => reportModal.classList.add('hidden'));
closeModalFooterBtn.addEventListener('click', () => reportModal.classList.add('hidden'));
printReportBtn.addEventListener('click', () => window.print());
modalDownloadWordBtn.addEventListener('click', () => generateAndDownloadWordDoc());

/* ==========================================================================
   Export Modal & Word (.doc) / PDF Generator
   ========================================================================== */

exportReportBtn.addEventListener('click', () => {
  exportModal.classList.remove('hidden');
});

closeExportModalBtn.addEventListener('click', () => exportModal.classList.add('hidden'));
cancelExportBtn.addEventListener('click', () => exportModal.classList.add('hidden'));

choiceExportWord.addEventListener('click', () => {
  exportModal.classList.add('hidden');
  generateAndDownloadWordDoc();
});

choiceExportPdf.addEventListener('click', () => {
  exportModal.classList.add('hidden');
  openFullReportModal();
  setTimeout(() => window.print(), 300);
});

function generateAndDownloadWordDoc(customerOverride = null) {
  const inv = customerOverride || state.investigation;
  if (!inv) return;

  const checks = inv.narrative?.recommended_checks || [];
  const findings = inv.findings || [];
  const flaggedTxs = inv.flagged_transactions || [];

  const htmlContent = `
    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
    <head>
      <meta charset="utf-8">
      <title>SentinelView Investigation Dossier - ${inv.customer_name}</title>
      <style>
        body { font-family: 'Calibri', 'Arial', sans-serif; font-size: 11pt; line-height: 1.5; color: #1a1a1a; margin: 20mm; }
        h1 { font-size: 20pt; color: #1e3a8a; border-bottom: 2pt solid #1e3a8a; padding-bottom: 4pt; margin-bottom: 12pt; }
        h2 { font-size: 14pt; color: #1e3a8a; margin-top: 14pt; margin-bottom: 6pt; }
        h3 { font-size: 12pt; color: #334155; margin-top: 10pt; margin-bottom: 4pt; }
        .meta-box { background-color: #f8fafc; border: 1pt solid #cbd5e1; padding: 10pt; margin-bottom: 14pt; }
        .verdict-box { background-color: #fef2f2; border-left: 4pt solid #dc2626; padding: 10pt; margin-bottom: 14pt; }
        .verdict-clean { background-color: #f0fdf4; border-left: 4pt solid #16a34a; padding: 10pt; margin-bottom: 14pt; }
        table { width: 100%; border-collapse: collapse; margin-top: 8pt; margin-bottom: 14pt; font-size: 10pt; }
        th { background-color: #1e3a8a; color: #ffffff; padding: 6pt 8pt; text-align: left; border: 1pt solid #1e3a8a; }
        td { padding: 5pt 8pt; border: 1pt solid #cbd5e1; }
        tr:nth-child(even) { background-color: #f8fafc; }
        .badge { font-weight: bold; padding: 2pt 6pt; border-radius: 3pt; font-size: 9pt; }
        .footer-note { font-size: 9pt; color: #64748b; border-top: 1pt solid #cbd5e1; padding-top: 8pt; margin-top: 20pt; }
      </style>
    </head>
    <body>
      <h1>SENTINELVIEW &bull; FRAUD INVESTIGATION DOSSIER</h1>
      
      <div class="meta-box">
        <strong>Customer:</strong> ${inv.customer_name} (ID: ${inv.customer_id})<br>
        <strong>Account No:</strong> ${inv.account_number} &bull; <strong>Type:</strong> ${inv.account_type}<br>
        <strong>Branch:</strong> ${inv.branch} &bull; <strong>Phone:</strong> ${inv.phone}<br>
        <strong>Customer Since:</strong> ${inv.customer_since} &bull; <strong>Last Analysed:</strong> ${inv.last_analysed}<br>
        <strong>Investigating Officer:</strong> Dharshini, Fraud Analyst (Officer #4029)
      </div>

      <div class="${inv.risk_level === 'HIGH' ? 'verdict-box' : 'verdict-clean'}">
        <h2 style="margin-top:0; color:${inv.risk_level === 'HIGH' ? '#dc2626' : '#16a34a'};">
          SURVEILLANCE VERDICT: ${inv.risk_level} (${inv.attention_title || 'ATTENTION REQUIRED'})
        </h2>
        <p><strong>First Finding:</strong> ${inv.first_finding || inv.attention_subtitle}</p>
      </div>

      <h2>1. Executive Behavioral AI Summary</h2>
      <p>${inv.narrative?.summary || 'No behavioral deviations detected.'}</p>

      <h2>2. Actionable Recommended Checks</h2>
      <ol>
        ${checks.map((c) => `<li>${c}</li>`).join('')}
      </ol>

      <h2>3. Risk Rules Evaluation Matrix</h2>
      <table>
        <thead>
          <tr>
            <th>Rule ID</th>
            <th>Rule Name</th>
            <th>Status</th>
            <th>Severity</th>
            <th>Observed Findings</th>
          </tr>
        </thead>
        <tbody>
          ${findings.map((f) => `
            <tr>
              <td><strong>${f.rule_id}</strong></td>
              <td>${f.rule_name}</td>
              <td style="color:${f.triggered ? '#dc2626' : '#16a34a'}; font-weight:bold;">${f.triggered ? 'TRIGGERED' : 'CLEAN'}</td>
              <td>${f.severity}</td>
              <td>${f.description}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>

      <h2>4. Comprehensive Transaction Audit Ledger (${(state.allTransactions && state.allTransactions.length > 0 ? state.allTransactions.length : flaggedTxs.length)} Total Records)</h2>
      <table>
        <thead>
          <tr>
            <th>Txn ID</th>
            <th>Date &amp; Time</th>
            <th>Description</th>
            <th>Payee</th>
            <th>Amount (INR)</th>
            <th>Channel</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${(state.allTransactions && state.allTransactions.length > 0 ? state.allTransactions : flaggedTxs).map((t) => {
            const isFlagged = flaggedTxs.some(f => f.transaction_id === t.transaction_id);
            const dt = parseSafeDate(t.date);
            const dateStr = dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) + ', ' +
                            dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
            return `
              <tr style="background-color: ${isFlagged ? '#fee2e2' : 'transparent'};">
                <td><strong>${t.transaction_id}</strong></td>
                <td>${dateStr}</td>
                <td>${t.description || '-'}</td>
                <td>${t.payee || '-'}</td>
                <td><strong>${formatInr(t.amount)}</strong></td>
                <td>${t.channel || 'Online'}</td>
                <td style="color: ${isFlagged ? '#dc2626' : '#16a34a'}; font-weight: bold;">${isFlagged ? 'FLAGGED' : 'BASELINE'}</td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>

      <div class="footer-note">
        <strong>Bank Fraud Desk Notice:</strong> This dossier contains proprietary surveillance indicators and behavioral baseline comparisons. It does not state fraud has occurred; it flags, explains, and submits evidence to the investigator.
      </div>
    </body>
    </html>
  `;

  const blob = new Blob(['\ufeff', htmlContent], {
    type: 'application/msword',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `SentinelView_Dossier_${inv.customer_id}_${inv.customer_name.replace(/\s+/g, '_')}.doc`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(`Dossier downloaded as Microsoft Word (.doc)`);
}

/* ==========================================================================
   Share & Case Note Management
   ========================================================================== */

shareBtn.addEventListener('click', () => {
  if (!state.investigation) return;
  const text = `SentinelView Investigation Dossier\nCustomer: ${state.investigation.customer_name} (${state.investigation.customer_id})\nRisk Level: ${state.investigation.risk_level}\nSummary: ${state.investigation.narrative?.summary || ''}`;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Investigation brief copied to clipboard.');
    });
  } else {
    showToast('Investigation link ready.');
  }
});

addNoteBtn.addEventListener('click', () => {
  if (!state.currentCustomerId) return;
  investigatorNoteInput.value = state.customerNotes[state.currentCustomerId] || '';
  noteModal.classList.remove('hidden');
});

closeNoteModalBtn.addEventListener('click', () => noteModal.classList.add('hidden'));
cancelNoteBtn.addEventListener('click', () => noteModal.classList.add('hidden'));
saveNoteBtn.addEventListener('click', () => {
  if (state.currentCustomerId) {
    state.customerNotes[state.currentCustomerId] = investigatorNoteInput.value;
    localStorage.setItem('sentinel_notes', JSON.stringify(state.customerNotes));
    noteModal.classList.add('hidden');
    showToast('Case note saved successfully.');
  }
});

/* ==========================================================================
   Transaction Detail Modal
   ========================================================================== */

function openTxnDetailModal(txId) {
  const tx = state.allTransactions.find((t) => t.transaction_id === txId);
  if (!tx) return;

  const rules = tx.triggered_rules || [];
  modalBodyContent.innerHTML = `
    <div style="padding-bottom: 12px; border-bottom: 1px solid var(--border-subtle); margin-bottom: 14px;">
      <h3 style="font-size: 16px; font-weight: 700;">Transaction Audit Details: ${tx.transaction_id}</h3>
      <p style="color: var(--text-muted); font-size: 12px;">Customer: ${state.currentCustomer?.name} (${tx.customer_id})</p>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px;">
      <div style="background: var(--bg-card); padding: 10px; border-radius: 6px; border: 1px solid var(--border-main);">
        <span style="font-size: 11px; color: var(--text-muted);">Amount</span>
        <div style="font-size: 16px; font-weight: 700; color: var(--text-main); font-family: 'JetBrains Mono', monospace;">${formatInr(tx.amount)}</div>
      </div>
      <div style="background: var(--bg-card); padding: 10px; border-radius: 6px; border: 1px solid var(--border-main);">
        <span style="font-size: 11px; color: var(--text-muted);">Channel</span>
        <div style="font-size: 14px; font-weight: 600; color: var(--text-main);">${tx.channel}</div>
      </div>
      <div style="background: var(--bg-card); padding: 10px; border-radius: 6px; border: 1px solid var(--border-main);">
        <span style="font-size: 11px; color: var(--text-muted);">Payee</span>
        <div style="font-size: 14px; font-weight: 600; color: var(--text-main);">${tx.payee}</div>
      </div>
      <div style="background: var(--bg-card); padding: 10px; border-radius: 6px; border: 1px solid var(--border-main);">
        <span style="font-size: 11px; color: var(--text-muted);">Date & Time</span>
        <div style="font-size: 14px; font-weight: 600; color: var(--text-main);">${tx.date_formatted || tx.date}</div>
      </div>
    </div>

    <div>
      <h4 style="font-size: 12px; font-weight: 700; margin-bottom: 6px;">Triggered Risk Rules</h4>
      ${rules.length > 0 ? `
        <div style="display: flex; flex-direction: column; gap: 6px;">
          ${rules.map((r) => `
            <div style="padding: 8px 10px; background: rgba(220, 38, 38, 0.08); border: 1px solid var(--risk-high-border); border-radius: 6px; font-size: 12px; color: var(--risk-high);">
              <strong>${r.rule_name} (${r.rule_id})</strong> &bull; Severity: ${r.severity}
            </div>
          `).join('')}
        </div>
      ` : `
        <p style="color: var(--text-muted); font-size: 12px;">This transaction aligns with customer's regular baseline.</p>
      `}
    </div>
  `;

  reportModal.classList.remove('hidden');
}

/* ==========================================================================
   VIEW 2: Dashboard Implementation
   ========================================================================== */

async function loadDashboardView() {
  try {
    const res = await fetch('/api/dashboard/stats');
    const data = await res.json();
    state.dashboardData = data;

    // 1. Metrics
    document.getElementById('statMonitored').textContent = data.metrics.total_monitored_accounts;
    document.getElementById('statHighAlerts').textContent = data.metrics.active_high_risk_alerts;
    document.getElementById('statVolume').textContent = data.metrics.reviewed_volume_inr;
    document.getElementById('statAccuracy').textContent = data.metrics.fraud_prevention_rate;

    document.getElementById('activeAlertQueueCount').textContent = `${data.alert_queue.length} Alerts Pending`;

    // 2. Alert Queue Table
    const tableBody = document.getElementById('dashAlertsTableBody');
    tableBody.innerHTML = data.alert_queue.map((a) => {
      const isHigh = a.risk_level === 'HIGH';
      return `
        <tr>
          <td><span class="badge-pill ${isHigh ? 'badge-risk-high' : 'badge-risk-medium'}">${a.priority}</span></td>
          <td><strong>${a.customer_name}</strong> <span style="font-size: 11px; color: var(--text-muted);">(${a.customer_id})</span></td>
          <td style="font-family: 'JetBrains Mono', monospace;">${a.account_number}</td>
          <td><span class="badge-pill ${isHigh ? 'badge-risk-high' : 'badge-risk-medium'}">${a.risk_level}</span></td>
          <td>${a.triggered_rules.map((r) => `<span class="rule-tag rule-tag-burst">${r}</span>`).join(' ')}</td>
          <td><strong>${a.flagged_tx_count} tx</strong></td>
          <td>${a.last_analysed}</td>
          <td>
            <button class="btn-investigate-now" data-customer-id="${a.customer_id}">
              Investigate &rarr;
            </button>
          </td>
        </tr>
      `;
    }).join('');

    tableBody.querySelectorAll('.btn-investigate-now').forEach((btn) => {
      btn.addEventListener('click', () => {
        const cid = btn.dataset.customerId;
        switchTab('investigate');
        selectCustomer(cid);
      });
    });

    // 3. Rule Distribution
    const distContainer = document.getElementById('ruleDistributionList');
    const dist = data.rule_distribution;
    const maxVal = Math.max(...Object.values(dist), 1);
    distContainer.innerHTML = Object.keys(dist).map((k) => {
      const val = dist[k];
      const pct = Math.round((val / maxVal) * 100);
      return `
        <div class="breakdown-item">
          <span style="width: 200px; font-weight: 500;">${k}</span>
          <div class="breakdown-bar-wrap">
            <div class="breakdown-bar" style="width: ${pct}%;"></div>
          </div>
          <span style="font-weight: 700; width: 30px; text-align: right;">${val}</span>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load dashboard data:', err);
  }
}

/* ==========================================================================
   VIEW 3: Risk Alerts View Implementation
   ========================================================================== */

async function loadAlertsView() {
  try {
    const res = await fetch('/api/alerts');
    const alerts = await res.json();
    state.alertsData = alerts;

    const highCount = alerts.filter((a) => a.risk_level === 'HIGH').length;
    const medCount = alerts.filter((a) => a.risk_level === 'MEDIUM').length;

    document.getElementById('alertCountAll').textContent = alerts.length;
    document.getElementById('alertCountHigh').textContent = highCount;
    document.getElementById('alertCountMed').textContent = medCount;

    renderAlertsCards('ALL');

    document.querySelectorAll('.filter-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.filter-chip').forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        renderAlertsCards(chip.dataset.filter);
      });
    });
  } catch (err) {
    console.error('Failed to load alerts view:', err);
  }
}

function renderAlertsCards(filter) {
  const container = document.getElementById('alertsCardsGrid');
  let list = state.alertsData;
  if (filter !== 'ALL') {
    list = list.filter((a) => a.risk_level === filter);
  }

  if (!list.length) {
    container.innerHTML = '<div style="color: var(--text-muted); padding: 20px;">No alerts in this category.</div>';
    return;
  }

  container.innerHTML = list.map((a) => {
    const isHigh = a.risk_level === 'HIGH';
    return `
      <div class="alert-card">
        <div class="alert-card-header">
          <div>
            <div class="alert-cust-name">${a.customer_name}</div>
            <div class="alert-cust-acc">ID: ${a.customer_id} &bull; Acc: ${a.account_number}</div>
          </div>
          <span class="badge-pill ${isHigh ? 'badge-risk-high' : 'badge-risk-medium'}">${a.risk_level}</span>
        </div>
        <div class="alert-rule-badges">
          ${a.triggered_rules.map((r) => `<span class="rule-tag rule-tag-large">${r}</span>`).join('')}
        </div>
        <div class="alert-summary">${a.summary}</div>
        <div class="alert-footer">
          <span>${a.timestamp} &bull; <strong>${a.flagged_count} flagged tx</strong></span>
          <button class="btn-investigate-now" data-customer-id="${a.customer_id}">Investigate Case &rarr;</button>
        </div>
      </div>
    `;
  }).join('');

  container.querySelectorAll('.btn-investigate-now').forEach((btn) => {
    btn.addEventListener('click', () => {
      const cid = btn.dataset.customerId;
      switchTab('investigate');
      selectCustomer(cid);
    });
  });
}

/* ==========================================================================
   VIEW 4: Reports Archive Implementation
   ========================================================================== */

async function loadReportsView() {
  try {
    const res = await fetch('/api/reports');
    const reports = await res.json();
    state.reportsData = reports;

    const tbody = document.getElementById('reportsArchiveBody');
    tbody.innerHTML = reports.map((r) => {
      const isClean = r.risk_level === 'NO RISK';
      return `
        <tr>
          <td><strong style="font-family: 'JetBrains Mono', monospace;">${r.report_id}</strong></td>
          <td><strong>${r.customer_name}</strong> <span style="color: var(--text-muted); font-size: 11px;">(${r.customer_id})</span></td>
          <td style="font-family: 'JetBrains Mono', monospace;">${r.account_number}</td>
          <td><span class="badge-pill ${getRiskBadgeClass(r.risk_level)}">${r.risk_level}</span></td>
          <td style="font-weight: 700; color: ${isClean ? 'var(--risk-clean)' : 'var(--risk-high)'};">${r.verdict}</td>
          <td>${r.generated_date}</td>
          <td>${r.investigator}</td>
          <td>
            <button class="link-btn btn-doc-export" data-cid="${r.customer_id}" style="margin-right: 8px;">
              Word (.doc)
            </button>
            <button class="link-btn btn-pdf-export" data-cid="${r.customer_id}">
              PDF
            </button>
          </td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.btn-doc-export').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const cid = btn.dataset.cid;
        let invData = state.investigationCache[cid];
        if (!invData) {
          const res = await fetch(`/api/customers/${cid}/investigate`, { method: 'POST' });
          invData = await res.json();
          state.investigationCache[cid] = invData;
        }
        generateAndDownloadWordDoc(invData);
      });
    });

    tbody.querySelectorAll('.btn-pdf-export').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const cid = btn.dataset.cid;
        switchTab('investigate');
        await selectCustomer(cid);
        openFullReportModal();
        setTimeout(() => window.print(), 300);
      });
    });
  } catch (err) {
    console.error('Failed to load reports view:', err);
  }
}

document.getElementById('exportAllReportsBtn').addEventListener('click', () => {
    window.print();
});

/* ==========================================================================
   Boot Application
   ========================================================================== */

async function boot() {
  applyTheme(state.theme);

  try {
    const res = await fetch('/api/customers');
    const customers = await res.json();
    state.customers = customers || [];

    // Pre-calculate badge count for High Risk alerts
    const highRiskCount = state.customers.filter((c) => c.risk_level === 'high').length;
    riskAlertsBadge.textContent = highRiskCount || '3';

    if (state.customers.length > 0) {
      state.currentCustomerId = state.customers[0].id;
      renderCustomerList();
      await selectCustomer(state.currentCustomerId);

      // Pre-warm client cache in background for all remaining customers for instant switching
      state.customers.slice(1).forEach(async (c) => {
        try {
          const cRes = await fetch(`/api/customers/${c.id}/investigate`, { method: 'POST' });
          const cData = await cRes.json();
          state.investigationCache[c.id] = cData;
        } catch (e) {
          // Silent fallback
        }
      });
    }
  } catch (err) {
    console.error('Failed to boot SentinelView:', err);
    showToast('Failed to connect to SentinelView backend.');
  }
}

boot();


let notificationTimer = null;

window.showNotification = function(title, msg) {
    const toast = document.getElementById('notificationToast');
    const t = document.getElementById('notifTitle');
    const m = document.getElementById('notifMsg');
    if(toast && t && m) {
        t.innerText = title;
        m.innerText = msg;
        toast.classList.add('show');
        if (notificationTimer) clearTimeout(notificationTimer);
        notificationTimer = setTimeout(() => toast.classList.remove('show'), 5000);
    }
};

window.toggleNotification = function(title, msg) {
    const toast = document.getElementById('notificationToast');
    if (toast && toast.classList.contains('show')) {
        toast.classList.remove('show');
        if (notificationTimer) clearTimeout(notificationTimer);
    } else {
        showNotification(title || 'New System Alert', msg || 'Unusual pattern detected across 3 accounts.');
    }
};

// Hook into header bell icon to toggle alert
const headerBell = document.getElementById('headerNotificationBtn');
if(headerBell) {
    headerBell.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleNotification('New System Alert', 'Unusual pattern detected across 3 accounts.');
    });
}

// Dismiss notification popover when clicking anywhere outside
document.addEventListener('click', (e) => {
    const toast = document.getElementById('notificationToast');
    if (toast && toast.classList.contains('show')) {
        if (!toast.contains(e.target) && (!headerBell || !headerBell.contains(e.target))) {
            toast.classList.remove('show');
            if (notificationTimer) clearTimeout(notificationTimer);
        }
    }
});

window.openTxModal = function() {
    const modal = document.getElementById('txModal');
    if (modal) {
        modal.classList.add('show');
        filterModalTx('all');
    }
};

window.closeTxModal = function() {
    const modal = document.getElementById('txModal');
    if (modal) {
        modal.classList.remove('show');
    }
};

window.filterModalTx = function(filter) {
    const btnAll = document.getElementById('modalFilterAll');
    const btnFlagged = document.getElementById('modalFilterFlagged');
    if (btnAll && btnFlagged) {
        if (filter === 'all') {
            btnAll.classList.add('active');
            btnAll.classList.remove('btn-outline');
            btnFlagged.classList.remove('active');
            btnFlagged.classList.add('btn-outline');
        } else {
            btnFlagged.classList.add('active');
            btnFlagged.classList.remove('btn-outline');
            btnAll.classList.remove('active');
            btnAll.classList.add('btn-outline');
        }
    }
    
    const tbody = document.getElementById('modalTxTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    const txs = (filter === 'all') ? state.allTransactions : state.flaggedTransactions;
    if (!txs || txs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-muted);">No ' + (filter === 'flagged' ? 'flagged ' : '') + 'transactions found.</td></tr>';
        return;
    }
    
    const flaggedSet = new Set((state.flaggedTransactions || []).map(f => f.transaction_id));
    
    tbody.innerHTML = txs.map(tx => {
        const isFlagged = flaggedSet.has(tx.transaction_id);
        const dt = parseSafeDate(tx.date);
        const dateFormatted = dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) + ', ' +
                              dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
        const amountFormatted = tx.amount_formatted || formatInr(tx.amount);
        const rowClass = isFlagged ? 'row-flagged' : '';
        
        let ruleBadge = '<span class="rule-tag rule-tag-clean">Baseline</span>';
        if (isFlagged && tx.triggered_rules && tx.triggered_rules.length > 0) {
            ruleBadge = tx.triggered_rules.map(r => `<span class="rule-tag rule-tag-burst">${r.badge_name || r.rule_name}</span>`).join(' ');
        } else if (isFlagged) {
            ruleBadge = '<span class="rule-tag rule-tag-burst">Flagged</span>';
        }
        
        return `
            <tr class="${rowClass}">
                <td style="font-family: monospace; font-weight: 600;">${tx.transaction_id}</td>
                <td>${dateFormatted}</td>
                <td>${tx.description || 'Transaction'}</td>
                <td><strong>${tx.payee || '-'}</strong></td>
                <td class="font-mono" style="font-weight: 700;">${amountFormatted}</td>
                <td>${tx.channel || 'Online'}</td>
                <td>${ruleBadge}</td>
            </tr>
        `;
    }).join('');
};

/* ==========================================================================
   Admin Upload Handlers & Runtime Cache Refresh
   ========================================================================== */

async function reloadSystemData() {
  try {
    const res = await fetch('/api/customers');
    const customers = await res.json();
    state.customers = customers || [];
    state.investigationCache = {};

    const highRiskCount = state.customers.filter((c) => c.risk_level === 'high').length;
    if (riskAlertsBadge) riskAlertsBadge.textContent = highRiskCount || '0';
    if (customerTotalCountEl) customerTotalCountEl.textContent = state.customers.length;

    renderCustomerList(customerSearchInput ? customerSearchInput.value : '');

    if (state.customers.length > 0) {
      const exists = state.customers.some((c) => c.id === state.currentCustomerId);
      const targetId = exists ? state.currentCustomerId : state.customers[0].id;
      await selectCustomer(targetId);

      // Pre-warm client cache in background
      state.customers.forEach(async (c) => {
        try {
          const cRes = await fetch(`/api/customers/${c.id}/investigate`, { method: 'POST' });
          const cData = await cRes.json();
          state.investigationCache[c.id] = cData;
        } catch (e) {}
      });
    }
  } catch (err) {
    console.error('Failed to reload system data:', err);
  }
}

// Transactions Upload Form
const uploadTxForm = document.getElementById('uploadTxForm');
const txUploadResult = document.getElementById('txUploadResult');
const btnUploadTx = document.getElementById('btnUploadTx');

if (uploadTxForm) {
  uploadTxForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!btnUploadTx || !txUploadResult) return;

    const fileInput = document.getElementById('txFileInput');
    if (!fileInput || !fileInput.files.length) {
      showToast('Please select a CSV file first.');
      return;
    }

    btnUploadTx.disabled = true;
    btnUploadTx.innerHTML = '<span>Processing Upload...</span>';
    txUploadResult.className = 'hidden';

    try {
      const formData = new FormData(uploadTxForm);
      const response = await fetch('/admin/upload-transactions', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (response.ok && data.status === 'success') {
        let rejectedHtml = '';
        if (data.rows_rejected && data.rows_rejected.length > 0) {
          rejectedHtml = `
            <div style="margin-top: 8px; font-size: 12px; color: #b45309;">
              <strong>Rejected Rows (${data.rows_rejected.length}):</strong>
              <ul style="margin: 4px 0 0 16px; padding: 0; max-height: 120px; overflow-y: auto;">
                ${data.rows_rejected.map(r => `<li>Row ${r.row}: ${r.reason}</li>`).join('')}
              </ul>
            </div>
          `;
        }

        txUploadResult.className = '';
        txUploadResult.style.background = 'rgba(16, 185, 129, 0.1)';
        txUploadResult.style.border = '1px solid rgba(16, 185, 129, 0.3)';
        txUploadResult.style.color = '#065f46';
        txUploadResult.innerHTML = `
          <div style="font-weight: 600; display: flex; align-items: center; justify-content: space-between;">
            <span>Upload Completed Successfully</span>
            <span><span class="badge-pill" style="background:#10b981; color:#fff;">+${data.rows_added} Rows</span></span>
          </div>
          <div style="margin-top: 4px;">${data.message || ''}</div>
          ${rejectedHtml}
        `;

        showToast(`Transactions updated: +${data.rows_added} added.`);
        uploadTxForm.reset();
        await reloadSystemData();
      } else {
        txUploadResult.className = '';
        txUploadResult.style.background = 'rgba(239, 68, 68, 0.1)';
        txUploadResult.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        txUploadResult.style.color = '#991b1b';
        txUploadResult.innerHTML = `
          <div style="font-weight: 600;">Upload Failed</div>
          <div style="margin-top: 4px;">${data.error || 'Unknown error occurred while processing CSV.'}</div>
          ${data.expected_columns ? `<div style="font-size: 11px; margin-top: 4px; font-family: monospace;">Expected columns: ${data.expected_columns.join(', ')}</div>` : ''}
        `;
        showToast('CSV Upload Failed: ' + (data.error || 'Server error'));
      }
    } catch (err) {
      console.error('Transactions upload error:', err);
      txUploadResult.className = '';
      txUploadResult.style.background = 'rgba(239, 68, 68, 0.1)';
      txUploadResult.style.border = '1px solid rgba(239, 68, 68, 0.3)';
      txUploadResult.style.color = '#991b1b';
      txUploadResult.innerHTML = `<strong>Error:</strong> Failed to connect to server.`;
      showToast('Network error during upload.');
    } finally {
      btnUploadTx.disabled = false;
      btnUploadTx.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <span>Ingest Transactions</span>
      `;
    }
  });
}

// Customers Upload Form
const uploadCustForm = document.getElementById('uploadCustForm');
const custUploadResult = document.getElementById('custUploadResult');
const btnUploadCust = document.getElementById('btnUploadCust');

if (uploadCustForm) {
  uploadCustForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!btnUploadCust || !custUploadResult) return;

    const fileInput = document.getElementById('custFileInput');
    if (!fileInput || !fileInput.files.length) {
      showToast('Please select a JSON or CSV file first.');
      return;
    }

    btnUploadCust.disabled = true;
    btnUploadCust.innerHTML = '<span>Processing Upload...</span>';
    custUploadResult.className = 'hidden';

    try {
      const formData = new FormData(uploadCustForm);
      const response = await fetch('/admin/upload-customers', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (response.ok && data.status === 'success') {
        let rejectedHtml = '';
        if (data.rows_rejected && data.rows_rejected.length > 0) {
          rejectedHtml = `
            <div style="margin-top: 8px; font-size: 12px; color: #b45309;">
              <strong>Rejected Records (${data.rows_rejected.length}):</strong>
              <ul style="margin: 4px 0 0 16px; padding: 0; max-height: 120px; overflow-y: auto;">
                ${data.rows_rejected.map(r => `<li>Row ${r.row}: ${r.reason}</li>`).join('')}
              </ul>
            </div>
          `;
        }

        custUploadResult.className = '';
        custUploadResult.style.background = 'rgba(99, 102, 241, 0.1)';
        custUploadResult.style.border = '1px solid rgba(99, 102, 241, 0.3)';
        custUploadResult.style.color = '#3730a3';
        custUploadResult.innerHTML = `
          <div style="font-weight: 600; display: flex; align-items: center; justify-content: space-between;">
            <span>Customers Ingested Successfully</span>
            <span><span class="badge-pill" style="background:#6366f1; color:#fff;">+${data.rows_added} Profiles</span></span>
          </div>
          <div style="margin-top: 4px;">${data.message || ''}</div>
          ${rejectedHtml}
        `;

        showToast(`Customer profiles updated: +${data.rows_added} added.`);
        uploadCustForm.reset();
        await reloadSystemData();
      } else {
        custUploadResult.className = '';
        custUploadResult.style.background = 'rgba(239, 68, 68, 0.1)';
        custUploadResult.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        custUploadResult.style.color = '#991b1b';
        custUploadResult.innerHTML = `
          <div style="font-weight: 600;">Upload Failed</div>
          <div style="margin-top: 4px;">${data.error || 'Unknown error occurred while processing customers.'}</div>
        `;
        showToast('Customer Upload Failed: ' + (data.error || 'Server error'));
      }
    } catch (err) {
      console.error('Customer upload error:', err);
      custUploadResult.className = '';
      custUploadResult.style.background = 'rgba(239, 68, 68, 0.1)';
      custUploadResult.style.border = '1px solid rgba(239, 68, 68, 0.3)';
      custUploadResult.style.color = '#991b1b';
      custUploadResult.innerHTML = `<strong>Error:</strong> Failed to connect to server.`;
      showToast('Network error during upload.');
    } finally {
      btnUploadCust.disabled = false;
      btnUploadCust.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <span>Ingest Customer Profiles</span>
      `;
    }
  });
}

/* ==========================================================================
   Mobile Navigation Drawer Toggle
   ========================================================================== */

const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebarNav = document.querySelector('.sidebar-nav');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');

function toggleMobileSidebar(open) {
  if (!sidebarNav || !sidebarBackdrop) return;
  const shouldOpen = open !== undefined ? open : !sidebarNav.classList.contains('open');
  if (shouldOpen) {
    sidebarNav.classList.add('open');
    sidebarBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
  } else {
    sidebarNav.classList.remove('open');
    sidebarBackdrop.classList.remove('open');
    document.body.style.overflow = '';
  }
}

if (mobileMenuBtn) {
  mobileMenuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleMobileSidebar();
  });
}

if (sidebarBackdrop) {
  sidebarBackdrop.addEventListener('click', () => toggleMobileSidebar(false));
}

// Close drawer automatically when clicking any nav link on mobile
navLinks.forEach((link) => {
  link.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      toggleMobileSidebar(false);
    }
  });
});


