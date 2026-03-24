"""
RAG Agent — Retrieval-Augmented Generation for Indian financial regulations.
Uses ChromaDB + SentenceTransformers. Loaded once at startup.
"""

from __future__ import annotations
import logging
from typing import Optional, List
from langchain_groq import ChatGroq
from agents.state import FinancialState

logger = logging.getLogger(__name__)

# Module-level singletons — initialised by init_rag()
_chroma_client = None
_embedding_model = None
_collection = None

# ─── Knowledge Documents ─────────────────────────────────────────────────────

_FINANCIAL_DOCUMENTS = [
    # ═══ Government Schemes ═══════════════════════════════════════════════════
    {"text": "Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY): Life insurance cover of ₹2 lakh at ₹330/year. Available for ages 18-50 with a bank account. Administered by Department of Financial Services. Auto-debit from savings account. Claim within 30 days of death.", "source": "DFS/PMJJBY", "category": "government_schemes"},
    {"text": "Pradhan Mantri Suraksha Bima Yojana (PMSBY): Accidental death/disability cover of ₹2 lakh at ₹12/year. Available for ages 18-70. Partial disability cover ₹1 lakh. Administered by DFS.", "source": "DFS/PMSBY", "category": "government_schemes"},
    {"text": "Atal Pension Yojana (APY): Guaranteed pension of ₹1,000-5,000/month from age 60. Available for ages 18-40 with income below ₹12 lakh. Co-contributed by Govt for first 5 years (₹1,000/year). Administered by PFRDA.", "source": "PFRDA/APY", "category": "government_schemes"},
    {"text": "Sukanya Samriddhi Yojana (SSY): Savings scheme for girl child (under 10). Interest rate ~8.2% (Q1 FY2024-25). Min deposit ₹250/year, max ₹1.5 lakh/year. Qualifies for 80C deduction. Maturity at 21 years from account opening.", "source": "Ministry of Finance/SSY", "category": "government_schemes"},
    {"text": "National Pension System (NPS): Additional ₹50,000 deduction under 80CCD(1B) over and above 80C limit. Tier-1 has lock-in till 60, Tier-2 is flexible. Equity cap: 75% (Active), 50% (Auto). 60% corpus tax-free at maturity. Annuity on remaining 40%.", "source": "PFRDA/NPS", "category": "retirement"},
    {"text": "Public Provident Fund (PPF): 15-year lock-in, current rate 7.1%. Qualifies for 80C. EEE status (exempt-exempt-exempt). Max ₹1.5 lakh/year. Partial withdrawal from 7th year. Loan facility from 3rd to 6th year.", "source": "Ministry of Finance/PPF", "category": "savings"},
    {"text": "PM Vaya Vandana Yojana (PMVVY): Pension scheme for senior citizens (60+). Guaranteed 7.4% return for 10 years. Max investment ₹15 lakh. Monthly pension options available.", "source": "LIC/PMVVY", "category": "government_schemes"},
    {"text": "Sovereign Gold Bond (SGB): Government bonds linked to gold price. 2.5% interest (semi-annual) + capital appreciation. Tax-free if held till maturity (8 years). Section 80C not applicable.", "source": "RBI/SGB", "category": "investment"},
    {"text": "Pradhan Mantri Mudra Yojana (PMMY): Loans up to ₹10 lakh for micro/small enterprises. Shishu (₹50K), Kishore (₹5L), Tarun (₹10L). No collateral required.", "source": "SIDBI/PMMY", "category": "government_schemes"},
    {"text": "Senior Citizens Savings Scheme (SCSS): For 60+ (55+ for retired). 8.2% interest (quarterly). Max ₹30 lakh. 5-year tenure, extendable 3 years. Qualifies for 80C. TDS on interest above ₹50,000.", "source": "Ministry of Finance/SCSS", "category": "savings"},

    # ═══ Tax Rules ════════════════════════════════════════════════════════════
    {"text": "Section 80C allows up to ₹1,50,000 deduction per year across ELSS, PPF, LIC premium, EPF, NSC, SCSS, tuition fees (2 children), home loan principal, and 5-year FD.", "source": "Income Tax Act/80C", "category": "tax"},
    {"text": "LTCG tax on equity mutual funds: 12.5% on gains above ₹1.25 lakh in a financial year (Budget 2024). STCG tax on equity: 20% for holding period < 12 months.", "source": "Income Tax Act/Capital Gains FY2024-25", "category": "tax"},
    {"text": "New Tax Regime FY2024-25: Standard deduction ₹75,000. Slabs: 0-3L nil, 3-7L 5%, 7-10L 10%, 10-12L 15%, 12-15L 20%, >15L 30%. Rebate u/s 87A for income ≤ ₹7L. Family pension deduction ₹25,000.", "source": "Income Tax Act/New Regime", "category": "tax"},
    {"text": "Old Tax Regime deductions: HRA (10%/40%/50% of basic), LTA (2 journeys in 4 years), 80C (₹1.5L), 80D (₹25K self + ₹25K parents, ₹50K if senior), 80CCD(1B) NPS (₹50K), 80E education loan interest (no limit), 80TTA savings interest (₹10K).", "source": "Income Tax Act/Old Regime", "category": "tax"},
    {"text": "HRA exemption calculation: Least of (a) Actual HRA received (b) 50%/40% of basic salary (metro/non-metro) (c) Rent paid minus 10% of basic salary. Requires rent receipts. PAN of landlord if rent > ₹1 lakh/year.", "source": "Income Tax Act/HRA", "category": "tax"},
    {"text": "Section 80D: Health insurance premium deduction. Self/spouse/children: ₹25,000 (₹50,000 for senior citizens). Parents: additional ₹25,000 (₹50,000 for senior). Preventive health check-up: ₹5,000 within limits.", "source": "Income Tax Act/80D", "category": "tax"},
    {"text": "Section 80E: Education loan interest deduction — no upper limit. Available for 8 years from start of repayment. Loan must be for higher education of self, spouse, children, or student of whom assessee is legal guardian.", "source": "Income Tax Act/80E", "category": "tax"},
    {"text": "Section 80G: Donations to approved charitable trusts — 50% or 100% deduction depending on institution. Donations above ₹2,000 must be non-cash.", "source": "Income Tax Act/80G", "category": "tax"},
    {"text": "Section 10(14) — Leave Travel Allowance (LTA): Tax-exempt for domestic travel expenses. 2 journeys in a block of 4 years. Covers rail/air fare for self and family.", "source": "Income Tax Act/LTA", "category": "tax"},
    {"text": "Form 16 is the TDS certificate from employer. Part A has TAN, PAN, employment period, TDS details. Part B has salary breakup, deductions, tax computation. Filed quarterly by employer.", "source": "Income Tax Act/Form 16", "category": "tax"},

    # ═══ Investment Guidelines ════════════════════════════════════════════════
    {"text": "SEBI mandates mutual fund categorization: Large Cap (top 100 by market cap), Mid Cap (101-250), Small Cap (251+). Each fund house can have only 1 scheme per category (except index and ETFs).", "source": "SEBI/MF Categorization", "category": "investment"},
    {"text": "ELSS (Equity Linked Savings Scheme): 3-year lock-in (shortest among 80C instruments), equity-oriented (>80% equity), qualifies for 80C deduction. Historical returns: 12-15% CAGR over 10+ years.", "source": "SEBI/ELSS", "category": "investment"},
    {"text": "Asset allocation rule of thumb for India: (110 - age)% in equity. Conservative investors: (100 - age)%. Aggressive: (120 - age)%. Adjust for dependents (+5% debt per dependent) and goals.", "source": "Financial Planning Standards Board", "category": "investment"},
    {"text": "SIP (Systematic Investment Plan): Rupee cost averaging reduces timing risk. ₹5,000/month in Nifty 50 index fund has historically yielded ~12% CAGR over 15+ years. Start early — 10 years of SIP from age 25 beats 20 years from age 35.", "source": "AMFI/SIP", "category": "investment"},
    {"text": "Portfolio rebalancing: Review allocation every 6-12 months. If any asset class drifts >5% from target, rebalance. Consider tax implications — book LTCG ≤ ₹1.25 lakh tax-free. Prefer SIP redirection over lump-sum switches.", "source": "SEBI/Advisory", "category": "investment"},
    {"text": "Index Funds vs Active Funds in India: Large cap index funds (Nifty 50, Sensex) have beaten 60%+ active large cap funds over 5 years. TER of index funds: 0.05-0.20% vs active: 1-2%. Better for core portfolio allocation.", "source": "SPIVA India Scorecard", "category": "investment"},
    {"text": "Direct vs Regular MF plans: Direct plans have 0.5-1.5% lower expense ratio. Over 20 years, a 1% difference in TER on ₹10,000/month SIP = ₹15-20 lakh more corpus. Switch to direct via AMC website or MF Utility.", "source": "SEBI/Direct Plans", "category": "investment"},
    {"text": "Nifty 50 historical returns: 1-year range -26% to +76%. 5-year CAGR: 10-16% typically. 15-year SIP never given negative return historically. Best for long-term goals.", "source": "NSE/Nifty 50", "category": "investment"},
    {"text": "Gold as asset class in India: 5-10% allocation recommended. Options: SGB (best — 2.5% interest + tax-free LTCG), Gold ETF, Gold savings fund. Avoid physical gold for investment (making charges, storage, purity risk).", "source": "WGC/Gold Investment", "category": "investment"},
    {"text": "REITs in India: Listed REITs (Embassy, Mindspace, Brookfield) offer commercial real estate exposure. Min lot ~₹10,000-15,000. Yield: 5-7% p.a. + capital appreciation. 90% of net distributable income mandatory distribution.", "source": "SEBI/REIT", "category": "investment"},

    # ═══ Emergency Fund & Insurance ═══════════════════════════════════════════
    {"text": "Emergency Fund Rule: Maintain 6 months of expenses in liquid form (savings account, liquid fund, or FD). For single-income households: 9-12 months. Essential before any aggressive investing.", "source": "Financial Planning Standards", "category": "emergency"},
    {"text": "Term Insurance: Ideal cover = 15-20x annual income. Pure protection, no investment component. Most cost-effective life cover. Age 30: ₹1 crore cover costs ~₹8,000-12,000/year. Increase cover at milestones (marriage, baby, home).", "source": "IRDAI/Term Insurance", "category": "insurance"},
    {"text": "Health Insurance: Minimum ₹5 lakh cover per family member. Consider top-up (₹20-50L deductible plans at ₹2,000-5,000/year). Super top-up covers aggregate claims. Critical illness rider adds ₹5-10L lump sum on diagnosis.", "source": "IRDAI/Health Insurance", "category": "insurance"},
    {"text": "Personal Accident Insurance: Covers accidental death and disability. ₹50 lakh cover costs ~₹5,000/year. Important for sole breadwinners. Covers permanent total/partial disability with lump sum.", "source": "IRDAI/PA Insurance", "category": "insurance"},
    {"text": "PMFBY (Pradhan Mantri Fasal Bima Yojana): Crop insurance for farmers. Premium: 2% kharif, 1.5% rabi, 5% commercial/horticulture. Covers yield loss, prevented sowing, post-harvest losses.", "source": "Ministry of Agriculture/PMFBY", "category": "insurance"},

    # ═══ Banking & Debt ═══════════════════════════════════════════════════════
    {"text": "Home Loan interest deduction: Up to ₹2 lakh under Section 24(b) for self-occupied property. No limit for let-out property. Additional ₹1.5 lakh under Section 80EEA for affordable housing (stamp value ≤ ₹45 lakh, until March 2022 loans).", "source": "Income Tax Act/Home Loan", "category": "tax"},
    {"text": "Credit Score in India (CIBIL): Range 300-900. Above 750 = good. Banks check for loans, credit cards. Improve by paying EMIs on time, keeping utilization below 30%, maintaining old credit accounts.", "source": "CIBIL/Credit Score", "category": "banking"},
    {"text": "Personal Loan vs Credit Card debt: Personal loan interest 10-16%, credit card revolving credit 36-42%. Always clear credit card dues in full. If stuck, balance transfer to personal loan to reduce interest burden.", "source": "RBI/Consumer Credit", "category": "banking"},
    {"text": "Debt-to-income ratio: Keep total EMIs (home + car + personal) below 40% of gross monthly income. Banks typically don't lend beyond 50% FOIR (Fixed Obligation to Income Ratio). Lower is better for financial health.", "source": "RBI/Lending Guidelines", "category": "banking"},

    # ═══ Retirement Planning ══════════════════════════════════════════════════
    {"text": "FIRE (Financial Independence Retire Early): Target corpus = 25-30x annual expenses. Safe withdrawal rate in India: 3-4% due to higher inflation (6-7% vs 2-3% in US). Bucket strategy: 2 years cash, 5 years debt, rest equity.", "source": "Financial Planning Research", "category": "retirement"},
    {"text": "EPF interest rate: 8.25% (FY2023-24). Mandatory for salaried employees. Employer + Employee each contribute 12% of basic. VPF (Voluntary PF) up to 100% of basic for additional tax-free returns at same rate. EEE status.", "source": "EPFO/EPF", "category": "retirement"},
    {"text": "Retirement corpus estimation: Monthly expense × 12 × 25 (for 4% SWR). Add 30% buffer for healthcare. At 6% inflation, ₹50,000/month today = ₹1.6 lakh/month in 20 years. Target changes with inflation.", "source": "Retirement Planning Guide", "category": "retirement"},
    {"text": "Annuity options in India: LIC, HDFC Life, ICICI Pru offer annuity products. Joint annuity (with spouse continuation) recommended. Compare annuity rates — typically 5-7% for age 60. Mandatory for 40% of NPS corpus.", "source": "IRDAI/Annuity", "category": "retirement"},

    # ═══ Seasonal & Regional ══════════════════════════════════════════════════
    {"text": "Indian festival season (Oct-Dec) typically sees 30-40% increase in discretionary spending. Plan budget buffer. Diwali: gold purchases, gifts, home improvement. Create a separate festival spending fund.", "source": "RBI Consumer Survey", "category": "seasonal"},
    {"text": "Monsoon season considerations for rural India: Crop insurance (PMFBY), increased emergency fund (+25%). Agricultural income is tax-exempt under Section 10(1) but allied income (dairy, horticulture processed goods) may not be.", "source": "Ministry of Agriculture/PMFBY", "category": "seasonal"},
    {"text": "Regional investment preferences in India: North (gold, real estate), South (equity, FDs), West (startups, equity, MFs), East (conservative, post office schemes, gold). Culture influences investment choice — consider diversifying beyond regional habits.", "source": "SEBI Investor Survey 2024", "category": "regional"},
    {"text": "Tax planning calendar: April — review and set up SIPs for 80C, October — mid-year deduction assessment, January — advance tax 3rd installment, March — last chance for ELSS/PPF/NPS. Don't wait till March rush.", "source": "Tax Planning Best Practices", "category": "tax"},

    # ═══ RBI & SEBI Regulatory ════════════════════════════════════════════════
    {"text": "RBI Liberalised Remittance Scheme (LRS): Indian residents can remit up to $250,000 per financial year for investment, education, travel, medical abroad. 20% TCS on amounts above ₹7 lakh (except education/medical).", "source": "RBI/LRS", "category": "regulatory"},
    {"text": "SEBI margin rules: Peak margin reporting for F&O. Delivery trades: no margin required. Pledging: must give explicit consent. No funding of margins by broker beyond T+1.", "source": "SEBI/Margin Rules", "category": "regulatory"},
    {"text": "KYC (Know Your Customer): One-time KYC valid across all MFs. CKYC simplifies verification. Required: PAN, Aadhaar, bank details, photograph. In-Person Verification (IPV) via VKYC or branch visit.", "source": "SEBI/KYC", "category": "regulatory"},
    {"text": "Nomination is essential for all financial accounts: MF folios, demat, bank, FD, insurance. Without nomination, legal heirs face lengthy succession certificate process. Update nominee after life events.", "source": "SEBI/Nomination", "category": "regulatory"},
    {"text": "Account Aggregator (AA) framework: RBI-regulated consent-based data sharing. Customer can share bank, MF, insurance, tax data digitally. Enables instant loan approval, financial planning. Live since 2021.", "source": "RBI/Account Aggregator", "category": "regulatory"},
]


def init_rag() -> None:
    """Initialise ChromaDB client, embedding model, and seed knowledge base."""
    global _chroma_client, _embedding_model, _collection

    import chromadb
    from sentence_transformers import SentenceTransformer

    logger.info("Initialising RAG system...")

    _chroma_client = chromadb.PersistentClient(path="./chroma_financial_db")

    # Try multilingual model first, fall back gracefully
    for model_name in (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "sentence-transformers/all-MiniLM-L6-v2",
    ):
        try:
            _embedding_model = SentenceTransformer(model_name)
            logger.info("Loaded embedding model: %s", model_name)
            break
        except Exception as e:
            logger.warning("Could not load %s: %s", model_name, e)

    if _embedding_model is None:
        raise RuntimeError("Failed to load any embedding model for RAG")

    # Get or create collection
    try:
        _collection = _chroma_client.get_collection("financial_knowledge")
        doc_count = _collection.count()
        if doc_count >= len(_FINANCIAL_DOCUMENTS):
            logger.info("RAG collection ready — %d documents", doc_count)
            return
        # Collection exists but is incomplete — delete and reseed
        _chroma_client.delete_collection("financial_knowledge")
    except Exception:
        pass

    _collection = _chroma_client.create_collection(
        name="financial_knowledge",
        metadata={"hnsw:space": "cosine"},
    )

    # Seed documents
    texts = [d["text"] for d in _FINANCIAL_DOCUMENTS]
    embeddings = _embedding_model.encode(texts).tolist()
    ids = [f"doc_{i}" for i in range(len(texts))]
    metadatas = [{"source": d["source"], "category": d["category"]} for d in _FINANCIAL_DOCUMENTS]

    _collection.add(documents=texts, embeddings=embeddings, ids=ids, metadatas=metadatas)
    logger.info("Seeded %d documents into RAG collection", len(texts))


# ─── Agent Node ───────────────────────────────────────────────────────────────

def rag_agent(state: FinancialState) -> dict:
    """LangGraph node — answer questions using RAG + LLM."""
    global _collection, _embedding_model

    if _collection is None or _embedding_model is None:
        init_rag()

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    query = state["messages"][-1].content

    # Embed and search
    query_emb = _embedding_model.encode([query]).tolist()
    try:
        results = _collection.query(
            query_embeddings=query_emb,
            n_results=5,
            include=["documents", "metadatas", "distances"],
        )
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
    except Exception as e:
        logger.error("RAG query failed: %s", e)
        docs, metas = [], []

    context = "\n\n".join(docs) if docs else "No specific regulation found in knowledge base."

    prompt = f"""You are a SEBI/RBI-compliant financial advisor for Indian investors.

REGULATORY CONTEXT:
{context}

USER QUESTION: {query}

Answer accurately based on the context above. If the context doesn't cover the question,
answer from general Indian financial knowledge and note it is general advice.
Always mention that this is informational, not personalised advice.
Keep answer under 150 words."""

    try:
        answer = llm.invoke(prompt).content
    except Exception as e:
        logger.error("LLM invocation failed in RAG agent: %s", e)
        answer = "I'm unable to generate a response right now. Please try again."

    sources = [m.get("source", "RBI/SEBI guidelines") for m in metas[:3]]

    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "rag_query": {"answer": answer, "sources": sources},
        }
    }
