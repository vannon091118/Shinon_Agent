// shinon-ui.mjs — Female Cyberpunk Cyberdeck UI v2.5
export const HTML = `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#050811">
<meta name="description" content="Shinon Cyberdeck Control Plane — Female Cyberpunk AI Persona">
<title>Shinon · Cyberdeck Control Plane</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --s0:#050811;--s1:#0a0e1a;--s2:#0f172a;--s3:#162036;--s4:#1e2c4a;
  --t0:#e0f7fc;--t1:#94b9d0;--t2:#5c8098;--t3:#385268;
  --mood:#00f5d4;--mood-glow:rgba(0,245,212,0.25);
  --cyan:#00f5d4;--magenta:#ff007f;--purple:#9b5de5;--gold:#ffb703;
  --blue:#48cae4;--red:#ff2a6d;--green:#05ffa1;
  --border:rgba(0,245,212,0.12);--border-md:rgba(0,245,212,0.25);--border-hi:rgba(0,245,212,0.5);
  --bg:var(--s0);--bg2:var(--s1);--bg3:var(--s2);--bg4:var(--s3);
  --fg:var(--t0);--fg2:var(--t1);--fg3:var(--t2);--fg4:var(--t3);
  --accent:var(--cyan);--accent2:#05ffa1;
  --shadow:0 8px 32px rgba(0,0,0,0.6);--radius:10px;--radius-sm:6px;
  font-family:'Rajdhani','Segoe UI',sans-serif;background:var(--s0);color:var(--t0);line-height:1.5;
}

body{
  min-height:100vh;
  background:
    linear-gradient(180deg, rgba(5,8,17,0.92) 0%, rgba(5,8,17,0.97) 100%),
    radial-gradient(ellipse 60% 40% at 15% -10%,rgba(0,245,212,0.08) 0%,transparent 60%),
    radial-gradient(ellipse 50% 40% at 85% 110%,rgba(255,0,127,0.08) 0%,transparent 60%),
    var(--s0);
  overflow:hidden;
  position:relative;
}

/* CYBERDECK SCANLINES */
body::after{
  content:'';
  position:fixed;
  inset:0;
  background:linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.25) 50%), linear-gradient(90deg, rgba(255,0,0,0.01), rgba(0,255,0,0.005), rgba(0,0,255,0.01));
  background-size:100% 3px, 6px 100%;
  pointer-events:none;
  z-index:999;
  opacity:0.4;
}

::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--s4);border-radius:3px}
*{scrollbar-width:thin;scrollbar-color:var(--s4) transparent}

.app{display:grid;grid-template-columns:60px 1fr 340px;grid-template-rows:54px 1fr;height:100vh;overflow:hidden;position:relative;z-index:1}

.hud-box{position:relative;border:1px solid var(--border);background:rgba(10,14,26,0.7);backdrop-filter:blur(12px)}
.hud-box::before{content:'';position:absolute;top:-1px;left:-1px;width:8px;height:8px;border-top:2px solid var(--cyan);border-left:2px solid var(--cyan)}
.hud-box::after{content:'';position:absolute;bottom:-1px;right:-1px;width:8px;height:8px;border-bottom:2px solid var(--cyan);border-right:2px solid var(--cyan)}

.sidebar{grid-column:1;grid-row:1/-1;background:var(--s1);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:14px 0;gap:8px;z-index:10}
.sidebar-btn{width:42px;height:42px;border-radius:8px;border:1px solid transparent;background:transparent;color:var(--t2);cursor:pointer;font-size:19px;display:flex;align-items:center;justify-content:center;position:relative;transition:all .2s cubic-bezier(.2,.8,.2,1)}
.sidebar-btn:hover{background:rgba(0,245,212,.1);color:var(--cyan);border-color:var(--border-md);box-shadow:0 0 12px rgba(0,245,212,.2)}
.sidebar-btn.active{background:rgba(0,245,212,.15);color:var(--cyan);border-color:var(--cyan);box-shadow:0 0 16px rgba(0,245,212,.3)}
.sidebar-btn .badge{position:absolute;top:3px;right:3px;width:8px;height:8px;border-radius:50%;background:var(--red);display:none;border:1.5px solid var(--s1)}
.sidebar-btn .badge.show{display:block}
.sidebar-spacer{flex:1}

.header{grid-column:2/-1;grid-row:1;background:rgba(10,14,26,0.85);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 24px;z-index:5}
.header-logo{display:flex;align-items:center;gap:12px}
.header-logo h1{font-family:'Orbitron',sans-serif;font-weight:800;font-size:1.05rem;letter-spacing:.12em;text-transform:uppercase;background:linear-gradient(90deg,var(--cyan) 0%,var(--magenta) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.header-tag{font-family:'Share Tech Mono',monospace;font-size:.62rem;color:var(--magenta);padding:2px 8px;border:1px solid rgba(255,0,127,0.3);border-radius:4px;background:rgba(255,0,127,0.06);letter-spacing:.1em}
.header-right{display:flex;align-items:center;gap:14px;font-family:'Share Tech Mono',monospace;font-size:.72rem}
.status-dot{width:8px;height:8px;border-radius:50%}
.status-dot.live{background:var(--green);box-shadow:0 0 8px rgba(5,255,161,.6)}
.status-dot.dead{background:var(--red)}
#conn-text{color:var(--t3)}
#mood-text{color:var(--mood);font-weight:600;letter-spacing:.15em;transition:color .6s ease}

.page{display:none;flex:1;overflow:hidden}
.page.active{display:flex;flex-direction:column}
#page-chat{grid-column:2;grid-row:2;background:var(--s0)}
#page-stats{grid-column:2/-1;grid-row:2}

.shinon-panel{grid-column:3;grid-row:2;background:linear-gradient(180deg,var(--s1) 0%,var(--s0) 100%);border-left:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;position:relative}

.shinon-face-wrap{display:flex;flex-direction:column;align-items:center;padding:24px 16px 16px;flex-shrink:0;position:relative}
.mood-halo{position:absolute;top:18px;width:170px;height:170px;border-radius:50%;background:radial-gradient(circle,var(--mood-glow) 0%,transparent 70%);animation:haloBreath 3.5s ease-in-out infinite;transition:background .8s ease;pointer-events:none}
@keyframes haloBreath{0%,100%{opacity:.5;transform:scale(.94)}50%{opacity:1;transform:scale(1.06)}}
.mood-ring-outer{position:relative;width:144px;height:144px;flex-shrink:0}
.mood-ring-spin{position:absolute;inset:-4px;border-radius:50%;border:2px solid transparent;border-top-color:var(--mood);border-right-color:var(--mood);opacity:.7;animation:moodSpin 3s linear infinite;transition:border-color .6s ease}
.mood-ring-spin2{position:absolute;inset:-9px;border-radius:50%;border:1px solid transparent;border-bottom-color:var(--magenta);border-left-color:var(--magenta);opacity:.4;animation:moodSpin 6s linear infinite reverse}
@keyframes moodSpin{to{transform:rotate(360deg)}}
.mood-ring-border{position:absolute;inset:0;border-radius:50%;border:2px solid var(--mood);opacity:.3;transition:border-color .6s ease;animation:moodPulse 2s ease-in-out infinite}
@keyframes moodPulse{0%,100%{opacity:.2}50%{opacity:.6}}

.shinon-face-inner{width:130px;height:130px;border-radius:50%;overflow:hidden;position:relative;animation:faceBob 4s ease-in-out infinite;box-shadow:0 0 20px var(--mood-glow);border:2px solid var(--border-hi);transition:box-shadow .6s ease;background:var(--s1)}
@keyframes faceBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
.shinon-face-img{width:100%;height:100%;object-fit:cover;display:block;filter:contrast(1.05) brightness(1.02)}

.shinon-title-wrap{text-align:center;margin-top:12px}
.shinon-name{font-family:'Orbitron',sans-serif;font-weight:800;font-size:.85rem;letter-spacing:.25em;text-transform:uppercase;color:var(--mood);transition:color .6s ease}
.shinon-sub{font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:.15em;color:var(--magenta);margin-top:2px}
.shinon-status{font-family:'Share Tech Mono',monospace;font-size:.65rem;letter-spacing:.12em;color:var(--t2);margin-top:4px;transition:all .4s}

.pipeline-section{flex:1;display:flex;flex-direction:column;overflow:hidden;padding:0 12px 12px;position:relative}
.pipeline-header{font-family:'Share Tech Mono',monospace;font-size:.65rem;letter-spacing:.12em;text-transform:uppercase;color:var(--t2);padding:8px;flex-shrink:0;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border)}
.pipeline-canvas{flex:1;display:block;width:100%}
.debug-toggle{background:rgba(0,245,212,0.06);border:1px solid var(--border-md);color:var(--t2);font-family:'Share Tech Mono',monospace;font-size:.6rem;padding:3px 10px;border-radius:4px;cursor:pointer;letter-spacing:.08em;transition:all .2s}
.debug-toggle:hover{color:var(--cyan);border-color:var(--cyan);background:rgba(0,245,212,0.15)}

.chat-messages{flex:1;overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:18px}
.chat-msg{display:flex;gap:12px;max-width:88%;animation:msgSlide .3s cubic-bezier(.2,.8,.2,1)}
@keyframes msgSlide{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.chat-msg.user{align-self:flex-end;flex-direction:row-reverse}
.chat-msg.shinon{align-self:flex-start}
.chat-avatar{width:38px;height:38px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:16px;overflow:hidden}
.chat-msg.user .chat-avatar{background:var(--s3);color:var(--t1);border:1px solid var(--border-md)}
.chat-msg.shinon .chat-avatar{background:var(--s1);border:2px solid var(--mood);box-shadow:0 0 12px var(--mood-glow);transition:border-color .6s,box-shadow .6s;padding:0}
.chat-avatar-face{width:100%;height:100%;object-fit:cover;border-radius:50%}
.chat-bubble-wrap{display:flex;flex-direction:column;gap:4px}
.chat-bubble{padding:12px 16px;font-size:.9rem;line-height:1.6;border-radius:12px;position:relative}
.chat-msg.user .chat-bubble{background:linear-gradient(135deg,var(--s3) 0%,var(--s4) 100%);border:1px solid var(--border-md);color:var(--t0);border-radius:12px 12px 2px 12px}
.chat-msg.shinon .chat-bubble{background:linear-gradient(135deg,rgba(0,245,212,0.06) 0%,rgba(155,93,229,0.04) 100%);border:1px solid var(--border-md);border-radius:12px 12px 12px 2px}
.model-badge{font-family:'Share Tech Mono',monospace;font-size:.6rem;color:var(--magenta);letter-spacing:.08em;padding-left:2px}
.typing-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--cyan);animation:typingBounce 1.4s infinite;margin:0 2px}
.typing-dot:nth-child(2){animation-delay:.2s}
.typing-dot:nth-child(3){animation-delay:.4s}
@keyframes typingBounce{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-4px)}}

.chat-empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:40px;text-align:center}
.chat-empty-avatar{width:96px;height:96px;border-radius:50%;overflow:hidden;border:2px solid var(--cyan);box-shadow:0 0 28px rgba(0,245,212,0.35);margin-bottom:4px}
.chat-empty-avatar img{width:100%;height:100%;object-fit:cover}
.chat-empty h2{font-family:'Orbitron',sans-serif;font-weight:800;font-size:1.5rem;letter-spacing:.1em;background:linear-gradient(135deg,var(--cyan),var(--magenta));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.chat-empty p{color:var(--t1);font-size:.9rem;line-height:1.7;max-width:420px}
.hint-chips{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:8px}
.hint-chip{padding:6px 16px;border:1px solid var(--border-md);border-radius:20px;font-size:.78rem;font-family:'Share Tech Mono',monospace;color:var(--t1);cursor:pointer;background:rgba(0,245,212,0.04);transition:all .2s}
.hint-chip:hover{background:rgba(0,245,212,0.12);border-color:var(--cyan);color:var(--cyan);box-shadow:0 0 12px rgba(0,245,212,0.2);transform:translateY(-1px)}

.chat-input-area{padding:16px 24px;border-top:1px solid var(--border);background:rgba(10,14,26,0.8);backdrop-filter:blur(12px);flex-shrink:0}
.chat-input-row{display:flex;gap:12px;align-items:flex-end}
.chat-input-row textarea{flex:1;padding:12px 16px;border:1px solid var(--border-md);border-radius:10px;background:rgba(22,32,54,0.8);color:var(--t0);font:inherit;font-size:.92rem;resize:none;min-height:48px;max-height:140px;outline:none;transition:border-color .3s,box-shadow .3s;line-height:1.5}
.chat-input-row textarea::placeholder{color:var(--t3)}
.chat-input-row textarea:focus{border-color:var(--cyan);box-shadow:0 0 16px rgba(0,245,212,0.15)}
.chat-send-btn{width:48px;height:48px;border:none;border-radius:10px;background:linear-gradient(135deg,var(--cyan),var(--accent2));color:var(--s0);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .25s;flex-shrink:0;box-shadow:0 0 18px rgba(0,245,212,0.3)}
.chat-send-btn:hover{box-shadow:0 0 28px rgba(0,245,212,0.5);transform:translateY(-1px) scale(1.03)}
.chat-send-btn:disabled{opacity:.4;cursor:not-allowed;transform:none;box-shadow:none}

.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;padding:20px 24px;overflow-y:auto;flex:1;align-content:start}
.stat-card{background:linear-gradient(135deg,var(--s2) 0%,var(--s1) 100%);border:1px solid var(--border);border-radius:10px;padding:18px;position:relative}
.stat-card::before{content:'';position:absolute;top:-1px;left:-1px;width:6px;height:6px;border-top:1.5px solid var(--cyan);border-left:1.5px solid var(--cyan)}
.stat-card .card-title{font:700 .7rem 'Orbitron',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--cyan);margin-bottom:14px}
.stat-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0}
.stat-row+.stat-row{border-top:1px solid var(--border)}
.stat-label{color:var(--t2);font-size:.8rem}
.stat-value{font:700 .88rem 'Share Tech Mono',monospace}
.stat-value.good{color:var(--green)}.stat-value.warn{color:var(--gold)}.stat-value.bad{color:var(--red)}
.key-chip{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:12px;font-size:.74rem;font-family:'Share Tech Mono',monospace;background:var(--s3);border:1px solid var(--border)}
.key-chip .dot{width:6px;height:6px;border-radius:50%}
.key-chip .dot.active{background:var(--green);box-shadow:0 0 6px var(--green)}.key-chip .dot.cooldown{background:var(--gold)}.key-chip .dot.dead{background:var(--red)}

.settings-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:100;display:none;opacity:0;transition:opacity .25s}
.settings-overlay.open{display:block;opacity:1}
.settings-panel{position:fixed;top:0;right:0;bottom:0;width:420px;max-width:92vw;background:var(--s1);border-left:1px solid var(--border);z-index:101;transform:translateX(100%);transition:transform .3s cubic-bezier(.2,.8,.2,1);display:flex;flex-direction:column;overflow-y:auto}
.settings-panel.open{transform:translateX(0)}
.settings-header{padding:20px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.settings-header h2{font:700 1.05rem 'Orbitron',sans-serif;letter-spacing:.08em;color:var(--cyan)}
.settings-close{width:32px;height:32px;border:1px solid var(--border);border-radius:6px;background:var(--s2);color:var(--t2);cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;transition:all .2s}
.settings-close:hover{background:var(--s3);color:var(--t0);border-color:var(--cyan)}
.settings-body{padding:22px 24px;display:flex;flex-direction:column;gap:24px;flex:1}
.settings-section h3{font:700 .7rem 'Share Tech Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--magenta);margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.settings-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0}
.settings-row label{font-size:.88rem;color:var(--t1)}
.settings-row input[type=range]{width:140px;accent-color:var(--cyan)}
.settings-row .range-val{font:700 .82rem 'Share Tech Mono',monospace;color:var(--cyan);min-width:26px;text-align:right}
.settings-row input[type=password],.settings-row input[type=text]{flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:6px;background:var(--s2);color:var(--t0);font:inherit;font-size:.85rem;outline:none}
.settings-row select{padding:8px 12px;border:1px solid var(--border);border-radius:6px;background:var(--s2);color:var(--t0);font:inherit;font-size:.85rem;min-width:130px}
.btn-save{background:var(--cyan);color:var(--s0);font-family:'Rajdhani',sans-serif;font-weight:700;padding:6px 18px;border:none;border-radius:6px;cursor:pointer;transition:all .2s}.btn-save:hover{background:var(--accent2);box-shadow:0 0 12px rgba(0,245,212,0.4)}
.settings-toast{padding:8px 14px;border-radius:6px;font-size:.8rem;font-family:'Share Tech Mono',monospace;display:none}
.settings-toast.show{display:block}
.settings-toast.ok{background:rgba(5,255,161,0.12);color:var(--green);border:1px solid var(--green)}
.settings-toast.err{background:rgba(255,42,109,0.12);color:var(--red);border:1px solid var(--red)}

.debug-overlay{position:fixed;inset:0;z-index:200;background:rgba(5,8,17,0.95);backdrop-filter:blur(14px);display:none;flex-direction:column}
.debug-overlay.open{display:flex}
.debug-header{padding:14px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.debug-header h2{font:700 .75rem 'Orbitron',sans-serif;letter-spacing:.15em;text-transform:uppercase;color:var(--cyan)}
.debug-close{width:30px;height:30px;background:rgba(0,245,212,0.1);border:1px solid var(--cyan);border-radius:6px;color:var(--cyan);cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;transition:all .2s}
.debug-close:hover{background:rgba(0,245,212,0.25)}
.debug-body{flex:1;overflow-y:auto;padding:20px 24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;align-content:start}

@media(max-width:900px){.app{grid-template-columns:50px 1fr}.shinon-panel{display:none}#page-chat{grid-column:2}#page-stats{grid-column:2}.header{grid-column:2}}
@media(max-width:640px){.stats-grid{grid-template-columns:1fr}.settings-panel{width:100vw}.chat-msg{max-width:96%}}
</style>
</head>
<body>
<div class="app">
  <nav class="sidebar">
    <button class="sidebar-btn active" id="btn-chat" data-page="chat" title="Chat" aria-label="Chat">💬</button>
    <button class="sidebar-btn" id="btn-stats" data-page="stats" title="Statistiken" aria-label="Statistiken">📊</button>
    <div class="sidebar-spacer"></div>
    <button class="sidebar-btn" id="btn-debug" title="Pipeline Debug" aria-label="Debug">🔬</button>
    <button class="sidebar-btn" id="btn-settings" title="Einstellungen" aria-label="Einstellungen">⚙️<span class="badge" id="keys-badge"></span></button>
  </nav>
  <header class="header">
    <div class="header-logo">
      <h1 id="page-title">Shinon · Cyberdeck Plane</h1>
      <span class="header-tag">CYBERNETIC AI</span>
    </div>
    <div class="header-right">
      <span id="conn-dot" class="status-dot live"></span>
      <span id="conn-text">ONLINE</span>
      <span>·</span>
      <span id="mood-text">IDLE</span>
    </div>
  </header>
  <section class="page active" id="page-chat">
    <div class="chat-messages" id="chat-messages">
      <div class="chat-empty" id="chat-empty">
        <div class="chat-empty-avatar">
          <img src="/assets/shinon_face.jpg" alt="Shinon Cyberdeck AI">
        </div>
        <h2>Shinon</h2>
        <p>Sie ist Shinon &mdash; deine skeptische Cyberdeck-KI.<br>Kritisch. Skeptisch. Präzise. Hinterfragt jede Annahme.</p>
        <div class="hint-chips">
          <span class="hint-chip" onclick="fillHint(this)">Was kannst du?</span>
          <span class="hint-chip" onclick="fillHint(this)">Erkläre die Pipeline</span>
          <span class="hint-chip" onclick="fillHint(this)">Was ist LIMEN?</span>
          <span class="hint-chip" onclick="fillHint(this)">Hinterfrage diese Idee…</span>
        </div>
      </div>
    </div>
    <div class="chat-input-area">
      <div class="chat-input-row">
        <textarea id="chat-input" rows="1" placeholder="Nachricht an Shinon…" aria-label="Chat-Nachricht"></textarea>
        <button class="chat-send-btn" id="chat-send" aria-label="Senden">▶</button>
      </div>
    </div>
  </section>
  <section class="page" id="page-stats">
    <div class="stats-grid" id="stats-grid"></div>
  </section>
  <div class="shinon-panel hud-box" id="shinon-panel">
    <div class="shinon-face-wrap">
      <div class="mood-halo" id="mood-halo"></div>
      <div class="mood-ring-outer">
        <div class="mood-ring-spin" id="ring-spin"></div>
        <div class="mood-ring-spin2" id="ring-spin2"></div>
        <div class="mood-ring-border" id="ring-border"></div>
        <div class="shinon-face-inner" id="shinon-face-inner">
          <img class="shinon-face-img" id="shinon-portrait" src="/assets/shinon_face.jpg" alt="Shinon AI Avatar">
        </div>
      </div>
      <div class="shinon-title-wrap">
        <div class="shinon-name" id="shinon-name">SHINON</div>
        <div class="shinon-sub">CYBERDECK PERSONA</div>
        <div class="shinon-status" id="shinon-status">◉ BEREIT</div>
      </div>
    </div>
    <div class="pipeline-section">
      <div class="pipeline-header">
        <span>SYSTEM PIPELINE</span>
        <button class="debug-toggle" id="debug-toggle-btn">DEBUG</button>
      </div>
      <canvas class="pipeline-canvas" id="pipeline-canvas"></canvas>
    </div>
  </div>
</div>

<div class="settings-overlay" id="settings-overlay"></div>
<aside class="settings-panel" id="settings-panel">
  <div class="settings-header">
    <h2>⚙️ Einstellungen</h2>
    <button class="settings-close" id="settings-close" aria-label="Schließen">✕</button>
  </div>
  <div class="settings-body">
    <div class="settings-section">
      <h3>🎨 Design</h3>
      <div class="settings-row">
        <label>Dark Mode</label>
        <input type="range" id="theme-toggle" min="0" max="1" value="1" oninput="toggleTheme(this.value)" aria-label="Theme">
      </div>
    </div>
    <div class="settings-section">
      <h3>🎭 Persönlichkeit <span class="tooltip" data-tip="Shinon bleibt immer kritisch. Werte justieren NUR Intensität.">ⓘ</span></h3>
      <div id="personality-sliders"></div>
    </div>
    <div class="settings-section">
      <h3>🔑 API-Keys</h3>
      <div id="keys-list"></div>
      <div class="settings-row" style="margin-top:8px;gap:8px">
        <select id="key-provider" aria-label="Anbieter">
          <option value="groq">Groq</option>
          <option value="openrouter">OpenRouter</option>
          <option value="nvidia">NVIDIA</option>
          <option value="mistral">Mistral</option>
        </select>
        <input type="password" id="key-value" placeholder="API-Key…" aria-label="Key">
        <button class="btn-save" id="key-save-btn">Speichern</button>
      </div>
      <div class="settings-toast" id="key-toast"></div>
    </div>
    <div class="settings-section">
      <h3>ℹ️ Über Shinon</h3>
      <p style="font-size:.82rem;color:var(--t1);line-height:1.7">
        Shinon Control Plane v2.0 &middot; Cyberdeck Engine<br>
        LIMEN Gateway &middot; KARMA FalsificationGate<br>
        goal-chain &middot; Promtguard &middot; skill-chains<br><br>
        <span class="tooltip" data-tip="Doctor Mous diagnostiziert Probleme ohne Secrets zu löschen.">🩺 Doctor Mous</span> &mdash; <code>./shinon doc</code>
      </p>
    </div>
  </div>
</aside>

<div class="debug-overlay" id="debug-overlay">
  <div class="debug-header">
    <h2>🔬 Cyberdeck Debug &middot; Dispatcher &middot; TID State &middot; Key Pool &middot; Mood Ring</h2>
    <button class="debug-close" id="debug-close">✕</button>
  </div>
  <div class="debug-body" id="debug-body">
    <div class="stat-card"><div class="card-title">⏳ Lade Debug-Daten…</div></div>
  </div>
</div>

<script>
const MOODS = {
  idle:  {color:'#00f5d4',glow:'rgba(0,245,212,0.25)', status:'◉ BEREIT',    moodText:'IDLE'},
  think: {color:'#ff007f',glow:'rgba(255,0,127,0.3)', status:'◎ VERARBEITE',moodText:'THINKING'},
  speak: {color:'#05ffa1',glow:'rgba(5,255,161,0.3)', status:'◉ ANTWORTET', moodText:'SPEAKING'},
  error: {color:'#ff2a6d',glow:'rgba(255,42,109,0.35)', status:'⊗ FEHLER',    moodText:'ERROR'},
  gate:  {color:'#ffb703',glow:'rgba(255,183,3,0.3)',  status:'◎ GATE-CHECK',moodText:'VALIDATING'},
};
let currentMood = 'idle';

function setMood(mood) {
  if (mood === currentMood) return;
  currentMood = mood;
  const m = MOODS[mood] || MOODS.idle;
  document.documentElement.style.setProperty('--mood', m.color);
  document.documentElement.style.setProperty('--mood-glow', m.glow);
  ['ring-spin','ring-spin2'].forEach(function(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.borderTopColor = m.color;
    el.style.borderRightColor = m.color;
    el.style.borderBottomColor = m.color;
    el.style.borderLeftColor = m.color;
  });
  const rb = document.getElementById('ring-border');
  if (rb) rb.style.borderColor = m.color;
  const halo = document.getElementById('mood-halo');
  if (halo) halo.style.background = 'radial-gradient(circle,'+m.glow+' 0%,transparent 70%)';
  const fi = document.getElementById('shinon-face-inner');
  if (fi) fi.style.boxShadow = '0 0 24px '+m.glow;
  const ns = document.getElementById('shinon-status');
  if (ns) { ns.innerHTML = m.status; ns.style.color = m.color; }
  const nn = document.getElementById('shinon-name');
  if (nn) nn.style.color = m.color;
  const mt = document.getElementById('mood-text');
  if (mt) { mt.textContent = m.moodText; mt.style.color = m.color; }
  document.querySelectorAll('.shinon-chat-avatar').forEach(function(el) {
    el.style.borderColor = m.color;
    el.style.boxShadow = '0 0 14px '+m.glow;
  });
}

const state = {
  page:'chat', messages:[], keys:[], theme:'dark',
  personality:{skepticism:8,directness:7,helpfulness:4,patience:5,curiosity:6}
};

function switchPage(page) {
  state.page = page;
  document.querySelectorAll('.page').forEach(function(p){ p.classList.remove('active'); });
  document.getElementById('page-'+page).classList.add('active');
  document.querySelectorAll('.sidebar-btn[data-page]').forEach(function(b){ b.classList.remove('active'); });
  const active = document.querySelector('.sidebar-btn[data-page="'+page+'"]');
  if (active) active.classList.add('active');
  const titles = {chat:'Shinon · Cyberdeck Plane', stats:'Statistiken & Tracking'};
  document.getElementById('page-title').textContent = titles[page] || 'Shinon';
  const sp = document.getElementById('shinon-panel');
  if (sp) sp.style.display = page==='chat' ? '' : 'none';
  if (page==='stats') loadStats();
  if (page==='chat') setTimeout(resizePipeline, 80);
}
document.querySelectorAll('.sidebar-btn[data-page]').forEach(function(btn) {
  btn.addEventListener('click', function(){ switchPage(btn.dataset.page); });
});

const settingsOverlay = document.getElementById('settings-overlay');
const settingsPanel = document.getElementById('settings-panel');
function openSettings(){ settingsOverlay.classList.add('open'); settingsPanel.classList.add('open'); loadSettings(); }
function closeSettings(){ settingsOverlay.classList.remove('open'); settingsPanel.classList.remove('open'); }
document.getElementById('btn-settings').addEventListener('click', openSettings);
document.getElementById('settings-close').addEventListener('click', closeSettings);
settingsOverlay.addEventListener('click', closeSettings);

const debugOverlay = document.getElementById('debug-overlay');
const btnDebug = document.getElementById('btn-debug');
const btnDebugToggle = document.getElementById('debug-toggle-btn');
function openDebug(){ debugOverlay.classList.add('open'); btnDebug.classList.add('active'); btnDebugToggle.classList.add('active'); loadDebugData(); }
function closeDebug(){ debugOverlay.classList.remove('open'); btnDebug.classList.remove('active'); btnDebugToggle.classList.remove('active'); }
btnDebug.addEventListener('click', openDebug);
btnDebugToggle.addEventListener('click', openDebug);
document.getElementById('debug-close').addEventListener('click', closeDebug);

function fillHint(el){ const i=document.getElementById('chat-input'); i.value=el.textContent; i.focus(); }

const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send');

function makeShinonAvatar() {
  const m = MOODS[currentMood]||MOODS.idle;
  return '<div class="chat-avatar shinon-chat-avatar" style="border:2px solid '+m.color+';box-shadow:0 0 12px '+m.glow+';background:var(--s1);padding:0;">'
    + '<img class="chat-avatar-face" src="/assets/shinon_face.jpg" alt="Shinon" style="width:100%;height:100%;object-fit:cover;border-radius:50%">'
    + '</div>';
}

function addMessage(role, content, model) {
  const empty = document.getElementById('chat-empty');
  if (empty) empty.remove();
  const div = document.createElement('div');
  div.className = 'chat-msg '+role;
  if (role==='shinon') {
    div.innerHTML = makeShinonAvatar()
      + '<div class="chat-bubble-wrap"><div class="chat-bubble">'+escapeHtml(content)+'</div>'
      + (model ? '<div class="model-badge">via '+escapeHtml(model)+'</div>' : '')
      + '</div>';
  } else {
    div.innerHTML = '<div class="chat-avatar">👤</div>'
      + '<div class="chat-bubble-wrap"><div class="chat-bubble">'+escapeHtml(content)+'</div></div>';
  }
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTyping() {
  const empty = document.getElementById('chat-empty');
  if (empty) empty.remove();
  const div = document.createElement('div');
  div.className = 'chat-msg shinon'; div.id = 'typing-indicator';
  div.innerHTML = makeShinonAvatar()
    + '<div class="chat-bubble-wrap"><div class="chat-bubble">'
    + '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>'
    + '</div></div>';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
function removeTyping(){ const t=document.getElementById('typing-indicator'); if(t)t.remove(); }

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = ''; chatSendBtn.disabled = true;
  addMessage('user', text);
  setMood('think'); addTyping(); triggerPipelineAnimation();
  try {
    const res = await fetch('/api/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,personality:state.personality})});
    const data = await res.json();
    removeTyping(); setMood('speak');
    addMessage('shinon', data.reply||'(keine Antwort — ist LIMEN gestartet?)', data.model);
    setTimeout(function(){ setMood('idle'); }, 2800);
  } catch(e) {
    removeTyping(); setMood('error');
    addMessage('shinon', '⚠️ Keine Verbindung zum Server. Ist LIMEN gestartet? ./shinon start');
    setTimeout(function(){ setMood('idle'); }, 3500);
  }
  chatSendBtn.disabled = false; chatInput.focus();
}
chatSendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', function(e){ if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();} });

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/\n/g,'<br>');
}

// ════ PIPELINE ENGINE ════
const NODES = [
  {id:'dispatcher',label:'DISPATCHER',sub:'split input', color:'#ff007f'},
  {id:'worker0',   label:'WORKER A',  sub:'process',     color:'#48cae4'},
  {id:'worker1',   label:'WORKER B',  sub:'process',     color:'#48cae4'},
  {id:'worker2',   label:'WORKER C',  sub:'process',     color:'#48cae4'},
  {id:'router',    label:'ROUTER',    sub:'route to API', color:'#ffb703'},
  {id:'provider',  label:'LIMEN',     sub:'API gateway',  color:'#ff2a6d'},
  {id:'falsgate',  label:'FALSI-GATE',sub:'KARMA verify', color:'#05ffa1'},
  {id:'eviltwin',  label:'EVIL TWIN', sub:'adversarial',  color:'#9b5de5'},
  {id:'result',    label:'RESULT',    sub:'validated',    color:'#00f5d4'},
];
const EDGES = [
  ['dispatcher','worker0'],['dispatcher','worker1'],['dispatcher','worker2'],
  ['worker0','router'],['worker1','router'],['worker2','router'],
  ['router','provider'],
  ['provider','falsgate'],['provider','eviltwin'],
  ['falsgate','result'],['eviltwin','result'],
];
const P = {balls:[],nodeMap:{},activeUntil:{},tick:0,animating:false};

function computeLayout(W, H) {
  const nW=56,nH=26,gap=36;
  const rows=[['dispatcher'],['worker0','worker1','worker2'],['router'],['provider'],['falsgate','eviltwin'],['result']];
  const map={};
  rows.forEach(function(row,ri){
    const y=12+ri*(nH+gap);
    const totalW=row.length*nW+(row.length-1)*16;
    const startX=W/2-totalW/2;
    row.forEach(function(id,ci){ map[id]={x:startX+ci*(nW+16),y:y,w:nW,h:nH}; });
  });
  return map;
}

function makeBall(fromId, toId, color, label) {
  const src=P.nodeMap[fromId], dst=P.nodeMap[toId];
  if (!src||!dst) return null;
  return {x:src.x+src.w/2,y:src.y+src.h/2,fx:src.x+src.w/2,fy:src.y+src.h/2,tx:dst.x+dst.w/2,ty:dst.y+dst.h/2,progress:0,speed:0.013+Math.random()*0.007,color:color,label:label,r:4.5,done:false,trail:[]};
}

const ANIM_SEQ = [
  {from:'dispatcher',to:'worker0',color:'#ff007f',label:'task',delay:0},
  {from:'dispatcher',to:'worker1',color:'#ff007f',label:'task',delay:140},
  {from:'dispatcher',to:'worker2',color:'#ff007f',label:'task',delay:280},
  {from:'worker0',to:'router',color:'#48cae4',label:'',delay:680},
  {from:'worker1',to:'router',color:'#48cae4',label:'',delay:800},
  {from:'worker2',to:'router',color:'#48cae4',label:'',delay:920},
  {from:'router',to:'provider',color:'#ffb703',label:'req',delay:1300},
  {from:'provider',to:'falsgate',color:'#ff2a6d',label:'res',delay:2100},
  {from:'provider',to:'eviltwin',color:'#9b5de5',label:'↑',delay:2250},
  {from:'falsgate',to:'result',color:'#00f5d4',label:'✓',delay:3100},
  {from:'eviltwin',to:'result',color:'#9b5de5',label:'syn',delay:3300},
];

function triggerPipelineAnimation() {
  if (P.animating) return;
  P.animating = true;
  ANIM_SEQ.forEach(function(s) {
    setTimeout(function(){
      const ball = makeBall(s.from, s.to, s.color, s.label);
      if (ball) P.balls.push(ball);
      P.activeUntil[s.to] = Date.now()+700;
    }, s.delay);
  });
  setTimeout(function(){ P.animating=false; }, 4200);
}

function resizePipeline() {
  const canvas = document.getElementById('pipeline-canvas');
  if (!canvas) return;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width; canvas.height = rect.height;
  P.nodeMap = computeLayout(canvas.width, canvas.height);
  NODES.forEach(function(n){ P.activeUntil[n.id]=0; });
}

function drawPipeline() {
  const canvas = document.getElementById('pipeline-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  if (!W||!H){ requestAnimationFrame(drawPipeline); return; }
  ctx.clearRect(0,0,W,H);
  const now = Date.now();
  P.tick++;

  EDGES.forEach(function(e) {
    const pa=P.nodeMap[e[0]], pb=P.nodeMap[e[1]];
    if (!pa||!pb) return;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(pa.x+pa.w/2,pa.y+pa.h/2);
    ctx.lineTo(pb.x+pb.w/2,pb.y+pb.h/2);
    ctx.strokeStyle='rgba(0,245,212,0.12)';
    ctx.lineWidth=1;
    ctx.setLineDash([3,7]);
    ctx.lineDashOffset = -(P.tick*0.4);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  });

  NODES.forEach(function(node) {
    const p=P.nodeMap[node.id];
    if (!p) return;
    const active=(P.activeUntil[node.id]||0)>now;
    const cx=p.x+p.w/2, cy=p.y+p.h/2;
    if (active) {
      ctx.save(); ctx.shadowColor=node.color; ctx.shadowBlur=18;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(p.x-2,p.y-2,p.w+4,p.h+4,6); else ctx.rect(p.x-2,p.y-2,p.w+4,p.h+4);
      ctx.fillStyle=node.color+'18'; ctx.fill(); ctx.restore();
    }
    ctx.save(); ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(p.x,p.y,p.w,p.h,5); else ctx.rect(p.x,p.y,p.w,p.h);
    ctx.fillStyle=active?node.color+'1a':'rgba(15,23,42,0.9)';
    ctx.fill();
    ctx.strokeStyle=active?node.color:'rgba(0,245,212,0.18)';
    ctx.lineWidth=active?1.5:1; ctx.stroke(); ctx.restore();
    if (node.id.startsWith('worker')&&active) {
      const pulse=Math.sin(now*0.006+parseInt(node.id.slice(-1)))*0.5+0.5;
      ctx.save(); ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(p.x+4,p.y+4,p.w-8,p.h-8,3); else ctx.rect(p.x+4,p.y+4,p.w-8,p.h-8);
      ctx.strokeStyle=node.color; ctx.lineWidth=1; ctx.globalAlpha=pulse*0.5; ctx.stroke(); ctx.restore();
    }
    ctx.save();
    ctx.font='bold 6.5px "Share Tech Mono",monospace';
    ctx.fillStyle=active?node.color:'rgba(148,185,208,0.85)';
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText(node.label,cx,cy-3);
    ctx.font='5.5px "Share Tech Mono",monospace';
    ctx.fillStyle=active?node.color+'aa':'rgba(56,82,104,0.8)';
    ctx.fillText(node.sub,cx,cy+6);
    ctx.restore();
  });

  P.balls = P.balls.filter(function(b){ return !b.done; });
  P.balls.forEach(function(ball) {
    ball.progress = Math.min(1, ball.progress+ball.speed);
    const t=ball.progress;
    const ease=t<0.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
    ball.x=ball.fx+(ball.tx-ball.fx)*ease;
    ball.y=ball.fy+(ball.ty-ball.fy)*ease;
    ball.trail.push({x:ball.x,y:ball.y});
    if (ball.trail.length>10) ball.trail.shift();
    ball.trail.forEach(function(pt,i){
      if(i===0) return;
      ctx.save(); ctx.beginPath();
      ctx.moveTo(ball.trail[i-1].x,ball.trail[i-1].y);
      ctx.lineTo(pt.x,pt.y);
      ctx.strokeStyle=ball.color;
      ctx.globalAlpha=(i/ball.trail.length)*0.35;
      ctx.lineWidth=ball.r*0.7; ctx.lineCap='round'; ctx.stroke(); ctx.restore();
    });
    ctx.save(); ctx.shadowColor=ball.color; ctx.shadowBlur=10;
    ctx.beginPath(); ctx.arc(ball.x,ball.y,ball.r,0,Math.PI*2);
    ctx.fillStyle=ball.color; ctx.fill(); ctx.restore();
    if (ball.label) {
      ctx.save(); ctx.font='5.5px "Share Tech Mono",monospace';
      ctx.fillStyle=ball.color; ctx.textAlign='center';
      ctx.fillText(ball.label,ball.x,ball.y-ball.r-3); ctx.restore();
    }
    if (ball.progress>=1) ball.done=true;
  });

  if (!P.animating && P.tick%100===0) {
    const edge=EDGES[Math.floor(Math.random()*EDGES.length)];
    const b=makeBall(edge[0],edge[1],'rgba(0,245,212,0.25)','');
    if(b){b.r=2;b.speed=0.005;P.balls.push(b);}
  }
  requestAnimationFrame(drawPipeline);
}

function initPipeline(){ resizePipeline(); drawPipeline(); }
window.addEventListener('resize', resizePipeline);
setTimeout(initPipeline, 250);

async function loadStats() {
  try {
    const [kR,sR,tR] = await Promise.all([
      fetch('/api/keys').then(function(r){return r.json();}),
      fetch('/api/state').then(function(r){return r.json();}).catch(function(){return {};}),
      fetch('/api/triggers').then(function(r){return r.json();}).catch(function(){return {};}),
    ]);
    renderStats(kR,sR,tR);
  } catch(e) {
    document.getElementById('stats-grid').innerHTML='<div class="stat-card"><div class="card-title">⚠️ Nicht verfügbar</div><p style="color:var(--t2);font-size:.82rem">Server nicht erreichbar</p></div>';
  }
}

function renderStats(keysData, stateData, triggersData) {
  const grid=document.getElementById('stats-grid');
  const keys=keysData.keys||[];
  const active=keys.filter(function(k){return k.status==='active';}).length;
  const cooldown=keys.filter(function(k){return k.status==='cooldown';}).length;
  const dead=keys.filter(function(k){return k.status==='dead';}).length;
  const isOffline=!keys.length&&(!stateData||!stateData.total);
  let html='';
  html+='<div class="stat-card"><div class="card-title">🔑 API-Keys Pool</div>';
  if (isOffline) {
    html+='<div class="stat-row"><span class="stat-label" style="color:var(--t3)">Backend offline</span></div>';
    html+='<div class="stat-row"><span class="stat-label" style="font-size:.7rem;color:var(--gold)">./shinon start</span></div>';
  } else {
    html+='<div class="stat-row"><span class="stat-label">Aktiv</span><span class="stat-value good">'+active+'</span></div>';
    html+='<div class="stat-row"><span class="stat-label">Cooldown</span><span class="stat-value warn">'+cooldown+'</span></div>';
    html+='<div class="stat-row"><span class="stat-label">Dead</span><span class="stat-value bad">'+dead+'</span></div>';
    keys.slice(0,8).forEach(function(k){
      html+='<div class="stat-row"><span class="stat-label" style="font-size:.74rem">'+k.provider+'</span><span class="key-chip"><span class="dot '+k.status+'"></span>'+(k.health_pct||100)+'%</span></div>';
    });
  }
  html+='</div>';
  if (stateData.total!==undefined) {
    html+='<div class="stat-card"><div class="card-title">🎯 goal-chain TIDs</div>';
    html+='<div class="stat-row"><span class="stat-label">Gesamt</span><span class="stat-value">'+(stateData.total||0)+'</span></div>';
    html+='<div class="stat-row"><span class="stat-label">Erledigt</span><span class="stat-value good">'+(stateData.done||0)+'</span></div>';
    html+='<div class="stat-row"><span class="stat-label">In Arbeit</span><span class="stat-value warn">'+(stateData.in_progress||0)+'</span></div>';
    html+='<div class="stat-row"><span class="stat-label">Fehlgeschlagen</span><span class="stat-value bad">'+(stateData.failed||0)+'</span></div>';
    html+='</div>';
  }
  grid.innerHTML = html;
}

async function loadSettings() {
  try {
    const res = await fetch('/api/personality');
    state.personality = await res.json();
    renderPersonalitySliders();
  } catch(e){}
  loadKeys();
}

function renderPersonalitySliders() {
  const container = document.getElementById('personality-sliders');
  if (!container) return;
  let html = '';
  for (const [key, val] of Object.entries(state.personality)) {
    html += '<div class="settings-row"><label style="text-transform:capitalize">' + key + '</label>' +
      '<input type="range" min="0" max="10" value="' + val + '" oninput="updatePersonality(\'' + key + '\',this.value)" aria-label="' + key + '">' +
      '<span class="range-val" id="pv-' + key + '">' + val + '</span></div>';
  }
  container.innerHTML = html;
}

function updatePersonality(key, value) {
  state.personality[key] = parseInt(value);
  const el = document.getElementById('pv-' + key);
  if (el) el.textContent = value;
  fetch('/api/personality', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [key]: parseInt(value) }),
  }).catch(function(){});
}

async function loadKeys() {
  try {
    const res = await fetch('/api/keys');
    const data = await res.json();
    state.keys = data.keys || [];
    renderKeysList();
  } catch(e){}
}

function renderKeysList() {
  const container = document.getElementById('keys-list');
  if (!container) return;
  if (state.keys.length === 0) {
    container.innerHTML = '<div style="color:var(--t2);font-size:.82rem;padding:8px 0">Keine Keys konfiguriert</div>';
    return;
  }
  let html = '';
  for (const k of state.keys) {
    const icon = k.status === 'active' ? '🟢' : (k.status === 'cooldown' ? '🟡' : '🔴');
    html += '<div class="settings-row"><span>' + icon + ' ' + k.provider + '</span><span style="font-size:.74rem;color:var(--t2);font-family:monospace">Health: ' + (k.health_pct || 100) + '%</span></div>';
  }
  container.innerHTML = html;
}

const saveBtn = document.getElementById('key-save-btn');
if (saveBtn) {
  saveBtn.addEventListener('click', async function() {
    const provider = document.getElementById('key-provider').value;
    const value = document.getElementById('key-value').value.trim();
    if (!value) return;
    const toast = document.getElementById('key-toast');
    try {
      const res = await fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, value }),
      });
      if (res.ok) {
        document.getElementById('key-value').value = '';
        toast.textContent = '✓ Key gespeichert';
        toast.className = 'settings-toast ok show';
        loadKeys();
      } else {
        toast.textContent = '✗ Fehler beim Speichern';
        toast.className = 'settings-toast err show';
      }
    } catch(e) {
      toast.textContent = '✗ Keine Verbindung';
      toast.className = 'settings-toast err show';
    }
    setTimeout(function(){ toast.classList.remove('show'); }, 3000);
  });
}

function toggleTheme(v) {}

async function loadDebugData() {
  const body = document.getElementById('debug-body');
  if (!body) return;
  body.innerHTML = '<div class="stat-card"><div class="card-title">⏳ Lade Debug-Daten…</div></div>';
  try {
    const [stateR, keysR, trigR] = await Promise.all([
      fetch('/api/state').then(function(r){return r.json();}).catch(function(){return {};}),
      fetch('/api/keys').then(function(r){return r.json();}).catch(function(){return {};}),
      fetch('/api/triggers').then(function(r){return r.json();}).catch(function(){return {};}),
    ]);
    let html = '';
    html += '<div class="stat-card"><div class="card-title">⚙️ System State</div>';
    html += '<div class="stat-row"><span class="stat-label">Mode</span><span class="stat-value good">STANDALONE</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Port</span><span class="stat-value">4300</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Total Tasks</span><span class="stat-value">'+(stateR.total||0)+'</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Done</span><span class="stat-value good">'+(stateR.done||0)+'</span></div>';
    html += '</div>';
    html += '<div class="stat-card"><div class="card-title">🔑 Key Pool Status</div>';
    (keysR.keys||[]).forEach(function(k){
      html += '<div class="stat-row"><span class="stat-label">'+k.provider+'</span><span class="key-chip"><span class="dot '+k.status+'"></span>'+k.status+' ('+(k.health_pct||100)+'%)</span></div>';
    });
    if (!(keysR.keys||[]).length) html += '<div class="stat-row"><span class="stat-label">Keine Keys konfiguriert</span></div>';
    html += '</div>';
    html += '<div class="stat-card"><div class="card-title">⚡ Trigger Log</div>';
    (trigR.triggers||[]).forEach(function(t){
      html += '<div class="stat-row"><span class="stat-label" style="font-size:.7rem">'+t.skill+'</span><span class="stat-value">'+t.trigger_count+'x</span></div>';
    });
    if (!(trigR.triggers||[]).length) html += '<div class="stat-row"><span class="stat-label">Keine Triggers aufgezeichnet</span></div>';
    body.innerHTML = html;
  } catch(e) {
    body.innerHTML = '<div class="stat-card"><div class="card-title">⚠️ Debug-Fehler</div><p style="color:var(--red);font-size:.82rem">Daten konnten nicht geladen werden</p></div>';
  }
}
</script>
</body>
</html>\`;
