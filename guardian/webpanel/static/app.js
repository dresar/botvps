/**
 * Serverinka Guardian Web Panel — SPA Logic
 * Telegram Mini App frontend for VPS control
 */

// ─── Telegram WebApp Init ───────────────────────────────────────────────────
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor('#0d1117');
  tg.setBackgroundColor('#0d1117');
}

// ─── Config ─────────────────────────────────────────────────────────────────
const BASE_URL = '';  // Same origin
const initData = tg?.initData || '';

const HEADERS = {
  'Content-Type': 'application/json',
  'X-Telegram-Init-Data': initData,
};

// ─── State ───────────────────────────────────────────────────────────────────
let cpuHistory = Array(30).fill(0);
let ramHistory = Array(30).fill(0);
let chartCpu = null, chartRam = null;
let wsMetrics = null;
let terminalCwd = '/';
let terminalHistory = [];
let terminalHistoryIdx = -1;
let currentInput = '';

// ─── Utils ───────────────────────────────────────────────────────────────────
function formatBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  if (b < 1073741824) return (b / 1048576).toFixed(1) + ' MB';
  return (b / 1073741824).toFixed(2) + ' GB';
}

function formatUptime(s) {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function pct(v) { return Math.min(100, Math.max(0, v)).toFixed(1) + '%'; }

function toast(msg, type = 'info', duration = 3000) {
  const c = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(BASE_URL + path, {
      headers: { ...HEADERS, ...(options.headers || {}) },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || res.statusText);
    }
    return await res.json();
  } catch (e) {
    console.error('API error:', path, e.message);
    throw e;
  }
}

// ─── Tab Routing ─────────────────────────────────────────────────────────────
document.getElementById('tabs').addEventListener('click', e => {
  const btn = e.target.closest('.tab');
  if (!btn) return;
  const tab = btn.dataset.tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('page-' + tab).classList.add('active');

  // Lazy load on tab switch
  if (tab === 'docker') loadDocker();
  if (tab === 'services') loadServices();
  if (tab === 'alerts') loadAlerts();
  if (tab === 'processes') loadProcesses();
  if (tab === 'terminal') focusTerminal();
});

// ─── Charts Init ─────────────────────────────────────────────────────────────
function initCharts() {
  const labels = Array(30).fill('');
  const chartCfg = (label, color, data) => ({
    type: 'line',
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderColor: color,
        backgroundColor: color + '22',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: {
          min: 0, max: 100,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#6b7280', font: { size: 10 }, callback: v => v + '%' },
        }
      }
    }
  });

  const ctxCpu = document.getElementById('chart-cpu').getContext('2d');
  const ctxRam = document.getElementById('chart-ram').getContext('2d');
  chartCpu = new Chart(ctxCpu, chartCfg('CPU %', '#3b82f6', cpuHistory));
  chartRam = new Chart(ctxRam, chartCfg('RAM %', '#8b5cf6', ramHistory));
}

function updateCharts(cpu, ram) {
  cpuHistory.push(cpu); cpuHistory.shift();
  ramHistory.push(ram); ramHistory.shift();
  chartCpu.data.datasets[0].data = [...cpuHistory];
  chartRam.data.datasets[0].data = [...ramHistory];
  chartCpu.update('none');
  chartRam.update('none');
}

// ─── WebSocket Live Metrics ───────────────────────────────────────────────────
function connectMetricsWS() {
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${wsProto}://${location.host}/ws/metrics`;
  wsMetrics = new WebSocket(wsUrl);

  wsMetrics.onopen = () => {
    document.getElementById('status-dot').style.background = 'var(--success)';
  };

  wsMetrics.onmessage = evt => {
    try {
      const d = JSON.parse(evt.data);
      updateStatCards(d);
      updateCharts(d.cpu, d.ram);
    } catch (_) {}
  };

  wsMetrics.onclose = () => {
    document.getElementById('status-dot').style.background = 'var(--danger)';
    setTimeout(connectMetricsWS, 4000);
  };

  wsMetrics.onerror = () => wsMetrics.close();
}

function updateStatCards(d) {
  const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  const setWidth = (id, pct) => { const el = document.getElementById(id); if (el) el.style.width = pct + '%'; };

  setEl('stat-cpu', pct(d.cpu));
  setWidth('bar-cpu', d.cpu);
  document.getElementById('bar-cpu').className = 'progress-fill cpu' + (d.cpu > 85 ? ' danger' : '');

  const ramPct = (d.ram_used / d.ram_total * 100);
  setEl('stat-ram', pct(ramPct));
  setEl('stat-ram-detail', formatBytes(d.ram_used) + ' / ' + formatBytes(d.ram_total));
  setWidth('bar-ram', ramPct);

  setEl('stat-load', d.load1?.toFixed(2) || '—');
  setEl('stat-load-detail', `${d.load1?.toFixed(2)} / ${d.load5?.toFixed(2)} / ${d.load15?.toFixed(2)}`);
  setWidth('bar-load', Math.min(100, (d.load1 || 0) * 25));

  setEl('uptime-badge', '⏱ ' + formatUptime(d.uptime || 0));
}

// ─── Dashboard Initial Load ───────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const data = await apiFetch('/api/metrics');
    document.getElementById('header-host').textContent = data.hostname || '—';
    document.getElementById('stat-cpu-cores').textContent = data.cpu_cores + ' cores @ ' + data.cpu_freq_mhz.toFixed(0) + ' MHz';
    document.getElementById('stat-disk').textContent = pct(data.disk_percent);
    document.getElementById('stat-disk-detail').textContent = formatBytes(data.disk_used_bytes) + ' / ' + formatBytes(data.disk_total_bytes);
    document.getElementById('bar-disk').style.width = data.disk_percent + '%';

    loadDisks();
  } catch (e) {
    toast('Gagal memuat dashboard: ' + e.message, 'error');
  }
}

async function loadDisks() {
  try {
    const disks = await apiFetch('/api/metrics/disks');
    const container = document.getElementById('disk-list');
    if (!disks.length) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">💿</div><p>Tidak ada partisi</p></div>'; return; }

    container.style = '';
    const html = `<div class="table-wrap"><table>
      <thead><tr><th>Mount</th><th>FS</th><th>Dipakai</th><th>Total</th><th>%</th></tr></thead>
      <tbody>${disks.map(d => {
        const pctVal = d.percent;
        const cls = pctVal > 90 ? 'danger' : pctVal > 75 ? 'warning' : 'disk';
        return `<tr>
          <td><code style="font-family:var(--mono);font-size:0.8rem">${d.mount_point}</code></td>
          <td style="color:var(--text-secondary)">${d.filesystem}</td>
          <td>${formatBytes(d.used_bytes)}</td>
          <td>${formatBytes(d.total_bytes)}</td>
          <td>
            <div style="display:flex;align-items:center;gap:8px;min-width:100px">
              <div class="progress-bar" style="flex:1;height:5px"><div class="progress-fill ${cls}" style="width:${pctVal}%"></div></div>
              <span style="font-size:0.78rem;color:var(--text-secondary);white-space:nowrap">${pctVal.toFixed(1)}%</span>
            </div>
          </td>
        </tr>`;
      }).join('')}</tbody>
    </table></div>`;
    container.innerHTML = html;
  } catch (e) {
    document.getElementById('disk-list').innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

// ─── Docker ──────────────────────────────────────────────────────────────────
async function loadDocker() {
  const container = document.getElementById('docker-list');
  container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  const showAll = document.getElementById('docker-show-all')?.checked ?? true;
  try {
    const containers = await apiFetch(`/api/docker?all=${showAll}`);
    if (!containers.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">🐳</div><p>Tidak ada container Docker</p></div>';
      return;
    }
    container.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>Nama</th><th>Image</th><th>Status</th><th>Ports</th><th>Dibuat</th><th>Aksi</th></tr></thead>
      <tbody>${containers.map(c => {
        const statusCls = c.state === 'running' ? 'running' : c.state === 'exited' ? 'stopped' : c.state;
        return `<tr>
          <td style="font-weight:600">${c.name}</td>
          <td style="font-size:0.78rem;color:var(--text-secondary);font-family:var(--mono)">${c.image}</td>
          <td><span class="badge ${statusCls} dot">${c.status}</span></td>
          <td style="font-size:0.75rem;font-family:var(--mono);color:var(--text-secondary)">${c.ports || '—'}</td>
          <td style="font-size:0.75rem;color:var(--text-muted)">${c.created}</td>
          <td>
            <div class="action-row">
              <button class="btn btn-success btn-sm" onclick="dockerAction('${c.id}','start','${c.name}')">▶</button>
              <button class="btn btn-danger btn-sm" onclick="dockerAction('${c.id}','stop','${c.name}')">⏹</button>
              <button class="btn btn-warning btn-sm" onclick="dockerAction('${c.id}','restart','${c.name}')">🔄</button>
              <button class="btn btn-ghost btn-sm" onclick="showDockerLogs('${c.id}','${c.name}')">📋</button>
            </div>
          </td>
        </tr>`;
      }).join('')}</tbody>
    </table></div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

async function dockerAction(id, action, name) {
  try {
    toast(`${action === 'start' ? '▶' : action === 'stop' ? '⏹' : '🔄'} ${action} "${name}"...`, 'info', 1500);
    await apiFetch(`/api/docker/${id}/${action}`, { method: 'POST' });
    toast(`✅ Container "${name}" berhasil di-${action}`, 'success');
    setTimeout(loadDocker, 1500);
  } catch (e) {
    toast(`❌ Gagal ${action} "${name}": ${e.message}`, 'error');
  }
}

async function showDockerLogs(id, name) {
  try {
    const data = await apiFetch(`/api/docker/${id}/logs?tail=100`);
    document.getElementById('log-service-input').value = '';
    document.getElementById('log-output').textContent = `=== Log Container: ${name} ===\n\n${data.logs}`;
    // Switch to logs tab
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelector('[data-tab="logs"]').classList.add('active');
    document.getElementById('page-logs').classList.add('active');
    document.getElementById('log-output').scrollTop = document.getElementById('log-output').scrollHeight;
  } catch (e) {
    toast('Gagal load log: ' + e.message, 'error');
  }
}

// ─── Services ─────────────────────────────────────────────────────────────────
async function loadServices() {
  const container = document.getElementById('services-list');
  container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  try {
    const services = await apiFetch('/api/services');
    if (!services.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚙️</div><p>Tidak ada service yang ditemukan</p></div>';
      return;
    }
    container.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>Service</th><th>Deskripsi</th><th>Status</th><th>Enabled</th><th>Aksi</th></tr></thead>
      <tbody>${services.map(s => {
        const cls = s.status === 'running' ? 'running' : s.status === 'failed' ? 'failed' : 'stopped';
        return `<tr>
          <td style="font-weight:600;font-family:var(--mono);font-size:0.82rem">${s.name}</td>
          <td style="font-size:0.78rem;color:var(--text-secondary)">${s.description.substring(0, 50)}</td>
          <td><span class="badge ${cls} dot">${s.status}</span></td>
          <td style="font-size:0.8rem">${s.enabled ? '<span style="color:var(--success)">✔</span>' : '<span style="color:var(--text-muted)">—</span>'}</td>
          <td>
            <div class="action-row">
              <button class="btn btn-success btn-sm" onclick="serviceAction('${s.name}','start')">▶</button>
              <button class="btn btn-danger btn-sm" onclick="serviceAction('${s.name}','stop')">⏹</button>
              <button class="btn btn-warning btn-sm" onclick="serviceAction('${s.name}','restart')">🔄</button>
              <button class="btn btn-ghost btn-sm" onclick="loadServiceLogs('${s.name}')">📋</button>
            </div>
          </td>
        </tr>`;
      }).join('')}</tbody>
    </table></div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

async function serviceAction(name, action) {
  try {
    toast(`${action} "${name}"...`, 'info', 1500);
    await apiFetch(`/api/services/${name}/${action}`, { method: 'POST' });
    toast(`✅ Service "${name}" berhasil di-${action}`, 'success');
    setTimeout(loadServices, 2000);
  } catch (e) {
    toast(`❌ Gagal ${action} "${name}": ${e.message}`, 'error');
  }
}

async function loadServiceLogs(name) {
  try {
    const lines = document.getElementById('log-lines-select')?.value || 100;
    const data = await apiFetch(`/api/services/${name}/logs?lines=${lines}`);
    document.getElementById('log-service-input').value = name;
    document.getElementById('log-output').textContent = data.logs || '(log kosong)';
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelector('[data-tab="logs"]').classList.add('active');
    document.getElementById('page-logs').classList.add('active');
    document.getElementById('log-output').scrollTop = document.getElementById('log-output').scrollHeight;
  } catch (e) {
    toast('Gagal load log: ' + e.message, 'error');
  }
}

async function loadLogs() {
  const svc = document.getElementById('log-service-input').value.trim();
  if (!svc) { toast('Masukkan nama service', 'error'); return; }
  document.getElementById('log-output').textContent = 'Memuat log...';
  const lines = document.getElementById('log-lines-select').value;
  try {
    const data = await apiFetch(`/api/services/${svc}/logs?lines=${lines}`);
    document.getElementById('log-output').textContent = data.logs || '(log kosong)';
    document.getElementById('log-output').scrollTop = document.getElementById('log-output').scrollHeight;
  } catch (e) {
    document.getElementById('log-output').textContent = 'Error: ' + e.message;
    toast('Gagal load log: ' + e.message, 'error');
  }
}

// ─── Alerts ───────────────────────────────────────────────────────────────────
async function loadAlerts() {
  const container = document.getElementById('alerts-list');
  container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  try {
    const alerts = await apiFetch('/api/alerts');
    if (!alerts.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">🔔</div><p>Tidak ada alert yang dikonfigurasi</p></div>';
      return;
    }
    container.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>Nama</th><th>Metrik</th><th>Threshold</th><th>Status</th><th>Aksi</th></tr></thead>
      <tbody>${alerts.map(a => `<tr>
        <td style="font-weight:600">${a.name}</td>
        <td style="font-family:var(--mono);font-size:0.8rem">${a.metric}</td>
        <td>${a.threshold}%</td>
        <td><span class="badge ${a.is_enabled ? 'running' : 'stopped'} dot">${a.is_enabled ? 'Aktif' : 'Nonaktif'}</span></td>
        <td><button class="btn btn-ghost btn-sm" onclick="toggleAlert(${a.id},'${a.name}')">${a.is_enabled ? '⏸ Nonaktifkan' : '▶ Aktifkan'}</button></td>
      </tr>`).join('')}</tbody>
    </table></div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

async function toggleAlert(id, name) {
  try {
    const data = await apiFetch(`/api/alerts/${id}/toggle`, { method: 'POST' });
    toast('✅ ' + data.message, 'success');
    loadAlerts();
  } catch (e) {
    toast('❌ ' + e.message, 'error');
  }
}

// ─── Processes ────────────────────────────────────────────────────────────────
async function loadProcesses() {
  const container = document.getElementById('processes-list');
  container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  try {
    const procs = await apiFetch('/api/metrics/processes?limit=25');
    if (!procs.length) {
      container.innerHTML = '<div class="empty-state"><p>Tidak ada proses</p></div>';
      return;
    }
    container.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>PID</th><th>Nama</th><th>User</th><th>CPU %</th><th>RAM %</th><th>Command</th></tr></thead>
      <tbody>${procs.map((p, i) => `<tr>
        <td style="font-family:var(--mono);color:var(--text-muted)">${p.pid}</td>
        <td style="font-weight:600">${p.name}</td>
        <td style="font-size:0.78rem;color:var(--text-secondary)">${p.username}</td>
        <td>
          <div style="display:flex;align-items:center;gap:6px">
            <div class="progress-bar" style="width:50px;height:4px"><div class="progress-fill ${p.cpu_percent > 50 ? 'danger' : 'cpu'}" style="width:${Math.min(100,p.cpu_percent)}%"></div></div>
            <span style="font-size:0.78rem;font-family:var(--mono)">${p.cpu_percent.toFixed(1)}%</span>
          </div>
        </td>
        <td style="font-size:0.78rem;font-family:var(--mono)">${p.memory_percent.toFixed(1)}%</td>
        <td style="font-size:0.72rem;color:var(--text-muted);font-family:var(--mono);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${p.cmdline}</td>
      </tr>`).join('')}</tbody>
    </table></div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

// ─── Terminal ─────────────────────────────────────────────────────────────────
function focusTerminal() {
  const input = document.getElementById('terminal-input');
  if (input) { setTimeout(() => input.focus(), 100); }
  if (document.getElementById('terminal-body').children.length === 0) {
    appendTerminalLine('system', '🖥️ Serverinka Terminal — Full Shell Access');
    appendTerminalLine('system', 'Ketik perintah Linux dan tekan Enter atau klik ▶ Run');
    appendTerminalLine('system', '─────────────────────────────────────────');
  }
}

function appendTerminalLine(type, text) {
  const body = document.getElementById('terminal-body');
  const line = document.createElement('div');
  line.className = 'terminal-line';
  if (type === 'prompt') {
    line.innerHTML = `<span class="terminal-prompt">$ </span><span class="terminal-cmd">${escapeHtml(text)}</span>`;
  } else if (type === 'output') {
    line.className = 'terminal-line terminal-output';
    line.textContent = text;
  } else if (type === 'error') {
    line.className = 'terminal-line terminal-error';
    line.textContent = text;
  } else if (type === 'blocked') {
    line.className = 'terminal-line terminal-blocked';
    line.textContent = '🚫 ' + text;
  } else {
    line.style.color = 'var(--text-muted)';
    line.textContent = text;
  }
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function clearTerminal() {
  document.getElementById('terminal-body').innerHTML = '';
  appendTerminalLine('system', '🧹 Terminal dibersihkan.');
}

async function sendTerminalCommand() {
  const input = document.getElementById('terminal-input');
  const cmd = input.value.trim();
  if (!cmd) return;

  input.value = '';
  terminalHistory.unshift(cmd);
  terminalHistoryIdx = -1;

  appendTerminalLine('prompt', cmd);

  try {
    const data = await apiFetch('/api/terminal/run', {
      method: 'POST',
      body: JSON.stringify({ command: cmd }),
    });

    document.getElementById('terminal-cwd').textContent = data.cwd || '/';

    if (data.blocked) {
      appendTerminalLine('blocked', `Perintah diblokir: ${data.block_reason}`);
    } else if (data.timed_out) {
      appendTerminalLine('error', 'Timeout: perintah melebihi batas waktu.');
    } else {
      if (data.stdout) appendTerminalLine('output', data.stdout);
      if (data.stderr) appendTerminalLine('error', data.stderr);
      if (!data.stdout && !data.stderr) appendTerminalLine('output', '(tidak ada output)');
    }
  } catch (e) {
    appendTerminalLine('error', 'Error: ' + e.message);
  }

  input.focus();
}

async function loadTerminalHistory() {
  try {
    const data = await apiFetch('/api/terminal/history?limit=15');
    const history = data.history || [];
    if (!history.length) { toast('Riwayat terminal kosong', 'info'); return; }
    appendTerminalLine('system', '─── Riwayat 15 Perintah Terakhir ───');
    history.forEach((h, i) => {
      const ts = new Date(h.executed_at * 1000).toLocaleTimeString('id-ID');
      appendTerminalLine('output', `${i+1}. [${ts}] ${h.exit_code === 0 ? '✅' : '❌'} ${h.command}`);
    });
  } catch (e) {
    toast('Gagal load history: ' + e.message, 'error');
  }
}

document.getElementById('terminal-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') { sendTerminalCommand(); return; }
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (terminalHistoryIdx < terminalHistory.length - 1) {
      terminalHistoryIdx++;
      e.target.value = terminalHistory[terminalHistoryIdx];
    }
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (terminalHistoryIdx > 0) {
      terminalHistoryIdx--;
      e.target.value = terminalHistory[terminalHistoryIdx];
    } else {
      terminalHistoryIdx = -1;
      e.target.value = '';
    }
  }
});

// ─── AI Chat ──────────────────────────────────────────────────────────────────
async function sendAIMessage() {
  const input = document.getElementById('ai-input');
  const btn = document.getElementById('ai-send-btn');
  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  btn.disabled = true;
  appendChatMsg('user', msg);

  const thinking = appendChatMsg('ai thinking', '⏳ Sedang berpikir...');

  try {
    const data = await apiFetch('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message: msg }),
    });
    thinking.remove();
    appendChatMsg('ai', data.response || '—');
  } catch (e) {
    thinking.remove();
    appendChatMsg('ai', '❌ Error: ' + e.message);
  }

  btn.disabled = false;
  input.focus();
}

function appendChatMsg(type, text) {
  const container = document.getElementById('ai-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg ' + type;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

document.getElementById('ai-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAIMessage(); }
});

// ─── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  initCharts();
  await loadDashboard();
  connectMetricsWS();
}

window.addEventListener('DOMContentLoaded', init);
