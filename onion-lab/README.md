# 🧅 ONION LAB — 3D Smart Onion Project Website

A premium, fully frontend interactive website: **agri-tech + 3D laboratory + product site**.
Companion presentation site for the *Onion Quality Analyzer* (SIH PS 26031).

## Stack

React 18 · Vite 5 · Tailwind CSS 3 · Framer Motion 11 · Three.js + React Three Fiber + drei

## Run it

```bash
cd onion-lab
npm install
npm run dev        # → http://localhost:5173
```

Production build: `npm run build` → `npm run preview`

## What's inside

| Section | Highlights |
|---|---|
| **Hero** | Procedural 3D onion (R3F): layered skin shells, canvas-generated texture, blue rim lighting, contact shadows, slow rotation, drag/scroll/pinch interaction, ROTATE/ZOOM/RESET controls, floating sensor chips, rotating rings |
| **Camera** | `getUserMedia` only on user click · permission/loading states · scanning overlay with corner brackets + animated scan line + FPS · `● CAMERA ACTIVE` · Stop Camera · graceful denial/unsupported handling · tracks cleaned up on unmount · labelled **DEMO ANALYSIS** (no detection claimed) |
| **Vision Lab** | Live camera + 3D onion joined by an animated "VISION LINK" data line |
| **Story** | Dark `#0F172A` section, dot-grid texture, blue radial glow, 6 topic cards |
| **How It Works** | 01–04 timeline, glowing nodes, scroll-triggered staggered reveals (horizontal → vertical on mobile) |
| **3D Explorer** | Large onion + 5 hotspots (Bulb, Skin, Roots, Leaves, Growth Area) → animated side info cards |
| **Dashboard** | Sample metric cards — explicitly labelled demonstration data |
| **A11y** | `prefers-reduced-motion` respected everywhere, 44px+ touch targets, semantic sections |

## Design tokens

`bg #FAFAFA · fg #0F172A · muted #F1F5F9 · mutext #64748B · electric #0052FF · electric2 #4D7CFF`
Type: **Calistoga** (display) · **Inter** (UI) · **JetBrains Mono** (technical labels)
Defined once in `tailwind.config.js` + CSS custom properties in `src/index.css`.

## Privacy

The camera stream never leaves the browser. Nothing is uploaded, nothing is stored.

## Components

`Navbar · Hero3D · OnionModel · FloatingSensorCard · CameraScanner · VisionLab ·
ProjectStory · HowItWorks · OnionExplorer · ProjectDashboard · Footer`
(+ `lib/cameraBus.js`, a tiny event bus so any *Start Camera* button can wake the scanner.)

## 3D model note

No `.glb` onion exists in this repo — `OnionModel.jsx` builds a **procedural onion**
(sphere displaced with ribs/neck/basal swell + papery shell layers + root tuft).
To use a real model later: drop `onion.glb` in `public/` and swap in
`useGLTF("/onion.glb")` from drei.
