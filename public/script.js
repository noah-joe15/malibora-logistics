/**
 * ============================================================
 *  MALIBORA CLOUD SYNCHRONIZER  v2.0
 *  B2B SaaS Data Engine — Production Grade
 * ============================================================
 *
 *  Responsibilities:
 *    • Full cloud → local sync (trucks, drivers, expenses,
 *      trips, compliance, debts)
 *    • Auto-retry with exponential back-off
 *    • Offline detection & graceful degradation
 *    • Per-request timeout guards
 *    • Shortcut deep-linking (PWA home-screen shortcuts)
 *    • Share-target intake (PWA receipt sharing)
 *    • Auto-refresh every 60 s while the tab is visible
 *    • Sync status indicator in the UI
 *
 *  Depends on globals defined in index.html:
 *    API_KEY, API_URL, currentCompanyId, db, renderAll(),
 *    showToast()  [our toast helper]
 * ============================================================
 */

'use strict';

// ─────────────────────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────────────────────
const SYNC_CONFIG = {
  AUTO_REFRESH_MS:   60_000,   // Re-sync every 60 s when tab is visible
  REQUEST_TIMEOUT_MS: 12_000,  // Abort any single fetch after 12 s
  MAX_RETRIES:        3,       // Retry failed fetches up to 3 times
  RETRY_BASE_MS:      800,     // Base delay for exponential back-off
};

// Single auto-refresh timer handle
let _autoRefreshTimer = null;

// Track whether a sync is currently running (prevent overlapping)
let _syncInProgress = false;

// Last successful sync timestamp
let _lastSyncAt = null;


// ─────────────────────────────────────────────────────────────
// UTILITIES
// ─────────────────────────────────────────────────────────────

/**
 * fetch() wrapper with:
 *   - automatic API-key header injection
 *   - AbortController timeout
 *   - exponential back-off retry on network/5xx errors
 */
async function cloudFetch(path, options = {}, retries = SYNC_CONFIG.MAX_RETRIES) {
  const url = `${API_URL}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    SYNC_CONFIG.REQUEST_TIMEOUT_MS
  );

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
        ...(options.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    // Treat 4xx as definitive failures (no retry)
    if (res.status >= 400 && res.status < 500) {
      const body = await res.json().catch(() => ({}));
      throw new CloudError(res.status, body.detail || `HTTP ${res.status}`, false);
    }

    // 5xx → retry
    if (!res.ok) {
      throw new CloudError(res.status, `Server error ${res.status}`, true);
    }

    return res;

  } catch (err) {
    clearTimeout(timeoutId);

    // AbortError = timeout
    if (err.name === 'AbortError') {
      throw new CloudError(0, `Request to ${path} timed out after ${SYNC_CONFIG.REQUEST_TIMEOUT_MS}ms`, true);
    }

    // Re-throw definitive (non-retryable) errors
    if (err instanceof CloudError && !err.retryable) throw err;

    // Retry with exponential back-off
    if (retries > 0) {
      const delay = SYNC_CONFIG.RETRY_BASE_MS * (SYNC_CONFIG.MAX_RETRIES - retries + 1);
      console.warn(`[Malibora Sync] Retrying ${path} in ${delay}ms … (${retries} left)`);
      await sleep(delay);
      return cloudFetch(path, options, retries - 1);
    }

    throw err;
  }
}

class CloudError extends Error {
  constructor(status, message, retryable = false) {
    super(message);
    this.name = 'CloudError';
    this.status = status;
    this.retryable = retryable;
  }
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

/** Returns true when the browser has a network connection. */
const isOnline = () => navigator.onLine;

/**
 * Safely parse a JSON response.
 * Returns a fallback value if parsing fails so one bad
 * endpoint doesn't crash the entire sync.
 */
async function safeJson(res, fallback = []) {
  try {
    return await res.json();
  } catch {
    console.warn('[Malibora Sync] Failed to parse JSON from', res.url);
    return fallback;
  }
}

/**
 * Parse "Category - Description" format used in expense descriptions.
 */
function parseExpenseDescription(raw = '') {
  if (!raw.includes(' - ')) return { cat: 'Other', desc: raw };
  const idx = raw.indexOf(' - ');
  return { cat: raw.slice(0, idx).trim(), desc: raw.slice(idx + 3).trim() };
}


// ─────────────────────────────────────────────────────────────
// SYNC STATUS UI
// ─────────────────────────────────────────────────────────────

/**
 * Injects or updates a tiny sync-status badge in the header.
 * Falls back silently if the element doesn't exist.
 */
function setSyncStatus(state) {
  // state: 'syncing' | 'ok' | 'error' | 'offline'
  let el = document.getElementById('syncStatusBadge');

  if (!el) {
    // Create the badge once and append to header
    el = document.createElement('div');
    el.id = 'syncStatusBadge';
    el.style.cssText = [
      'display:flex', 'align-items:center', 'gap:6px',
      'padding:5px 12px', 'border-radius:50px',
      'font-size:0.72rem', 'font-weight:700',
      'letter-spacing:0.5px',
      'border:1px solid',
      'transition:all 0.4s ease',
      'backdrop-filter:blur(8px)',
    ].join(';');
    const header = document.querySelector('.header');
    if (header) header.appendChild(el);
  }

  const configs = {
    syncing: { bg: 'rgba(96,165,250,0.15)',  border: 'rgba(96,165,250,0.35)',  color: '#93c5fd', dot: 'rgba(96,165,250,0.8)',  text: 'Syncing…',  anim: true  },
    ok:      { bg: 'rgba(52,211,153,0.12)',  border: 'rgba(52,211,153,0.35)',  color: '#34d399', dot: '#34d399',               text: 'Live',      anim: true  },
    error:   { bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.35)', color: '#f87171', dot: '#f87171',               text: 'Sync Failed', anim: false },
    offline: { bg: 'rgba(100,116,139,0.15)', border: 'rgba(100,116,139,0.35)', color: '#94a3b8', dot: '#64748b',               text: 'Offline',   anim: false },
  };

  const cfg = configs[state] || configs.ok;

  el.style.background   = cfg.bg;
  el.style.borderColor  = cfg.border;
  el.style.color        = cfg.color;
  el.innerHTML = `
    <div style="
      width:7px;height:7px;border-radius:50%;
      background:${cfg.dot};flex-shrink:0;
      ${cfg.anim ? 'animation:blink 1.4s infinite;' : ''}
    "></div>
    ${cfg.text}
  `;
}


// ─────────────────────────────────────────────────────────────
// MASTER SYNC FUNCTION
// ─────────────────────────────────────────────────────────────

/**
 * Pulls all company data from the cloud and populates `db`.
 * Safe to call multiple times — overlapping calls are skipped.
 *
 * @param {object}  opts
 * @param {boolean} opts.silent   - skip toasts (used by auto-refresh)
 * @param {boolean} opts.force    - bypass the in-progress guard
 */
async function syncDashboardWithCloud({ silent = false, force = false } = {}) {
  if (_syncInProgress && !force) {
    console.info('[Malibora Sync] Skipped — sync already running.');
    return;
  }

  if (!currentCompanyId) {
    console.error('[Malibora Sync] Aborted — no company logged in.');
    return;
  }

  if (!isOnline()) {
    setSyncStatus('offline');
    if (!silent) showToast('Offline', 'No internet connection. Showing last known data.', 'warning');
    return;
  }

  _syncInProgress = true;
  setSyncStatus('syncing');

  console.info(`[Malibora Sync] Starting for company_id=${currentCompanyId} …`);
  const t0 = performance.now();

  try {
    // ── 1. Fetch all endpoints in parallel ─────────────────
    const cid = currentCompanyId;
    const [
      trucksRes,
      driversRes,
      expensesRes,
      tripsRes,
      complianceRes,
      debtsRes,
    ] = await Promise.all([
      cloudFetch(`/api/trucks?company_id=${cid}`),
      cloudFetch(`/api/drivers?company_id=${cid}`),
      cloudFetch(`/api/expenses?company_id=${cid}`),
      cloudFetch(`/api/trips?company_id=${cid}`),
      cloudFetch(`/api/compliance?company_id=${cid}`),
      cloudFetch(`/api/debts?company_id=${cid}`),
    ]);

    // ── 2. Parse JSON (each independently, no cascade failure) ──
    const [
      cloudTrucks,
      cloudDrivers,
      cloudExpenses,
      cloudTrips,
      cloudCompliance,
      cloudDebts,
    ] = await Promise.all([
      safeJson(trucksRes,     []),
      safeJson(driversRes,    []),
      safeJson(expensesRes,   []),
      safeJson(tripsRes,      []),
      safeJson(complianceRes, []),
      safeJson(debtsRes,      []),
    ]);

    // ── 3. Map cloud data into dashboard db format ──────────

    // TRUCKS
    db.trucks = cloudTrucks.map(t => ({
      id:             t.id,
      plate:          t.plate,
      model:          t.model,
      trailers:       0,
      interval:       5000,
      odo:            0,
      lastServiceOdo: 0,
    }));

    // DRIVERS — parse "Name (Plate)" format if present
    db.drivers = cloudDrivers.map(d => {
      let name = d.name, truck = '';
      if (d.name.includes('(') && d.name.includes(')')) {
        const match = d.name.match(/^(.+?)\s*\((.+?)\)$/);
        if (match) { name = match[1].trim(); truck = match[2].trim(); }
      }
      return {
        id:        d.id,
        name,
        truck,
        cloudName: d.name,
      };
    });

    // EXPENSES → transaction records
    const expenseTxs = cloudExpenses.map(e => {
      const { cat, desc } = parseExpenseDescription(e.description);
      return {
        id:          e.id,
        type:        'expense',
        date:        new Date().toISOString().slice(0, 10),
        truck:       'N/A',
        driver:      'System',
        cat,
        desc,
        amount:      e.amount,
        isCloudSync: true,
      };
    });

    // TRIPS → transaction records + derive customers list
    const tripTxs = cloudTrips.map(t => ({
      id:          t.id,
      type:        'income',
      date:        t.date,
      truck:       t.truck,
      driver:      t.driver,
      customer:    t.customer,
      total:       t.total_price,
      paid:        t.paid_amount,
      bal:         t.balance,
      tripStatus:  t.trip_status,
      dist:        t.distance,
      cargo:       t.cargo,
      routeFull:   t.route_full,
      routeFrom:   t.route_from,
      routeTo:     t.route_to,
      paymentMethod: t.payment_method || 'Cash',
      isCloudSync: true,
    }));

    // Merge — replace cloud-sourced records, keep any locally pending ones
    db.txs = [
      ...db.txs.filter(tx => !tx.isCloudSync),  // keep local-only
      ...expenseTxs,
      ...tripTxs,
    ];

    // COMPLIANCE
    db.compliance = cloudCompliance.map(c => ({
      id:     c.id,
      type:   c.record_type,
      truck:  c.truck,
      date:   c.expiry_date,
      amount: c.amount,
      status: c.status,
      daysLeft: c.days_until_expiry ?? null,
    }));

    // DEBTS (payment records — used to offset balances)
    db.debts = cloudDebts.map(d => ({
      id:       d.id,
      date:     d.date,
      customer: d.customer,
      amount:   d.amount,
      desc:     d.description,
    }));

    // Unique customers derived from trip history
    db.customers = [
      ...new Set(tripTxs.map(t => t.customer).filter(Boolean)),
    ];

    // ── 4. Refresh UI ───────────────────────────────────────
    if (typeof renderAll === 'function') renderAll();
    if (typeof renderHistory === 'function') renderHistory();

    // ── 5. Post-sync alerts ─────────────────────────────────
    _checkComplianceAlerts(db.compliance);
    _checkPendingDebts(db.txs, db.debts);

    // ── 6. Status & timing ──────────────────────────────────
    _lastSyncAt = new Date();
    const elapsed = Math.round(performance.now() - t0);
    console.info(`[Malibora Sync] ✅ Complete in ${elapsed}ms — `
      + `${db.trucks.length} trucks, ${db.drivers.length} drivers, `
      + `${tripTxs.length} trips, ${expenseTxs.length} expenses, `
      + `${db.compliance.length} permits, ${cloudDebts.length} debts`);

    setSyncStatus('ok');
    if (!silent) showToast('Sync Complete', `Fleet data refreshed in ${elapsed}ms.`, 'success');

  } catch (err) {
    setSyncStatus('error');
    console.error('[Malibora Sync] ❌ Failed:', err);

    if (!silent) {
      if (err instanceof CloudError && err.status === 403) {
        showToast('Auth Error', 'Invalid API key. Contact support.', 'error');
      } else if (!isOnline()) {
        showToast('Offline', 'Lost internet connection.', 'warning');
        setSyncStatus('offline');
      } else {
        showToast('Sync Failed', err.message || 'Could not reach the cloud.', 'error');
      }
    }
  } finally {
    _syncInProgress = false;
  }
}


// ─────────────────────────────────────────────────────────────
// POST-SYNC ALERT CHECKS
// ─────────────────────────────────────────────────────────────

/**
 * Fire notification alerts for expiring/expired permits.
 * Only runs once per session per permit (tracked by id).
 */
const _alertedPermits = new Set();
function _checkComplianceAlerts(compliance = []) {
  compliance.forEach(c => {
    if (_alertedPermits.has(c.id)) return;
    const days = c.daysLeft;
    if (days === null) return;
    if (days < 0) {
      if (typeof addNotif === 'function')
        addNotif(`🔴 ${c.type} (${c.truck}) EXPIRED ${Math.abs(days)} day${Math.abs(days) !== 1 ? 's' : ''} ago`, 'danger');
      _alertedPermits.add(c.id);
    } else if (days <= 14) {
      if (typeof addNotif === 'function')
        addNotif(`🟡 ${c.type} (${c.truck}) expires in ${days} day${days !== 1 ? 's' : ''}`, 'warn');
      _alertedPermits.add(c.id);
    }
  });
}

/**
 * Warn if any customer has a debt older than 30 days.
 */
const _alertedDebtors = new Set();
function _checkPendingDebts(txs = [], debts = []) {
  const debtCollected = {};
  debts.forEach(d => {
    debtCollected[d.customer] = (debtCollected[d.customer] || 0) + d.amount;
  });

  const outstanding = {};
  txs.filter(t => t.type === 'income').forEach(t => {
    if (t.bal > 0) {
      outstanding[t.customer] = (outstanding[t.customer] || 0) + t.bal;
    }
  });

  Object.entries(outstanding).forEach(([customer, gross]) => {
    const net = gross - (debtCollected[customer] || 0);
    if (net > 0 && !_alertedDebtors.has(customer)) {
      if (typeof addNotif === 'function')
        addNotif(`💰 ${customer} has outstanding balance of ${net.toLocaleString()} TZS`, 'warn');
      _alertedDebtors.add(customer);
    }
  });
}


// ─────────────────────────────────────────────────────────────
// AUTO-REFRESH  (visibility-aware)
// ─────────────────────────────────────────────────────────────

/**
 * Start the auto-refresh loop.
 * Pauses when the tab is hidden; resumes when it comes back.
 */
function startAutoRefresh() {
  stopAutoRefresh(); // clear any existing timer

  const tick = () => {
    if (currentCompanyId && document.visibilityState === 'visible') {
      syncDashboardWithCloud({ silent: true });
    }
    _autoRefreshTimer = setTimeout(tick, SYNC_CONFIG.AUTO_REFRESH_MS);
  };

  _autoRefreshTimer = setTimeout(tick, SYNC_CONFIG.AUTO_REFRESH_MS);

  // Resume immediately when tab regains focus
  document.addEventListener('visibilitychange', _onVisibilityChange);

  console.info(`[Malibora Sync] Auto-refresh every ${SYNC_CONFIG.AUTO_REFRESH_MS / 1000}s.`);
}

function stopAutoRefresh() {
  if (_autoRefreshTimer) {
    clearTimeout(_autoRefreshTimer);
    _autoRefreshTimer = null;
  }
  document.removeEventListener('visibilitychange', _onVisibilityChange);
}

function _onVisibilityChange() {
  if (document.visibilityState === 'visible' && currentCompanyId) {
    // Tab came back into view — sync immediately
    syncDashboardWithCloud({ silent: true });
  }
}


// ─────────────────────────────────────────────────────────────
// ONLINE / OFFLINE EVENTS
// ─────────────────────────────────────────────────────────────

window.addEventListener('online', () => {
  console.info('[Malibora Sync] Connection restored — syncing …');
  if (typeof showToast === 'function')
    showToast('Back Online', 'Connection restored. Syncing data…', 'info');
  setSyncStatus('syncing');
  syncDashboardWithCloud({ silent: true });
});

window.addEventListener('offline', () => {
  console.warn('[Malibora Sync] Connection lost.');
  if (typeof showToast === 'function')
    showToast('Offline', 'Connection lost. Showing cached data.', 'warning');
  setSyncStatus('offline');
});


// ─────────────────────────────────────────────────────────────
// PWA SHORTCUT DEEP-LINKING
// ─────────────────────────────────────────────────────────────

/**
 * Reads ?shortcut= query param set by manifest.json shortcuts
 * and navigates to the correct section after login.
 *
 * Call this once after syncDashboardWithCloud() resolves.
 */
function handlePWAShortcut() {
  const params = new URLSearchParams(window.location.search);
  const shortcut = params.get('shortcut');
  if (!shortcut) return;

  const sectionMap = {
    'log-trip':   () => { nav2('operations'); if (typeof setMode === 'function') setMode('income'); },
    'log-expense':() => { nav2('operations'); if (typeof setMode === 'function') setMode('expense'); },
    'map':        () => nav2('map-section'),
    'compliance': () => nav2('compliance'),
  };

  const handler = sectionMap[shortcut];
  if (handler) {
    console.info(`[Malibora PWA] Shortcut activated: ${shortcut}`);
    handler();
  }
}


// ─────────────────────────────────────────────────────────────
// PWA SHARE-TARGET HANDLER (bank receipt sharing)
// ─────────────────────────────────────────────────────────────

/**
 * When a user shares a receipt image to Malibora via the OS share sheet,
 * the browser POST's to /?action=share.
 * This function reads the shared file and pre-fills the bank receipt field.
 */
async function handleShareTarget() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('action') !== 'share') return;

  try {
    const formData = await getSharedData(); // navigator.serviceWorker read
    if (!formData) return;

    const file = formData.get('receipt');
    if (!file) return;

    console.info(`[Malibora Share] Received file: ${file.name} (${file.type})`);

    // Pre-fill the bank receipt file input if it exists
    const receiptInput = document.getElementById('opBankReceipt');
    if (receiptInput) {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      receiptInput.files = dataTransfer.files;

      // Switch to operations → bank payment mode
      nav2('operations');
      if (typeof setMode === 'function') setMode('income');
      const pmEl = document.getElementById('opPaymentMethod');
      if (pmEl) { pmEl.value = 'Bank'; if (typeof togglePaymentFields === 'function') togglePaymentFields(); }

      if (typeof showToast === 'function')
        showToast('Receipt Attached', `${file.name} ready to upload.`, 'success');
    }
  } catch (err) {
    console.warn('[Malibora Share] Could not handle shared file:', err);
  }
}

async function getSharedData() {
  if (!navigator.serviceWorker?.controller) return null;
  return new Promise(resolve => {
    const channel = new MessageChannel();
    channel.port1.onmessage = e => resolve(e.data);
    navigator.serviceWorker.controller.postMessage(
      { type: 'GET_SHARE_DATA' },
      [channel.port2]
    );
    setTimeout(() => resolve(null), 3000); // timeout
  });
}


// ─────────────────────────────────────────────────────────────
// CLOUD WRITE HELPERS  (used by index.html save functions)
// ─────────────────────────────────────────────────────────────

/**
 * POST a new trip and re-sync on success.
 * Returns { ok: true, id } or throws.
 */
async function cloudSaveTrip(payload) {
  const res = await cloudFetch('/api/trips', {
    method: 'POST',
    body: JSON.stringify({ company_id: currentCompanyId, ...payload }),
  });
  const data = await safeJson(res, {});
  await syncDashboardWithCloud({ silent: true });
  return { ok: true, id: data?.data?.id };
}

/**
 * POST a new expense and re-sync on success.
 */
async function cloudSaveExpense(description, amount) {
  const res = await cloudFetch('/api/expenses', {
    method: 'POST',
    body: JSON.stringify({ company_id: currentCompanyId, description, amount }),
  });
  const data = await safeJson(res, {});
  await syncDashboardWithCloud({ silent: true });
  return { ok: true, id: data?.data?.id };
}

/**
 * PATCH a trip's status (e.g. In Transit → Completed).
 */
async function cloudUpdateTripStatus(tripId, newStatus) {
  const res = await cloudFetch(
    `/api/trips/${tripId}/status?company_id=${currentCompanyId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ trip_status: newStatus }),
    }
  );
  await syncDashboardWithCloud({ silent: true });
  return { ok: res.ok };
}

/**
 * DELETE a record from the cloud.
 */
async function cloudDeleteRecord(table, recordId) {
  await cloudFetch(
    `/api/delete-record?table=${table}&record_id=${recordId}&company_id=${currentCompanyId}`,
    { method: 'DELETE' }
  );
  await syncDashboardWithCloud({ silent: true });
}

/**
 * POST a debt payment to the cloud.
 */
async function cloudSaveDebtPayment(customer, amount) {
  const res = await cloudFetch('/api/debts', {
    method: 'POST',
    body: JSON.stringify({
      company_id:  currentCompanyId,
      date:        new Date().toISOString().slice(0, 10),
      customer,
      amount,
      description: 'Payment Collected',
    }),
  });
  const data = await safeJson(res, {});
  await syncDashboardWithCloud({ silent: true });
  return { ok: true, id: data?.data?.id };
}


// ─────────────────────────────────────────────────────────────
// LAST SYNC TIMESTAMP DISPLAY
// ─────────────────────────────────────────────────────────────

/**
 * Renders "Last synced: 2 min ago" text in an optional element.
 * Call setInterval(updateLastSyncDisplay, 30_000) after login.
 */
function updateLastSyncDisplay() {
  const el = document.getElementById('lastSyncTime');
  if (!el || !_lastSyncAt) return;
  const seconds = Math.round((Date.now() - _lastSyncAt.getTime()) / 1000);
  let label;
  if (seconds < 10)       label = 'just now';
  else if (seconds < 60)  label = `${seconds}s ago`;
  else if (seconds < 3600) label = `${Math.floor(seconds / 60)}m ago`;
  else                    label = _lastSyncAt.toLocaleTimeString();
  el.textContent = `Last synced: ${label}`;
}


// ─────────────────────────────────────────────────────────────
// PUBLIC API (everything index.html needs to call)
// ─────────────────────────────────────────────────────────────
// All functions are globally scoped (no module bundler required).
// index.html usage after login:
//
//   await syncDashboardWithCloud();   // full initial sync
//   startAutoRefresh();               // begin 60s auto-refresh
//   handlePWAShortcut();              // navigate via manifest shortcut
//   handleShareTarget();              // handle receipt share
//   setInterval(updateLastSyncDisplay, 30_000);
