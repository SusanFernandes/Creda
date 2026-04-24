"""
Export router — PDF and CSV exports for portfolio, tax, goals data.
Uses ReportLab for PDF generation and csv module for CSV.
"""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import Portfolio, PortfolioFund, GoalPlan, AdviceLog

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/portfolio/csv")
async def export_portfolio_csv(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Export portfolio holdings as CSV."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = result.scalars().first()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Fund Name", "AMC", "Scheme Type", "Category", "Plan Type",
        "Invested (₹)", "Current Value (₹)", "Units", "XIRR (%)",
        "Expense Ratio (%)", "Alpha vs Benchmark (%)",
    ])

    if portfolio:
        funds_result = await db.execute(
            select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
        )
        for fund in funds_result.scalars():
            writer.writerow([
                fund.fund_name, fund.amc, fund.scheme_type, fund.category,
                fund.plan_type, f"{fund.invested:.2f}", f"{fund.current_value:.2f}",
                f"{fund.units:.4f}", f"{fund.xirr:.2f}",
                f"{fund.expense_ratio:.2f}", f"{fund.alpha_vs_benchmark:.2f}",
            ])

    output.seek(0)
    filename = f"creda_portfolio_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/goals/csv")
async def export_goals_csv(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Export goal plans as CSV."""
    result = await db.execute(
        select(GoalPlan).where(GoalPlan.user_id == auth.user_id)
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Goal Name", "Target Amount (₹)", "Target Date", "Monthly Investment (₹)",
        "Current Saved (₹)", "Recommended SIP (₹)", "Expected Return (%)",
        "On Track", "Progress (%)", "Drift Amount (₹)",
    ])

    for goal in result.scalars():
        writer.writerow([
            goal.goal_name, f"{goal.target_amount:.2f}",
            goal.target_date.isoformat() if goal.target_date else "",
            f"{goal.monthly_investment:.2f}", f"{goal.current_saved:.2f}",
            f"{goal.recommended_sip:.2f}", f"{goal.expected_return_rate:.1f}",
            "Yes" if goal.is_on_track else "No",
            f"{goal.progress_pct:.1f}", f"{goal.drift_amount:.2f}",
        ])

    output.seek(0)
    filename = f"creda_goals_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/compliance/csv")
async def export_compliance_csv(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Export SEBI compliance advice audit trail as CSV."""
    result = await db.execute(
        select(AdviceLog)
        .where(AdviceLog.user_id == auth.user_id)
        .order_by(AdviceLog.created_at.desc())
        .limit(500)
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Intent", "Agent", "User Message", "Response (truncated)",
        "Model", "Risk Profile", "Suitable", "Suitability Rationale",
        "Channel", "Response Time (ms)",
    ])

    for log in result.scalars():
        writer.writerow([
            log.created_at.isoformat() if log.created_at else "",
            log.intent, log.agent_used,
            log.user_message[:200],
            log.response_text[:300],
            log.model_name, log.risk_profile,
            "Yes" if log.is_suitable else "No",
            log.suitability_rationale[:200],
            log.channel, log.response_time_ms,
        ])

    output.seek(0)
    filename = f"creda_compliance_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/portfolio/pdf")
async def export_portfolio_pdf(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Export portfolio summary as PDF using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        # Fallback: return CSV if reportlab not installed
        return await export_portfolio_csv(auth=auth, db=db)

    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == auth.user_id).order_by(Portfolio.created_at.desc())
    )
    portfolio = result.scalars().first()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("CREDA Portfolio Report", styles["Title"]))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    if portfolio:
        # Summary
        summary_data = [
            ["Metric", "Value"],
            ["Total Invested", f"₹{portfolio.total_invested:,.0f}"],
            ["Current Value", f"₹{portfolio.current_value:,.0f}"],
            ["Gain/Loss", f"₹{portfolio.current_value - portfolio.total_invested:,.0f}"],
            ["XIRR", f"{portfolio.xirr:.1f}%"],
        ]
        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Holdings
        elements.append(Paragraph("Holdings Detail", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        funds_result = await db.execute(
            select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
        )
        funds = funds_result.scalars().all()

        if funds:
            holdings_data = [["Fund", "Invested", "Current", "XIRR"]]
            for f in funds:
                holdings_data.append([
                    f.fund_name[:40],
                    f"₹{f.invested:,.0f}",
                    f"₹{f.current_value:,.0f}",
                    f"{f.xirr:.1f}%",
                ])
            holdings_table = Table(holdings_data, colWidths=[220, 100, 100, 60])
            holdings_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            elements.append(holdings_table)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "This report is auto-generated by CREDA AI and does not constitute financial advice. "
        "SEBI disclaimer: Past performance is not indicative of future results.",
        styles["Normal"],
    ))

    doc.build(elements)
    buffer.seek(0)

    filename = f"creda_portfolio_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
