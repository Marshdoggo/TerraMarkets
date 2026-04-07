from __future__ import annotations

from app.core.db import SessionLocal
from app.services.demo_market_service import seed_demo_markets


def main():
    db = SessionLocal()
    try:
        summary = seed_demo_markets(db)
        db.commit()
        print(
            "Seeded demo markets:",
            f"created={summary['created_markets']}",
            f"existing={summary['existing_markets']}",
            f"created_links={summary['created_links']}",
            f"existing_links={summary['existing_links']}",
        )
        for pipeline in summary["pipelines"]:
            print(
                f"{pipeline['pipeline_label']}:",
                f"markets+{pipeline['created_markets']}",
                f"markets={pipeline['existing_markets']}",
                f"links+{pipeline['created_links']}",
                f"links={pipeline['existing_links']}",
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
