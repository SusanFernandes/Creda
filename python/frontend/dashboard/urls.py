from django.urls import path
from dashboard import views
from views import onboarding as onboarding_views

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("chat/", views.chat_view, name="chat"),
    path("portfolio/", views.portfolio_view, name="portfolio"),
    path("portfolio/upload/", views.portfolio_upload, name="portfolio_upload"),
    path("health/", views.health_view, name="health"),
    path("fire/", views.fire_view, name="fire"),
    path("tax/", views.tax_view, name="tax"),
    path("budget/", views.budget_view, name="budget"),
    path("goals/", views.goals_view, name="goals"),
    path("stress-test/", views.stress_test_view, name="stress_test"),
    path("settings/", views.settings_view, name="settings"),
    path("settings/assumptions/", views.assumptions_view, name="settings_assumptions"),
    path("onboarding/", views.onboarding_view, name="onboarding"),
    path("onboarding/wizard/", onboarding_views.onboarding_wizard_view, name="onboarding_wizard"),
    path(
        "onboarding/save-step/<int:step_number>/",
        onboarding_views.onboarding_save_step_view,
        name="onboarding_save_step",
    ),
    path("onboarding/resume/", onboarding_views.onboarding_resume_view, name="onboarding_resume"),
    path("notifications/", views.notifications_view, name="notifications"),
    # New pages
    path("couples/", views.couples_view, name="couples"),
    path("sip-calculator/", views.sip_calculator_view, name="sip_calculator"),
    path("market-pulse/", views.market_pulse_view, name="market_pulse"),
    path("tax-copilot/", views.tax_copilot_view, name="tax_copilot"),
    path("personality/", views.money_personality_view, name="money_personality"),
    path("goal-simulator/", views.goal_simulator_view, name="goal_simulator"),
    path("social-proof/", views.social_proof_view, name="social_proof"),
    path("research/", views.research_view, name="research"),
    path("voice/", views.voice_view, name="voice"),
    path("advisor/", views.advisor_view, name="advisor"),
    path("compliance/", views.compliance_view, name="compliance"),
    path("family/", views.family_view, name="family"),
    # API proxy endpoints
    path("api/profile/upsert/", views.api_profile_upsert, name="api_profile_upsert"),
    path("api/chat/", views.api_chat, name="api_chat"),
    path("api/voice/", views.api_voice, name="api_voice"),
    path("api/nudges/<str:nudge_id>/read/", views.api_nudge_read, name="api_nudge_read"),
    path("api/nudges/<str:nudge_id>/read", views.api_nudge_read, name="api_nudge_read_no_slash"),
    path("api/nudges/mark-all-read/", views.api_nudge_mark_all_read, name="api_nudge_mark_all_read"),
]
