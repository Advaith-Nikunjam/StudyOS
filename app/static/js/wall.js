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
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const clockEl = document.getElementById('wall-clock');
  if (clockEl) clockEl.textContent = timeStr;

  const ssClockEl = document.getElementById('ss-clock');
  if (ssClockEl) ssClockEl.textContent = timeStr;
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
    enterSleepMode();
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
  const journeyPctEl = document.getElementById('wall-journey-pct');
  if (journeyPctEl) {
    const pct = data.dsa ? data.dsa.percentage : 6;
    journeyPctEl.textContent = `${pct}%`;
  }

  // Slide 3 Revision & Weakness Data Binding
  const revsContainer = document.getElementById('wall-revisions-list');
  if (revsContainer && data.todays_revisions_summary) {
    const revs = data.todays_revisions_summary.today || [];
    if (revs.length > 0) {
      const dots = ['var(--status-green)', 'var(--status-yellow)', 'var(--status-orange)', 'var(--accent-purple)'];
      revsContainer.innerHTML = revs.slice(0, 5).map((r, idx) => `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span><span style="display:inline-block; width:8px; height:8px; background:${dots[idx % dots.length]}; border-radius:50%; margin-right:0.5rem;"></span> ${r.concept_name}</span>
          <span style="color:var(--text-muted);">Today</span>
        </div>
      `).join('');
    }
  }

  const weaknessContainer = document.getElementById('wall-weakness-radar-container');
  if (weaknessContainer && data.weakness_radar && data.weakness_radar.top_weaknesses) {
    const topWeaknesses = data.weakness_radar.top_weaknesses.slice(0, 5);
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
        <div class="urgent-alert-card" style="border-color:var(--status-yellow); border-left-color:var(--status-yellow);">
          <div style="display:flex; align-items:center; gap:1rem;">
            <span style="font-size:1.5rem;">📝</span>
            <div style="text-align:left;">
              <div style="font-weight:700; font-size:1.1rem; color:var(--text-primary);">${a.title}</div>
              <div style="font-size:0.8rem; color:var(--text-muted);">${a.category} • Est. ${a.est_mins || 45} mins</div>
            </div>
          </div>
          <div>
            <span style="font-size:0.85rem; color:var(--status-yellow); margin-right:1rem; font-weight:600;">Due: ${a.due_date}</span>
            <button class="btn btn-secondary" style="border-color:var(--status-yellow); color:var(--status-yellow); font-size:0.75rem;">ASSIGNMENT</button>
          </div>
        </div>
      `;
    });

    urgentEvts.forEach(e => {
      urgentHtml += `
        <div class="urgent-alert-card" style="border-color:var(--status-red); border-left-color:var(--status-red);">
          <div style="display:flex; align-items:center; gap:1rem;">
            <span style="font-size:1.5rem;">🎓</span>
            <div style="text-align:left;">
              <div style="font-weight:700; font-size:1.1rem; color:var(--text-primary);">${e.title}</div>
              <div style="font-size:0.8rem; color:var(--text-muted);">${e.subject || 'College Event'}</div>
            </div>
          </div>
          <div>
            <span style="font-size:0.85rem; color:var(--status-red); margin-right:1rem; font-weight:600;">Due: ${e.due_date}</span>
            <button class="btn btn-secondary" style="border-color:var(--status-red); color:var(--status-red); font-size:0.75rem;">EVENT</button>
          </div>
        </div>
      `;
    });

    overdueRevs.forEach(r => {
      urgentHtml += `
        <div class="urgent-alert-card" style="border-color:var(--status-orange); border-left-color:var(--status-orange);">
          <div style="display:flex; align-items:center; gap:1rem;">
            <span style="font-size:1.5rem;">🔄</span>
            <div style="text-align:left;">
              <div style="font-weight:700; font-size:1.1rem; color:var(--text-primary);">${r.concept_name}</div>
              <div style="font-size:0.8rem; color:var(--text-muted);">${r.domain} Revision Overdue (${r.days_overdue || 1}d)</div>
            </div>
          </div>
          <div>
            <span style="font-size:0.85rem; color:var(--status-orange); margin-right:1rem; font-weight:600;">Revision Overdue</span>
            <button class="btn btn-secondary" style="border-color:var(--status-orange); color:var(--status-orange); font-size:0.75rem;">REVISE</button>
          </div>
        </div>
      `;
    });

    if (urgentHtml) {
      urgentContainer.innerHTML = urgentHtml;
    } else {
      urgentContainer.innerHTML = `<div style="color:var(--text-muted);">All assignments and revisions are up to date! Great work!</div>`;
    }
  }

  // Slide 4 Urgent Conditional Trigger
  const pill4 = document.getElementById('pill-4');
  if (data.has_pending_urgent) {
    totalScreens = 4;
    if (pill4) pill4.style.display = 'inline-block';
  } else {
    totalScreens = 3;
    if (pill4) pill4.style.display = 'none';
    if (currentScreen === 4) setScreen(1);
  }
}

function handleGlobalKeyDown(e) {
  if (isSleepMode) return;
  const key = e.key;
  if (key === 'ArrowLeft' || key === 'a' || key === 'A') {
    e.preventDefault(); prevScreen();
  } else if (key === 'ArrowRight' || key === 'd' || key === 'D') {
    e.preventDefault(); nextScreen();
  } else if (['1','2','3'].includes(key)) {
    e.preventDefault(); setScreen(parseInt(key)); triggerManualNavigation();
  } else if (key === '4' && totalScreens >= 4) {
    e.preventDefault(); setScreen(4); triggerManualNavigation();
  }
}

function startRotationTimer() {
  if (rotationInterval) clearInterval(rotationInterval);
  rotationInterval = setInterval(() => {
    if (!isSleepMode && !isAutoPaused) {
      let nextNum = (currentScreen % totalScreens) + 1;
      setScreen(nextNum);
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
  let target = (currentScreen % totalScreens) + 1;
  setScreen(target);
  triggerManualNavigation();
}

function prevScreen() {
  let target = (currentScreen - 2 + totalScreens) % totalScreens + 1;
  setScreen(target);
  triggerManualNavigation();
}

function setScreen(num) {
  if (num > totalScreens) num = 1;
  currentScreen = num;
  for (let i = 1; i <= 4; i++) {
    const scr = document.getElementById(`screen-${i}`);
    const pill = document.getElementById(`pill-${i}`);
    if (scr) scr.style.display = (i === num) ? 'flex' : 'none';
    if (pill) pill.classList.toggle('active', i === num);
  }
}

function enterSleepMode() {
  isSleepMode = true;
  const overlay = document.getElementById('screensaver-overlay');
  if (overlay) overlay.style.display = 'flex';
}

async function handleUserWakeInteraction(e) {
  if (e.type === 'keydown' && e.key.toUpperCase() === 'S' && !isSleepMode) {
    enterSleepMode();
    return;
  }
  if (isSleepMode) {
    isSleepMode = false;
    const overlay = document.getElementById('screensaver-overlay');
    if (overlay) overlay.style.display = 'none';
    try {
      await fetch('/api/v1/wall/sleep', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({sleep: false})
      });
    } catch (err) { console.warn(err); }
    fetchDisplayState();
  }
}
