# CREDA Demo — "Meet Arjun" (8-Minute Hackathon Scenario)

> *"Meet Arjun. He earns ₹1.8 lakh a month and has no idea where it goes."*

## The Philosophy

Judges don't remember features. They remember moments. This demo has one emotional arc:
a real Indian — confused, underpaid by his own money, no financial plan — walks into
CREDA and walks out with a complete financial life in 8 minutes.

You're not demoing a product. You're demoing a **transformation**.

---

## Characters

| Character | ID | Role | Details |
|---|---|---|---|
| **Arjun Mehta** | 100 | Primary user | 29, Bengaluru, IT salaried, ₹1.8L/mo, moderate risk |
| **Priya Sharma** | 101 | Fiancée (linked spouse) | 27, PM, ₹1.4L/mo, getting married in 6 months |

## Credentials

```
Arjun:  arjun@demo.creda.in / demo1234
Priya:  priya@demo.creda.in / demo1234
```

---

## Arjun's Profile (Pre-Seeded)

| Field | Value |
|---|---|
| Age | 29 |
| City | Bengaluru (Metro — affects HRA) |
| Monthly Income | ₹1,80,000 |
| Monthly Expenses | ₹95,000 (rent ₹28K, food ₹12K, transport ₹8K, misc ₹47K) |
| Risk Tolerance | Moderate |
| EPF | ₹21,600/mo (12% employer + 12% employee) |
| 80C Done | ₹45,000 (ELSS SIP only) |
| 80C Remaining | ₹1,05,000 unfilled |
| NPS | None |
| Insurance | ₹5L health (employer only), **no term life** |
| Emergency Fund | ₹60,000 (< 1 month expenses — critically low) |

### Portfolio (6 funds, pre-loaded as CAMS upload)

| Fund | Category | Invested | Current | XIRR |
|---|---|---|---|---|
| Mirae Asset Large Cap — Direct Growth | Large Cap | ₹2,20,000 | ₹2,68,000 | 12.1% |
| Axis Midcap — Direct Growth | Mid Cap | ₹1,50,000 | ₹2,05,000 | 16.8% |
| Parag Parikh Flexi Cap — Direct Growth | Flexi Cap | ₹1,80,000 | ₹2,31,000 | 14.3% |
| ICICI Pru Bluechip — Direct Growth | Large Cap | ₹80,000 | ₹94,000 | 8.9% |
| SBI Small Cap — Direct Growth | Small Cap | ₹60,000 | ₹88,000 | 21.4% |
| Axis Bluechip — Direct Growth | Large Cap | ₹40,000 | ₹44,500 | 6.2% |

**Total: ₹7,30,000 invested → ₹8,30,500 current → XIRR 13.2%**

**Deliberate problems baked in:**
- 3 large-cap funds = massive overlap (Mirae, ICICI, Axis Bluechip)
- Axis Bluechip is dead weight (6.2% XIRR)
- Nifty 50 returned 15.8% → Arjun underperforms by 2.6%
- 100% equity, 0% debt allocation
- No term life insurance

### Goals (4 pre-configured)

| Goal | Target | Current | Progress | Timeline |
|---|---|---|---|---|
| Emergency Fund | ₹5,70,000 | ₹60,000 | 10.5% | Ongoing |
| Wedding | ₹8,00,000 | ₹1,20,000 | 15% | 6 months |
| Home Down Payment | ₹30,00,000 | ₹0 | 0% | 5 years |
| Retirement (FIRE) | Computed | — | — | Age 50 |

### Life Events (2 pre-configured)
- Marriage in 6 months (Priya)
- ₹3,00,000 performance bonus received

---

## The Demo Script: 8 Minutes, Scene by Scene

### Opening (0:00–0:45) — The Problem

> "India has 54 lakh CAs and RIAs. It has 140 crore people. The math doesn't work.
> For 95% of Indians, financial planning is either unaffordable or completely absent.
> CREDA puts a SEBI-aware AI financial advisor inside Economic Times — available to
> every Indian, in their language, right now."
>
> "Let me show you Arjun."

---

### Scene 1: Dashboard Landing (0:45–1:30) — First Wow

Log in as Arjun. Dashboard loads with:

1. **Money Health Score — 42/100, RED**
   > "Arjun earns ₹1.8 lakh a month, has ₹8.3 lakh in mutual funds, and his
   > financial health score is 42. Why?"

   Click into Health Score. Show six dimension bars:
   - Emergency Fund: ~18/100 — "He has ₹60K. He needs ₹5.7L."
   - Insurance: ~12/100 — "No term life. If Arjun dies tomorrow, Priya inherits nothing."
   - Tax Efficiency: ~55/100 — "₹1.05L of 80C on the table = ₹32,760 in avoidable taxes."

2. **Nudge Notifications** — 3+ active nudges:
   - "⚠️ Your SIP of ₹5,000 is due in 2 days"
   - "🚨 Emergency fund covers only 10.5% of target"
   - "💡 Tax season: ₹1.05L of 80C unused"

   > "CREDA proactively monitors Arjun's financial life. He didn't ask for this."

---

### Scene 2: Portfolio X-Ray (1:30–2:30) — The Sharp Insight

Navigate to **Portfolio X-Ray**. The page shows:

- **Overlap alert**: 3 large-cap funds holding the same 50 stocks. "Overlap HIGH."
- **Benchmark underperformance**: "XIRR 13.2% vs Nifty 50 at 15.8%."
- Click **Run X-Ray Analysis** — full results appear:
  - Top/bottom performers
  - Expense drag calculation
  - AI rebalancing recommendation: "Exit Axis Bluechip (6.2%). Redirect to Nifty index fund."

> "60 seconds of specific, calculated, actionable output."

---

### Scene 3: Tax Wizard (2:30–3:15) — The Money Found

Navigate to **Tax**. Show old vs new regime comparison:
- ₹1,05,000 of unclaimed 80C
- Missed deduction: NPS 80CCD(1B) ₹50,000 + ELSS top-up ₹55,000
- **Tax saved: ₹32,760**

Switch to Year-Round Copilot tab:
> "47 days until 80C deadline. Action: ₹55K in ELSS now. ₹50K in NPS. Total saved: ₹32,760."
>
> "CREDA didn't give advice. It gave a calendar with amounts and a deadline."

---

### Scene 4: Life Event — The Bonus (3:15–4:00) — The Decision Engine

Navigate to **Life Events**. Click the ₹3L bonus quick button or type:
> "I just received a ₹3 lakh performance bonus."

The Life Event Advisor responds with structured, personalized allocation:
1. **Emergency Fund** — ~40% (₹60K → ₹1.8L, covers 1.9 months)
2. **Tax optimization** — ~18% (ELSS before March 31)
3. **Wedding fund** — ~27% (park in liquid fund)
4. **Home down payment** — ~15% (kickstart SIP)

> "Health score improves from 42 → ~61 with this single deployment."
>
> "That's not a chatbot. That's a financial advisor that knows Arjun's specific numbers."

---

### Scene 5: Couples Finance (4:00–4:45) — The Relationship Moment

Navigate to **Couples Finance**. Priya's profile is already linked (shows green badge).
Click **Run Joint Analysis**.

- Combined income: ₹3,20,000/mo
- Combined savings rate: ~50%
- **HRA routing**: "Priya lives with parents. Arjun pays ₹28K rent in Bengaluru metro. CREDA routes all HRA exemption to Arjun. Saves ₹40,320/year."
- **NPS routing**: Route through Arjun's employer for 80CCD(2) match.

> "India's first AI that optimizes a couple's finances as a unit."

---

### Scene 6: FIRE Planner (4:45–5:30) — The Dream

Navigate to **FIRE Planner**. Arjun's target: retire at 50.

- **FIRE number**: ~₹7.2 Cr
- **Current corpus**: ₹8.3L
- **Required SIP**: ~₹42,000/mo
- **Current SIP**: ₹15,000/mo → Gap: ₹27,000/mo
- **Year-by-year roadmap TABLE** (the key visual):

| Year | Age | Annual SIP | Portfolio Value | Action |
|---|---|---|---|---|
| Y1 | 30 | ₹1,80,000 | ~₹18L | Start NPS ₹5K/mo |
| Y2 | 31 | ₹1,98,000 | ~₹30L | Step up SIP |
| Y5 | 34 | ₹2,64,000 | ~₹75L | Add debt allocation |
| Y10 | 39 | ₹4,26,000 | ~₹1.8Cr | Review allocation |
| Y20 | 49 | ₹9,38,000 | ~₹6.5Cr | Shift conservative |
| Y21 | 50 | — | ~₹7.2Cr | 🎯 FIRE REACHED |

- **Glide path**: Visual equity→debt transition bars

> "This isn't a calculator. It's a 21-year financial roadmap with specific actions at specific ages."

---

### Scene 7: Voice Feature (5:30–6:15) — The Hero Moment

Click the floating mic FAB. Speak in Hindi:
> "मेरा पोर्टफोलियो कैसा है और मुझे अभी क्या करना चाहिए?"

The system:
1. Transcribes Hindi → classifies intent → runs portfolio agent
2. Responds with TTS audio in Hindi
3. Shows transcript + intent on screen

> "Hindi, Tamil, Bengali, Telugu — 11 Indian languages. Because most of India
> doesn't think about money in English."

---

### Scene 8: Market Intelligence (6:15–6:45)

Navigate to **Market Pulse**:
- Live Nifty 50, Sensex, Bank Nifty indices
- Today's top headlines from ET RSS
- Portfolio impact: personalized to Arjun's holdings

> "CREDA doesn't just show market news. It tells you what today's news means for YOUR portfolio."

---

### Scene 9: WhatsApp (6:45–7:15)

Show a WhatsApp conversation with the Twilio number:
> "Should I buy more SBI Small Cap?"

Response:
> "SBI Small Cap is your highest performer at 21.4% XIRR. But you already have 10.7%
> allocation in small cap. Recommendation: Increase Parag Parikh Flexi Cap SIP instead."

> "140 crore Indians have WhatsApp. 5 crore have a financial advisor. CREDA bridges that gap."

---

### Scene 10: Compliance Layer (7:15–7:30)

Navigate to **Compliance**. Show audit trail: every AI recommendation logged with
timestamp, agent, intent, user ID, suitability rationale.

> "Every recommendation is logged with a SEBI-compatible audit trail."

---

### Scene 11: The Score After (7:30–8:00) — The Close

Navigate back to Health Score.
> "When Arjun arrived, his score was 42. After acting on CREDA's recommendations —
> deploying the bonus, claiming HRA correctly, filling 80C, starting NPS —
> his projected score is 74."

Close:
> "CREDA isn't a chatbot you talk to once. It's a financial operating system for India —
> sitting inside Economic Times, available to every reader, in their language, at zero cost.
> The 95% who can't afford a financial advisor now have one."

---

## Running the Demo

```bash
# 1. Start infrastructure
cd python
make docker         # PostgreSQL, Redis, ChromaDB, TTS engines

# 2. Run migrations
make migrate

# 3. Seed demo data (Arjun + Priya + family link)
make seed

# 4. Start servers
make all           # Django (8000) + FastAPI (8001)

# 5. Open browser
# http://localhost:8000 → Login as arjun@demo.creda.in / demo1234
```

### Reset Demo

```bash
cd python/demo
python regenerate.py           # Wipe + re-seed
python regenerate.py --clean   # Wipe only (no re-seed)
```

### Run E2E Test

```bash
cd python/demo
python test_e2e_demo.py             # All 11 scenes
python test_e2e_demo.py --scene 2   # Single scene
```

---

## Files in This Folder

| File | Purpose |
|---|---|
| `README.md` | This file — full demo scenario + setup guide |
| `demo_config.json` | Scenario configuration + expected output benchmarks |
| `test_e2e_demo.py` | Automated E2E test for all 11 demo scenes |
| `sample_cams.json` | Simulated CAMS-format portfolio data |
| `sample_form16.json` | Simulated Form 16 tax data |
| `regenerate.py` | Script to wipe and re-seed demo data |

---

## Q&A Prep (Judges Will Ask These)

| Question | Answer |
|---|---|
| "How do you handle wrong AI advice?" | SEBI compliance audit trail — every response logged, reviewable. Human Handoff agent escalates edge cases. |
| "What's your data source for NAV?" | AMFI via mfapi.in and mftool — same source as BSE, free, updated daily. |
| "How is this different from Zerodha/Groww?" | They're execution platforms. CREDA is advisory — it tells you what to do, tracks whether you did it, and explains why, in your language. |
| "Can ET integrate this?" | Django frontend embeds as iframe/widget. FastAPI is standalone microservice. WhatsApp needs Twilio on ET's business account. |
| "What about user data?" | Data lives in user's PostgreSQL instance. CREDA doesn't store portfolio data externally. |

---

## Non-Negotiables (Must Work for Demo)

- [ ] Money Health Score shows ~42 with red bars for Arjun
- [ ] Portfolio X-Ray shows overlap callout + benchmark underperformance
- [ ] Tax Wizard shows missed ₹1,05,000 deduction + ₹32,760 savings
- [ ] Voice works end-to-end (STT → agent → TTS audio plays)
- [ ] At least 3 nudge notifications on dashboard load
- [ ] Couples Finance shows linked Priya + HRA routing
- [ ] FIRE roadmap table renders with year-by-year data
- [ ] Life Event Advisor gives structured bonus allocation
