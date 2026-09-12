/* ==========================================================================
   SAVAGE WARRIOR APP — APPLICATION LOGIC
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Feather Icons
  if (typeof feather !== 'undefined') {
    feather.replace();
  }

  // --- STATE & LOCAL STORAGE ---
  const STORAGE_KEY = 'savage_warrior_data_v1';
  
  let appState = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {
    streak: 19,
    prsCrushed: 42,
    intensity: '100%',
    wallpaper: null,
    protocol: [
      { id: 1, title: '05:00 AM — Awakening & Ice Cold Immersion', xp: 50, completed: true },
      { id: 2, title: 'Fasted Ruck March / 5km Outdoor Assault', xp: 100, completed: true },
      { id: 3, title: 'Compound Heavy Lift (Deadlift / Bench PR)', xp: 150, completed: false },
      { id: 4, title: 'High-Protein Carnivore Fuel & Electrolytes', xp: 75, completed: true },
      { id: 5, title: 'Evening Mobility & Mental Visualization', xp: 50, completed: false }
    ],
    prs: [
      { id: 1, exercise: 'Conventional Deadlift', weight: '220 kg', reps: 3, rpe: 9.5, date: 'Oct 24, 2026', notes: 'Beltless, hook grip locked in. Explosive lockout.' },
      { id: 2, exercise: 'Weighted Pull-Up', weight: '+50 kg', reps: 5, rpe: 9.0, date: 'Oct 23, 2026', notes: 'Strict dead hang, chest to bar.' },
      { id: 3, exercise: 'Incline Barbell Bench', weight: '142.5 kg', reps: 4, rpe: 9.5, date: 'Oct 22, 2026', notes: 'Solid stability, pause at chest.' }
    ],
    stats: {
      deadlift: { weight: '240 kg', sub: 'Est. 1RM 260kg' },
      squat: { weight: '210 kg', sub: 'Est. 1RM 225kg' },
      bench: { weight: '155 kg', sub: 'Est. 1RM 168kg' },
      press: { weight: '102.5 kg', sub: 'Strict Overhead' }
    },
    gear: [
      { id: 1, name: 'SBD 13mm Lever Belt', category: 'Armor & Belts', durability: 95, notes: 'IPF approved red carbon finish.' },
      { id: 2, name: 'Ergonomic Knee Sleeves', category: 'Joint Support', durability: 88, notes: '7mm neoprene heavy rebound.' },
      { id: 3, name: 'Cotton Lifting Straps', category: 'Grip & Straps', durability: 72, notes: 'Aramid reinforced stitch for heavy rows.' },
      { id: 4, name: 'Ironmind Captains of Crush', category: 'Combat Accessory', durability: 100, notes: 'No. 3 grip trainer.' }
    ],
    journal: `# Savage Warrior Journal — MAIN PAGE: PR FLOW\n\n## Today's Objective\nCrush the compound volume. Focus on relentless tension and explosive concentric drive.\n\n- [x] Hydration & electrolyte load\n- [ ] 220kg Deadlift Triple\n- [ ] Evening stretch routine\n\n> "Discipline equals freedom. The iron never lies."`
  };

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(appState));
    } catch (e) {
      console.warn('LocalStorage save trim:', e);
    }
    showSaveIndicator();
  }

  function showSaveIndicator() {
    const indicator = document.getElementById('save-indicator');
    if (indicator) {
      indicator.textContent = 'Saved to disk ✓';
      setTimeout(() => {
        indicator.textContent = 'Auto-saved to local disk';
      }, 2000);
    }
  }

  // --- WALLPAPER SYSTEM ---
  const bgLayer = document.getElementById('bg-image-layer');

  const PRESET_WALLPAPERS = {
    valhalla: `radial-gradient(circle at 50% 30%, #3b0a0a 0%, #07070a 85%)`,
    cyber: `radial-gradient(circle at 30% 30%, #092c44 0%, #050714 85%)`,
    blood: `radial-gradient(circle at 70% 70%, #520b0b 0%, #140505 85%)`
  };

  function applyWallpaper(wallpaperVal) {
    if (!wallpaperVal) return;
    
    let bgStyle = wallpaperVal;
    if (wallpaperVal.startsWith('data:') || wallpaperVal.startsWith('blob:') || wallpaperVal.startsWith('http')) {
      bgStyle = `url('${wallpaperVal}')`;
    } else if (PRESET_WALLPAPERS[wallpaperVal]) {
      bgStyle = PRESET_WALLPAPERS[wallpaperVal];
    }

    if (bgLayer) {
      bgLayer.style.backgroundImage = bgStyle;
      bgLayer.style.backgroundSize = 'cover';
      bgLayer.style.backgroundPosition = 'center';
    }
  }

  // Load saved wallpaper on startup
  if (appState.wallpaper) {
    applyWallpaper(appState.wallpaper);
  }

  // --- AUDIO SYNTHESIZER & MP3 PLAYER SYSTEM ---
  let isAudioPlaying = false;
  let audioContext = null;
  let synthInterval = null;
  const audioEl = document.getElementById('bg-audio');
  const audioToggleBtn = document.getElementById('audio-toggle-btn');
  const audioIcon = document.getElementById('audio-icon');
  const audioWaves = document.getElementById('audio-waves');
  const audioStatusLabel = document.getElementById('audio-status-label');

  function playEpicSynthDrum() {
    try {
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioContext.state === 'suspended') {
        audioContext.resume();
      }

      // Deep War Drum Boom
      const osc = audioContext.createOscillator();
      const gain = audioContext.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(80, audioContext.currentTime);
      osc.frequency.exponentialRampToValueAtTime(30, audioContext.currentTime + 0.6);

      gain.gain.setValueAtTime(0.5, audioContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.7);

      osc.connect(gain);
      gain.connect(audioContext.destination);

      osc.start();
      osc.stop(audioContext.currentTime + 0.7);

      if (Math.random() > 0.6) {
        const drone = audioContext.createOscillator();
        const droneGain = audioContext.createGain();
        drone.type = 'sawtooth';
        drone.frequency.setValueAtTime(45, audioContext.currentTime);
        droneGain.gain.setValueAtTime(0.15, audioContext.currentTime);
        droneGain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 2.0);
        drone.connect(droneGain);
        droneGain.connect(audioContext.destination);
        drone.start();
        drone.stop(audioContext.currentTime + 2.0);
      }
    } catch (e) {
      console.log('Web audio synth note:', e);
    }
  }

  function toggleAudio() {
    isAudioPlaying = !isAudioPlaying;
    
    const audioSourceType = document.querySelector('input[name="audioSource"]:checked')?.value || 'synth';

    if (isAudioPlaying) {
      audioToggleBtn.classList.add('active');
      audioIcon.setAttribute('data-feather', 'volume-2');
      audioStatusLabel.textContent = 'SOUND: ON';

      if (audioSourceType === 'file' && audioEl.src && !audioEl.paused) {
        // already playing html5 audio
      } else if (audioSourceType === 'file' && audioEl.src) {
        audioEl.play().catch(err => {
          console.log('HTML5 audio play blocked/error, fallback to synth:', err);
          startSynthLoop();
        });
      } else {
        startSynthLoop();
      }
    } else {
      audioToggleBtn.classList.remove('active');
      audioIcon.setAttribute('data-feather', 'volume-x');
      audioStatusLabel.textContent = 'SOUND: OFF';

      stopSynthLoop();
      audioEl.pause();
    }
    feather.replace();
  }

  function startSynthLoop() {
    stopSynthLoop();
    playEpicSynthDrum();
    synthInterval = setInterval(playEpicSynthDrum, 1800);
  }

  function stopSynthLoop() {
    if (synthInterval) {
      clearInterval(synthInterval);
      synthInterval = null;
    }
  }

  audioToggleBtn.addEventListener('click', toggleAudio);

  // --- NAVIGATION TAB SWITCHING ---
  const navItems = document.querySelectorAll('.nav-item');
  const sections = document.querySelectorAll('.app-section');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetId = item.getAttribute('data-target');
      
      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');

      sections.forEach(sec => {
        sec.classList.remove('active');
        if (sec.id === targetId) {
          sec.classList.add('active');
        }
      });
      
      document.querySelector('.content-scrollable').scrollTop = 0;
    });
  });

  // --- RENDER FUNCTIONS ---

  // 1. Render Daily Protocol Checklist
  function renderProtocol() {
    const container = document.getElementById('protocol-checklist');
    if (!container) return;

    container.innerHTML = appState.protocol.map(item => `
      <div class="protocol-item ${item.completed ? 'completed' : ''}" data-id="${item.id}">
        <div class="protocol-left">
          <div class="checkbox-custom">
            ${item.completed ? '<i data-feather="check" style="width:14px;height:14px;"></i>' : ''}
          </div>
          <span class="protocol-title">${item.title}</span>
        </div>
        <span class="protocol-xp">+${item.xp} XP</span>
      </div>
    `).join('');

    feather.replace();

    container.querySelectorAll('.protocol-item').forEach(el => {
      el.addEventListener('click', () => {
        const id = parseInt(el.getAttribute('data-id'));
        const p = appState.protocol.find(x => x.id === id);
        if (p) {
          p.completed = !p.completed;
          saveState();
          renderProtocol();
        }
      });
    });
  }

  // 2. Render PR Flow Stream
  function renderPRFlow() {
    const container = document.getElementById('pr-flow-container');
    if (!container) return;

    container.innerHTML = appState.prs.map(pr => `
      <div class="pr-card">
        <div class="pr-card-header">
          <span class="pr-exercise-name">${pr.exercise}</span>
          <span class="pr-date-tag">${pr.date}</span>
        </div>
        <div class="pr-metrics">
          <span>WEIGHT: <span class="pr-stat">${pr.weight}</span></span>
          <span>REPS: <span class="pr-stat">${pr.reps}</span></span>
          <span>RPE: <span class="pr-stat">${pr.rpe}</span></span>
        </div>
        ${pr.notes ? `<div class="pr-notes-text">"${pr.notes}"</div>` : ''}
      </div>
    `).join('');

    document.getElementById('total-prs-counter').textContent = appState.prs.length + 39;
  }

  // 3. Render Strength Stats
  function renderStats() {
    const grid = document.getElementById('strength-stats-grid');
    if (!grid) return;

    const stats = appState.stats;
    grid.innerHTML = `
      <div class="stat-box">
        <div class="stat-box-title">DEADLIFT</div>
        <div class="stat-box-value">${stats.deadlift.weight}</div>
        <div class="stat-box-sub">${stats.deadlift.sub}</div>
      </div>
      <div class="stat-box">
        <div class="stat-box-title">SQUAT</div>
        <div class="stat-box-value">${stats.squat.weight}</div>
        <div class="stat-box-sub">${stats.squat.sub}</div>
      </div>
      <div class="stat-box">
        <div class="stat-box-title">BENCH PRESS</div>
        <div class="stat-box-value">${stats.bench.weight}</div>
        <div class="stat-box-sub">${stats.bench.sub}</div>
      </div>
      <div class="stat-box">
        <div class="stat-box-title">OVERHEAD PRESS</div>
        <div class="stat-box-value">${stats.press.weight}</div>
        <div class="stat-box-sub">Strict Barbell</div>
      </div>
    `;
  }

  // 4. Render Gear Management
  function renderGear() {
    const container = document.getElementById('gear-list-container');
    if (!container) return;

    container.innerHTML = appState.gear.map(g => {
      let durClass = '';
      if (g.durability < 75) durClass = 'warning';
      if (g.durability < 50) durClass = 'danger';

      return `
        <div class="gear-card" data-id="${g.id}">
          <div class="gear-card-top">
            <div>
              <div class="gear-name">${g.name}</div>
              <span class="gear-category-badge">${g.category}</span>
            </div>
            <button class="btn-icon-xs delete-gear-btn" data-id="${g.id}">Delete</button>
          </div>
          <div class="gear-durability-wrap">
            <div class="gear-dur-text">
              <span>TACTICAL DURABILITY</span>
              <span>${g.durability}%</span>
            </div>
            <div class="gear-dur-bar-bg">
              <div class="gear-dur-bar-fill ${durClass}" style="width: ${g.durability}%"></div>
            </div>
          </div>
          ${g.notes ? `<div class="gear-notes">${g.notes}</div>` : ''}
        </div>
      `;
    }).join('');

    document.getElementById('total-gear-count').textContent = appState.gear.length;
    
    if (appState.gear.length > 0) {
      const total = appState.gear.reduce((acc, cur) => acc + cur.durability, 0);
      const avg = Math.round(total / appState.gear.length);
      document.getElementById('gear-condition-avg').textContent = avg + '%';
    }

    container.querySelectorAll('.delete-gear-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt(btn.getAttribute('data-id'));
        appState.gear = appState.gear.filter(g => g.id !== id);
        saveState();
        renderGear();
      });
    });
  }

  // --- MARKDOWN COMBAT LOG & PREVIEW ---
  const mdInput = document.getElementById('markdown-input');
  const mdPreview = document.getElementById('markdown-preview');
  const toggleMdModeBtn = document.getElementById('toggle-md-mode-btn');
  let isPreviewMode = false;

  mdInput.value = appState.journal;

  mdInput.addEventListener('input', () => {
    appState.journal = mdInput.value;
    saveState();
  });

  document.getElementById('save-journal-btn').addEventListener('click', () => {
    saveState();
    alert('Combat log entry saved successfully to disk!');
  });

  toggleMdModeBtn.addEventListener('click', () => {
    isPreviewMode = !isPreviewMode;
    const icon = document.getElementById('md-toggle-icon');
    
    if (isPreviewMode) {
      mdPreview.innerHTML = marked.parse(mdInput.value);
      mdInput.classList.add('hidden');
      mdPreview.classList.remove('hidden');
      icon.setAttribute('data-feather', 'edit-3');
    } else {
      mdInput.classList.remove('hidden');
      mdPreview.classList.add('hidden');
      icon.setAttribute('data-feather', 'eye');
    }
    feather.replace();
  });

  // Export Markdown (.md)
  document.getElementById('export-md-btn').addEventListener('click', () => {
    const blob = new Blob([appState.journal], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `savage-warrior-log-${new Date().toISOString().slice(0,10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // --- 1RM CALCULATOR WIDGET ---
  document.getElementById('calc-weight').addEventListener('input', update1RM);
  document.getElementById('calc-reps').addEventListener('input', update1RM);

  function update1RM() {
    const w = parseFloat(document.getElementById('calc-weight').value) || 0;
    const r = parseInt(document.getElementById('calc-reps').value) || 1;
    const rm = w * (1 + r / 30);
    document.getElementById('calc-1rm').textContent = rm.toFixed(1);
  }
  update1RM();

  document.getElementById('apply-to-stats-btn').addEventListener('click', () => {
    const rm = document.getElementById('calc-1rm').textContent;
    alert(`Estimated 1RM (${rm} kg) calculated. Keep driving forward!`);
  });

  // --- MODALS HANDLING ---
  
  // 1. PR Modal
  const prModal = document.getElementById('modal-new-pr');
  document.getElementById('open-pr-modal-btn').addEventListener('click', () => prModal.classList.remove('hidden'));
  document.getElementById('close-pr-modal').addEventListener('click', () => prModal.classList.add('hidden'));

  document.getElementById('pr-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const newPr = {
      id: Date.now(),
      exercise: document.getElementById('pr-exercise').value,
      weight: document.getElementById('pr-weight').value + ' kg',
      reps: parseInt(document.getElementById('pr-reps').value),
      rpe: parseFloat(document.getElementById('pr-rpe').value) || 9.0,
      date: 'Today, ' + new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      notes: document.getElementById('pr-notes').value
    };

    appState.prs.unshift(newPr);
    saveState();
    renderPRFlow();
    prModal.classList.add('hidden');
    document.getElementById('pr-form').reset();
  });

  // 2. Gear Modal
  const gearModal = document.getElementById('modal-gear');
  document.getElementById('open-gear-modal-btn').addEventListener('click', () => gearModal.classList.remove('hidden'));
  document.getElementById('close-gear-modal').addEventListener('click', () => gearModal.classList.add('hidden'));

  document.getElementById('gear-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const newGear = {
      id: Date.now(),
      name: document.getElementById('gear-name').value,
      category: document.getElementById('gear-category').value,
      durability: parseInt(document.getElementById('gear-durability').value),
      notes: document.getElementById('gear-notes').value
    };

    appState.gear.push(newGear);
    saveState();
    renderGear();
    gearModal.classList.add('hidden');
    document.getElementById('gear-form').reset();
  });

  // 3. Media Modal (WebP & MP3 Wallpaper Configuration)
  const mediaModal = document.getElementById('modal-media');
  document.getElementById('media-modal-btn').addEventListener('click', () => mediaModal.classList.remove('hidden'));
  document.getElementById('close-media-modal').addEventListener('click', () => mediaModal.classList.add('hidden'));
  document.getElementById('save-media-settings-btn').addEventListener('click', () => mediaModal.classList.add('hidden'));

  // MP3 File Uploader
  const mp3Input = document.getElementById('mp3-file-input');
  const mp3Label = document.getElementById('mp3-filename-label');
  mp3Input.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      mp3Label.textContent = file.name;
      const fileUrl = URL.createObjectURL(file);
      audioEl.src = fileUrl;
      document.getElementById('audio-src-file').checked = true;
      if (isAudioPlaying) {
        audioEl.play();
        stopSynthLoop();
      }
    }
  });

  // Image / WebP Wallpaper Uploader (Sets directly as App Wallpaper)
  const webpInput = document.getElementById('webp-file-input');
  const webpLabel = document.getElementById('webp-filename-label');

  webpInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      webpLabel.textContent = file.name;
      const reader = new FileReader();
      reader.onload = (event) => {
        const imageUrl = event.target.result;
        applyWallpaper(imageUrl);
        appState.wallpaper = imageUrl;
        saveState();
      };
      reader.readAsDataURL(file);
    }
  });

  // Preset background wallpaper buttons
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const presetKey = btn.getAttribute('data-bg');
      
      applyWallpaper(presetKey);
      appState.wallpaper = presetKey;
      saveState();
    });
  });

  // Reset daily routine button
  document.getElementById('reset-daily-routine-btn').addEventListener('click', () => {
    appState.protocol.forEach(p => p.completed = false);
    saveState();
    renderProtocol();
  });

  // Set today date display
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  document.getElementById('current-date-display').textContent = new Date().toLocaleDateString('en-US', options).toUpperCase();

  // Initial render calls
  renderProtocol();
  renderPRFlow();
  renderStats();
  renderGear();
});
