---
name: design-tools-router
description: "Router für 40 Design-Tools-Skills (DataViz 18 + Figma 12 + Canva 3 + Hyperframes 5 + Remotion 1 + MagicPath 1). Leitet Design-Intents an den richtigen Sub-Skill. Use bei D3, Three.js, Dashboard, Geospatial, Figma Design-to-Code, Canva, GSAP, Remotion Video."
category: design-tools
stack: KREATIV + GOVERNANCE
risk: low
side_effects: file_changes
requires_approval: false
version: "1.0.0"
last_verified: "2026-08-11"
---

# 🎨 Design Tools Router — 40 Skills

> **Router für `design-tools/`** — Wählt Sub-Skill basierend auf Tool und Visualisierungs-Typ.

---

## 🗺️ Routing-Tabelle

### Data Visualization (18 Skills) — `design-tools/build-web-data-visualization/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "data visualization", "data viz", "which chart" | `data-visualization` | `build-web-data-visualization/data-visualization` |
| "visualization strategy", "viz critique", "which viz" | `visualization-strategy-and-critique` | `build-web-data-visualization/visualization-strategy-and-critique` |
| "D3", "d3.js", "D3 visualization" | `d3-data-visualization` | `build-web-data-visualization/d3-data-visualization` |
| "Three.js viz", "3D visualization", "WebGL viz" | `threejs-data-visualization` | `build-web-data-visualization/threejs-data-visualization` |
| "Canvas2D viz", "canvas visualization" | `canvas2d-data-visualization` | `build-web-data-visualization/canvas2d-data-visualization` |
| "React viz", "Next.js viz", "React chart" | `react-and-nextjs-data-visualization` | `build-web-data-visualization/react-and-nextjs-data-visualization` |
| "TypeScript viz", "viz engineering" | `typescript-data-visualization-engineering` | `build-web-data-visualization/typescript-data-visualization-engineering` |
| "dashboard", "real-time viz", "live chart" | `dashboards-and-real-time-visualization` | `build-web-data-visualization/dashboards-and-real-time-visualization` |
| "geospatial", "map viz", "cartographic", "mapbox" | `geospatial-and-cartographic-visualization` | `build-web-data-visualization/geospatial-and-cartographic-visualization` |
| "scrollytelling", "parallax viz", "scroll story" | `scrollytelling-and-parallax-data-visualization` | `build-web-data-visualization/scrollytelling-and-parallax-data-visualization` |
| "statistical viz", "uncertainty viz", "error bars" | `statistical-and-uncertainty-visualization` | `build-web-data-visualization/statistical-and-uncertainty-visualization` |
| "node link", "diagram layout", "graph viz" | `node-link-and-diagram-layout` | `build-web-data-visualization/node-link-and-diagram-layout` |
| "UML viz", "software architecture viz" | `uml-and-software-architecture-visualization` | `build-web-data-visualization/uml-and-software-architecture-visualization` |
| "Gantt chart", "timeline viz" | `gantt-chart-visualization` | `build-web-data-visualization/gantt-chart-visualization` |
| "accessibility viz", "inclusive viz", "a11y chart" | `accessibility-and-inclusive-visualization` | `build-web-data-visualization/accessibility-and-inclusive-visualization` |
| "grammar of graphics", "declarative viz", "ggplot" | `grammar-of-graphics-and-declarative-visualization` | `build-web-data-visualization/grammar-of-graphics-and-declarative-visualization` |
| "testing viz", "test visualization" | `testing-data-visualizations` | `build-web-data-visualization/testing-data-visualizations` |
| "reports PDF viz", "slide automation viz" | `reports-pdfs-and-slide-automation` | `build-web-data-visualization/reports-pdfs-and-slide-automation` |

### Figma (12 Skills) — `design-tools/figma/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Figma design to code", "Figma to React", "export Figma" | `figma-design-to-code` | `figma/figma-design-to-code` |
| "Figma generate design", "create Figma design" | `figma-generate-design` | `figma/figma-generate-design` |
| "Figma generate diagram", "Figma diagram" | `figma-generate-diagram` | `figma/figma-generate-diagram` |
| "Figma generate library", "Figma components" | `figma-generate-library` | `figma/figma-generate-library` |
| "Figma create file", "new Figma file" | `figma-create-new-file` | `figma/figma-create-new-file` |
| "Figma use", "Figma basics", "how to Figma" | `figma-use` | `figma/figma-use` |
| "Figma FigJam", "whiteboard Figma" | `figma-use-figjam` | `figma/figma-use-figjam` |
| "Figma slides", "presentation Figma" | `figma-use-slides` | `figma/figma-use-slides` |
| "Figma motion", "animation Figma" | `figma-use-motion` | `figma/figma-use-motion` |
| "Figma implement motion", "Figma animation code" | `figma-implement-motion` | `figma/figma-implement-motion` |
| "Figma code connect", "Figma dev mode" | `figma-code-connect` | `figma/figma-code-connect` |
| "Figma SwiftUI", "Figma to iOS" | `figma-swiftui` | `figma/figma-swiftui` |

### Canva (3 Skills) — `design-tools/canva/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Canva presentation", "branded Canva" | `canva-branded-presentation` | `canva/canva-branded-presentation` |
| "Canva resize", "social media Canva", "resize Canva" | `canva-resize-for-all-social-media` | `canva/canva-resize-for-all-social-media` |
| "Canva translate", "translate design Canva" | `canva-translate-design` | `canva/canva-translate-design` |

### Hyperframes (5 Skills) — `design-tools/hyperframes/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Hyperframes", "Hyperframes design" | `hyperframes` | `hyperframes/hyperframes` |
| "Hyperframes CLI", "Hyperframes command" | `hyperframes-cli` | `hyperframes/hyperframes-cli` |
| "Hyperframes Registry", "HF registry" | `hyperframes-registry` | `hyperframes/hyperframes-registry` |
| "GSAP", "GSAP animation", "greensock" | `gsap` | `hyperframes/gsap` |
| "website to Hyperframes", "convert to Hyperframes" | `website-to-hyperframes` | `hyperframes/website-to-hyperframes` |

### Remotion (1 Skill) — `design-tools/remotion/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Remotion", "React video", "programmatic video" | `remotion` | `remotion/remotion` |

### MagicPath (1 Skill) — `design-tools/magicpath/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "MagicPath", "MagicPath UI" | `magicpath` | `magicpath/magicpath` |

---

## 🔀 Routing-Logik

```
User-Intent erkennen:
├─ "chart", "D3", "dashboard", "map", "visualization"
│  → design-tools/build-web-data-visualization/<skill>
│
├─ "Figma", "design to code", "figjam"
│  → design-tools/figma/<skill>
│
├─ "Canva", "branded presentation", "social media resize"
│  → design-tools/canva/<skill>
│
├─ "Hyperframes", "GSAP", "greensock"
│  → design-tools/hyperframes/<skill>
│
├─ "Remotion", "React video"
│  → design-tools/remotion/<skill>
│
├─ "MagicPath"
│  → design-tools/magicpath/<skill>
│
└─ Unklar? → Frage: "Visualisierung, Figma, Canva, oder Animation?"
```

---

## Verwendung

```
User: "Erstelle ein interaktives D3-Dashboard"
→ Router: design-tools/build-web-data-visualization/d3-data-visualization + dashboards-and-real-time-visualization

User: "Exportiere Figma Design zu React Code"
→ Router: design-tools/figma/figma-design-to-code

User: "Animierte GSAP Landing Page"
→ Router: design-tools/hyperframes/gsap
```

_40 Skills · DataViz 18 + Figma 12 + Canva 3 + Hyperframes 5 + Remotion 1 + MagicPath 1 · August 2026_
