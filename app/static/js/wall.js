// StudyOS Wall Kiosk Application JS Logic — Image 2 Reference Implementation

let currentScreen = 1;
let totalScreens = 3; // Dynamically adjusts to 4 if pending urgent items exist
let rotationInterval = null;
let inactivityTimeout = null;
let isSleepMode = false;
let isAutoPaused = false;
let lastSyncedTimeStr = "--:--";
const INACTIVITY_TIMEOUT_MS = 20000;

let touchStartX = 0;
let touchStartY = 0;

document.addEventListener('DOMContentLoaded', () => {
  updateClock();
  setInterval(updateClock, 1000);
  
  fetchDisplayState();
  setInterval(fetchDisplayState, 10000); // Poll API every 10 seconds
  
  startRotationTimer();
  
  window.addEventListener('keydown', handleGlobalKeyDown, true);

  window.addEventListener('touchstart', (e) => {
    if (e.touches && e.touches.length > 0) {
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
    }
  }, { passive: true });

  window.addEventListener('touchend', (e) => {
    if (e.changedTouches && e.changedTouches.length > 0) {
      const touchEndX = e.changedTouches[0].clientX;
      const touchEndY = e.changedTouches[0].clientY;
      const deltaX = touchEndX - touchStartX;
      const deltaY = touchEndY - touchStartY;

      if (Math.abs(deltaX) > 50 && Math.abs(deltaX) > Math.abs(deltaY)) {
        if (deltaX < 0) {
          nextScreen();
        } else {
          prevScreen();
        }
      }
    }
  }, { passive: true });

  ['keydown', 'mousedown', 'touchstart', 'pointerdown'].forEach(evt => {
    window.addEventListener(evt, handleUserWakeInteraction, { passive: true });
  });
});

function updateClock() {
  const now = new Date();
  const hours = now.getHours();
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const displayHours = String(hours % 12 || 12).padStart(2, '0');
  const timeStr = `${displayHours}:${minutes} ${ampm}`;

  const clockEl = document.getElementById('wall-clock');
  if (clockEl) clockEl.textContent = timeStr;

  const ssTimeEl = document.getElementById('ss-time-digital');
  if (ssTimeEl) ssTimeEl.innerHTML = `${displayHours}<span class="bedtime-colon">:</span>${minutes}`;

  const ssSecEl = document.getElementById('ss-seconds-digital');
  if (ssSecEl) ssSecEl.textContent = seconds;

  const ssAmpmEl = document.getElementById('ss-ampm-digital');
  if (ssAmpmEl) ssAmpmEl.textContent = ampm;

  const ssDateEl = document.getElementById('ss-date-digital');
  if (ssDateEl) {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    ssDateEl.textContent = now.toLocaleDateString('en-US', options);
  }
}

async function fetchDisplayState() {
  try {
    const res = await fetch('/api/display-state');
    if (!res.ok) throw new Error("Server HTTP Error");
    const data = await res.json();
    
    localStorage.setItem('studyos_wall_cache', JSON.stringify(data));
    const offlineBanner = document.getElementById('offline-banner');
    if (offlineBanner) offlineBanner.style.display = 'none';
    lastSyncedTimeStr = new Date().toLocaleTimeString();
    
    renderWallState(data);
  } catch (err) {
    console.warn("Wall Display disconnected, rendering cached state:", err);
    const offlineBanner = document.getElementById('offline-banner');
    if (offlineBanner) offlineBanner.style.display = 'block';
    const syncTimeEl = document.getElementById('last-synced-time');
    if (syncTimeEl) syncTimeEl.textContent = lastSyncedTimeStr;
    
    const cached = localStorage.getItem('studyos_wall_cache');
    if (cached) {
      renderWallState(JSON.parse(cached));
    }
  }
}

function renderWallState(data) {
  if (data.wall_sleep_mode && !isSleepMode) {
    enterSleepMode(false);
  }

  const ssSprintBadge = document.getElementById('ss-sprint-badge');
  if (ssSprintBadge) {
    ssSprintBadge.textContent = data.sprint_activated 
      ? `DAY ${String(data.day_number).padStart(2, '0')} / ${data.total_days} • BEDTIME CLOCK`
      : "PRE-SPRINT • BEDTIME CLOCK";
  }

  const ssModeBadge = document.getElementById('ss-mode-badge');
  if (ssModeBadge) {
    ssModeBadge.textContent = `${(data.env_mode || "REAL").toUpperCase()} MODE`;
  }

  const ssMustWinText = document.getElementById('ss-must-win-text');
  if (ssMustWinText && data.must_win && data.must_win.text) {
    ssMustWinText.textContent = data.must_win.text;
  }
  
  const dateStrEl = document.getElementById('wall-date-str');
  if (dateStrEl) dateStrEl.textContent = data.current_date_formatted;
  
  const envBadge = document.getElementById('wall-env-badge');
  if (envBadge) {
    const envMode = (data.env_mode || "REAL").toUpperCase();
    envBadge.textContent = `${envMode} MODE`;
  }

  const dayBadge = document.getElementById('wall-day-badge');
  if (dayBadge) {
    if (!data.sprint_activated) {
      dayBadge.textContent = "PRE-SPRINT (NOT STARTED)";
    } else {
      dayBadge.textContent = `DAY ${String(data.day_number).padStart(2, '0')} / ${data.total_days} • Week ${data.current_week} • ${data.current_week_info ? data.current_week_info.title : 'Foundation Phase'}`;
    }
  }

  // Slide 1 Data Binding
  const mustWinTextEl = document.getElementById('wall-must-win-text');
  if (mustWinTextEl && data.must_win && data.must_win.text) {
    mustWinTextEl.textContent = data.must_win.text;
  }
  
  const tasksContainer = document.getElementById('wall-today-tasks');
  if (tasksContainer && data.today_top_tasks) {
    const tasks = data.today_top_tasks.slice(0, 6);
    const totalMins = tasks.reduce((sum, t) => sum + (t.est_mins || 30), 0);
    const countText = document.getElementById('wall-plan-count-text');
    if (countText) countText.textContent = `${tasks.length} Tasks Scheduled • ~${totalMins} min`;

    if (tasks.length > 0) {
      const categoryIcons = {
        'Assignment': '📝',
        'College': '🎓',
        'DSA': '</>',
        'ML': '🧠',
        'DL': '⚡',
        'SentinelAI': '🛡️',
        'General': '📌'
      };

      const categoryColors = {
        'Assignment': '#F59E0B',
        'College': '#EAB308',
        'DSA': 'var(--accent-blue)',
        'ML': 'var(--status-green)',
        'DL': 'var(--accent-purple)',
        'SentinelAI': 'var(--status-orange)',
        'General': 'var(--accent-indigo)'
      };

      tasksContainer.innerHTML = tasks.map((t, idx) => {
        const icon = categoryIcons[t.category] || '📌';
        const color = categoryColors[t.category] || 'var(--accent-indigo)';
        const isDone = t.status === 'completed';

        return `
          <div class="wall-plan-card" style="border-bottom:3px solid ${color}; ${isDone ? 'opacity:0.65;' : ''}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="badge" style="background:rgba(255,255,255,0.08); color:${color}; font-weight:700;">${String(idx + 1).padStart(2, '0')} ${icon} ${t.category} ${isDone ? '✓' : ''}</span>
              <span style="font-family:var(--font-mono); font-size:0.8rem; color:var(--text-muted);">${t.est_mins || 45} min</span>
            </div>
            <div style="font-size:1.1rem; font-weight:700; color:var(--text-primary); margin:0.5rem 0 0.25rem 0; ${isDone ? 'text-decoration:line-through; color:var(--text-muted);' : ''}">${t.title}</div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">${isDone ? 'Completed' : (t.notes || 'Scheduled Task')}</div>
          </div>
        `;
      }).join('');
    } else {
      tasksContainer.innerHTML = `<div style="color:var(--text-muted); padding:1rem; grid-column:span 3;">No tasks scheduled for today.</div>`;
    }
  }

  const completionPctEl = document.getElementById('wall-completion-pct');
  if (completionPctEl) {
    const done = data.today_top_tasks ? data.today_top_tasks.filter(t => t.status === 'completed').length : 0;
    const total = data.today_top_tasks ? data.today_top_tasks.length : 0;
    completionPctEl.textContent = `${done} / ${total}`;
  }

  // Slide 2 Journey Data Binding
  const dayNum = data.day_number || 1;
  const currentWeek = data.current_week || 1;
  const dayBadgeText = `DAY ${String(dayNum).padStart(2, '0')} / 120`;

  ['wall-s2-day-badge', 'wall-s3-day-badge', 'wall-s4-day-badge'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = dayBadgeText;
  });

  const journeyPct = Math.round((dayNum / 120) * 100);

  const journeyPctEl = document.getElementById('wall-journey-pct');
  if (journeyPctEl) journeyPctEl.textContent = `${journeyPct}%`;

  const journeySubEl = document.getElementById('wall-journey-sub');
  if (journeySubEl) journeySubEl.textContent = `${dayNum} / 120 Days Completed`;

  // Dynamically Highlight Active Phase Card (1 to 5)
  let activePhase = 1;
  if (dayNum > 110) activePhase = 5;
  else if (dayNum > 90) activePhase = 4;
  else if (dayNum > 60) activePhase = 3;
  else if (dayNum > 30) activePhase = 2;

  for (let i = 1; i <= 5; i++) {
    const card = document.getElementById(`phase-card-${i}`);
    if (card) {
      const titleEl = card.querySelector('.phase-title');
      if (i === activePhase) {
        card.classList.add('active');
        if (titleEl) titleEl.style.color = '#A5B4FC';
      } else {
        card.classList.remove('active');
        if (titleEl) titleEl.style.color = 'var(--text-primary)';
      }
    }
  }

  // Update Slide 2 Bottom Row Stats
  const s2Week = document.getElementById('wall-s2-stat-week');
  if (s2Week) s2Week.textContent = `Week ${currentWeek}`;

  const s2Days = document.getElementById('wall-s2-stat-days');
  if (s2Days) s2Days.textContent = `Day ${dayNum} / 120`;

  const s2Dsa = document.getElementById('wall-s2-stat-dsa');
  if (s2Dsa && data.dsa) s2Dsa.textContent = `${data.dsa.solved_independent || 0} / 270`;

  const s2Sentinel = document.getElementById('wall-s2-stat-sentinel');
  if (s2Sentinel && data.sentinelai) s2Sentinel.textContent = data.sentinelai.active_version || "V0.1";

  // Slide 3 Revision & Weakness Data Binding
  const revsContainer = document.getElementById('wall-revisions-list');
  const revDueBadge = document.getElementById('wall-rev-due-badge');
  if (data.todays_revisions_summary) {
    const todayRevs = data.todays_revisions_summary.today || [];
    const overdueRevs = data.todays_revisions_summary.overdue || [];
    const dueCount = data.todays_revisions_summary.today_count || todayRevs.length;
    const overdueCount = data.todays_revisions_summary.overdue_count || overdueRevs.length;

    if (revDueBadge) {
      if (overdueCount > 0) {
        revDueBadge.textContent = `${overdueCount} Overdue`;
        revDueBadge.className = 'badge badge-red-vivid';
      } else {
        revDueBadge.textContent = `${dueCount} Due Today`;
        revDueBadge.className = 'badge badge-yellow';
      }
    }

    if (revsContainer) {
      const combined = [];
      overdueRevs.forEach(r => combined.push({ ...r, label: 'Overdue', color: 'var(--status-red)' }));
      todayRevs.forEach(r => combined.push({ ...r, label: 'Today', color: 'var(--status-green)' }));

      const displayList = combined.slice(0, 5);
      if (displayList.length > 0) {
        revsContainer.innerHTML = displayList.map(r => `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span><span style="display:inline-block; width:8px; height:8px; background:${r.color}; border-radius:50%; margin-right:0.5rem;"></span> ${r.concept_name}</span>
            <span style="color:var(--text-muted); font-size:0.8rem;">${r.label}</span>
          </div>
        `).join('');
      } else {
        revsContainer.innerHTML = `<div style="color:var(--text-muted); padding:0.5rem 0;">No revisions scheduled for today.</div>`;
      }
    }
  }

  const weaknessContainer = document.getElementById('wall-weakness-radar-container');
  if (data.weakness_radar) {
    const topWeaknesses = (data.weakness_radar.top_weaknesses || []).slice(0, 5);
    if (weaknessContainer) {
      if (topWeaknesses.length > 0) {
        const colors = ['var(--status-red)', 'var(--status-orange)', 'var(--status-yellow)', 'var(--status-green)', 'var(--status-green)'];
        weaknessContainer.innerHTML = topWeaknesses.map((w, idx) => {
          const pct = Math.min(w.mistake_count * 20, 100);
          return `
            <div style="display:flex; justify-content:space-between;">
              <span>${w.topic}</span>
              <span style="color:${colors[idx % colors.length]}; font-weight:700;">${pct}%</span>
            </div>
          `;
        }).join('');
      } else {
        weaknessContainer.innerHTML = `<div style="color:var(--text-muted);">No recorded weaknesses yet.</div>`;
      }
    }

    // Recommendation Advice Text
    const adviceEl = document.getElementById('wall-weakness-advice-text');
    if (adviceEl) {
      if (topWeaknesses.length > 0) {
        const focusTopics = topWeaknesses.slice(0, 2).map(w => w.topic).join(' & ');
        adviceEl.textContent = `Focus more on ${focusTopics}. Solve, revise, and strengthen!`;
      } else {
        adviceEl.textContent = 'Keep maintaining your daily problem solving consistency!';
      }
    }

    // Bottom Stats Row Data Binding
    const statTotal = document.getElementById('wall-stat-weak-total');
    if (statTotal) statTotal.textContent = data.weakness_radar.unresolved_count ?? topWeaknesses.length;

    const statAvg = document.getElementById('wall-stat-weak-avg');
    if (statAvg) {
      if (topWeaknesses.length > 0) {
        const avgPct = Math.round(topWeaknesses.reduce((sum, w) => sum + Math.min(w.mistake_count * 20, 100), 0) / topWeaknesses.length);
        statAvg.textContent = `${avgPct}%`;
      } else {
        statAvg.textContent = '0%';
      }
    }

    const statResolved = document.getElementById('wall-stat-weak-resolved');
    if (statResolved) {
      const resolvedCount = data.weakness_radar.improved_count ?? 0;
      statResolved.innerHTML = `${resolvedCount} <span style="font-size:0.8rem; font-weight:400; color:var(--text-secondary);">(This Sprint)</span>`;
    }
  }

  // Slide 4 Urgent & Assignments Data Binding
  const urgentContainer = document.getElementById('wall-urgent-container');
  const urgentCountText = document.getElementById('wall-urgent-count-text');
  const activeAssigns = data.active_assignments || [];
  const urgentEvts = data.urgent_events || [];
  const overdueRevs = (data.todays_revisions_summary && data.todays_revisions_summary.overdue) ? data.todays_revisions_summary.overdue : [];

  const totalUrgentCount = activeAssigns.length + urgentEvts.length + overdueRevs.length;

  if (urgentCountText) {
    urgentCountText.textContent = totalUrgentCount > 0 
      ? `${totalUrgentCount} ITEM${totalUrgentCount > 1 ? 'S' : ''} NEED YOUR ATTENTION` 
      : 'NO PENDING URGENT ITEMS';
  }

  if (urgentContainer) {
    let urgentHtml = '';

    activeAssigns.forEach(a => {
      urgentHtml += `
        <div class="urgent-alert-card" style="border-color:#F59E0B; border-left:6px solid #F59E0B; background:rgba(22, 30, 49, 0.95);">
          <div style="display:flex; align-items:center; gap:1.2rem;">
            <span style="font-size:1.8rem; flex-shrink:0;">📝</span>
            <div style="text-align:left;">
              <div style="font-weight:800; font-size:1.15rem; color:#F8FAFC; line-height:1.3;">${a.title}</div>
              <div style="font-size:0.85rem; color:#CBD5E1; font-weight:500; margin-top:0.2rem;">${a.category} • Est. ${a.est_mins || 45} mins</div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:0.75rem; flex-shrink:0;">
            <span class="badge badge-yellow-vivid">Due: ${a.due_date}</span>
            <button class="btn btn-secondary" style="border-color:#F59E0B; color:#FCD34D; font-weight:700; font-size:0.78rem; background:rgba(245,158,11,0.12); padding:0.35rem 0.85rem;">ASSIGNMENT</button>
          </div>
        </div>
      `;
    });

    urgentEvts.forEach(e => {
      urgentHtml += `
        <div class="urgent-alert-card" style="border-color:#EF4444; border-left:6px solid #EF4444; background:rgba(22, 30, 49, 0.95);">
          <div style="display:flex; align-items:center; gap:1.2rem;">
            <span style="font-size:1.8rem; flex-shrink:0;">🎓</span>
            <div style="text-align:left;">
              <div style="font-weight:800; font-size:1.15rem; color:#F8FAFC; line-height:1.3;">${e.title}</div>
              <div style="font-size:0.85rem; color:#CBD5E1; font-weight:500; margin-top:0.2rem;">${e.subject || 'College Event'}</div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:0.75rem; flex-shrink:0;">
            <span class="badge badge-red-vivid">Due: ${e.due_date}</span>
            <button class="btn btn-secondary" style="border-color:#EF4444; color:#FF8A8A; font-weight:700; font-size:0.78rem; background:rgba(239,68,68,0.12); padding:0.35rem 0.85rem;">EVENT</button>
          </div>
        </div>
      `;
    });

    overdueRevs.forEach(r => {
      urgentHtml += `
        <div class="urgent-alert-card" style="border-color:#F97316; border-left:6px solid #F97316; background:rgba(22, 30, 49, 0.95);">
          <div style="display:flex; align-items:center; gap:1.2rem;">
            <span style="font-size:1.8rem; flex-shrink:0;">🔄</span>
            <div style="text-align:left;">
              <div style="font-weight:800; font-size:1.15rem; color:#F8FAFC; line-height:1.3;">${r.concept_name}</div>
              <div style="font-size:0.85rem; color:#CBD5E1; font-weight:500; margin-top:0.2rem;">${r.domain} • Overdue (${r.days_overdue || 1}d)</div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:0.75rem; flex-shrink:0;">
            <span class="badge badge-orange-vivid">Revision Overdue</span>
            <button class="btn btn-secondary" style="border-color:#F97316; color:#FDBA74; font-weight:700; font-size:0.78rem; background:rgba(249,115,22,0.12); padding:0.35rem 0.85rem;">REVISE</button>
          </div>
        </div>
      `;
    });

    if (urgentHtml) {
      urgentContainer.innerHTML = urgentHtml;
    } else {
      urgentContainer.innerHTML = `<div style="color:var(--text-muted); font-size:1.1rem; padding:2rem;">All assignments and revisions are up to date! Great work!</div>`;
    }
  }

  // Slide 4 Urgent & Slide 5 Timetable Conditional Triggers
  const pill4 = document.getElementById('pill-4');
  if (data.has_pending_urgent) {
    if (pill4) pill4.style.display = 'inline-block';
  } else {
    if (pill4) pill4.style.display = 'none';
    if (currentScreen === 4) setScreen(1);
  }

  // Slide 5 Timetable Data Binding (With Deduplication)
  const ttContainer = document.getElementById('wall-timetable-container');
  if (ttContainer && data.today_timetable) {
    const rawSlots = data.today_timetable;
    const seenKeys = new Set();
    const slots = rawSlots.filter(s => {
      const key = `${s.title}_${s.start_time}_${s.end_time}`;
      if (seenKeys.has(key)) return false;
      seenKeys.add(key);
      return true;
    });

    if (slots.length > 0) {
      const categoryBadges = {
        'Exam': 'badge-red-vivid',
        'Assignment': 'badge-yellow-vivid',
        'College': 'badge-indigo',
        'DSA': 'badge-cyan',
        'ML': 'badge-green',
        'Break': 'badge-yellow'
      };

      ttContainer.innerHTML = slots.map(s => {
        const badgeClass = categoryBadges[s.category] || 'badge-indigo';
        return `
          <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-surface); border:1px solid var(--border-bright); border-radius:var(--radius-md); padding:1rem 1.5rem; box-shadow:0 4px 12px rgba(0,0,0,0.3);">
            <div style="display:flex; align-items:center; gap:1.25rem;">
              <div style="font-family:var(--font-mono); font-weight:800; font-size:1.1rem; color:var(--accent-cyan); min-width:130px;">
                ${s.start_time} - ${s.end_time}
              </div>
              <div>
                <div style="font-weight:800; font-size:1.2rem; color:#F8FAFC;">
                  ${s.title}
                  ${s.is_blocked ? '<span style="font-size:0.75rem; color:var(--status-yellow); margin-left:0.5rem; border:1px solid rgba(245,158,11,0.5); padding:0.15rem 0.5rem; border-radius:4px;">TIME BLOCKED</span>' : ''}
                  ${s.source === 'ical_sync' || s.source === 'google_cal' ? '<span style="font-size:0.75rem; color:var(--accent-indigo); margin-left:0.3rem;">🔗 CALENDAR SYNCED</span>' : ''}
                </div>
                <div style="font-size:0.85rem; color:#CBD5E1; margin-top:0.2rem;">Spoken: "${s.spoken_announcement || s.title}"</div>
              </div>
            </div>
            <div>
              <span class="badge ${badgeClass}" style="font-size:0.85rem; padding:0.4rem 0.85rem;">${s.category}</span>
            </div>
          </div>
        `;
      }).join('');
    } else {
      ttContainer.innerHTML = `<div style="color:var(--text-muted); font-size:1.1rem; padding:2rem; text-align:center;">No timetable slots scheduled for today. Add slots or sync your Google Calendar from the Dashboard!</div>`;
    }
  }

  totalScreens = 5;
}

function handleGlobalKeyDown(e) {
  if (isSleepMode) return;
  const key = e.key;
  if (key === 'ArrowLeft' || key === 'a' || key === 'A') {
    e.preventDefault(); prevScreen();
  } else if (key === 'ArrowRight' || key === 'd' || key === 'D') {
    e.preventDefault(); nextScreen();
  } else if (['1','2','3','4','5'].includes(key)) {
    e.preventDefault(); setScreen(parseInt(key)); triggerManualNavigation();
  }
}

function startRotationTimer() {
  if (rotationInterval) clearInterval(rotationInterval);
  rotationInterval = setInterval(() => {
    if (!isSleepMode && !isAutoPaused) {
      let target = (currentScreen % 5) + 1;
      const pill4 = document.getElementById('pill-4');
      if (target === 4 && pill4 && pill4.style.display === 'none') {
        target = 5;
      }
      setScreen(target);
    }
  }, 25000);
}

function triggerManualNavigation() {
  isAutoPaused = true;
  const autoStatusPill = document.getElementById('wall-auto-status');
  if (autoStatusPill) {
    autoStatusPill.textContent = "AUTO PAUSED";
    autoStatusPill.className = "badge badge-yellow";
  }
  if (inactivityTimeout) clearTimeout(inactivityTimeout);
  inactivityTimeout = setTimeout(() => {
    isAutoPaused = false;
    if (autoStatusPill) {
      autoStatusPill.textContent = "AUTO ON";
      autoStatusPill.className = "badge badge-green";
    }
    startRotationTimer();
  }, INACTIVITY_TIMEOUT_MS);
}

function nextScreen() {
  let target = (currentScreen % 5) + 1;
  const pill4 = document.getElementById('pill-4');
  if (target === 4 && pill4 && pill4.style.display === 'none') {
    target = 5;
  }
  setScreen(target);
  triggerManualNavigation();
}

function prevScreen() {
  let target = (currentScreen - 2 + 5) % 5 + 1;
  const pill4 = document.getElementById('pill-4');
  if (target === 4 && pill4 && pill4.style.display === 'none') {
    target = 3;
  }
  setScreen(target);
  triggerManualNavigation();
}

function setScreen(num) {
  if (num > 5) num = 1;
  currentScreen = num;
  for (let i = 1; i <= 5; i++) {
    const scr = document.getElementById(`screen-${i}`);
    const pill = document.getElementById(`pill-${i}`);
    if (scr) scr.style.display = (i === num) ? 'flex' : 'none';
    if (pill) pill.classList.toggle('active', i === num);
  }
}

async function enterSleepMode(persistToBackend = false) {
  isSleepMode = true;
  const overlay = document.getElementById('screensaver-overlay');
  if (overlay) overlay.style.display = 'flex';

  if (persistToBackend) {
    try {
      await fetch('/api/v1/wall/sleep', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({sleep: true})
      });
    } catch (err) { console.warn("Sleep mode sync error:", err); }
  }
}

async function wakeWallDisplay(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  isSleepMode = false;
  const overlay = document.getElementById('screensaver-overlay');
  if (overlay) overlay.style.display = 'none';
  try {
    await fetch('/api/v1/wall/sleep', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({sleep: false})
    });
  } catch (err) { console.warn("Sleep wake sync error:", err); }
  fetchDisplayState();
}

let dimmerModeIndex = 0; // 0: Normal, 1: Dim (30%), 2: Ultra Dim (15%)
function toggleNightDimmer(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  const overlay = document.getElementById('screensaver-overlay');
  const btn = document.getElementById('ss-dimmer-btn');
  dimmerModeIndex = (dimmerModeIndex + 1) % 3;

  if (!overlay || !btn) return;

  overlay.classList.remove('dimmer-dim', 'dimmer-extra-dim', 'bedtime-dim-soft', 'bedtime-dim-ultra');
  if (dimmerModeIndex === 1) {
    overlay.classList.add('bedtime-dim-soft');
    btn.textContent = "🌙 Dimmer: DIM (30%)";
    btn.style.borderColor = "#f59e0b";
    btn.style.color = "#fcd34d";
  } else if (dimmerModeIndex === 2) {
    overlay.classList.add('bedtime-dim-ultra');
    btn.textContent = "🌙 Dimmer: ULTRA DIM (15%)";
    btn.style.borderColor = "#ef4444";
    btn.style.color = "#fca5a5";
  } else {
    btn.textContent = "🌙 Dimmer: NORMAL";
    btn.style.borderColor = "#6366f1";
    btn.style.color = "#a5b4fc";
  }
}

async function handleUserWakeInteraction(e) {
  if (e.type === 'keydown') {
    const key = e.key.toLowerCase();
    if ((key === 's' || key === 'z') && !isSleepMode) {
      enterSleepMode(true);
      return;
    }
    if (isSleepMode) {
      wakeWallDisplay(e);
      return;
    }
  }

  if (isSleepMode) {
    // Prevent waking up if clicking controls inside the bedtime clock card (like Dimmer button)
    if (e.target && e.target.closest && e.target.closest('#bedtime-clock-card')) {
      return;
    }
    wakeWallDisplay(e);
  }
}

// Web Speech + Ubuntu Linux OS Voice Announcement Engine for Wall Kiosk
let wallSpokenLog = new Set();
let wallTimetableSlots = [];
let wallVoiceEnabled = true;

function toggleWallVoice() {
  wallVoiceEnabled = !wallVoiceEnabled;
  const btn = document.getElementById('wall-voice-btn');
  if (btn) btn.textContent = wallVoiceEnabled ? "🔊 Voice Alerts: ON" : "🔇 Voice Alerts: OFF";
}

async function speakWallAnnouncement(text) {
  if (!wallVoiceEnabled) return;
  
  // 1. Visual Toast Banner
  const toast = document.getElementById('wall-announcement-toast');
  const toastText = document.getElementById('wall-toast-text');
  if (toast && toastText) {
    toastText.textContent = text;
    toast.style.display = 'flex';
    setTimeout(() => { toast.style.display = 'none'; }, 10000);
  }

  // 2. Web Speech API (Chrome/Browser)
  if ('speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (err) { console.warn("Wall Speech Error:", err); }
  }

  // 3. Ubuntu / Linux Backend Speech API (spd-say / espeak)
  try {
    await fetch('/api/v1/system/speak', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
  } catch (e) {}
}

setInterval(() => {
  if (isSleepMode || !wallVoiceEnabled) return;
  const now = new Date();
  const timeHHMM = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  const dateISO = now.toISOString().split('T')[0];

  const cachedStr = localStorage.getItem('studyos_wall_cache');
  if (cachedStr) {
    try {
      const parsed = JSON.parse(cachedStr);
      wallTimetableSlots = parsed.today_timetable || [];
    } catch (e) {}
  }

  wallTimetableSlots.forEach(s => {
    if (s.start_time === timeHHMM) {
      const key = `wall_${dateISO}_${s.id}_${timeHHMM}`;
      if (!wallSpokenLog.has(key)) {
        wallSpokenLog.add(key);
        const text = s.spoken_announcement || `Attention! ${s.title} is starting now at ${s.start_time}.`;
        speakWallAnnouncement(text);
      }
    }
  });
}, 20000);
