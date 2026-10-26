import unittest
from bot.db.connection import db
from bot.db.repositories.jobs_repo import JobsRepo
from bot.services.matching import calculate_match_score


class TestSeparatedJobsAndInternships(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await db.connect()

    async def asyncTearDown(self):
        await db.disconnect()

    async def test_jobs_and_internships_isolation(self):
        """Pullik ishlar va Amaliyotlar mutlaqo aralashib ketmasligini tekshirish."""
        all_jobs = await JobsRepo.get_open_jobs()
        self.assertTrue(len(all_jobs) >= 17)

        # 1. Pullik ishlar (jobs) filtri
        paid_jobs = [j for j in all_jobs if j.get("listing_type") != "state_internship"]
        internships = [j for j in all_jobs if j.get("listing_type") == "state_internship"]

        self.assertTrue(len(paid_jobs) > 0)
        self.assertTrue(len(internships) > 0)

        # Pullik ishlar ichida hech qanday tekin davlat amaliyoti bo'lmasligi kerak
        for j in paid_jobs:
            self.assertNotEqual(j.get("listing_type"), "state_internship")

        # Amaliyotlar ichida hech qanday oddiy pullik ish bo'lmasligi kerak
        for j in internships:
            self.assertEqual(j.get("listing_type"), "state_internship")

    async def test_new_specialized_internships_exist(self):
        """3 ta yangi mutaxassislik amaliyoti bazada mavjudligini tekshirish."""
        all_jobs = await JobsRepo.get_open_jobs()
        titles = [j["title"] for j in all_jobs]

        # 1. IT Park
        self.assertTrue(any("IT Park" in t for t in titles), "IT Park amaliyoti mavjud bo'lishi kerak")
        it_job = next(j for j in all_jobs if "IT Park" in j["title"])
        self.assertEqual(it_job["listing_type"], "state_internship")
        self.assertEqual(it_job["category"], "it")

        # 2. Tibbiyot birlashmasi
        self.assertTrue(any("Shifoxona" in t or "Tibbiyot" in t for t in titles), "Shifoxona amaliyoti mavjud bo'lishi kerak")
        med_job = next(j for j in all_jobs if "Shifoxona" in j["title"])
        self.assertEqual(med_job["listing_type"], "state_internship")
        self.assertEqual(med_job["category"], "medical")

        # 3. Kapitalbank
        self.assertTrue(any("Kapitalbank" in t for t in titles), "Kapitalbank amaliyoti mavjud bo'lishi kerak")
        bank_job = next(j for j in all_jobs if "Kapitalbank" in j["title"])
        self.assertEqual(bank_job["listing_type"], "state_internship")
        self.assertEqual(bank_job["category"], "office")

    async def test_student_matching_for_new_internships(self):
        """Tegishli soha talabalari uchun yangi amaliyotlar mos kelishini tekshirish."""
        all_jobs = await JobsRepo.get_open_jobs()
        it_job = next(j for j in all_jobs if "IT Park" in j["title"])
        med_job = next(j for j in all_jobs if "Shifoxona" in j["title"])
        bank_job = next(j for j in all_jobs if "Kapitalbank" in j["title"])

        # IT talabasi
        it_student = {
            "id": 701,
            "full_name": "Aziz Dasturchi",
            "faculty": "Raqamli texnologiyalar",
            "major": "Dasturiy injiniring",
            "course": 2,
            "gpa_score": 4.5,
            "location_lat": 41.5530,
            "location_lon": 60.6295,
            "max_distance_km": 10.0,
        }
        is_ok, score, reasons = calculate_match_score(it_student, it_job)
        self.assertTrue(is_ok)
        self.assertTrue(score >= 80.0)

        # Tibbiyot talabasi
        med_student = {
            "id": 702,
            "full_name": "Gulnoza Vrach",
            "faculty": "Davolash",
            "major": "Davolash ishi",
            "course": 3,
            "gpa_score": 4.7,
            "location_lat": 41.5600,
            "location_lon": 60.6200,
            "max_distance_km": 10.0,
        }
        is_ok_m, score_m, reasons_m = calculate_match_score(med_student, med_job)
        self.assertTrue(is_ok_m)
        self.assertTrue(score_m >= 80.0)

        # Bank/Iqtisodiyot talabasi
        econ_student = {
            "id": 703,
            "full_name": "Bobur Bankir",
            "faculty": "Iqtisodiyot",
            "major": "Bank ishi",
            "course": 3,
            "gpa_score": 4.3,
            "location_lat": 41.5525,
            "location_lon": 60.6315,
            "max_distance_km": 10.0,
        }
        is_ok_b, score_b, reasons_b = calculate_match_score(econ_student, bank_job)
        self.assertTrue(is_ok_b)
        self.assertTrue(score_b >= 80.0)


if __name__ == "__main__":
    unittest.main()
