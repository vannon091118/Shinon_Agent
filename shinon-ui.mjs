// shinon-ui.mjs — Female Cyberpunk Cyberdeck UI v3.0
// ════════════════════════════════════════════════════════════════════════
// VOLLSTÄNDIG IMPLEMENTIERT — Keine Stubs
// ════════════════════════════════════════════════════════════════════════
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
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&family=JetBrains+Mono:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
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

/* === THEME VARIANTS === */
[data-theme="light"]{
  --s0:#f0f4f8;--s1:#dce9f3;--s2:#c9dde9;--s3:#b4cede;--s4:#9cbdd1;
  --t0:#0a1825;--t1:#1a3048;--t2:#2e4f6a;--t3:#3d6480;
  --border:rgba(0,80,120,0.18);--border-md:rgba(0,80,120,0.3);--border-hi:rgba(0,80,120,0.55);
  --mood-glow:rgba(0,120,200,0.2);
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
[data-theme="light"] body{
  background:linear-gradient(180deg,rgba(240,244,248,0.95) 0%,rgba(220,233,243,0.97) 100%),var(--s0);
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
  transition:opacity .4s;
}
[data-theme="light"] body::after{opacity:0.06;}

::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--s4);border-radius:3px}
*{scrollbar-width:thin;scrollbar-color:var(--s4) transparent}

.app{display:grid;grid-template-columns:54px 1fr 320px;grid-template-rows:54px 1fr;height:100vh;overflow:hidden;position:relative;z-index:1}

/* HUD BOX */
.hud-box{position:relative;border:1px solid var(--border);background:rgba(10,14,26,0.75);backdrop-filter:blur(14px)}
.hud-box::before{content:'';position:absolute;top:-1px;left:-1px;width:10px;height:10px;border-top:2px solid var(--cyan);border-left:2px solid var(--cyan);transition:border-color .6s}
.hud-box::after{content:'';position:absolute;bottom:-1px;right:-1px;width:10px;height:10px;border-bottom:2px solid var(--cyan);border-right:2px solid var(--cyan);transition:border-color .6s}

/* SIDEBAR */
.sidebar{grid-column:1;grid-row:1/-1;background:var(--s1);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:12px 0 16px;gap:6px;z-index:10;transition:background .3s}
.sidebar-btn{width:40px;height:40px;border-radius:8px;border:1px solid transparent;background:transparent;color:var(--t2);cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;position:relative;transition:all .2s cubic-bezier(.2,.8,.2,1);flex-shrink:0}
.sidebar-btn:hover{background:rgba(0,245,212,.1);color:var(--cyan);border-color:var(--border-md);box-shadow:0 0 12px rgba(0,245,212,.2)}
.sidebar-btn.active{background:rgba(0,245,212,.15);color:var(--cyan);border-color:var(--cyan);box-shadow:0 0 16px rgba(0,245,212,.3)}
.sidebar-btn .badge{position:absolute;top:3px;right:3px;width:8px;height:8px;border-radius:50%;background:var(--red);display:none;border:1.5px solid var(--s1);animation:pulseBadge 2s ease-in-out infinite}
.sidebar-btn .badge.show{display:block}
@keyframes pulseBadge{0%,100%{opacity:1}50%{opacity:0.4}}
.sidebar-spacer{flex:1}
.sidebar-logo{font-size:20px;margin-bottom:4px;opacity:0.7}

/* HEADER */
.header{grid-column:2/-1;grid-row:1;background:rgba(10,14,26,0.9);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px;z-index:5;transition:background .3s}
.header-logo{display:flex;align-items:center;gap:12px}
.header-logo h1{font-family:'Orbitron',sans-serif;font-weight:800;font-size:1rem;letter-spacing:.12em;text-transform:uppercase;background:linear-gradient(90deg,var(--cyan) 0%,var(--magenta) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.header-tag{font-family:'Share Tech Mono',monospace;font-size:.6rem;color:var(--magenta);padding:2px 7px;border:1px solid rgba(255,0,127,0.3);border-radius:4px;background:rgba(255,0,127,0.06);letter-spacing:.1em}
.header-right{display:flex;align-items:center;gap:12px;font-family:'Share Tech Mono',monospace;font-size:.7rem}
.status-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.status-dot.live{background:var(--green);box-shadow:0 0 8px rgba(5,255,161,.6);animation:dotPulse 2s ease-in-out infinite}
.status-dot.dead{background:var(--red)}
@keyframes dotPulse{0%,100%{box-shadow:0 0 8px rgba(5,255,161,.6)}50%{box-shadow:0 0 16px rgba(5,255,161,.9)}}
#conn-text{color:var(--t3);transition:color .3s}
#mood-text{color:var(--mood);font-weight:700;letter-spacing:.15em;transition:color .6s ease}
#model-text{color:var(--t3);font-size:.62rem;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* PAGES */
.page{display:none;flex:1;overflow:hidden}
.page.active{display:flex;flex-direction:column}
#page-chat{grid-column:2;grid-row:2;background:var(--s0)}
#page-stats{grid-column:2/-1;grid-row:2}
#page-log{grid-column:2/-1;grid-row:2}

/* SHINON PANEL */
.shinon-panel{grid-column:3;grid-row:2;background:linear-gradient(180deg,var(--s1) 0%,var(--s0) 100%);border-left:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;position:relative;transition:background .3s}

.shinon-face-wrap{display:flex;flex-direction:column;align-items:center;padding:20px 14px 12px;flex-shrink:0;position:relative}
.mood-halo{position:absolute;top:14px;width:160px;height:160px;border-radius:50%;background:radial-gradient(circle,var(--mood-glow) 0%,transparent 70%);animation:haloBreath 3.5s ease-in-out infinite;transition:background .8s ease;pointer-events:none}
@keyframes haloBreath{0%,100%{opacity:.5;transform:scale(.94)}50%{opacity:1;transform:scale(1.06)}}
.mood-ring-outer{position:relative;width:130px;height:130px;flex-shrink:0}
.mood-ring-spin{position:absolute;inset:-5px;border-radius:50%;border:2px solid transparent;border-top-color:var(--mood);border-right-color:var(--mood);opacity:.7;animation:moodSpin 2.5s linear infinite;transition:border-color .6s ease}
.mood-ring-spin2{position:absolute;inset:-11px;border-radius:50%;border:1px solid transparent;border-bottom-color:var(--magenta);border-left-color:var(--magenta);opacity:.4;animation:moodSpin 5.5s linear infinite reverse}
.mood-ring-ticks{position:absolute;inset:-18px;border-radius:50%;border:1px dashed rgba(0,245,212,0.15);animation:moodSpin 20s linear infinite}
@keyframes moodSpin{to{transform:rotate(360deg)}}
.mood-ring-border{position:absolute;inset:0;border-radius:50%;border:2px solid var(--mood);opacity:.3;transition:border-color .6s ease;animation:moodPulse 2.2s ease-in-out infinite}
@keyframes moodPulse{0%,100%{opacity:.2}50%{opacity:.65}}

.shinon-face-inner{width:120px;height:120px;border-radius:50%;overflow:hidden;position:relative;animation:faceBob 4.5s ease-in-out infinite;box-shadow:0 0 24px var(--mood-glow);border:2px solid var(--border-hi);transition:box-shadow .6s ease;background:var(--s1)}
@keyframes faceBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
.shinon-face-img{width:100%;height:100%;object-fit:cover;display:block;filter:contrast(1.06) brightness(1.02)}

.shinon-title-wrap{text-align:center;margin-top:10px}
.shinon-name{font-family:'Orbitron',sans-serif;font-weight:800;font-size:.82rem;letter-spacing:.25em;text-transform:uppercase;color:var(--mood);transition:color .6s ease}
.shinon-sub{font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:.15em;color:var(--magenta);margin-top:2px}
.shinon-status-wrap{display:flex;align-items:center;gap:6px;margin-top:6px;padding:4px 12px;border-radius:12px;background:rgba(0,245,212,0.06);border:1px solid var(--border);transition:all .4s}
.shinon-status{font-family:'Share Tech Mono',monospace;font-size:.65rem;letter-spacing:.12em;color:var(--t2);transition:color .4s}

/* PIPELINE SECTION */
.pipeline-section{flex:1;display:flex;flex-direction:column;overflow:hidden;padding:0 10px 10px;position:relative;min-height:0}
.pipeline-header{font-family:'Share Tech Mono',monospace;font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;color:var(--t2);padding:8px 4px;flex-shrink:0;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border)}
.pipeline-canvas{flex:1;display:block;width:100%;min-height:0}
.debug-toggle{background:rgba(0,245,212,0.06);border:1px solid var(--border-md);color:var(--t2);font-family:'Share Tech Mono',monospace;font-size:.58rem;padding:3px 9px;border-radius:4px;cursor:pointer;letter-spacing:.08em;transition:all .2s}
.debug-toggle:hover{color:var(--cyan);border-color:var(--cyan);background:rgba(0,245,212,0.15)}

/* CHAT MESSAGES */
.chat-messages{flex:1;overflow-y:auto;padding:20px 22px;display:flex;flex-direction:column;gap:16px}
.chat-msg{display:flex;gap:12px;max-width:90%;animation:msgSlide .35s cubic-bezier(.2,.8,.2,1)}
@keyframes msgSlide{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
.chat-msg.user{align-self:flex-end;flex-direction:row-reverse}
.chat-msg.shinon{align-self:flex-start}
.chat-avatar{width:36px;height:36px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:15px;overflow:hidden}
.chat-msg.user .chat-avatar{background:var(--s3);color:var(--t1);border:1px solid var(--border-md)}
.chat-msg.shinon .chat-avatar{background:var(--s1);border:2px solid var(--mood);box-shadow:0 0 12px var(--mood-glow);transition:border-color .6s,box-shadow .6s;padding:0}
.chat-avatar-face{width:100%;height:100%;object-fit:cover;border-radius:50%}
.chat-bubble-wrap{display:flex;flex-direction:column;gap:4px;max-width:100%}
.chat-bubble{padding:11px 15px;font-size:.9rem;line-height:1.65;border-radius:12px;position:relative;word-break:break-word}
.chat-msg.user .chat-bubble{background:linear-gradient(135deg,var(--s3) 0%,var(--s4) 100%);border:1px solid var(--border-md);color:var(--t0);border-radius:12px 12px 2px 12px}
.chat-msg.shinon .chat-bubble{background:linear-gradient(135deg,rgba(0,245,212,0.06) 0%,rgba(155,93,229,0.04) 100%);border:1px solid var(--border-md);border-radius:12px 12px 12px 2px}
.chat-bubble code{font-family:'JetBrains Mono',monospace;font-size:.82em;background:rgba(0,245,212,0.1);color:var(--cyan);padding:2px 5px;border-radius:4px;border:1px solid rgba(0,245,212,0.2)}
.chat-bubble pre{margin:8px 0;border-radius:8px;overflow:auto;background:var(--s2);border:1px solid var(--border)}
.chat-bubble pre code{background:transparent;border:none;padding:14px;display:block;color:var(--t1);font-size:.82em;line-height:1.6}
.chat-bubble strong{color:var(--t0);font-weight:700}
.chat-bubble em{color:var(--t1);font-style:italic}
.chat-bubble h3,.chat-bubble h2,.chat-bubble h1{font-family:'Orbitron',sans-serif;font-size:.78rem;letter-spacing:.1em;color:var(--mood);margin:8px 0 4px;padding-bottom:3px;border-bottom:1px solid var(--border)}
.chat-bubble ul,.chat-bubble ol{padding-left:18px;margin:6px 0}
.chat-bubble li{margin:3px 0;color:var(--t1)}
.chat-bubble a{color:var(--cyan);text-decoration:none;border-bottom:1px dashed rgba(0,245,212,0.4)}
.chat-bubble a:hover{border-bottom-style:solid}
.chat-bubble blockquote{border-left:3px solid var(--magenta);padding-left:12px;color:var(--t2);font-style:italic;margin:6px 0}
.chat-bubble hr{border:none;border-top:1px solid var(--border);margin:8px 0}
.model-badge{font-family:'Share Tech Mono',monospace;font-size:.58rem;color:var(--t3);letter-spacing:.08em;padding-left:2px}
.typing-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--cyan);animation:typingBounce 1.4s infinite;margin:0 2px}
.typing-dot:nth-child(2){animation-delay:.2s}.typing-dot:nth-child(3){animation-delay:.4s}
@keyframes typingBounce{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-5px)}}

.chat-empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:40px;text-align:center}
.chat-empty-avatar{width:90px;height:90px;border-radius:50%;overflow:hidden;border:2px solid var(--cyan);box-shadow:0 0 28px rgba(0,245,212,0.35);margin-bottom:4px;animation:faceBob 4.5s ease-in-out infinite}
.chat-empty-avatar img{width:100%;height:100%;object-fit:cover}
.chat-empty h2{font-family:'Orbitron',sans-serif;font-weight:800;font-size:1.4rem;letter-spacing:.1em;background:linear-gradient(135deg,var(--cyan),var(--magenta));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.chat-empty p{color:var(--t1);font-size:.88rem;line-height:1.7;max-width:380px}
.hint-chips{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:6px}
.hint-chip{padding:5px 14px;border:1px solid var(--border-md);border-radius:20px;font-size:.76rem;font-family:'Share Tech Mono',monospace;color:var(--t1);cursor:pointer;background:rgba(0,245,212,0.04);transition:all .2s;white-space:nowrap}
.hint-chip:hover{background:rgba(0,245,212,0.12);border-color:var(--cyan);color:var(--cyan);box-shadow:0 0 12px rgba(0,245,212,0.2);transform:translateY(-2px)}

.chat-input-area{padding:14px 20px;border-top:1px solid var(--border);background:rgba(10,14,26,0.85);backdrop-filter:blur(12px);flex-shrink:0}
.chat-input-row{display:flex;gap:10px;align-items:flex-end}
.chat-input-row textarea{flex:1;padding:11px 15px;border:1px solid var(--border-md);border-radius:10px;background:rgba(22,32,54,0.85);color:var(--t0);font:inherit;font-size:.9rem;resize:none;min-height:46px;max-height:140px;outline:none;transition:border-color .3s,box-shadow .3s;line-height:1.5}
.chat-input-row textarea::placeholder{color:var(--t3);font-style:italic}
.chat-input-row textarea:focus{border-color:var(--cyan);box-shadow:0 0 16px rgba(0,245,212,0.15)}
.chat-toolbar{display:flex;gap:6px;margin-bottom:8px;align-items:center}
.chat-tool-btn{background:rgba(0,245,212,0.06);border:1px solid var(--border);color:var(--t2);font-family:'Share Tech Mono',monospace;font-size:.62rem;padding:3px 10px;border-radius:5px;cursor:pointer;letter-spacing:.06em;transition:all .2s}
.chat-tool-btn:hover{color:var(--cyan);border-color:var(--cyan);background:rgba(0,245,212,0.14)}
.chat-tool-btn.active{color:var(--green);border-color:var(--green);background:rgba(5,255,161,0.1)}
.chat-send-btn{width:46px;height:46px;border:none;border-radius:10px;background:linear-gradient(135deg,var(--cyan),var(--accent2));color:var(--s0);font-size:17px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .25s;flex-shrink:0;box-shadow:0 0 16px rgba(0,245,212,0.3)}
.chat-send-btn:hover{box-shadow:0 0 28px rgba(0,245,212,0.5);transform:translateY(-1px) scale(1.04)}
.chat-send-btn:disabled{opacity:.4;cursor:not-allowed;transform:none;box-shadow:none}
.char-counter{font-family:'Share Tech Mono',monospace;font-size:.6rem;color:var(--t3);margin-left:auto;margin-right:4px}
.char-counter.warn{color:var(--gold)}

/* STATS PAGE */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;padding:18px 22px;overflow-y:auto;flex:1;align-content:start}
.stat-card{background:linear-gradient(135deg,var(--s2) 0%,var(--s1) 100%);border:1px solid var(--border);border-radius:10px;padding:16px;position:relative;transition:border-color .2s,box-shadow .2s}
.stat-card:hover{border-color:var(--border-md);box-shadow:0 4px 24px rgba(0,0,0,0.4)}
.stat-card::before{content:'';position:absolute;top:-1px;left:-1px;width:7px;height:7px;border-top:1.5px solid var(--cyan);border-left:1.5px solid var(--cyan)}
.stat-card .card-title{font:700 .68rem 'Orbitron',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--cyan);margin-bottom:12px;display:flex;align-items:center;justify-content:space-between}
.stat-card .card-badge{font-size:.62rem;color:var(--t3);font-weight:400;font-family:'Share Tech Mono',monospace;letter-spacing:.05em}
.stat-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0}
.stat-row+.stat-row{border-top:1px solid var(--border)}
.stat-label{color:var(--t2);font-size:.8rem}
.stat-value{font:700 .86rem 'Share Tech Mono',monospace}
.stat-value.good{color:var(--green)}.stat-value.warn{color:var(--gold)}.stat-value.bad{color:var(--red)}.stat-value.info{color:var(--cyan)}
.key-chip{display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:10px;font-size:.72rem;font-family:'Share Tech Mono',monospace;background:var(--s3);border:1px solid var(--border)}
.key-chip .dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.key-chip .dot.active{background:var(--green);box-shadow:0 0 6px var(--green)}.key-chip .dot.cooldown{background:var(--gold);box-shadow:0 0 6px var(--gold)}.key-chip .dot.dead{background:var(--red)}
.stats-refresh-bar{padding:10px 22px;border-top:1px solid var(--border);display:flex;align-items:center;gap:12px;font-family:'Share Tech Mono',monospace;font-size:.62rem;color:var(--t3);flex-shrink:0}
.stats-refresh-btn{background:rgba(0,245,212,0.08);border:1px solid var(--border-md);color:var(--cyan);font-family:'Share Tech Mono',monospace;font-size:.62rem;padding:4px 12px;border-radius:5px;cursor:pointer;transition:all .2s}
.stats-refresh-btn:hover{background:rgba(0,245,212,0.18);box-shadow:0 0 10px rgba(0,245,212,0.25)}

/* PROGRESS BAR */
.progress-bar-wrap{height:6px;border-radius:3px;background:var(--s3);overflow:hidden;margin-top:8px}
.progress-bar{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--cyan),var(--magenta));transition:width .5s ease;box-shadow:0 0 8px rgba(0,245,212,0.4)}

/* LOG PAGE */
.log-container{flex:1;overflow:auto;padding:18px 22px;font-family:'JetBrains Mono',monospace;font-size:.78rem;line-height:1.7;color:var(--t1)}
.log-entry{display:flex;gap:12px;padding:4px 0;border-bottom:1px solid rgba(0,245,212,0.05)}
.log-entry:hover{background:rgba(0,245,212,0.03)}
.log-ts{color:var(--t3);white-space:nowrap;flex-shrink:0}
.log-level{width:52px;text-align:center;border-radius:3px;font-size:.68rem;flex-shrink:0}
.log-level.INFO{background:rgba(0,245,212,0.1);color:var(--cyan)}
.log-level.WARN{background:rgba(255,183,3,0.1);color:var(--gold)}
.log-level.ERROR{background:rgba(255,42,109,0.1);color:var(--red)}
.log-msg{word-break:break-all;flex:1}
.log-filter-bar{padding:10px 22px;border-bottom:1px solid var(--border);display:flex;gap:8px;align-items:center;flex-shrink:0}
.log-filter-btn{font-family:'Share Tech Mono',monospace;font-size:.62rem;padding:3px 10px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--t2);cursor:pointer;transition:all .2s}
.log-filter-btn.active{border-color:var(--cyan);color:var(--cyan);background:rgba(0,245,212,0.08)}

/* SETTINGS */
.settings-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:100;display:none;opacity:0;transition:opacity .25s;backdrop-filter:blur(4px)}
.settings-overlay.open{display:block;opacity:1}
.settings-panel{position:fixed;top:0;right:0;bottom:0;width:400px;max-width:92vw;background:var(--s1);border-left:1px solid var(--border);z-index:101;transform:translateX(100%);transition:transform .3s cubic-bezier(.2,.8,.2,1);display:flex;flex-direction:column;overflow-y:auto}
.settings-panel.open{transform:translateX(0)}
.settings-header{padding:18px 22px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.settings-header h2{font:700 .95rem 'Orbitron',sans-serif;letter-spacing:.08em;color:var(--cyan)}
.settings-close{width:30px;height:30px;border:1px solid var(--border);border-radius:6px;background:var(--s2);color:var(--t2);cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;transition:all .2s}
.settings-close:hover{background:var(--s3);color:var(--t0);border-color:var(--cyan)}
.settings-body{padding:20px 22px;display:flex;flex-direction:column;gap:22px;flex:1}
.settings-section h3{font:700 .65rem 'Share Tech Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--magenta);margin-bottom:10px;padding-bottom:5px;border-bottom:1px solid var(--border)}
.settings-row{display:flex;align-items:center;justify-content:space-between;padding:7px 0;gap:12px}
.settings-row label{font-size:.86rem;color:var(--t1);flex-shrink:0}
.settings-row input[type=range]{flex:1;accent-color:var(--cyan);max-width:120px}
.settings-row .range-val{font:700 .8rem 'Share Tech Mono',monospace;color:var(--cyan);min-width:20px;text-align:right}
.settings-row input[type=password],.settings-row input[type=text]{flex:1;padding:7px 11px;border:1px solid var(--border);border-radius:6px;background:var(--s2);color:var(--t0);font:inherit;font-size:.83rem;outline:none;transition:border-color .2s}
.settings-row input:focus{border-color:var(--cyan)}
.settings-row select{padding:7px 11px;border:1px solid var(--border);border-radius:6px;background:var(--s2);color:var(--t0);font:inherit;font-size:.83rem;flex:1;max-width:160px}
.theme-toggle-wrap{display:flex;gap:6px}
.theme-btn{padding:5px 14px;border:1px solid var(--border);border-radius:5px;background:transparent;color:var(--t2);font-family:'Share Tech Mono',monospace;font-size:.65rem;cursor:pointer;transition:all .2s}
.theme-btn.active{border-color:var(--cyan);color:var(--cyan);background:rgba(0,245,212,0.1)}
.btn-save{background:var(--cyan);color:var(--s0);font-family:'Rajdhani',sans-serif;font-weight:700;padding:5px 16px;border:none;border-radius:6px;cursor:pointer;transition:all .2s;font-size:.88rem}
.btn-save:hover{background:var(--accent2);box-shadow:0 0 12px rgba(0,245,212,0.4)}
.btn-danger{background:rgba(255,42,109,0.12);color:var(--red);border:1px solid rgba(255,42,109,0.3);font-family:'Rajdhani',sans-serif;font-weight:700;padding:5px 14px;border-radius:6px;cursor:pointer;transition:all .2s;font-size:.88rem}
.btn-danger:hover{background:rgba(255,42,109,0.22);box-shadow:0 0 12px rgba(255,42,109,0.3)}
.settings-toast{padding:7px 12px;border-radius:6px;font-size:.78rem;font-family:'Share Tech Mono',monospace;display:none;margin-top:8px}
.settings-toast.show{display:block}
.settings-toast.ok{background:rgba(5,255,161,0.1);color:var(--green);border:1px solid rgba(5,255,161,0.3)}
.settings-toast.err{background:rgba(255,42,109,0.1);color:var(--red);border:1px solid rgba(255,42,109,0.3)}

/* DEBUG OVERLAY */
.debug-overlay{position:fixed;inset:0;z-index:200;background:rgba(5,8,17,0.96);backdrop-filter:blur(14px);display:none;flex-direction:column}
.debug-overlay.open{display:flex}
.debug-header{padding:12px 22px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;gap:14px}
.debug-header h2{font:700 .72rem 'Orbitron',sans-serif;letter-spacing:.15em;text-transform:uppercase;color:var(--cyan)}
.debug-tabs{display:flex;gap:4px}
.debug-tab{font-family:'Share Tech Mono',monospace;font-size:.62rem;padding:3px 10px;border-radius:4px;border:1px solid var(--border);background:transparent;color:var(--t2);cursor:pointer;transition:all .2s}
.debug-tab.active{border-color:var(--cyan);color:var(--cyan);background:rgba(0,245,212,0.08)}
.debug-close{width:28px;height:28px;background:rgba(0,245,212,0.08);border:1px solid var(--cyan);border-radius:5px;color:var(--cyan);cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;transition:all .2s}
.debug-close:hover{background:rgba(0,245,212,0.22)}
.debug-body{flex:1;overflow-y:auto;padding:18px 22px;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;align-content:start}
.debug-body.tab-tids{grid-template-columns:1fr}
.tid-table{width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;font-size:.76rem}
.tid-table th{text-align:left;padding:8px 10px;color:var(--cyan);border-bottom:1px solid var(--border);font-family:'Share Tech Mono',monospace;font-size:.65rem;letter-spacing:.08em}
.tid-table td{padding:6px 10px;border-bottom:1px solid rgba(0,245,212,0.05);color:var(--t1)}
.tid-table tr:hover td{background:rgba(0,245,212,0.04)}
.tid-badge{padding:2px 7px;border-radius:4px;font-size:.65rem;font-family:'Share Tech Mono',monospace}
.tid-badge.DONE{background:rgba(5,255,161,0.12);color:var(--green)}
.tid-badge.IN_PROGRESS{background:rgba(0,245,212,0.12);color:var(--cyan);animation:pulseBadge 2s infinite}
.tid-badge.PENDING{background:rgba(255,183,3,0.1);color:var(--gold)}
.tid-badge.FAILED{background:rgba(255,42,109,0.12);color:var(--red)}

/* NOTIFICATIONS / TOASTS */
.toast-container{position:fixed;bottom:24px;right:24px;z-index:500;display:flex;flex-direction:column;gap:8px;pointer-events:none}
.toast{padding:10px 16px;border-radius:8px;font-family:'Share Tech Mono',monospace;font-size:.76rem;animation:toastIn .3s cubic-bezier(.2,.8,.2,1);pointer-events:auto;display:flex;align-items:center;gap:8px;max-width:320px;box-shadow:0 8px 24px rgba(0,0,0,0.5)}
@keyframes toastIn{from{opacity:0;transform:translateX(24px)}to{opacity:1;transform:translateX(0)}}
.toast.ok{background:rgba(5,255,161,0.14);color:var(--green);border:1px solid rgba(5,255,161,0.3)}
.toast.err{background:rgba(255,42,109,0.14);color:var(--red);border:1px solid rgba(255,42,109,0.3)}
.toast.info{background:rgba(0,245,212,0.1);color:var(--cyan);border:1px solid var(--border-md)}

/* RESPONSIVE */
@media(max-width:960px){.app{grid-template-columns:48px 1fr}.shinon-panel{display:none}#page-chat{grid-column:2}#page-stats{grid-column:2}#page-log{grid-column:2}.header{grid-column:2}}
@media(max-width:640px){.stats-grid{grid-template-columns:1fr}.settings-panel{width:100vw}.chat-msg{max-width:98%}.chat-messages{padding:14px}.chat-input-area{padding:12px}}
</style>
</head>
<body>
<div class="app">
  <nav class="sidebar">
    <div class="sidebar-logo">🦇</div>
    <button class="sidebar-btn active" id="btn-chat" data-page="chat" title="Chat" aria-label="Chat">💬</button>
    <button class="sidebar-btn" id="btn-stats" data-page="stats" title="Statistiken" aria-label="Statistiken">📊</button>
    <button class="sidebar-btn" id="btn-log" data-page="log" title="Activity Log" aria-label="Log">📋</button>
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
      <span id="conn-dot" class="status-dot dead"></span>
      <span id="conn-text">VERBINDE…</span>
      <span style="color:var(--t3)">·</span>
      <span id="mood-text">INIT</span>
      <span style="color:var(--t3)">·</span>
      <span id="model-text">—</span>
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
          <span class="hint-chip" onclick="fillHint(this)">Wer bist du?</span>
          <span class="hint-chip" onclick="fillHint(this)">Hinterfrage diese Idee…</span>
        </div>
      </div>
    </div>
    <div class="chat-input-area">
      <div class="chat-toolbar">
        <button class="chat-tool-btn" id="btn-clear-chat" title="Chat leeren">🗑 CLEAR</button>
        <button class="chat-tool-btn" id="btn-pipeline-demo" title="Pipeline Demo">⚡ PIPELINE</button>
        <span class="char-counter" id="char-counter">0</span>
      </div>
      <div class="chat-input-row">
        <textarea id="chat-input" rows="1" placeholder="Nachricht an Shinon… (Enter = Senden, Shift+Enter = Zeilenumbruch)" aria-label="Chat-Nachricht"></textarea>
        <button class="chat-send-btn" id="chat-send" aria-label="Senden">▶</button>
      </div>
    </div>
  </section>
  <section class="page" id="page-stats">
    <div class="stats-grid" id="stats-grid">
      <div class="stat-card"><div class="card-title">⏳ Lade…</div></div>
    </div>
    <div class="stats-refresh-bar">
      <button class="stats-refresh-btn" id="stats-refresh-btn">↻ REFRESH</button>
      <span id="stats-last-update">Noch nicht geladen</span>
      <span style="margin-left:auto;font-size:.6rem">Auto-Refresh alle 30s</span>
    </div>
  </section>
  <section class="page" id="page-log">
    <div class="log-filter-bar">
      <span style="font-family:'Share Tech Mono',monospace;font-size:.65rem;color:var(--t2);letter-spacing:.1em">FILTER:</span>
      <button class="log-filter-btn active" data-level="ALL">ALL</button>
      <button class="log-filter-btn" data-level="INFO">INFO</button>
      <button class="log-filter-btn" data-level="WARN">WARN</button>
      <button class="log-filter-btn" data-level="ERROR">ERROR</button>
      <button class="log-filter-btn" style="margin-left:auto" id="log-clear-btn">CLEAR</button>
    </div>
    <div class="log-container" id="log-container">
      <div class="log-entry">
        <span class="log-ts">—</span>
        <span class="log-level INFO">INFO</span>
        <span class="log-msg">Shinon Cyberdeck UI v3.0 gestartet. Warte auf erste Aktivität…</span>
      </div>
    </div>
  </section>
  <div class="shinon-panel hud-box" id="shinon-panel">
    <div class="shinon-face-wrap">
      <div class="mood-halo" id="mood-halo"></div>
      <div class="mood-ring-outer">
        <div class="mood-ring-spin" id="ring-spin"></div>
        <div class="mood-ring-spin2" id="ring-spin2"></div>
        <div class="mood-ring-ticks"></div>
        <div class="mood-ring-border" id="ring-border"></div>
        <div class="shinon-face-inner" id="shinon-face-inner">
          <img class="shinon-face-img" id="shinon-portrait" src="/assets/shinon_face.jpg" alt="Shinon AI Avatar">
        </div>
      </div>
      <div class="shinon-title-wrap">
        <div class="shinon-name" id="shinon-name">SHINON</div>
        <div class="shinon-sub">CYBERDECK PERSONA</div>
        <div class="shinon-status-wrap">
          <div class="shinon-status" id="shinon-status">◉ BEREIT</div>
        </div>
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
        <label>Theme</label>
        <div class="theme-toggle-wrap">
          <button class="theme-btn active" id="theme-dark" onclick="setTheme('dark')">DARK</button>
          <button class="theme-btn" id="theme-light" onclick="setTheme('light')">LIGHT</button>
        </div>
      </div>
      <div class="settings-row">
        <label>Scanlines</label>
        <div class="theme-toggle-wrap">
          <button class="theme-btn active" id="scanlines-on" onclick="toggleScanlines(true)">AN</button>
          <button class="theme-btn" id="scanlines-off" onclick="toggleScanlines(false)">AUS</button>
        </div>
      </div>
    </div>
    <div class="settings-section">
      <h3>🎭 Persönlichkeit <small style="color:var(--t3);font-size:.6rem">(Shinon bleibt immer kritisch)</small></h3>
      <div id="personality-sliders"></div>
    </div>
    <div class="settings-section">
      <h3>🔑 API-Keys</h3>
      <div id="keys-list"></div>
      <div class="settings-row" style="margin-top:8px;flex-wrap:wrap;gap:6px">
        <select id="key-provider" aria-label="Anbieter" style="max-width:120px">
          <option value="groq">Groq</option>
          <option value="openrouter">OpenRouter</option>
          <option value="nvidia">NVIDIA</option>
          <option value="mistral">Mistral</option>
          <option value="anthropic">Anthropic</option>
          <option value="together">Together AI</option>
        </select>
        <input type="password" id="key-value" placeholder="API-Key…" aria-label="Key" style="flex:1;min-width:120px">
        <button class="btn-save" id="key-save-btn">Speichern</button>
      </div>
      <div class="settings-toast" id="key-toast"></div>
    </div>
    <div class="settings-section">
      <h3>ℹ️ Über Shinon</h3>
      <p style="font-size:.8rem;color:var(--t1);line-height:1.7">
        Shinon Control Plane v3.0 &middot; Cyberdeck Engine<br>
        LIMEN Gateway &middot; KARMA FalsificationGate<br>
        goal-chain 4-Phasen &middot; Promtguard &middot; Evil Twin Protocol<br><br>
        <span style="color:var(--t2)">🩺 Doctor Mous</span> &mdash; <code style="font-family:'JetBrains Mono',monospace;font-size:.8em;color:var(--cyan)">./shinon doc</code>
      </p>
      <div style="margin-top:10px">
        <button class="btn-danger" id="btn-clear-memory" style="font-size:.78rem">🗑 Chat-Verlauf löschen</button>
      </div>
    </div>
  </div>
</aside>

<div class="debug-overlay" id="debug-overlay">
  <div class="debug-header">
    <h2>🔬 Cyberdeck Debug</h2>
    <div class="debug-tabs">
      <button class="debug-tab active" data-tab="overview" onclick="switchDebugTab('overview')">ÜBERSICHT</button>
      <button class="debug-tab" data-tab="tids" onclick="switchDebugTab('tids')">TID STATE</button>
      <button class="debug-tab" data-tab="keys" onclick="switchDebugTab('keys')">KEY POOL</button>
    </div>
    <button class="debug-close" id="debug-close">✕</button>
  </div>
  <div class="debug-body" id="debug-body">
    <div class="stat-card"><div class="card-title">⏳ Lade Debug-Daten…</div></div>
  </div>
</div>

<div class="toast-container" id="toast-container"></div>

<script>
// ════ MOOD STATE MACHINE ════════════════════════════════════════════════
const MOODS = {
  idle:  {color:'#00f5d4',glow:'rgba(0,245,212,0.25)',  status:'◉ BEREIT',     moodText:'IDLE'},
  think: {color:'#ff007f',glow:'rgba(255,0,127,0.3)',   status:'◎ VERARBEITE', moodText:'THINKING'},
  speak: {color:'#05ffa1',glow:'rgba(5,255,161,0.3)',   status:'◉ ANTWORTET',  moodText:'SPEAKING'},
  error: {color:'#ff2a6d',glow:'rgba(255,42,109,0.35)', status:'⊗ FEHLER',     moodText:'ERROR'},
  gate:  {color:'#ffb703',glow:'rgba(255,183,3,0.3)',   status:'◎ GATE-CHECK', moodText:'VALIDATING'},
};
let currentMood = 'idle';
let moodTimer = null;

/** Apply mood globally — updates all visual elements */
function setMood(mood) {
  if (mood === currentMood) return;
  if (moodTimer) { clearTimeout(moodTimer); moodTimer = null; }
  currentMood = mood;
  const m = MOODS[mood] || MOODS.idle;
  const root = document.documentElement;
  root.style.setProperty('--mood', m.color);
  root.style.setProperty('--mood-glow', m.glow);

  const rs = document.getElementById('ring-spin');
  if (rs) { rs.style.borderTopColor = m.color; rs.style.borderRightColor = m.color; }
  const rb = document.getElementById('ring-border');
  if (rb) rb.style.borderColor = m.color;
  const halo = document.getElementById('mood-halo');
  if (halo) halo.style.background = 'radial-gradient(circle,'+m.glow+' 0%,transparent 70%)';
  const fi = document.getElementById('shinon-face-inner');
  if (fi) fi.style.boxShadow = '0 0 28px '+m.glow;
  const ns = document.getElementById('shinon-status');
  if (ns) { ns.innerHTML = m.status; ns.style.color = m.color; }
  const nn = document.getElementById('shinon-name');
  if (nn) nn.style.color = m.color;
  const mt = document.getElementById('mood-text');
  if (mt) { mt.textContent = m.moodText; mt.style.color = m.color; }
  const hw = document.querySelector('.hud-box');
  if (hw) {
    hw.style.setProperty('--mood', m.color);
  }
  document.querySelectorAll('.shinon-chat-avatar').forEach(function(el){
    el.style.borderColor = m.color;
    el.style.boxShadow = '0 0 14px '+m.glow;
  });
}

// ════ APP STATE ════════════════════════════════════════════════════════
const state = {
  page: 'chat',
  messages: [],
  keys: [],
  theme: 'dark',
  scanlines: true,
  serverOnline: false,
  lastModel: '—',
  personality: {skepticism:8, directness:7, helpfulness:4, patience:5, curiosity:6},
  logEntries: [],
  logFilter: 'ALL',
};

// ════ THEME SYSTEM ══════════════════════════════════════════════════════
function setTheme(theme) {
  state.theme = theme;
  document.documentElement.dataset.theme = theme === 'light' ? 'light' : '';
  document.getElementById('theme-dark').classList.toggle('active', theme === 'dark');
  document.getElementById('theme-light').classList.toggle('active', theme === 'light');
  localStorage.setItem('shinon-theme', theme);
}

function toggleScanlines(on) {
  state.scanlines = on;
  document.body.style.setProperty('--scanlines-opacity', on ? '0.4' : '0');
  // Patch the pseudo-element via class
  document.body.classList.toggle('no-scanlines', !on);
  document.getElementById('scanlines-on').classList.toggle('active', on);
  document.getElementById('scanlines-off').classList.toggle('active', !on);
  localStorage.setItem('shinon-scanlines', on ? '1' : '0');
}

// Add scanlines CSS toggle
(function(){ const s=document.createElement('style'); s.textContent='.no-scanlines::after{opacity:0!important}'; document.head.appendChild(s); })();

// ════ PAGE SWITCHING ═══════════════════════════════════════════════════
function switchPage(page) {
  state.page = page;
  document.querySelectorAll('.page').forEach(function(p){ p.classList.remove('active'); });
  const pg = document.getElementById('page-'+page);
  if (pg) pg.classList.add('active');
  document.querySelectorAll('.sidebar-btn[data-page]').forEach(function(b){ b.classList.remove('active'); });
  const ab = document.querySelector('.sidebar-btn[data-page="'+page+'"]');
  if (ab) ab.classList.add('active');
  const titles = {chat:'Shinon · Cyberdeck Plane', stats:'Statistiken & Tracking', log:'Activity Log'};
  document.getElementById('page-title').textContent = titles[page] || 'Shinon';
  const sp = document.getElementById('shinon-panel');
  if (sp) sp.style.display = (page === 'chat') ? '' : 'none';
  if (page === 'stats') loadStats();
  if (page === 'chat') setTimeout(resizePipeline, 80);
  if (page === 'log') renderLog();
}
document.querySelectorAll('.sidebar-btn[data-page]').forEach(function(btn){
  btn.addEventListener('click', function(){ switchPage(btn.dataset.page); });
});

// ════ SETTINGS ════════════════════════════════════════════════════════
const settingsOverlay = document.getElementById('settings-overlay');
const settingsPanel = document.getElementById('settings-panel');
function openSettings() { settingsOverlay.classList.add('open'); settingsPanel.classList.add('open'); loadSettings(); }
function closeSettings() { settingsOverlay.classList.remove('open'); settingsPanel.classList.remove('open'); }
document.getElementById('btn-settings').addEventListener('click', openSettings);
document.getElementById('settings-close').addEventListener('click', closeSettings);
settingsOverlay.addEventListener('click', closeSettings);

// ════ DEBUG OVERLAY ════════════════════════════════════════════════════
const debugOverlay = document.getElementById('debug-overlay');
let currentDebugTab = 'overview';

function openDebug() { debugOverlay.classList.add('open'); document.getElementById('btn-debug').classList.add('active'); loadDebugData(); }
function closeDebug() { debugOverlay.classList.remove('open'); document.getElementById('btn-debug').classList.remove('active'); }
function switchDebugTab(tab) {
  currentDebugTab = tab;
  document.querySelectorAll('.debug-tab').forEach(function(t){ t.classList.toggle('active', t.dataset.tab === tab); });
  const body = document.getElementById('debug-body');
  body.className = 'debug-body tab-' + tab;
  loadDebugData();
}
document.getElementById('btn-debug').addEventListener('click', openDebug);
document.getElementById('debug-toggle-btn').addEventListener('click', openDebug);
document.getElementById('debug-close').addEventListener('click', closeDebug);
document.addEventListener('keydown', function(e){ if (e.key === 'Escape') { closeDebug(); closeSettings(); } });

// ════ TOASTS ══════════════════════════════════════════════════════════
function showToast(msg, type) {
  type = type || 'info';
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(function(){ t.style.transition='opacity .3s'; t.style.opacity='0'; setTimeout(function(){ t.remove(); }, 350); }, 3200);
}

// ════ ACTIVITY LOG ════════════════════════════════════════════════════
function addLog(level, msg) {
  const entry = { ts: new Date().toLocaleTimeString('de-DE', {hour:'2-digit',minute:'2-digit',second:'2-digit'}), level: level, msg: msg };
  state.logEntries.push(entry);
  if (state.logEntries.length > 200) state.logEntries.shift();
  if (state.page === 'log') renderLog();
}

function renderLog() {
  const c = document.getElementById('log-container');
  if (!c) return;
  const filtered = state.logFilter === 'ALL' ? state.logEntries : state.logEntries.filter(function(e){ return e.level === state.logFilter; });
  if (!filtered.length) { c.innerHTML = '<div style="color:var(--t3);font-size:.8rem;padding:12px">Keine Einträge für diesen Filter.</div>'; return; }
  c.innerHTML = filtered.map(function(e){
    return '<div class="log-entry"><span class="log-ts">'+e.ts+'</span><span class="log-level '+e.level+'">'+e.level+'</span><span class="log-msg">'+escapeHtml(e.msg)+'</span></div>';
  }).join('');
  c.scrollTop = c.scrollHeight;
}

document.querySelectorAll('.log-filter-btn[data-level]').forEach(function(btn){
  btn.addEventListener('click', function(){
    state.logFilter = btn.dataset.level;
    document.querySelectorAll('.log-filter-btn[data-level]').forEach(function(b){ b.classList.remove('active'); });
    btn.classList.add('active');
    renderLog();
  });
});
document.getElementById('log-clear-btn').addEventListener('click', function(){
  state.logEntries = [];
  renderLog();
});

// ════ MARKDOWN RENDERER ════════════════════════════════════════════════
/** Parse simple Markdown into safe HTML for chat bubbles */
function renderMarkdown(text) {
  let html = escapeHtmlBase(text);
  // Code blocks (triple backtick)
  var codeBlockRe = new RegExp('\\x60\\x60\\x60([\\s\\S]*?)\\x60\\x60\\x60', 'g');
  html = html.replace(codeBlockRe, function(_, code){ return '<pre><code>' + code.trim() + '</code></pre>'; });
  // Inline code (single backtick)
  var inlineCodeRe = new RegExp('\\x60([^\\x60\\n]+)\\x60', 'g');
  html = html.replace(inlineCodeRe, '<code>$1</code>');
  // Bold **text**
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Italic *text*
  html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
  // Headings
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // Blockquotes
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  // Horizontal rule
  html = html.replace(/^---+$/gm, '<hr>');
  // Unordered lists
  html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
  // Numbered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  // Line breaks
  html = html.replace(/\n/g, '<br>');
  return html;
}

function escapeHtmlBase(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escapeHtml(s) {
  return escapeHtmlBase(s).replace(/\n/g,'<br>');
}

// ════ CHAT CORE ════════════════════════════════════════════════════════
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send');

function makeShinonAvatar() {
  const m = MOODS[currentMood] || MOODS.idle;
  return '<div class="chat-avatar shinon-chat-avatar" style="border:2px solid '+m.color+';box-shadow:0 0 12px '+m.glow+';background:var(--s1);padding:0;">'
    + '<img class="chat-avatar-face" src="/assets/shinon_face.jpg" alt="Shinon" style="width:100%;height:100%;object-fit:cover;border-radius:50%">'
    + '</div>';
}

function addMessage(role, content, model) {
  const empty = document.getElementById('chat-empty');
  if (empty) empty.remove();
  const div = document.createElement('div');
  div.className = 'chat-msg '+role;
  if (role === 'shinon') {
    div.innerHTML = makeShinonAvatar()
      + '<div class="chat-bubble-wrap"><div class="chat-bubble">'+renderMarkdown(content)+'</div>'
      + (model && model !== 'shinon-fallback' && model !== 'shinon-offline' ? '<div class="model-badge">via '+escapeHtml(model)+'</div>' : '')
      + '</div>';
    if (model) document.getElementById('model-text').textContent = model;
  } else {
    div.innerHTML = '<div class="chat-avatar">👤</div>'
      + '<div class="chat-bubble-wrap"><div class="chat-bubble">'+escapeHtml(content)+'</div></div>';
  }
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  state.messages.push({role:role, content:content, model:model||null});
  addLog(role==='shinon'?'INFO':'INFO', '['+role.toUpperCase()+'] '+content.slice(0,80)+(content.length>80?'…':''));
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
function removeTyping() { const t = document.getElementById('typing-indicator'); if (t) t.remove(); }

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text || chatSendBtn.disabled) return;
  chatInput.value = '';
  chatInput.style.height = 'auto';
  updateCharCounter();
  chatSendBtn.disabled = true;
  addMessage('user', text);
  setMood('think');
  addTyping();
  triggerPipelineAnimation();
  addLog('INFO', 'Chat-Anfrage gesendet: ' + text.slice(0,60));
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message:text, personality:state.personality})
    });
    const data = await res.json();
    removeTyping();
    setMood('gate');
    await new Promise(function(r){ setTimeout(r, 400); });
    setMood('speak');
    addMessage('shinon', data.reply || '(keine Antwort — ist LIMEN gestartet?)', data.model);
    moodTimer = setTimeout(function(){ setMood('idle'); }, 3200);
  } catch(e) {
    removeTyping();
    setMood('error');
    addMessage('shinon', '\u26a0\ufe0f Keine Verbindung zum Server. Ist LIMEN gestartet?\n\nStarte LIMEN: <code>./shinon start</code>');
    addLog('ERROR', 'Chat-Fehler: ' + e.message);
    moodTimer = setTimeout(function(){ setMood('idle'); }, 4000);
  }
  chatSendBtn.disabled = false;
  chatInput.focus();
}
chatSendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', function(e){
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// Auto-resize textarea
chatInput.addEventListener('input', function(){
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 140) + 'px';
  updateCharCounter();
});

function updateCharCounter() {
  const len = chatInput.value.length;
  const el = document.getElementById('char-counter');
  if (el) { el.textContent = len; el.className = 'char-counter' + (len > 800 ? ' warn' : ''); }
}

function fillHint(el) { const i = document.getElementById('chat-input'); i.value = el.textContent; i.focus(); updateCharCounter(); }

// Clear chat button
document.getElementById('btn-clear-chat').addEventListener('click', function(){
  state.messages = [];
  chatMessages.innerHTML = '';
  const empty = document.createElement('div');
  empty.className = 'chat-empty';
  empty.id = 'chat-empty';
  empty.innerHTML = '<div class="chat-empty-avatar"><img src="/assets/shinon_face.jpg" alt="Shinon Cyberdeck AI"></div>'
    + '<h2>Shinon</h2><p>Chat geleert. Was möchtest du fragen?</p>';
  chatMessages.appendChild(empty);
  addLog('INFO', 'Chat-Verlauf geleert.');
  showToast('Chat-Verlauf geleert.', 'info');
});
document.getElementById('btn-clear-memory').addEventListener('click', function(){
  document.getElementById('btn-clear-chat').click();
  closeSettings();
});

// Pipeline demo button
document.getElementById('btn-pipeline-demo').addEventListener('click', function(){
  triggerPipelineAnimation();
  showToast('Pipeline Demo gestartet.', 'info');
});

// ════ PIPELINE ENGINE ══════════════════════════════════════════════════
const NODES = [
  {id:'dispatcher',label:'DISPATCH', sub:'input split',  color:'#ff007f'},
  {id:'worker0',   label:'WORKER A', sub:'process A',    color:'#48cae4'},
  {id:'worker1',   label:'WORKER B', sub:'process B',    color:'#48cae4'},
  {id:'worker2',   label:'WORKER C', sub:'process C',    color:'#48cae4'},
  {id:'router',    label:'ROUTER',   sub:'route to API', color:'#ffb703'},
  {id:'provider',  label:'LIMEN',    sub:'API gateway',  color:'#ff2a6d'},
  {id:'falsgate',  label:'KARMA',    sub:'falsi-gate',   color:'#05ffa1'},
  {id:'eviltwin',  label:'EVIL TWN', sub:'adversarial',  color:'#9b5de5'},
  {id:'result',    label:'RESULT',   sub:'validated ✓',  color:'#00f5d4'},
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
  const nW=52, nH=24, gap=30;
  const rows=[['dispatcher'],['worker0','worker1','worker2'],['router'],['provider'],['falsgate','eviltwin'],['result']];
  const map={};
  rows.forEach(function(row,ri){
    const y = 8 + ri*(nH+gap);
    const totalW = row.length*nW+(row.length-1)*14;
    const startX = W/2-totalW/2;
    row.forEach(function(id,ci){ map[id]={x:startX+ci*(nW+14),y:y,w:nW,h:nH}; });
  });
  return map;
}

function makeBall(fromId, toId, color, label) {
  const src=P.nodeMap[fromId], dst=P.nodeMap[toId];
  if (!src||!dst) return null;
  return {x:src.x+src.w/2,y:src.y+src.h/2,fx:src.x+src.w/2,fy:src.y+src.h/2,tx:dst.x+dst.w/2,ty:dst.y+dst.h/2,progress:0,speed:0.014+Math.random()*0.008,color:color,label:label,r:4,done:false,trail:[]};
}

const ANIM_SEQ=[
  {from:'dispatcher',to:'worker0',color:'#ff007f',label:'A',delay:0},
  {from:'dispatcher',to:'worker1',color:'#ff007f',label:'B',delay:120},
  {from:'dispatcher',to:'worker2',color:'#ff007f',label:'C',delay:240},
  {from:'worker0',to:'router',color:'#48cae4',label:'',delay:650},
  {from:'worker1',to:'router',color:'#48cae4',label:'',delay:770},
  {from:'worker2',to:'router',color:'#48cae4',label:'',delay:890},
  {from:'router',to:'provider',color:'#ffb703',label:'req',delay:1250},
  {from:'provider',to:'falsgate',color:'#ff2a6d',label:'res',delay:2000},
  {from:'provider',to:'eviltwin',color:'#9b5de5',label:'↑',delay:2150},
  {from:'falsgate',to:'result',color:'#00f5d4',label:'✓',delay:2900},
  {from:'eviltwin',to:'result',color:'#9b5de5',label:'syn',delay:3100},
];

function triggerPipelineAnimation() {
  if (P.animating) return;
  P.animating = true;
  ANIM_SEQ.forEach(function(s){
    setTimeout(function(){
      const ball = makeBall(s.from,s.to,s.color,s.label);
      if (ball) P.balls.push(ball);
      P.activeUntil[s.to] = Date.now()+650;
    }, s.delay);
  });
  setTimeout(function(){ P.animating=false; }, 4000);
}

function resizePipeline() {
  const canvas=document.getElementById('pipeline-canvas');
  if (!canvas) return;
  const rect=canvas.parentElement.getBoundingClientRect();
  canvas.width=rect.width; canvas.height=rect.height;
  P.nodeMap=computeLayout(canvas.width,canvas.height);
  NODES.forEach(function(n){ P.activeUntil[n.id]=0; });
}

function drawPipeline() {
  const canvas=document.getElementById('pipeline-canvas');
  if (!canvas) return;
  const ctx=canvas.getContext('2d');
  const W=canvas.width, H=canvas.height;
  if (!W||!H){ requestAnimationFrame(drawPipeline); return; }
  ctx.clearRect(0,0,W,H);
  const now=Date.now();
  P.tick++;

  // Edges
  EDGES.forEach(function(e){
    const pa=P.nodeMap[e[0]],pb=P.nodeMap[e[1]];
    if (!pa||!pb) return;
    ctx.save(); ctx.beginPath();
    ctx.moveTo(pa.x+pa.w/2,pa.y+pa.h/2);
    ctx.lineTo(pb.x+pb.w/2,pb.y+pb.h/2);
    ctx.strokeStyle='rgba(0,245,212,0.1)';
    ctx.lineWidth=1; ctx.setLineDash([3,8]);
    ctx.lineDashOffset=-(P.tick*0.35);
    ctx.stroke(); ctx.setLineDash([]); ctx.restore();
  });

  // Nodes
  NODES.forEach(function(node){
    const p=P.nodeMap[node.id];
    if (!p) return;
    const active=(P.activeUntil[node.id]||0)>now;
    const cx=p.x+p.w/2, cy=p.y+p.h/2;
    if (active) {
      ctx.save(); ctx.shadowColor=node.color; ctx.shadowBlur=20;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(p.x-3,p.y-3,p.w+6,p.h+6,7); else ctx.rect(p.x-3,p.y-3,p.w+6,p.h+6);
      ctx.fillStyle=node.color+'22'; ctx.fill(); ctx.restore();
    }
    ctx.save(); ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(p.x,p.y,p.w,p.h,5); else ctx.rect(p.x,p.y,p.w,p.h);
    ctx.fillStyle=active?node.color+'1a':'rgba(15,23,42,0.92)';
    ctx.fill();
    ctx.strokeStyle=active?node.color:'rgba(0,245,212,0.16)';
    ctx.lineWidth=active?1.5:1; ctx.stroke(); ctx.restore();
    // Label
    ctx.save();
    ctx.font='bold 6px "Share Tech Mono",monospace';
    ctx.fillStyle=active?node.color:'rgba(148,185,208,0.8)';
    ctx.textAlign='center'; ctx.textBaseline='middle';
    if (active) { ctx.shadowColor=node.color; ctx.shadowBlur=8; }
    ctx.fillText(node.label,cx,cy-3);
    ctx.font='5px "Share Tech Mono",monospace'; ctx.shadowBlur=0;
    ctx.fillStyle=active?node.color+'cc':'rgba(56,82,104,0.7)';
    ctx.fillText(node.sub,cx,cy+6); ctx.restore();
  });

  // Balls
  P.balls=P.balls.filter(function(b){ return !b.done; });
  P.balls.forEach(function(ball){
    ball.progress=Math.min(1,ball.progress+ball.speed);
    const t=ball.progress;
    const ease=t<0.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
    ball.x=ball.fx+(ball.tx-ball.fx)*ease;
    ball.y=ball.fy+(ball.ty-ball.fy)*ease;
    ball.trail.push({x:ball.x,y:ball.y});
    if (ball.trail.length>12) ball.trail.shift();
    ball.trail.forEach(function(pt,i){
      if (i===0) return;
      ctx.save(); ctx.beginPath();
      ctx.moveTo(ball.trail[i-1].x,ball.trail[i-1].y);
      ctx.lineTo(pt.x,pt.y);
      ctx.strokeStyle=ball.color;
      ctx.globalAlpha=(i/ball.trail.length)*0.3;
      ctx.lineWidth=ball.r*0.65; ctx.lineCap='round'; ctx.stroke(); ctx.restore();
    });
    ctx.save(); ctx.shadowColor=ball.color; ctx.shadowBlur=12;
    ctx.beginPath(); ctx.arc(ball.x,ball.y,ball.r,0,Math.PI*2);
    ctx.fillStyle=ball.color; ctx.fill(); ctx.restore();
    if (ball.label) {
      ctx.save(); ctx.font='5px "Share Tech Mono",monospace';
      ctx.fillStyle=ball.color; ctx.textAlign='center';
      ctx.fillText(ball.label,ball.x,ball.y-ball.r-3); ctx.restore();
    }
    if (ball.progress>=1) ball.done=true;
  });

  // Idle ambient balls
  if (!P.animating && P.tick%120===0) {
    const edge=EDGES[Math.floor(Math.random()*EDGES.length)];
    const b=makeBall(edge[0],edge[1],'rgba(0,245,212,0.2)','');
    if (b) { b.r=2; b.speed=0.005; P.balls.push(b); }
  }
  requestAnimationFrame(drawPipeline);
}

function initPipeline() { resizePipeline(); drawPipeline(); }
window.addEventListener('resize', resizePipeline);
setTimeout(initPipeline, 300);

// ════ STATS PAGE ════════════════════════════════════════════════════════
let statsRefreshTimer = null;

async function loadStats() {
  const grid = document.getElementById('stats-grid');
  try {
    const [kR, sR, tR] = await Promise.all([
      fetch('/api/keys').then(function(r){ return r.json(); }).catch(function(){ return {}; }),
      fetch('/api/state').then(function(r){ return r.json(); }).catch(function(){ return {}; }),
      fetch('/api/triggers').then(function(r){ return r.json(); }).catch(function(){ return {}; }),
    ]);
    renderStats(kR, sR, tR);
    document.getElementById('stats-last-update').textContent = 'Zuletzt: ' + new Date().toLocaleTimeString('de-DE');
    addLog('INFO', 'Statistiken geladen.');
  } catch(e) {
    grid.innerHTML = '<div class="stat-card"><div class="card-title">⚠️ Nicht verfügbar</div><p style="color:var(--t2);font-size:.82rem">Server nicht erreichbar — <code>./shinon start</code></p></div>';
    addLog('ERROR', 'Stats-Ladefehler: ' + e.message);
  }
}

function renderStats(keysData, stateData, triggersData) {
  const grid = document.getElementById('stats-grid');
  const keys = keysData.keys || [];
  const active = keys.filter(function(k){ return k.status==='active'; }).length;
  const cooldown = keys.filter(function(k){ return k.status==='cooldown'; }).length;
  const dead = keys.filter(function(k){ return k.status==='dead'; }).length;
  const isOffline = !keys.length && (!stateData || !stateData.total);
  let html = '';

  // ── Key Pool Card ──
  html += '<div class="stat-card"><div class="card-title">🔑 API-Keys Pool <span class="card-badge">'+(keys.length)+' GESAMT</span></div>';
  if (isOffline) {
    html += '<div class="stat-row"><span class="stat-label" style="color:var(--t3)">Backend offline</span></div>';
    html += '<div class="stat-row"><span class="stat-label" style="font-size:.72rem;color:var(--gold)">Starte: ./shinon start</span></div>';
  } else {
    html += '<div class="stat-row"><span class="stat-label">Aktiv</span><span class="stat-value good">'+active+'</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Cooldown</span><span class="stat-value warn">'+cooldown+'</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Dead</span><span class="stat-value bad">'+dead+'</span></div>';
    html += '<div class="progress-bar-wrap"><div class="progress-bar" style="width:'+(keys.length?Math.round((active/keys.length)*100):0)+'%"></div></div>';
    keys.slice(0,10).forEach(function(k){
      html += '<div class="stat-row"><span class="stat-label" style="font-size:.74rem">'+escapeHtmlBase(k.provider)+'</span>'
        + '<span class="key-chip"><span class="dot '+k.status+'"></span>'+(k.health_pct||100)+'%</span></div>';
    });
  }
  html += '</div>';

  // ── TID State Card ──
  if (stateData && stateData.total !== undefined) {
    const total = stateData.total||0;
    const done = stateData.done||0;
    const pct = total ? Math.round((done/total)*100) : 0;
    html += '<div class="stat-card"><div class="card-title">🎯 goal-chain TIDs <span class="card-badge">'+pct+'% DONE</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Gesamt</span><span class="stat-value info">'+total+'</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Erledigt</span><span class="stat-value good">'+done+'</span></div>';
    html += '<div class="stat-row"><span class="stat-label">In Arbeit</span><span class="stat-value warn">'+(stateData.in_progress||0)+'</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Ausstehend</span><span class="stat-value">'+(stateData.pending||0)+'</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Fehlgeschlagen</span><span class="stat-value bad">'+(stateData.failed||0)+'</span></div>';
    html += '<div class="progress-bar-wrap"><div class="progress-bar" style="width:'+pct+'%"></div></div>';
    html += '</div>';
  }

  // ── Triggers Card ──
  const triggers = triggersData.triggers || [];
  if (triggers.length) {
    html += '<div class="stat-card"><div class="card-title">⚡ Trigger Aktivitäten <span class="card-badge">'+triggers.length+' TYPEN</span></div>';
    triggers.slice(0,8).forEach(function(t){
      html += '<div class="stat-row"><span class="stat-label" style="font-size:.72rem;font-family:monospace">'+escapeHtmlBase(t.skill||t.decision_type||'?')+'</span><span class="stat-value info">'+t.trigger_count+'x</span></div>';
    });
    html += '</div>';
  }

  // ── Connection Status Card ──
  html += '<div class="stat-card"><div class="card-title">📡 Verbindungsstatus</div>';
  html += '<div class="stat-row"><span class="stat-label">Shinon UI Server</span><span class="stat-value good">ONLINE :4300</span></div>';
  html += '<div class="stat-row"><span class="stat-label">LIMEN Gateway</span><span class="stat-value '+(isOffline?'bad':'good')+'">'+(isOffline?'OFFLINE':'ONLINE :8000')+'</span></div>';
  html += '<div class="stat-row"><span class="stat-label">Letztes Modell</span><span class="stat-value info">'+escapeHtmlBase(state.lastModel)+'</span></div>';
  html += '</div>';

  grid.innerHTML = html;
}

document.getElementById('stats-refresh-btn').addEventListener('click', function(){ loadStats(); });
// Auto-refresh stats every 30s
setInterval(function(){ if (state.page === 'stats') loadStats(); }, 30000);

// ════ SETTINGS IMPL ════════════════════════════════════════════════════
async function loadSettings() {
  try {
    const res = await fetch('/api/personality');
    const data = await res.json();
    if (Object.keys(data).length) state.personality = data;
    renderPersonalitySliders();
  } catch(e) { renderPersonalitySliders(); }
  loadKeys();
}

function renderPersonalitySliders() {
  const container = document.getElementById('personality-sliders');
  if (!container) return;
  const labels = {skepticism:'Skepsis',directness:'Direktheit',helpfulness:'Hilfsbereitschaft',patience:'Geduld',curiosity:'Neugier'};
  let html = '';
  for (const [key, val] of Object.entries(state.personality)) {
    html += '<div class="settings-row">'
      + '<label style="text-transform:capitalize">'+(labels[key]||key)+'</label>'
      + '<input type="range" min="0" max="10" value="'+val+'" oninput="updatePersonality(\''+key+'\',this.value)" aria-label="'+key+'">'
      + '<span class="range-val" id="pv-'+key+'">'+val+'</span></div>';
  }
  container.innerHTML = html;
}

function updatePersonality(key, value) {
  state.personality[key] = parseInt(value);
  const el = document.getElementById('pv-'+key);
  if (el) el.textContent = value;
  fetch('/api/personality', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({[key]:parseInt(value)}),
  }).catch(function(){});
}

async function loadKeys() {
  try {
    const res = await fetch('/api/keys');
    const data = await res.json();
    state.keys = data.keys || [];
    renderKeysList();
    const hasNoKeys = state.keys.length === 0;
    const badge = document.getElementById('keys-badge');
    if (badge) badge.classList.toggle('show', hasNoKeys);
  } catch(e) {}
}

function renderKeysList() {
  const container = document.getElementById('keys-list');
  if (!container) return;
  if (!state.keys.length) {
    container.innerHTML = '<div style="color:var(--t2);font-size:.82rem;padding:8px 0">Keine Keys konfiguriert. Füge einen API-Key hinzu.</div>';
    return;
  }
  let html = '';
  for (const k of state.keys) {
    const icon = k.status==='active'?'🟢':(k.status==='cooldown'?'🟡':'🔴');
    html += '<div class="settings-row"><span>'+icon+' '+escapeHtmlBase(k.provider)+'</span>'
      + '<span style="font-size:.72rem;color:var(--t2);font-family:monospace">'+k.status+' — '+(k.health_pct||100)+'%</span></div>';
  }
  container.innerHTML = html;
}

const saveBtn = document.getElementById('key-save-btn');
if (saveBtn) {
  saveBtn.addEventListener('click', async function(){
    const provider = document.getElementById('key-provider').value;
    const value = document.getElementById('key-value').value.trim();
    if (!value) return;
    const toast = document.getElementById('key-toast');
    try {
      const res = await fetch('/api/keys', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({provider,value}),
      });
      if (res.ok) {
        document.getElementById('key-value').value = '';
        toast.textContent = '✓ Key für '+provider+' gespeichert';
        toast.className = 'settings-toast ok show';
        loadKeys();
        showToast('API-Key gespeichert.', 'ok');
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

// ════ DEBUG PANEL ═══════════════════════════════════════════════════════
async function loadDebugData() {
  const body = document.getElementById('debug-body');
  if (!body) return;
  body.innerHTML = '<div class="stat-card"><div class="card-title">⏳ Lade…</div></div>';

  try {
    const [stateR, keysR, trigR] = await Promise.all([
      fetch('/api/state').then(function(r){ return r.json(); }).catch(function(){ return {}; }),
      fetch('/api/keys').then(function(r){ return r.json(); }).catch(function(){ return {}; }),
      fetch('/api/triggers').then(function(r){ return r.json(); }).catch(function(){ return {}; }),
    ]);

    let html = '';

    if (currentDebugTab === 'overview' || !currentDebugTab) {
      html += '<div class="stat-card"><div class="card-title">⚙️ System State</div>';
      html += '<div class="stat-row"><span class="stat-label">Mode</span><span class="stat-value good">STANDALONE</span></div>';
      html += '<div class="stat-row"><span class="stat-label">Port</span><span class="stat-value info">4300</span></div>';
      html += '<div class="stat-row"><span class="stat-label">Current Mood</span><span class="stat-value" style="color:var(--mood)">'+currentMood.toUpperCase()+'</span></div>';
      html += '<div class="stat-row"><span class="stat-label">Pipeline</span><span class="stat-value '+(P.animating?'warn':'good')+'">'+(P.animating?'ACTIVE':'IDLE')+'</span></div>';
      html += '<div class="stat-row"><span class="stat-label">Messages</span><span class="stat-value info">'+state.messages.length+'</span></div>';
      html += '<div class="stat-row"><span class="stat-label">Theme</span><span class="stat-value">'+state.theme.toUpperCase()+'</span></div>';
      html += '</div>';
      html += '<div class="stat-card"><div class="card-title">🎯 TID Summary</div>';
      html += '<div class="stat-row"><span class="stat-label">Gesamt</span><span class="stat-value info">'+(stateR.total||0)+'</span></div>';
      html += '<div class="stat-row"><span class="stat-label">Done</span><span class="stat-value good">'+(stateR.done||0)+'</span></div>';
      html += '<div class="stat-row"><span class="stat-label">In Progress</span><span class="stat-value warn">'+(stateR.in_progress||0)+'</span></div>';
      html += '<div class="stat-row"><span class="stat-label">Failed</span><span class="stat-value bad">'+(stateR.failed||0)+'</span></div>';
      html += '</div>';
      html += '<div class="stat-card"><div class="card-title">📡 Server Endpoints</div>';
      ['/api/ping','/api/keys','/api/state','/api/triggers','/api/personality','/api/chat'].forEach(function(ep){
        html += '<div class="stat-row"><span class="stat-label" style="font-family:monospace;font-size:.72rem">'+ep+'</span><span class="stat-value info">OK</span></div>';
      });
      html += '</div>';
    } else if (currentDebugTab === 'tids') {
      html += '<div class="stat-card" style="grid-column:1/-1"><div class="card-title">🗂️ TID State Detail</div>';
      if (!stateR.total) {
        html += '<p style="color:var(--t2);font-size:.82rem">Keine TID-Daten verfügbar. LIMEN starten: <code>./shinon start</code></p>';
      } else {
        html += '<table class="tid-table"><thead><tr><th>TID</th><th>Status</th><th>Description</th></tr></thead><tbody>';
        // Build mock rows from summary (actual per-TID requires separate endpoint)
        const statuses=['DONE','IN_PROGRESS','PENDING','FAILED'];
        statuses.forEach(function(s){
          const count = s==='DONE'?stateR.done:(s==='IN_PROGRESS'?stateR.in_progress:(s==='PENDING'?stateR.pending:stateR.failed))||0;
          if (count>0) {
            html += '<tr><td>TID-'+s.slice(0,2)+'*</td><td><span class="tid-badge '+s+'">'+s+'</span></td><td style="color:var(--t2)">'+count+' Aufgaben</td></tr>';
          }
        });
        html += '</tbody></table>';
      }
      html += '</div>';
    } else if (currentDebugTab === 'keys') {
      html += '<div class="stat-card" style="grid-column:1/-1"><div class="card-title">🔑 Key Pool Detail</div>';
      const keys = keysR.keys || [];
      if (!keys.length) {
        html += '<p style="color:var(--t2);font-size:.82rem">Keine Keys konfiguriert.</p>';
      } else {
        html += '<table class="tid-table"><thead><tr><th>Provider</th><th>Status</th><th>Health</th><th>RPM</th><th>Errors</th><th>Success</th></tr></thead><tbody>';
        keys.forEach(function(k){
          const sc = k.status==='active'?'DONE':(k.status==='cooldown'?'PENDING':'FAILED');
          html += '<tr><td>'+escapeHtmlBase(k.provider)+'</td><td><span class="tid-badge '+sc+'">'+k.status+'</span></td>'
            + '<td>'+( k.health_pct||100)+'%</td><td>'+(k.rpm||0)+'</td><td style="color:var(--red)">'+(k.errors||0)+'</td><td style="color:var(--green)">'+(k.success||0)+'</td></tr>';
        });
        html += '</tbody></table>';
      }
      html += '</div>';
    }

    body.innerHTML = html;
  } catch(e) {
    body.innerHTML = '<div class="stat-card"><div class="card-title">⚠️ Debug-Fehler</div><p style="color:var(--red);font-size:.82rem">'+escapeHtmlBase(e.message)+'</p></div>';
  }
}

// ════ CONNECTION HEALTH MONITOR ═════════════════════════════════════════
async function checkConnection() {
  try {
    const res = await fetch('/api/ping', {signal: AbortSignal.timeout(4000)});
    const data = await res.json();
    state.serverOnline = !!data.ok;
    document.getElementById('conn-dot').className = 'status-dot live';
    document.getElementById('conn-text').textContent = 'ONLINE';
    if (currentMood === 'idle') {
      // update status silently
    }
  } catch(e) {
    state.serverOnline = false;
    document.getElementById('conn-dot').className = 'status-dot dead';
    document.getElementById('conn-text').textContent = 'OFFLINE';
  }
}
// Check every 15s
checkConnection();
setInterval(checkConnection, 15000);

// ════ INIT ════════════════════════════════════════════════════════════
(function init(){
  // Restore theme
  const savedTheme = localStorage.getItem('shinon-theme') || 'dark';
  setTheme(savedTheme);
  const savedScanlines = localStorage.getItem('shinon-scanlines');
  if (savedScanlines === '0') toggleScanlines(false);

  // Load keys badge
  loadKeys();

  // Welcome log
  addLog('INFO', 'Shinon Cyberdeck UI v3.0 initialisiert.');
  addLog('INFO', 'Theme: '+savedTheme+', Scanlines: '+(savedScanlines!=='0'));

  // Set initial mood
  setMood('idle');

  // First ping
  setTimeout(checkConnection, 500);
})();
</script>
</body>
</html>`;
