"""
CREDA Demo Regenerator
======================
Wipes and re-seeds the demo users (Arjun + Priya) in both databases.
Does NOT touch non-demo users (id != 100, 101).

Usage:
    cd python/demo
    python regenerate.py           # wipe demo users + re-seed
    python regenerate.py --clean   # wipe demo users only
"""
import argparse
import asyncio
import os
import sys

# ── Project paths ─────────────────────────────────────────────────
DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(DEMO_DIR, "..", "backend")
FRONTEND_DIR = os.path.join(DEMO_DIR, "..", "frontend")
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, FRONTEND_DIR)

DEMO_IDS = ["100", "101"]
DEMO_DJANGO_IDS = [100, 101]


# ═══════════════════════════════════════════════════════════════════
#  Clean FastAPI database
# ═══════════════════════════════════════════════════════════════════

async def clean_fastapi():
    """Remove demo users from creda_api."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import text
    from app.config import settings

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Order matters — foreign keys
    tables_to_clean = [
        "conversation_messages",
        "nudges",
        "life_events",
        "family_links",
        "goal_plans",
        "portfolio_funds",
        "portfolios",
        "user_profiles",
        "users",
    ]

    async with Session() as db:
        for table in tables_to_clean:
            col = "user_id" if table != "users" else "id"
            if table == "portfolio_funds":
                # portfolio_funds references portfolio, not user directly
                await db.execute(text(
                    "DELETE FROM portfolio_funds WHERE portfolio_id IN "
                    "(SELECT id FROM portfolios WHERE user_id IN :ids)"
                ), {"ids": tuple(DEMO_IDS)})
            elif table == "family_links":
                # family_links has owner_id and member_id
                for uid in DEMO_IDS:
                    await db.execute(text(
                        "DELETE FROM family_links WHERE owner_id = :uid OR member_id = :uid"
                    ), {"uid": uid})
            else:
                for uid in DEMO_IDS:
                    await db.execute(text(
                        f"DELETE FROM {table} WHERE {col} = :uid"
                    ), {"uid": uid})
        await db.commit()

    await engine.dispose()
    print("  [clean] Demo users removed from creda_api")


# ═══════════════════════════════════════════════════════════════════
#  Clean Django database
# ═══════════════════════════════════════════════════════════════════

def clean_django():
    """Remove demo users from creda_django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "creda.settings")
    import django
    django.setup()

    from accounts.models import User as DjangoUser
    deleted, _ = DjangoUser.objects.filter(id__in=DEMO_DJANGO_IDS).delete()
    print(f"  [clean] Removed {deleted} demo rows from creda_django")


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="CREDA Demo Regenerator")
    parser.add_argument("--clean", action="store_true", help="Only wipe — do not re-seed")
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  CREDA Demo Regenerator")
    print("=" * 60)
    print()

    # Step 1: Clean
    print("  [1/2] Cleaning demo data...")
    clean_django()
    asyncio.run(clean_fastapi())
    print()

    if args.clean:
        print("  Clean-only mode. Done.")
        return

    # Step 2: Re-seed (delegate to seed_demo.py)
    print("  [2/2] Re-seeding demo data...")
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, BACKEND_DIR)
    from seed_demo import seed_django_db, seed_fastapi_db
    seed_django_db()
    asyncio.run(seed_fastapi_db())
    print()

    print("=" * 60)
    print("  Demo regenerated! Log in at http://localhost:8000 with:")
    print("    Email: arjun@demo.creda.in")
    print("    Password: demo1234")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
