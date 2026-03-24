# Creda Website — React + Vite

Web frontend for the CREDA platform. Built with React, Vite, TailwindCSS, and shadcn/ui components.

---

## Prerequisites

- **Node.js 18+** or **Bun** (recommended)
- Backend running at `http://localhost:8080` (see `Creda_Fastapi/README.md`)

---

## Setup

```bash
cd Creda_Website

# Install dependencies
bun install     # recommended
# or: npm install

# Start dev server
bun dev         # http://localhost:5173
# or: npm run dev
```

---

## Scripts

| Command | Description |
|---------|-------------|
| `bun dev` | Start Vite dev server (HMR) |
| `bun run build` | Production build → `dist/` |
| `bun run build:dev` | Dev mode build |
| `bun run preview` | Preview production build locally |
| `bun run lint` | ESLint check |

---

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Landing | `/` | Marketing page |
| Dashboard | `/dashboard` | Overview with financial summary |
| Enhanced Dashboard | `/enhanced-dashboard` | Advanced dashboard with charts |
| Portfolio | `/portfolio` | MF portfolio view (ET PS9) |
| Budget | `/budget` | Budget tracking |
| Expense Analytics | `/expense-analytics` | Spending analysis |
| Financial Health | `/financial-health` | Money health score |
| Goals | `/goals` | Financial goal tracker |
| Advisory | `/advisory` | AI financial advisor chat |
| Voice | `/voice` | Voice-based financial assistant |
| Knowledge | `/knowledge` | Financial knowledge base |
| Security | `/security` | Account security settings |
| Settings | `/settings` | App preferences |
| Help | `/help` | Help & support |
| Auth | `/auth` | Authentication (Clerk) |

---

## Tech Stack

- **React 18** + **TypeScript**
- **Vite** — build tool
- **TailwindCSS** — utility-first styling
- **shadcn/ui** (Radix primitives) — UI components
- **Clerk** — authentication
- **React Query** — server state management
- **Recharts** + **Tremor** — data visualisation
- **Framer Motion** — animations
- **React Router** — client-side routing
- **Axios** — HTTP client
- **Zod** — schema validation

---

## Project Structure

```
src/
├── pages/          # 17 route pages
├── components/     # Shared UI components
│   ├── ui/         # shadcn primitives
│   ├── charts/     # Chart components
│   └── layout/     # Navigation, sidebar
├── contexts/       # React context providers
├── hooks/          # Custom hooks
├── services/       # API client functions
├── types/          # TypeScript types
├── utils/          # Helpers
└── lib/            # Third-party config
```

---

## Environment

Create `.env` if connecting to a non-default backend:

```env
VITE_API_URL=http://localhost:8080
VITE_CLERK_PUBLISHABLE_KEY=pk_your_key
```
