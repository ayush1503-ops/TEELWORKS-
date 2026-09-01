# 🚀 Deploying ONION LAB (3D website) — free, ~5 minutes

ONION LAB is a **fully static site** (React + Vite + Three.js, no backend).
That means free static hosting with automatic HTTPS — which also unlocks the
**camera on phones** (`getUserMedia` needs HTTPS or localhost).

> Deploying the **Onion Quality Analyzer** (FastAPI) too? That's the other
> guide: [`../onion-grader/docs/DEPLOYMENT.md`](../onion-grader/docs/DEPLOYMENT.md)

---

## OPTION A — Vercel (recommended)

### From the browser (easiest)

1. Push the project to GitHub:
   ```bash
   cd onion-lab
   git init
   git add .
   git commit -m "ONION LAB - 3D onion project website"
   git branch -M main
   git remote add origin https://github.com/<you>/onion-lab.git
   git push -u origin main
   ```
   (Make sure `node_modules/` and `dist/` are NOT committed — a `.gitignore`
   comes with the project.)

2. Go to **vercel.com** → sign up **with GitHub**.
3. **Add New → Project** → import your `onion-lab` repo.
4. Vercel auto-detects Vite. Just confirm:
   | Field | Value |
   |---|---|
   | Framework preset | Vite |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |
   | Install Command | `npm install` |
5. Click **Deploy** → ~1 minute later you get
   `https://onion-lab-<you>.vercel.app` ✅

### From the terminal (no GitHub needed)

```bash
cd onion-lab
npm install -g vercel   # once
vercel                  # first run asks you to log in
vercel --prod           # put it on the internet
```

Every later `vercel --prod` (or git push, if connected) redeploys.

## OPTION B — Netlify

1. **app.netlify.com** → sign up → **Add new site → Import an existing project**.
2. Pick the repo → build `npm run build` → publish directory `dist` → Deploy.
3. Or drag-and-drop: run `npm run build` locally, then drop the generated
   `dist/` folder onto **app.netlify.com/drop** — live in seconds, no repo.

## OPTION C — Cloudflare Pages

**pages.cloudflare.com** → Create a project → Connect to Git →
Framework: **Vite** → Build `npm run build` → Output `dist` → Save and Deploy.

## OPTION D — GitHub Pages (free, stays in your GitHub account)

1. In `vite.config.js` add your repo name as `base`:
   ```js
   export default defineConfig({
     base: "/onion-lab/",        // <- your repo name
     // ...rest stays the same
   });
   ```
2. Build and publish:
   ```bash
   npm run build
   npm install -g gh-pages
   gh-pages -d dist
   ```
3. Repo → **Settings → Pages** → Source: `gh-pages` branch →
   your site: `https://<you>.github.io/onion-lab/`

---

## Deploy checklist (all options)

- [x] `npm run build` succeeds locally (already verified in this project)
- [x] No environment variables needed — the site calls no backend
- [x] Camera works on the deployed URL (automatic HTTPS on every option above)
- [ ] Open the deployed site **on your phone** → Start Camera → allow → works
- [ ] Test one low-end device / slow connection (the 3D onion loads lazily via GPU — it falls back gracefully; heavy decorative rings are desktop-only)

## Local development & phone testing

```bash
cd onion-lab
npm install
npm run dev -- --host      # prints a LAN URL like http://192.168.x.x:5173
```
Open that URL on your phone (same Wi-Fi). Camera note: browsers only grant
`getUserMedia` on **HTTPS or localhost** — for a real phone camera test over
Wi-Fi, either use the deployed HTTPS URL or run `npx local-ssl-proxy`…

 simplest: deploy (2 min) and test on the real HTTPS URL.

## Deploying BOTH projects together (SIH setup)

| Project | Host | URL looks like | Cost |
|---|---|---|---|
| ONION LAB (this site) | Vercel / Netlify / CF Pages | `https://onion-lab.vercel.app` | free |
| Onion Quality Analyzer | Render (see its DEPLOYMENT.md) | `https://onion-quality-analyzer.onrender.com` | free |

They are independent — no cross-calls, no CORS setup needed.

**Optional single-server setup:** the analyzer's FastAPI can also serve this
website — build ONION LAB, copy `dist/` into the analyzer repo, and mount it
with `StaticFiles` exactly like its own frontend. One service, one URL. (Ask
and I'll wire it.)

## Custom domain (optional, free)

Vercel/Netlify/Cloudflare: **Settings → Domains → Add**. A free `*.vercel.app`
/ `*.netlify.app` / `*.pages.dev` subdomain is fine for a college exhibition.
