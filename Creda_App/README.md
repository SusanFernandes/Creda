# Creda App — Expo / React Native

Mobile app for the CREDA platform. Built with Expo, React Native, NativeWind (TailwindCSS), and Drizzle ORM for local storage.

---

## Prerequisites

- **Node.js 18+**
- **Expo CLI** (`npx expo`)
- **Android Studio** or **Xcode** (for emulators), or Expo Go on a physical device
- Backend running at the configured API URL (see `Creda_Fastapi/README.md`)

---

## Setup

```bash
cd Creda_App

# Install dependencies
npx expo install

# Start dev server
npx expo start           # QR code for Expo Go
npx expo start --android # Direct to Android emulator
npx expo start --ios     # Direct to iOS simulator
npx expo start --web     # Web browser
```

---

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Expo with cache clear |
| `npm run dev:android` | Android emulator |
| `npm run dev:web` | Web browser |
| `npm run ios` | iOS simulator |
| `npm run clean` | Remove `.expo` and `node_modules` |

---

## Screens

### Auth Flow
| Screen | File | Description |
|--------|------|-------------|
| Login | `app/login.tsx` | Email/password login |
| Signup | `app/signup.tsx` | New account registration |
| Auth | `app/auth.tsx` | Auth entry point |

### Protected (Drawer + Tabs)
| Screen | File | Description |
|--------|------|-------------|
| Home | `(tabs)/index.tsx` | Main dashboard |
| Investments | `(tabs)/investments.tsx` | Portfolio overview |
| Expenses | `(tabs)/expenses.tsx` | Expense tracker |
| Bills | `(tabs)/bills.tsx` | Bill reminders |
| Budgets | `(drawer)/budgets.tsx` | Budget management |
| Goals | `(drawer)/goals.tsx` | Financial goals |
| Insurance | `(drawer)/insurance.tsx` | Insurance tracker |
| Knowledge | `(drawer)/knowledge.tsx` | Financial knowledge base |
| Fraud | `(drawer)/fraud.tsx` | Fraud alerts |
| Voice | `(drawer)/voice.tsx` | Voice financial assistant |
| Voice Agent | `(protected)/voiceagent.tsx` | Full voice agent interface |

---

## Tech Stack

- **Expo SDK** — managed workflow
- **React Native** + **TypeScript**
- **NativeWind** — TailwindCSS for React Native
- **Expo Router** — file-based navigation
- **Drizzle ORM** — local SQLite database
- **React Query** — data fetching
- **Shopify Skia** — custom charts
- **Zustand** — state management (auth, user, common stores)
- **Gorhom Bottom Sheet** — bottom sheet UI
- **Axios** — HTTP client

---

## Project Structure

```
Creda_App/
├── app/                    # Expo Router file-based routes
│   ├── _layout.tsx         # Root layout
│   ├── login.tsx           # Login screen
│   ├── signup.tsx          # Signup screen
│   └── (protected)/        # Auth-gated routes
│       ├── voiceagent.tsx
│       └── (drawer)/       # Drawer navigation
│           └── (tabs)/     # Bottom tab navigation
├── components/             # Shared components
│   ├── ui/                 # Primitives (rn-primitives)
│   ├── charts/             # Skia-based charts
│   └── forms/              # Form components (bills, budgets, goals, etc.)
├── hooks/                  # Custom hooks (DB, queries)
├── store/                  # Zustand stores
├── db/                     # Drizzle schema & seed
├── lib/                    # Utils, types, constants
├── services/               # Notification service
├── drizzle/                # SQL migrations
└── assets/                 # Images, onboarding assets
```

---

## Local Database

Uses Drizzle ORM with SQLite for offline-first data (expenses, budgets, goals). Migrations are in `drizzle/`.

---

## Environment

Update API URLs in the store or config:

```typescript
// store/commonStore.ts or lib/constants.ts
const API_URL = "http://your-backend-ip:8080";
```
