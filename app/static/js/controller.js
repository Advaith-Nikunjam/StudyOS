// StudyOS Controller Application JS Logic — Complete Navigation & Real Roadmap Engine

let currentTaskFilter = 'ALL';

function getLocalTodayIsoDate() {
  return new Date(Date.now() - (new Date().getTimezoneOffset() * 60000)).toISOString().split('T')[0];
}

document.addEventListener('DOMContentLoaded', () => {
  const todayStr = getLocalTodayIsoDate();
  const dateInput = document.getElementById('sprint-start-date-input');
  if (dateInput) dateInput.value = todayStr;

  const restartDateInput = document.getElementById('restart-sprint-date-input');
  if (restartDateInput) restartDateInput.value = todayStr;

  const atmDueDate = document.getElementById('atm-due-date');
  if (atmDueDate) atmDueDate.value = todayStr;

  loadDashboardData();
  setInterval(loadDashboardData, 15000); // Auto-refresh every 15s
});

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'flex';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'none';
  }
}

function openRoadmapHub(el) { if (el) setActiveNavItem(el); openModal('roadmap-modal'); if (typeof loadRoadmapView === 'function') loadRoadmapView(); }
function openDsaTrackerHub(el) { if (el) setActiveNavItem(el); openModal('dsa-modal'); }
function openMlConceptsHub(el) { if (el) setActiveNavItem(el); openModal('ml-modal'); }
function openSentinelAiHub(el) { if (el) setActiveNavItem(el); openModal('sentinelai-modal'); }
function openRevisionsHub(el) { if (el) setActiveNavItem(el); openModal('revisions-modal'); }
function openWeaknessRadarHub(el) { if (el) setActiveNavItem(el); openModal('weakness-modal'); }
function openRecoveryHub(el) { if (el) setActiveNavItem(el); openModal('recovery-modal'); }
function openExamModeHub(el) { if (el) setActiveNavItem(el); openModal('exam-mode-modal'); }
function openReportsHub(el) { if (el) setActiveNavItem(el); openModal('reports-modal'); }
function openSettingsHub(el) { if (el) setActiveNavItem(el); openModal('settings-modal'); }

let globalSprintStatus = null;
let globalMustWin = null;
let globalTasks = [];
let globalRevisions = null;
let globalWeaknesses = null;
let globalRecovery = null;
let cachedRoadmapData = null;

async function loadDashboardData() {
  try {
    const res = await fetch('/api/v1/dashboard');
    if (!res.ok) return;
    const data = await res.json();
    
    globalSprintStatus = data.sprint_status;
    globalMustWin = data.must_win;
    globalTasks = data.tasks || [];
    globalRevisions = data.revisions;
    globalWeaknesses = data.weaknesses;
    globalRecovery = data.recovery_plan;

    renderHeader(data.sprint_status);
    renderMustWin(data.must_win);
    renderMetrics(data.sprint_status);
    renderTasks(data.tasks);
    renderRevisions(data.revisions);
    renderWeaknessRadar(data.weaknesses);
    renderRecoveryPlan(data.recovery_plan);
    renderMistakes(data.mistakes);
  } catch (err) {
    console.error("Error loading dashboard data:", err);
  }
}

function setActiveNavItem(element) {
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
    item.classList.remove('active');
  });
  if (element) {
    element.classList.add('active');
  }
}

function renderHeader(status) {
  const envMode = (status.env_mode || "REAL").toUpperCase();
  
  const testBanner = document.getElementById('test-mode-banner');
  const demoBanner = document.getElementById('demo-mode-banner');
  if (testBanner) testBanner.style.display = (envMode === 'TEST') ? 'flex' : 'none';
  if (demoBanner) demoBanner.style.display = (envMode === 'DEMO') ? 'flex' : 'none';

  ['REAL', 'TEST', 'DEMO'].forEach(m => {
    const pill = document.getElementById(`env-pill-${m.toLowerCase()}`);
    if (pill) {
      if (m === envMode) {
        pill.className = "btn btn-primary";
        pill.style.fontWeight = "700";
      } else {
        pill.className = "btn btn-secondary";
        pill.style.fontWeight = "400";
      }
    }
  });

  const healthBadge = document.getElementById('health-badge');
  if (healthBadge) {
    if (!status.sprint_activated) {
      healthBadge.textContent = "SETUP PHASE";
      healthBadge.className = "badge badge-indigo";
    } else {
      healthBadge.textContent = status.health.label;
      healthBadge.className = `badge badge-${status.health.status.toLowerCase()}`;
    }
  }
  
  const modeBadge = document.getElementById('sprint-mode-badge');
  if (modeBadge) {
    modeBadge.textContent = `${status.current_mode} MODE`;
    modeBadge.className = status.exam_mode_active ? "badge badge-yellow" : "badge badge-indigo";
  }
  
  const dayBadge = document.getElementById('sprint-day-badge');
  const startSprintBtn = document.getElementById('start-sprint-btn');
  
  if (!status.sprint_activated) {
    if (dayBadge) {
      dayBadge.textContent = "PRE-SPRINT (NOT STARTED)";
      dayBadge.style.color = "var(--accent-indigo)";
    }
    if (startSprintBtn) startSprintBtn.style.display = "inline-flex";
  } else {
    if (dayBadge) {
      dayBadge.textContent = `DAY ${String(status.day_number).padStart(2, '0')} / 120`;
      dayBadge.style.color = "var(--text-primary)";
    }
    if (startSprintBtn) startSprintBtn.style.display = "none";
  }

  const sidebarPct = document.getElementById('sidebar-sprint-pct');
  const sidebarSub = document.getElementById('sidebar-sprint-sub');
  const sidebarBar = document.getElementById('sidebar-sprint-bar');
  if (sidebarPct) sidebarPct.textContent = `${status.dsa.percentage || 6}%`;
  if (sidebarSub) sidebarSub.textContent = `${status.day_number || 7} / 120 Days Completed`;
  if (sidebarBar) sidebarBar.style.width = `${status.dsa.percentage || 6}%`;
}

function renderMustWin(mustWin) {
  const textEl = document.getElementById('ctrl-must-win-text');
  const badgeEl = document.getElementById('ctrl-must-win-badge');
  if (!mustWin || !textEl) return;

  textEl.textContent = mustWin.text || "Master Arrays & complete SentinelAI data ingestion (V0.1)";
  
  if (badgeEl) {
    if (mustWin.result === 'achieved') {
      badgeEl.textContent = "ACHIEVED 🎉";
      badgeEl.className = "badge badge-green";
    } else if (mustWin.result === 'partially_achieved') {
      badgeEl.textContent = "PARTIAL ⚡";
      badgeEl.className = "badge badge-yellow";
    } else if (mustWin.result === 'missed') {
      badgeEl.textContent = "MISSED ❌";
      badgeEl.className = "badge badge-red";
    } else {
      badgeEl.textContent = "PENDING";
      badgeEl.className = "badge badge-indigo";
    }
  }
}

function renderMetrics(status) {
  const dsaVal = document.getElementById('dsa-solved-val');
  const dsaTarget = document.getElementById('dsa-target-text');
  if (dsaVal) dsaVal.textContent = status.dsa.solved_independent;
  if (dsaTarget) dsaTarget.textContent = `Target: ${status.dsa.target} problems (${status.dsa.percentage}%)`;
  
  const conceptsVal = document.getElementById('concepts-mastered-val');
  const conceptsTotal = document.getElementById('concepts-total-text');
  if (conceptsVal) conceptsVal.textContent = status.concepts.mastered;
  if (conceptsTotal) conceptsTotal.textContent = `Mastered (${status.concepts.percentage}%)`;
  
  const sentinelVer = document.getElementById('sentinel-ver-val');
  const sentinelPct = document.getElementById('sentinel-pct-text');
  if (sentinelVer) sentinelVer.textContent = status.sentinelai.active_version;
  if (sentinelPct) sentinelPct.textContent = `${status.sentinelai.percentage}% Complete`;
  
  const weekVal = document.getElementById('sprint-week-val');
  const monthText = document.getElementById('sprint-month-text');
  
  if (!status.sprint_activated) {
    if (weekVal) weekVal.textContent = "Pre-Sprint";
    if (monthText) monthText.textContent = "StudyOS Setup & Testing Phase";
  } else {
    if (weekVal) weekVal.textContent = `Week ${status.current_week}`;
    if (monthText) monthText.textContent = `Week ${status.current_week} • ${status.current_week_info.title}`;
  }
}

function filterTasks(cat, btn) {
  currentTaskFilter = cat;
  document.querySelectorAll('.task-filter-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderTasks(globalTasks);
}

function renderTasks(tasks) {
  tasks = tasks || [];
  const container = document.getElementById('today-tasks-list');
  const progressText = document.getElementById('task-progress-text');
  const progressFill = document.getElementById('task-progress-fill');

  const completed = tasks.filter(t => t.status === 'completed').length;
  const total = tasks.length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  
  if (progressText) progressText.textContent = `${total} Tasks Scheduled • ${completed}/${total} Done`;
  if (progressFill) progressFill.style.width = `${pct}%`;

  const ringVal = document.getElementById('must-win-ring-pct');
  const ringCircle = document.getElementById('must-win-ring-circle');
  if (ringVal) ringVal.textContent = `${pct}%`;
  if (ringCircle) {
    const dashOffset = 251.2 - (251.2 * pct / 100);
    ringCircle.setAttribute('stroke-dashoffset', dashOffset);
  }
  
  if (!container) return;

  let filtered = tasks;
  if (currentTaskFilter !== 'ALL') {
    if (currentTaskFilter === 'Assignment') {
      filtered = tasks.filter(t => t.category === 'Assignment');
    } else if (currentTaskFilter === 'College') {
      filtered = tasks.filter(t => t.category === 'College');
    } else if (currentTaskFilter === 'DSA') {
      filtered = tasks.filter(t => t.category === 'DSA');
    } else if (currentTaskFilter === 'ML') {
      filtered = tasks.filter(t => t.category === 'ML' || t.category === 'DL' || t.category === 'ComputerVision');
    } else if (currentTaskFilter === 'SentinelAI') {
      filtered = tasks.filter(t => t.category === 'SentinelAI');
    }
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); font-size:0.9rem; padding:1.25rem 0.5rem; text-align:center; background:var(--bg-surface); border-radius:var(--radius-sm); border:1px dashed var(--border-subtle);">No ${currentTaskFilter === 'ALL' ? '' : currentTaskFilter} tasks scheduled. Click <strong>'➕ Add Task / Assignment'</strong> above or type below to add one!</div>`;
    return;
  }

  const categoryColors = {
    'Assignment': '#F59E0B',
    'College': '#EAB308',
    'DSA': 'var(--accent-blue)',
    'ML': 'var(--status-green)',
    'DL': 'var(--accent-purple)',
    'ComputerVision': 'var(--accent-cyan)',
    'SentinelAI': 'var(--status-orange)',
    'General': 'var(--text-secondary)'
  };

  const categoryIcons = {
    'Assignment': '📝',
    'College': '🎓',
    'DSA': '</>',
    'ML': '🧠',
    'DL': '⚡',
    'SentinelAI': '🛡️',
    'General': '📌'
  };

  container.innerHTML = filtered.map((t, idx) => {
    const numStr = String(idx + 1).padStart(2, '0');
    const color = categoryColors[t.category] || 'var(--accent-indigo)';
    const icon = categoryIcons[t.category] || '📌';
    const isDone = t.status === 'completed';

    return `
      <div class="task-row-item" style="display:flex; align-items:center; gap:0.75rem; padding:0.65rem 0.85rem; background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); margin-bottom:0.5rem; ${isDone ? 'opacity:0.65; border-left:4px solid var(--status-green);' : ''}">
        <input type="checkbox" ${isDone ? 'checked' : ''} onchange="toggleTaskStatus(${t.id}, this.checked)" style="width:18px; height:18px; cursor:pointer; accent-color:var(--status-green);">
        <div class="task-badge-num" style="${isDone ? 'background:rgba(16,185,129,0.15); color:var(--status-green);' : ''}">${numStr}</div>
        <div class="task-info-col" style="flex:1;">
          <div>
            <span class="task-cat-tag" style="color:${color}; font-weight:700; font-size:0.8rem;">[${icon} ${t.category}]</span> 
            <strong style="${isDone ? 'text-decoration:line-through; color:var(--text-muted);' : 'color:var(--text-primary);'}">${t.title}</strong>
          </div>
          <div class="task-sub-desc" style="font-size:0.78rem; color:var(--text-secondary);">${t.notes || 'Scheduled Study Task'}</div>
        </div>
        <div style="font-family:var(--font-mono); font-size:0.82rem; color:var(--accent-cyan); white-space:nowrap;">⏱️ ${t.estimated_minutes}m</div>
        <button onclick="deleteTask(${t.id})" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:0.9rem; padding:0.25rem 0.45rem; border-radius:4px; transition:all 0.15s ease;" title="Delete Task" onmouseover="this.style.color='var(--status-red)'" onmouseout="this.style.color='var(--text-muted)'">🗑️</button>
      </div>
    `;
  }).join('');
}

function renderRevisions(revisions) {
  const container = document.getElementById('ctrl-revisions-list');
  const countText = document.getElementById('revisions-count-text');
  
  if (!revisions) return;
  const dueToday = revisions.today || [];
  const overdue = revisions.overdue || [];
  
  if (countText) countText.textContent = `${dueToday.length} Due Today (${overdue.length} Overdue)`;
  if (!container) return;

  if (dueToday.length === 0 && overdue.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted);">Zero revisions due today. All concepts up to date!</div>`;
    return;
  }

  let html = '';
  overdue.forEach(r => {
    html += `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0.75rem; background:rgba(239, 68, 68, 0.1); border-left:3px solid var(--status-red); border-radius:var(--radius-sm);">
        <div>
          <strong style="color:var(--status-red);">⚠️ [${r.domain}] ${r.concept_name}</strong>
          <span style="font-size:0.75rem; color:var(--text-muted); margin-left:0.5rem;">Rev #${r.revision_number} (${r.days_overdue}d overdue)</span>
        </div>
        <button class="btn btn-secondary" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick="completeRevision(${r.id})">Mark Done</button>
      </div>
    `;
  });

  dueToday.forEach(r => {
    html += `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0.75rem; background:var(--bg-surface); border-left:3px solid var(--accent-indigo); border-radius:var(--radius-sm);">
        <div>
          <strong>[${r.domain}] ${r.concept_name}</strong>
          <span style="font-size:0.75rem; color:var(--text-muted); margin-left:0.5rem;">Rev #${r.revision_number}</span>
        </div>
        <button class="btn btn-primary" style="padding:0.2rem 0.5rem; font-size:0.75rem;" onclick="completeRevision(${r.id})">Complete</button>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderWeaknessRadar(weaknesses) {
  const container = document.getElementById('ctrl-weakness-list');
  if (!container) return;

  if (!weaknesses || !weaknesses.top_weaknesses || weaknesses.top_weaknesses.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted);">Zero active weaknesses recorded. Excellent mastery!</div>`;
    return;
  }

  const colors = {'critical': 'var(--status-red)', 'high': 'var(--status-orange)', 'medium': 'var(--status-yellow)', 'low': 'var(--status-green)'};

  container.innerHTML = weaknesses.top_weaknesses.slice(0, 4).map(w => {
    const color = colors[w.severity] || 'var(--accent-cyan)';
    const pct = Math.min(w.mistake_count * 20, 100);
    return `
      <div>
        <div style="display:flex; justify-content:space-between; margin-bottom:0.15rem;">
          <span>${w.topic}</span>
          <span style="color:${color}; font-weight:700;">${pct}%</span>
        </div>
        <div class="progress-bar-bg" style="height:4px; margin:0;"><div class="progress-bar-fill" style="width:${pct}%; background:${color};"></div></div>
      </div>
    `;
  }).join('');
}

function renderRecoveryPlan(recovery) {
  const container = document.getElementById('ctrl-recovery-box');
  const badge = document.getElementById('ctrl-recovery-badge');
  if (!recovery) return;

  if (recovery.recovery_mode_active) {
    if (badge) {
      badge.textContent = "RECOVERY ACTIVE";
      badge.className = "badge badge-yellow";
    }
    if (container) {
      container.innerHTML = `
        <div style="color:var(--status-yellow); font-weight:600; margin-bottom:0.25rem;">⚠️ Backlog: ${recovery.total_missed_hours} hrs</div>
        <div style="font-size:0.8rem; color:var(--text-secondary);">Today Workload: <strong>${recovery.total_workload_hours}h</strong> (Est. ${recovery.days_to_clear_backlog} days to clear)</div>
      `;
    }
  } else {
    if (badge) {
      badge.textContent = "SCHEDULE NORMAL";
      badge.className = "badge badge-green";
    }
    if (container) {
      container.innerHTML = `
        <strong style="color:var(--status-green);">You are on track!</strong><br>
        No pending backlog. Great consistency!
      `;
    }
  }
}

function renderMistakes(mistakes) {
  const container = document.getElementById('mistakes-list');
  if (!container || !mistakes) return;
  const unresolved = mistakes.filter(m => !m.resolved);
  
  if (unresolved.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted);">No unresolved mistakes recorded.</div>`;
    return;
  }
  
  container.innerHTML = unresolved.slice(0, 4).map(m => `
    <div style="color:var(--status-red); font-size:0.8rem;">⚠️ ${m.description} (x${m.count})</div>
  `).join('');
}

// Modal Handlers & Side Navigation Views
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = 'flex';
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = 'none';
}

// ==========================================
// REAL ROADMAP HUB ENGINE (FETCHEED LIVE FROM DB)
// ==========================================
async function openRoadmapHub(el) {
  if (el) setActiveNavItem(el);
  openModal('roadmap-modal');
  
  const container = document.getElementById('roadmap-weeks-list');
  if (!container) return;
  
  container.innerHTML = `<div style="color:var(--text-muted); font-size:0.9rem;">Loading full 16-week database roadmap...</div>`;
  
  try {
    const res = await fetch('/api/v1/roadmap');
    if (!res.ok) throw new Error("Failed to load roadmap");
    const data = await res.json();
    cachedRoadmapData = data;
    
    renderRoadmapWeeks(data.weeks, 0); // 0 = all
  } catch (err) {
    console.error("Roadmap fetch error:", err);
    container.innerHTML = `<div style="color:var(--status-red);">Error loading roadmap from backend database.</div>`;
  }
}

function renderRoadmapWeeks(weeks, monthFilter = 0) {
  const container = document.getElementById('roadmap-weeks-list');
  if (!container) return;

  const currentWeek = globalSprintStatus ? globalSprintStatus.current_week : 2;
  
  let filtered = weeks;
  if (monthFilter > 0) {
    filtered = weeks.filter(w => w.month_number === monthFilter);
  }

  container.innerHTML = filtered.map(w => {
    const isCurrent = w.week_number === currentWeek;
    const isPast = w.week_number < currentWeek;

    let borderStyle = 'border:1px solid var(--border-subtle);';
    let statusBadge = `<span class="badge" style="background:var(--bg-primary); color:var(--text-muted);">UPCOMING</span>`;
    
    if (isCurrent) {
      borderStyle = 'border:2px solid var(--accent-indigo); background:rgba(99,102,241,0.08);';
      statusBadge = `<span class="badge badge-indigo">CURRENT ACTIVE WEEK</span>`;
    } else if (isPast) {
      borderStyle = 'border:1px solid var(--status-green); background:rgba(16,185,129,0.04);';
      statusBadge = `<span class="badge badge-green">COMPLETED</span>`;
    }

    return `
      <div style="background:var(--bg-card); ${borderStyle} border-radius:var(--radius-md); padding:1rem 1.25rem; margin-bottom:0.85rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
          <div>
            <strong style="font-family:var(--font-display); font-size:1.1rem; color:var(--text-primary);">${w.title}</strong>
            <span style="font-size:0.75rem; color:var(--text-muted); margin-left:0.5rem; font-family:var(--font-mono);">WEEK ${String(w.week_number).padStart(2,'0')} • MONTH ${w.month_number}</span>
          </div>
          ${statusBadge}
        </div>
        
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:0.75rem; font-size:0.82rem; margin-top:0.5rem;">
          <div style="background:var(--bg-surface); padding:0.6rem 0.75rem; border-radius:var(--radius-sm);">
            <div style="font-size:0.7rem; font-weight:700; color:var(--accent-blue); text-transform:uppercase; margin-bottom:0.25rem;">&lt;/&gt; DSA Focus (${w.dsa_target_count} Target)</div>
            <div style="color:var(--text-primary); font-weight:500;">${w.focus_dsa}</div>
          </div>
          <div style="background:var(--bg-surface); padding:0.6rem 0.75rem; border-radius:var(--radius-sm);">
            <div style="font-size:0.7rem; font-weight:700; color:var(--status-green); text-transform:uppercase; margin-bottom:0.25rem;">🧠 ML / DL Focus</div>
            <div style="color:var(--text-primary); font-weight:500;">${w.focus_ml_dl}</div>
          </div>
          <div style="background:var(--bg-surface); padding:0.6rem 0.75rem; border-radius:var(--radius-sm);">
            <div style="font-size:0.7rem; font-weight:700; color:var(--accent-purple); text-transform:uppercase; margin-bottom:0.25rem;">🛡️ SentinelAI Focus</div>
            <div style="color:var(--text-primary); font-weight:500;">${w.focus_sentinelai}</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function filterRoadmapMonth(monthNum) {
  if (!cachedRoadmapData || !cachedRoadmapData.weeks) return;
  
  // Highlight active filter pill
  [0, 1, 2, 3, 4].forEach(m => {
    const btn = document.getElementById(`rm-filter-btn-${m}`);
    if (btn) btn.className = (m === monthNum) ? "btn btn-primary" : "btn btn-secondary";
  });

  renderRoadmapWeeks(cachedRoadmapData.weeks, monthNum);
}

// Hub Openers
function openDsaTrackerHub(el) { if (el) setActiveNavItem(el); openModal('dsa-tracker-modal'); }
function openMlConceptsHub(el) { if (el) setActiveNavItem(el); openModal('ml-concepts-modal'); }
function openSentinelAiHub(el) { if (el) setActiveNavItem(el); openModal('sentinelai-modal'); }
function openRevisionsHub(el) {
  if (el) setActiveNavItem(el);
  renderRevisionsModalList(globalRevisions);
  openModal('revisions-modal');
}

function renderRevisionsModalList(revisions) {
  const container = document.getElementById('revisions-modal-list');
  if (!container) return;
  if (!revisions) {
    container.innerHTML = `<div style="color:var(--text-muted);">No revision data loaded.</div>`;
    return;
  }
  const dueToday = revisions.today || [];
  const overdue = revisions.overdue || [];
  if (dueToday.length === 0 && overdue.length === 0) {
    container.innerHTML = `<div style="color:var(--status-green); padding:0.5rem 0;">🎉 Zero revisions due today. All concepts up to date!</div>`;
    return;
  }
  let html = '<div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1rem;">';
  overdue.forEach(r => {
    html += `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:0.6rem 0.85rem; background:rgba(239, 68, 68, 0.1); border-left:3px solid var(--status-red); border-radius:var(--radius-sm);">
        <div>
          <strong style="color:var(--status-red);">⚠️ [${r.domain}] ${r.concept_name}</strong>
          <div style="font-size:0.75rem; color:var(--text-muted);">Rev #${r.revision_number} (${r.days_overdue}d overdue)</div>
        </div>
        <button class="btn btn-secondary" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="completeRevision(${r.id}); closeModal('revisions-modal');">Complete</button>
      </div>`;
  });
  dueToday.forEach(r => {
    html += `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:0.6rem 0.85rem; background:var(--bg-surface); border-left:3px solid var(--accent-indigo); border-radius:var(--radius-sm);">
        <div>
          <strong>[${r.domain}] ${r.concept_name}</strong>
          <div style="font-size:0.75rem; color:var(--text-muted);">Rev #${r.revision_number}</div>
        </div>
        <button class="btn btn-primary" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="completeRevision(${r.id}); closeModal('revisions-modal');">Complete</button>
      </div>`;
  });
  html += '</div>';
  container.innerHTML = html;
}
function openWeaknessRadarHub(el) { if (el) setActiveNavItem(el); openModal('weakness-modal'); }
function openRecoveryHub(el) { if (el) setActiveNavItem(el); openModal('recovery-modal'); }
function openExamModeHub(el) { if (el) setActiveNavItem(el); openModal('exam-mode-modal'); }
function openReportsHub(el) { if (el) setActiveNavItem(el); openModal('reports-modal'); }
function openSettingsHub(el) { if (el) setActiveNavItem(el); openModal('settings-modal'); }

async function toggleExamMode() {
  const enable = !(globalSprintStatus && globalSprintStatus.exam_mode_active);
  const res = await fetch('/api/v1/mode/exam', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enable})
  });
  const data = await res.json();
  alert(`${data.message}\n\nExam Mode Logic: Allocates 120m for College Exam Prep, maintains lightweight DSA retention, reduces recovery cap to 0.5h, and protects academic performance.`);
  loadDashboardData();
}

async function handleLogDsaSubmit(e) {
  e.preventDefault();
  const problem_name = document.getElementById('dsa-prob-name').value;
  const topic = document.getElementById('dsa-prob-topic').value;
  const difficulty = document.getElementById('dsa-prob-diff').value;
  const time_taken_mins = parseInt(document.getElementById('dsa-prob-time').value) || 30;

  const res = await fetch('/api/v1/dsa/log', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({problem_name, topic, difficulty, time_taken_mins, independent_solve: true})
  });
  const data = await res.json();
  alert(data.message);
  closeModal('dsa-tracker-modal');
  loadDashboardData();
}

async function handleLogConceptSubmit(e) {
  e.preventDefault();
  const conceptName = document.getElementById('concept-name-input').value;
  if (!conceptName) return;

  await fetch('/api/v1/jarvis/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_input: `mastered concept: ${conceptName}`})
  });
  
  alert(`Mastered Concept '${conceptName}' logged successfully!`);
  closeModal('ml-concepts-modal');
  loadDashboardData();
}

async function completeRevision(revisionId) {
  const res = await fetch('/api/v1/revisions/complete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({revision_id: revisionId, confidence_rating: 'high'})
  });
  const data = await res.json();
  alert(data.message);
  loadDashboardData();
}

async function promptUpdateMustWin() {
  const currentText = document.getElementById('ctrl-must-win-text').textContent;
  const newText = prompt("Enter Today's Must Win (Primary Outcome):", currentText);
  if (newText && newText.trim()) {
    await fetch('/api/v1/must-win', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({must_win_text: newText.trim()})
    });
    loadDashboardData();
  }
}

async function handleWeeklyReviewSubmit(e) {
  e.preventDefault();
  const q1 = document.getElementById('wr-q1').value;
  const q2 = document.getElementById('wr-q2').value;
  const q3 = document.getElementById('wr-q3').value;
  const q4 = document.getElementById('wr-q4').value;

  const res = await fetch('/api/v1/weekly-review', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      q1_missed_work_cause: q1,
      q2_biggest_difficulty: q2,
      q3_next_week_improvements: q3,
      q4_next_week_priority: q4
    })
  });
  const data = await res.json();
  alert(`Weekly Review Saved Successfully!\nReport file: ${data.report_file}`);
  closeModal('weekly-review-modal');
  loadDashboardData();
}

async function requestEnvSwitch(targetMode) {
  if (targetMode === 'REAL') {
    openModal('real-mode-confirm-modal');
    return;
  }
  
  const res = await fetch('/api/v1/env/switch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({env_mode: targetMode, confirmed: true})
  });
  const data = await res.json();
  alert(data.message);
  loadDashboardData();
}

async function confirmSwitchToRealMode() {
  closeModal('real-mode-confirm-modal');
  const res = await fetch('/api/v1/env/switch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({env_mode: 'REAL', confirmed: true})
  });
  const data = await res.json();
  alert(data.message);
  loadDashboardData();
}

async function handleStartDaySubmit(e) {
  e.preventDefault();
  const must_win_text = document.getElementById('sd-must-win').value;
  const available_hours = parseFloat(document.getElementById('sd-hours').value) || 4.0;
  const constraints = document.getElementById('sd-constraints').value;
  const energy_level = document.getElementById('sd-energy').value;

  const res = await fetch('/api/v1/day/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({must_win_text, available_hours, constraints, energy_level})
  });
  const data = await res.json();
  alert(data.message || "Day Start successfully logged.");
  closeModal('start-day-modal');
  loadDashboardData();
}

async function handleEndDaySubmit(e) {
  e.preventDefault();
  const must_win_result = document.getElementById('ed-must-win-result').value;
  const focused_hours = parseFloat(document.getElementById('ed-hours').value) || 4.0;
  const what_learned = document.getElementById('ed-learned').value;
  const mistakes_noted = document.getElementById('ed-mistakes').value;

  const res = await fetch('/api/v1/day/end', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({must_win_result, focused_hours, what_learned, mistakes_noted})
  });
  const data = await res.json();
  alert(`${data.message}\nDaily Report: ${data.report_file || 'Saved'}`);
  closeModal('end-day-modal');
  loadDashboardData();
}

async function handleStartSprintSubmit(e) {
  e.preventDefault();
  const startDateStr = document.getElementById('sprint-start-date-input').value;
  if (!startDateStr) return;
  
  const res = await fetch('/api/v1/sprint/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({start_date: startDateStr})
  });
  
  const data = await res.json();
  if (!res.ok) {
    if (res.status === 400 && data.detail && data.detail.includes("ALREADY activated")) {
      if (confirm("120-Day Sprint is ALREADY active!\n\nWould you like to RESTART your sprint timeline from Day 01?")) {
        closeModal('start-sprint-modal');
        openRestartSprintModal();
      }
      return;
    }
    alert(`Error activating sprint: ${data.detail || data.message}`);
    return;
  }
  
  alert(`${data.message}\nStart Date: ${data.actual_start_date}\nEnd Date (120 Days): ${data.actual_end_date}`);
  closeModal('start-sprint-modal');
  loadDashboardData();
}

function openRestartSprintModal() {
  closeModal('settings-modal');
  const dateInput = document.getElementById('restart-sprint-date-input');
  if (dateInput) dateInput.value = getLocalTodayIsoDate();
  openModal('restart-sprint-modal');
}

async function handleRestartSprintSubmit(e) {
  e.preventDefault();
  const startDateStr = document.getElementById('restart-sprint-date-input').value;
  if (!startDateStr) return;
  
  if (!confirm(`Are you sure you want to RESTART your 120-Day Sprint starting on ${startDateStr}? This will reset your timeline to Day 01.`)) return;

  const res = await fetch('/api/v1/sprint/restart', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({start_date: startDateStr})
  });
  
  const data = await res.json();
  if (!res.ok) {
    alert(`Error restarting sprint: ${data.detail || data.message}`);
    return;
  }
  
  alert(`${data.message}\nNew Start Date (Day 01): ${data.actual_start_date}\nNew End Date (120 Days): ${data.actual_end_date}`);
  closeModal('restart-sprint-modal');
  loadDashboardData();
}

async function resetTestData() {
  if (!confirm("Are you sure you want to reset all TEST data and test report files? Real data will remain untouched.")) return;
  const res = await fetch('/api/v1/test/reset', {method: 'POST'});
  const data = await res.json();
  alert(data.message);
  loadDashboardData();
}

async function resetDemoData() {
  if (!confirm("Are you sure you want to reset DEMO mode back to the curated showcase state?")) return;
  const res = await fetch('/api/v1/demo/reset', {method: 'POST'});
  const data = await res.json();
  alert(data.message);
  loadDashboardData();
}

async function toggleTaskStatus(taskId, isCompleted) {
  const newStatus = isCompleted ? 'completed' : 'planned';
  await fetch(`/api/v1/tasks/${taskId}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({status: newStatus})
  });
  loadDashboardData();
}

async function handleQuickTaskAdd(e) {
  e.preventDefault();
  const title = document.getElementById('quick-task-title').value.trim();
  const category = document.getElementById('quick-task-cat').value;
  const mins = parseInt(document.getElementById('quick-task-mins').value) || 45;
  if (!title) return;

  const todayStr = new Date().toISOString().split('T')[0];

  const res = await fetch('/api/v1/tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      title,
      category,
      priority: 'medium',
      estimated_minutes: mins,
      due_date: todayStr
    })
  });

  if (res.ok) {
    document.getElementById('quick-task-title').value = '';
    loadDashboardData();
  } else {
    alert("Error creating task. Please try again.");
  }
}

async function handleAddTaskModalSubmit(e) {
  e.preventDefault();
  const title = document.getElementById('atm-title').value.trim();
  const category = document.getElementById('atm-category').value;
  const priority = document.getElementById('atm-priority').value;
  const mins = parseInt(document.getElementById('atm-mins').value) || 45;
  const due_date = document.getElementById('atm-due-date').value || new Date().toISOString().split('T')[0];
  const notes = document.getElementById('atm-notes').value.trim();

  if (!title) return;

  const res = await fetch('/api/v1/tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      title,
      category,
      priority,
      estimated_minutes: mins,
      due_date,
      notes
    })
  });

  if (res.ok) {
    closeModal('add-task-modal');
    document.getElementById('atm-title').value = '';
    document.getElementById('atm-notes').value = '';
    loadDashboardData();
  } else {
    alert("Failed to create task/assignment.");
  }
}

async function deleteTask(taskId) {
  if (!confirm("Are you sure you want to delete this task/assignment?")) return;
  const res = await fetch(`/api/v1/tasks/${taskId}`, {
    method: 'DELETE'
  });
  if (res.ok) {
    loadDashboardData();
  } else {
    alert("Failed to delete task.");
  }
}

async function handleJarvisSubmit(e) {
  e.preventDefault();
  const inputEl = document.getElementById('jarvis-input');
  const userText = inputEl.value.trim();
  if (!userText) return;
  
  appendJarvisMessage('User', userText);
  inputEl.value = '';
  
  const res = await fetch('/api/v1/jarvis/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_input: userText})
  });
  
  const data = await res.json();
  if (data.requires_confirmation) {
    appendJarvisMessage('JARVIS [SAFETY PREVIEW]', `⚠️ ${data.message}\n${data.preview}`);
  } else {
    appendJarvisMessage('JARVIS', `✅ ${data.message}`);
    loadDashboardData();
  }
}

function appendJarvisMessage(sender, text) {
  const log = document.getElementById('jarvis-chat-log');
  if (!log) return;
  log.style.display = 'block';
  const msgDiv = document.createElement('div');
  msgDiv.innerHTML = `<strong style="color:var(--accent-cyan);">${sender}:</strong> ${text}`;
  log.appendChild(msgDiv);
  log.scrollTop = log.scrollHeight;
}

async function handleAddMistakeSubmit(e) {
  e.preventDefault();
  const mistake_type = document.getElementById('mistake-type-input').value;
  const description = document.getElementById('mistake-desc-input').value;
  
  await fetch('/api/v1/jarvis/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_input: `Add mistake ${mistake_type}: ${description}`})
  });
  
  closeModal('weakness-modal');
  loadDashboardData();
}

async function toggleWallSleep() {
  await fetch('/api/v1/wall/sleep', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({sleep: true})
  });
  alert("Wall Display explicit Sleep Mode activated!");
}

async function triggerManualBackup() {
  const res = await fetch('/api/v1/backup/create', {method: 'POST'});
  const data = await res.json();
  alert(`Backup Created Successfully!\n• SQLite: ${data.sqlite_backup}\n• JSON Export: ${data.json_export}`);
}

// ==========================================
// TIMETABLE & VOICE ANNOUNCEMENT ENGINE
// ==========================================
let cachedTimetableSlots = [];
let voiceAnnouncementsEnabled = true;
let spokenSlotsLog = new Set();
let timetableDayFilter = 'All';

function toggleVoiceAnnouncements() {
  voiceAnnouncementsEnabled = !voiceAnnouncementsEnabled;
  const btn = document.getElementById('voice-toggle-btn');
  if (btn) {
    btn.textContent = voiceAnnouncementsEnabled ? "🔊 Voice: ON" : "🔇 Voice: OFF";
    btn.style.color = voiceAnnouncementsEnabled ? "#A5B4FC" : "#64748B";
  }
}

function speakAnnouncement(text) {
  if (!voiceAnnouncementsEnabled || !('speechSynthesis' in window)) return;
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  } catch (err) {
    console.warn("Web Speech Error:", err);
  }
}

async function openTimetableHub(el) {
  if (el) setActiveNavItem(el);
  openModal('timetable-modal');
  await loadTimetableSlots();
}

async function loadTimetableSlots() {
  const listContainer = document.getElementById('timetable-slots-list');
  if (listContainer) listContainer.innerHTML = `<div style="color:var(--text-muted); padding:1rem;">Loading timetable schedule...</div>`;

  try {
    const res = await fetch('/api/v1/timetable');
    if (!res.ok) throw new Error("Failed to fetch timetable");
    const data = await res.json();
    cachedTimetableSlots = data.slots || [];

    const urlInput = document.getElementById('cal-ics-url-input');
    const statusText = document.getElementById('cal-sync-status-text');
    if (data.calendar_config) {
      if (urlInput && data.calendar_config.ics_url) urlInput.value = data.calendar_config.ics_url;
      if (statusText && data.calendar_config.last_synced_at) {
        statusText.textContent = `Last Synced: ${new Date(data.calendar_config.last_synced_at).toLocaleTimeString()}`;
        statusText.style.color = "var(--status-green)";
      }
    }

    renderTimetableSlots(cachedTimetableSlots, timetableDayFilter);
    renderTimetableMatrix(cachedTimetableSlots);
  } catch (err) {
    console.error("Timetable load error:", err);
  }
}

function filterTimetableDay(day, btnEl) {
  timetableDayFilter = day;
  document.querySelectorAll('.tt-day-pill').forEach(b => {
    b.className = "btn btn-secondary tt-day-pill";
  });
  if (btnEl) btnEl.className = "btn btn-primary tt-day-pill";
  renderTimetableSlots(cachedTimetableSlots, day);
}

function renderTimetableSlots(slots, dayFilter) {
  const container = document.getElementById('timetable-slots-list');
  if (!container) return;

  let filtered = slots;
  if (dayFilter !== 'All') {
    filtered = slots.filter(s => s.day_of_week === dayFilter || s.day_of_week === 'Daily');
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); font-size:0.85rem; padding:1.5rem; text-align:center; background:var(--bg-card); border-radius:var(--radius-sm);">No schedule slots found for ${dayFilter}. Add one below or sync your Google Calendar feed!</div>`;
    return;
  }

  const categoryBadges = {
    'Exam': 'badge-red-vivid',
    'Assignment': 'badge-yellow-vivid',
    'College': 'badge-indigo',
    'DSA': 'badge-cyan',
    'ML': 'badge-green',
    'Break': 'badge-yellow'
  };

  container.innerHTML = filtered.map(s => {
    const badgeClass = categoryBadges[s.category] || 'badge-indigo';
    const isBlocked = s.is_blocked;
    const isSynced = s.source === 'ical_sync' || s.source === 'google_cal';

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-card); border:1px solid var(--border-bright); border-radius:var(--radius-sm); padding:0.75rem 1rem;">
        <div style="display:flex; align-items:center; gap:0.85rem;">
          <div style="font-family:var(--font-mono); font-weight:700; font-size:0.88rem; color:var(--accent-cyan); min-width:90px;">
            ${s.start_time} - ${s.end_time}
          </div>
          <div>
            <div style="font-weight:700; font-size:0.95rem; color:var(--text-primary);">
              ${s.title}
              ${isBlocked ? '<span style="font-size:0.68rem; color:var(--status-yellow); margin-left:0.5rem; border:1px solid rgba(245,158,11,0.4); padding:0.1rem 0.4rem; border-radius:4px;">TIME BLOCKED</span>' : ''}
              ${isSynced ? '<span style="font-size:0.68rem; color:var(--accent-indigo); margin-left:0.3rem;">🔗 SYNCED</span>' : ''}
            </div>
            <div style="font-size:0.78rem; color:var(--text-muted);">${s.day_of_week} ${s.date_str ? '(' + s.date_str + ')' : ''} • Spoken: "${s.spoken_announcement || s.title}"</div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <span class="badge ${badgeClass}">${s.category}</span>
          <button class="btn btn-secondary" style="padding:0.2rem 0.5rem; font-size:0.75rem; color:var(--status-red);" onclick="deleteTimetableSlot(${s.id})">Delete</button>
        </div>
      </div>
    `;
  }).join('');
}

async function handleCreateTimetableSubmit(e) {
  e.preventDefault();
  const day_of_week = document.getElementById('tt-form-day').value;
  const start_time = document.getElementById('tt-form-start').value;
  const end_time = document.getElementById('tt-form-end').value;
  const title = document.getElementById('tt-form-title').value.trim();
  const category = document.getElementById('tt-form-cat').value;
  const spoken_announcement = document.getElementById('tt-form-spoken').value.trim();
  const is_blocked = document.getElementById('tt-form-blocked').checked;

  if (!title) return;

  const res = await fetch('/api/v1/timetable', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      day_of_week, start_time, end_time, title, category, spoken_announcement, is_blocked
    })
  });

  if (res.ok) {
    document.getElementById('tt-form-title').value = '';
    document.getElementById('tt-form-spoken').value = '';
    await loadTimetableSlots();
    loadDashboardData();
  } else {
    alert("Failed to add timetable slot.");
  }
}

async function deleteTimetableSlot(slotId) {
  if (!confirm("Are you sure you want to delete this schedule slot?")) return;
  const res = await fetch(`/api/v1/timetable/${slotId}`, {method: 'DELETE'});
  if (res.ok) {
    await loadTimetableSlots();
    loadDashboardData();
  }
}

async function handleCalendarSyncSubmit(e) {
  e.preventDefault();
  const url = document.getElementById('cal-ics-url-input').value.trim();
  if (!url) return;

  const statusText = document.getElementById('cal-sync-status-text');
  if (statusText) statusText.textContent = "Syncing...";

  try {
    const res = await fetch('/api/v1/calendar/sync', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ics_url: url})
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert(`Calendar Synced Successfully!\n${data.events_synced} event(s) imported and time-blocked.`);
      await loadTimetableSlots();
      loadDashboardData();
    } else {
      alert("Calendar Sync Error: " + (data.message || "Failed to fetch calendar"));
    }
  } catch (err) {
    alert("Failed to sync calendar feed.");
  }
}

// ==========================================
// WEEKLY TABULAR MATRIX EDITOR FUNCTIONS
// ==========================================

function switchTimetableTab(tab) {
  const matrixTab = document.getElementById('timetable-tab-matrix');
  const listTab = document.getElementById('timetable-tab-list');
  const matrixBtn = document.getElementById('tt-tab-matrix-btn');
  const listBtn = document.getElementById('tt-tab-list-btn');

  if (tab === 'matrix') {
    if (matrixTab) matrixTab.style.display = 'block';
    if (listTab) listTab.style.display = 'none';
    if (matrixBtn) matrixBtn.className = "btn btn-primary";
    if (listBtn) listBtn.className = "btn btn-secondary";
  } else {
    if (matrixTab) matrixTab.style.display = 'none';
    if (listTab) listTab.style.display = 'block';
    if (matrixBtn) matrixBtn.className = "btn btn-secondary";
    if (listBtn) listBtn.className = "btn btn-primary";
  }
}

function clearMatrixCell(btnEl) {
  const container = btnEl.closest('td');
  if (!container) return;
  const input = container.querySelector('.matrix-cell-title');
  if (input) {
    input.value = '';
    input.style.borderColor = 'var(--border-subtle)';
  }
}

async function deleteMatrixRow(btnEl) {
  const tr = btnEl.closest('tr');
  if (!tr) return;

  const titleInputs = tr.querySelectorAll('.matrix-cell-title');
  const slotIds = [];
  titleInputs.forEach(input => {
    const slotId = input.getAttribute('data-slot-id');
    if (slotId) slotIds.push(slotId);
  });

  const confirmMsg = slotIds.length > 0
    ? `Delete this entire time row and remove ${slotIds.length} scheduled slot(s) from your timetable?`
    : `Delete this time row?`;

  if (!confirm(confirmMsg)) return;

  for (const slotId of slotIds) {
    try {
      await fetch(`/api/v1/timetable/${slotId}`, { method: 'DELETE' });
    } catch (err) {
      console.warn(`Failed to delete slot ${slotId}:`, err);
    }
  }

  tr.remove();
  await loadTimetableSlots();
  loadDashboardData();
}

function renderTimetableMatrix(slots) {
  const tbody = document.getElementById('timetable-matrix-tbody');
  if (!tbody) return;

  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  
  let standardTimes = [];
  slots.forEach(s => {
    if (s.start_time && s.end_time) {
      const timeStr = `${s.start_time}-${s.end_time}`;
      if (!standardTimes.includes(timeStr)) {
        standardTimes.push(timeStr);
      }
    }
  });

  if (standardTimes.length === 0) {
    standardTimes = [
      "09:00-10:00", "10:00-11:00", "11:00-12:00", 
      "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"
    ];
  } else {
    standardTimes.sort((a, b) => a.localeCompare(b));
  }

  let rowsHtml = "";

  standardTimes.forEach((timeRange) => {
    rowsHtml += `
      <tr style="border-bottom:1px solid var(--border-subtle);">
        <td style="padding:0.4rem; background:var(--bg-surface); font-family:var(--font-mono); font-weight:700; font-size:0.78rem; color:var(--accent-cyan);">
          <div style="display:flex; align-items:center; gap:0.25rem;">
            <input type="text" class="matrix-time-input" value="${timeRange}" style="width:82px; background:var(--bg-card); border:1px solid var(--border-subtle); color:var(--accent-cyan); padding:0.2rem 0.3rem; border-radius:4px; font-weight:700; font-size:0.72rem;" placeholder="HH:MM-HH:MM">
            <button type="button" class="btn btn-secondary" style="padding:0.15rem 0.35rem; font-size:0.7rem; color:var(--status-red); border-color:rgba(239,68,68,0.4);" onclick="deleteMatrixRow(this)" title="Delete entire time row">🗑️</button>
          </div>
        </td>
    `;

    days.forEach(day => {
      const match = slots.find(s => 
        (s.day_of_week === day || s.day_of_week === 'Daily') && 
        `${s.start_time}-${s.end_time}` === timeRange
      );

      const slotId = match ? match.id : '';
      const title = match ? match.title : '';
      const category = match ? match.category : 'College';
      const isBlocked = match ? match.is_blocked : true;

      const catColors = {
        'College': '#6366F1',
        'Exam': '#EF4444',
        'Assignment': '#F59E0B',
        'DSA': '#06B6D4',
        'ML': '#10B981',
        'Break': '#EAB308'
      };
      const borderColor = match ? (catColors[category] || '#6366F1') : 'var(--border-subtle)';

      rowsHtml += `
        <td style="padding:0.4rem; border-left:1px solid var(--border-subtle); position:relative;">
          <div style="display:flex; flex-direction:column; gap:0.25rem;">
            <div style="display:flex; align-items:center; gap:0.2rem;">
              <input type="text" class="matrix-cell-title" data-slot-id="${slotId}" data-day="${day}" data-time="${timeRange}" value="${title}" title="${title}" placeholder="+ Add Activity" style="width:100%; background:var(--bg-card); border:1px solid ${borderColor}; color:var(--text-primary); padding:0.3rem 0.45rem; border-radius:4px; font-size:0.78rem; text-overflow:ellipsis; white-space:nowrap; overflow:hidden;">
              <button type="button" onclick="clearMatrixCell(this)" style="background:none; border:none; color:var(--status-red); cursor:pointer; font-size:0.75rem; padding:0 0.15rem;" title="Clear this activity">✕</button>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <select class="matrix-cell-cat" style="background:var(--bg-surface); border:1px solid var(--border-subtle); color:var(--text-secondary); font-size:0.68rem; padding:0.1rem 0.2rem; border-radius:3px;">
                <option value="College" ${category==='College'?'selected':''}>🎓 Col</option>
                <option value="Exam" ${category==='Exam'?'selected':''}>🎓 Exam</option>
                <option value="Assignment" ${category==='Assignment'?'selected':''}>📝 Assg</option>
                <option value="DSA" ${category==='DSA'?'selected':''}>&lt;/&gt; DSA</option>
                <option value="ML" ${category==='ML'?'selected':''}>🧠 ML</option>
                <option value="Break" ${category==='Break'?'selected':''}>☕ Break</option>
              </select>
              <label style="font-size:0.65rem; color:var(--text-muted); cursor:pointer; display:flex; align-items:center; gap:0.15rem;" title="Block this time window">
                <input type="checkbox" class="matrix-cell-block" ${isBlocked?'checked':''} style="accent-color:var(--accent-indigo);"> 🔒 Block
              </label>
            </div>
          </div>
        </td>
      `;
    });

    rowsHtml += `</tr>`;
  });

  tbody.innerHTML = rowsHtml;
}

function addMatrixTimeRow() {
  const tbody = document.getElementById('timetable-matrix-tbody');
  if (!tbody) return;

  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const newRow = document.createElement('tr');
  newRow.style.borderBottom = '1px solid var(--border-subtle)';

  let rowContent = `
    <td style="padding:0.4rem; background:var(--bg-surface); font-family:var(--font-mono); font-weight:700;">
      <div style="display:flex; align-items:center; gap:0.25rem;">
        <input type="text" class="matrix-time-input" value="18:00-19:00" style="width:82px; background:var(--bg-card); border:1px solid var(--border-subtle); color:var(--accent-cyan); padding:0.2rem 0.3rem; border-radius:4px; font-weight:700; font-size:0.72rem;" placeholder="HH:MM-HH:MM">
        <button type="button" class="btn btn-secondary" style="padding:0.15rem 0.35rem; font-size:0.7rem; color:var(--status-red); border-color:rgba(239,68,68,0.4);" onclick="deleteMatrixRow(this)" title="Delete entire time row">🗑️</button>
      </div>
    </td>
  `;

  days.forEach(day => {
    rowContent += `
      <td style="padding:0.4rem; border-left:1px solid var(--border-subtle);">
        <div style="display:flex; flex-direction:column; gap:0.25rem;">
          <div style="display:flex; align-items:center; gap:0.2rem;">
            <input type="text" class="matrix-cell-title" data-slot-id="" data-day="${day}" data-time="18:00-19:00" value="" placeholder="+ Add Activity" style="width:100%; background:var(--bg-card); border:1px solid var(--border-subtle); color:var(--text-primary); padding:0.3rem 0.45rem; border-radius:4px; font-size:0.78rem;">
            <button type="button" onclick="clearMatrixCell(this)" style="background:none; border:none; color:var(--status-red); cursor:pointer; font-size:0.75rem; padding:0 0.15rem;" title="Clear this activity">✕</button>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <select class="matrix-cell-cat" style="background:var(--bg-surface); border:1px solid var(--border-subtle); color:var(--text-secondary); font-size:0.68rem; padding:0.1rem 0.2rem; border-radius:3px;">
              <option value="College">🎓 Col</option>
              <option value="Exam">🎓 Exam</option>
              <option value="Assignment">📝 Assg</option>
              <option value="DSA">&lt;/&gt; DSA</option>
              <option value="ML">🧠 ML</option>
              <option value="Break">☕ Break</option>
            </select>
            <label style="font-size:0.65rem; color:var(--text-muted); cursor:pointer; display:flex; align-items:center; gap:0.15rem;">
              <input type="checkbox" class="matrix-cell-block" checked style="accent-color:var(--accent-indigo);"> 🔒 Block
            </label>
          </div>
        </div>
      </td>
    `;
  });

  newRow.innerHTML = rowContent;
  tbody.appendChild(newRow);
}

async function saveMatrixTimetable() {
  const tbody = document.getElementById('timetable-matrix-tbody');
  if (!tbody) return;

  const rows = tbody.querySelectorAll('tr');
  let saveCount = 0;

  for (const row of rows) {
    const timeInput = row.querySelector('.matrix-time-input');
    if (!timeInput) continue;
    const timeRange = timeInput.value.trim();
    let [startTime, endTime] = timeRange.split('-');
    if (!startTime) startTime = "09:00";
    if (!endTime) endTime = "10:00";
    startTime = startTime.trim();
    endTime = endTime.trim();

    const cells = row.querySelectorAll('td');
    for (let i = 1; i < cells.length; i++) {
      const cell = cells[i];
      const titleInput = cell.querySelector('.matrix-cell-title');
      const catSelect = cell.querySelector('.matrix-cell-cat');
      const blockCheck = cell.querySelector('.matrix-cell-block');

      if (!titleInput) continue;

      const title = titleInput.value.trim();
      const slotId = titleInput.getAttribute('data-slot-id');
      const day = titleInput.getAttribute('data-day');
      const category = catSelect ? catSelect.value : 'College';
      const isBlocked = blockCheck ? blockCheck.checked : true;

      if (title && !slotId) {
        await fetch('/api/v1/timetable', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            day_of_week: day,
            start_time: startTime,
            end_time: endTime,
            title: title,
            category: category,
            spoken_announcement: `Attention! ${title} is starting now at ${startTime}.`,
            is_blocked: isBlocked
          })
        });
        saveCount++;
      } else if (title && slotId) {
        await fetch(`/api/v1/timetable/${slotId}`, {
          method: 'PUT',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            title: title,
            day_of_week: day,
            start_time: startTime,
            end_time: endTime,
            category: category,
            is_blocked: isBlocked
          })
        });
        saveCount++;
      } else if (!title && slotId) {
        await fetch(`/api/v1/timetable/${slotId}`, {method: 'DELETE'});
      }
    }
  }

  alert("Weekly Timetable saved successfully!");
  await loadTimetableSlots();
  loadDashboardData();
}
