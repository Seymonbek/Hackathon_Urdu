from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    EMPLOYER = "employer"
    ADMIN = "admin"
    TUTOR = "tutor"
    GUEST = "guest"


class UserStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"


class OrgType(str, Enum):
    COMMERCIAL = "commercial"
    STATE_AGENCY = "state_agency"


class JobCategory(str, Enum):
    COURT_LAW = "court_law"        # Sudlar, Adliya, Yuridik byuro
    MEDICAL = "medical"            # Shifoxonalar, Tez yordam, Poliklinika
    EDUCATION = "education"        # Maktablar, O'quv markazlari, Repetitorlik
    RETAIL = "retail"              # Savdo, Do'konlar, Supermarketlar, Kassa
    MEDIA_SMM = "media_smm"        # SMM, Dizayn, Mobilografiya, Kopirayting
    OFFICE = "office"              # Call-center, Operatorlik, 1C ma'lumot kiritish
    HORECA = "horeca"              # Kafelar, Restoranlar, Barista, Ofitsiant
    IT = "it"                      # Dasturchi stajor, Veb-sayt, Texnik yordam
    GIG = "gig"                    # 1 kunlik tadbirlar, Ko'rgazma, Promouter


class ListingType(str, Enum):
    PAID_JOB = "paid_job"
    STATE_INTERNSHIP = "state_internship"
    TUITION_GRANT_JOB = "tuition_grant_job"


class WorkFormat(str, Enum):
    OFFLINE_SHIFT = "offline_shift"
    REMOTE_TASK = "remote_task"
    ONE_DAY_GIG = "one_day_gig"
    HOSPITAL_NIGHT_SHIFT = "hospital_night_shift"


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    DONE = "done"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class SponsorshipStatus(str, Enum):
    OFFERED = "offered"
    STUDENT_ACCEPTED = "student_accepted"
    OTM_VERIFIED = "otm_verified"
    PAID = "paid"
    REJECTED = "rejected"
