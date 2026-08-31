// StudyOS Controller Application JS Logic — Complete Navigation & Real Roadmap Engine

let currentTaskFilter = 'ALL';

document.addEventListener('DOMContentLoaded', () => {
  const todayStr = new Date().toISOString().split('T')[0];
  const dateInput = document.getElementById('sprint-start-date-input');
  if (dateInput) dateInput.value = todayStr;

  const atmDueDate = document.getElementById('atm-due-date');
  if (atmDueDate) atmDueDate.value = todayStr;

  loadDashboardData();
  setInterval(loadDashboardData, 15000); // Auto-refresh every 15s
});

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
    alert(`Error activating sprint: ${data.detail || data.message}`);
    return;
  }
  
  alert(`${data.message}\nStart Date: ${data.actual_start_date}\nEnd Date (120 Days): ${data.actual_end_date}`);
  closeModal('start-sprint-modal');
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
