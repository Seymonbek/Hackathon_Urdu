import asyncio
import os
import sys

# Windows UTF-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

from bot.db.connection import db
from bot.db.seed import seed_initial_data
from bot.db.repositories.jobs_repo import JobsRepo
from bot.db.repositories.employers_repo import EmployersRepo


async def test_db():
    print("Database ulanishi test qilinmoqda...")
    await db.connect()

    print("Seed ma'lumotlari yuklanmoqda...")
    await seed_initial_data()

    employers = await EmployersRepo.get_all()
    print(f"Bazada tashkilotlar soni: {len(employers)}")
    for e in employers:
        print(f" - {e['company_name']} ({e['org_type']}, {e['category']})")

    jobs = await JobsRepo.get_open_jobs()
    print(f"\nBazada ochiq e'lonlar soni: {len(jobs)}")
    for j in jobs:
        print(f" - [{j['listing_type']}] {j['title']} | To'lov: {j['pay_amount']} so'm | Kontrakt: {j['tuition_coverage_percent']}%")

    await db.disconnect()
    print("\n✅ DATABASE VA SEED TESTI MUVAFFAQIYATLI YAKUNLANDI!")


if __name__ == "__main__":
    asyncio.run(test_db())
