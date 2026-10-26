-- POSTGRESQL PRODUCTION DDL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "cube";
CREATE EXTENSION IF NOT EXISTS "earthdistance";

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('student', 'employer', 'admin', 'guest');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'guest';
EXCEPTION WHEN others THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE user_status AS ENUM ('active', 'paused', 'blocked');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE org_type_enum AS ENUM ('commercial', 'state_agency');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE listing_type_enum AS ENUM ('paid_job', 'state_internship', 'tuition_grant_job');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE work_format_enum AS ENUM ('offline_shift', 'remote_task', 'one_day_gig', 'hospital_night_shift');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE app_status_enum AS ENUM ('pending', 'accepted', 'rejected', 'withdrawn', 'done', 'no_show', 'cancelled');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE sponsorship_status_enum AS ENUM ('offered', 'student_accepted', 'otm_verified', 'paid', 'rejected');
EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE NOT NULL,
    role user_role NOT NULL,
    status user_status DEFAULT 'active',
    lang VARCHAR(5) DEFAULT 'uz',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(30),
    region VARCHAR(150),
    university VARCHAR(255),
    faculty VARCHAR(150) NOT NULL,
    major VARCHAR(150) NOT NULL,
    course SMALLINT CHECK(course BETWEEN 1 AND 6) NOT NULL,
    course_label VARCHAR(50),
    is_contract BOOLEAN DEFAULT TRUE,
    yearly_tuition_amount INTEGER DEFAULT 0,
    gpa_score NUMERIC(3, 2) DEFAULT 0.00,
    interests JSONB DEFAULT '[]'::jsonb,
    skills JSONB DEFAULT '[]'::jsonb,
    location_lat DOUBLE PRECISION,
    location_lon DOUBLE PRECISION,
    location_name VARCHAR(255),
    max_distance_km DOUBLE PRECISION DEFAULT 5.0,
    schedule_busy JSONB DEFAULT '{}'::jsonb,
    buffer_min SMALLINT DEFAULT 45,
    work_formats JSONB DEFAULT '["offline_shift","remote_task","state_internship"]'::jsonb,
    min_pay INTEGER DEFAULT 0,
    transport_cost INTEGER DEFAULT 0,
    trust_score SMALLINT DEFAULT 100,
    is_adult_confirmed BOOLEAN DEFAULT TRUE,
    verified_student BOOLEAN DEFAULT FALSE,
    exam_from DATE,
    exam_to DATE,
    internship_status VARCHAR(20) DEFAULT 'none',
    resume_s3_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employers (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    org_type org_type_enum NOT NULL,
    category VARCHAR(50) NOT NULL,
    address VARCHAR(300) NOT NULL,
    district VARCHAR(100) NOT NULL,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    contact_phone VARCHAR(25) NOT NULL,
    contact_person VARCHAR(100) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    offers_tuition_sponsorship BOOLEAN DEFAULT FALSE,
    rating NUMERIC(3, 2) DEFAULT 5.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    employer_id BIGINT REFERENCES employers(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    listing_type listing_type_enum NOT NULL,
    category VARCHAR(50) NOT NULL,
    work_format work_format_enum NOT NULL,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    slots_needed SMALLINT DEFAULT 1,
    filled_count SMALLINT DEFAULT 0,
    target_majors JSONB DEFAULT '[]'::jsonb,
    min_course_required SMALLINT DEFAULT 1,
    min_gpa_required NUMERIC(3, 2) DEFAULT 0.00,
    required_skills JSONB DEFAULT '[]'::jsonb,
    job_date DATE,
    start_time VARCHAR(5),
    end_time VARCHAR(5),
    total_hours NUMERIC(4, 1),
    pay_amount INTEGER DEFAULT 0,
    pay_unit VARCHAR(30) DEFAULT 'per_shift',
    pay_method VARCHAR(20) DEFAULT 'cash',
    pay_timing VARCHAR(30) DEFAULT 'daily',
    tuition_coverage_percent SMALLINT DEFAULT 0,
    work_obligation_years SMALLINT DEFAULT 0,
    duties JSONB NOT NULL,
    perks JSONB DEFAULT '[]'::jsonb,
    is_urgent BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
    student_id BIGINT REFERENCES students(id) ON DELETE CASCADE,
    match_score NUMERIC(5, 2) NOT NULL,
    is_backup BOOLEAN DEFAULT FALSE,
    backup_rank SMALLINT DEFAULT 0,
    status app_status_enum DEFAULT 'pending',
    reject_reason VARCHAR(255),
    student_confirmed_at TIMESTAMPTZ,
    employer_confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_job_student UNIQUE (job_id, student_id)
);

CREATE TABLE IF NOT EXISTS tuition_sponsorships (
    id BIGSERIAL PRIMARY KEY,
    application_id BIGINT REFERENCES applications(id) ON DELETE CASCADE,
    student_id BIGINT REFERENCES students(id) ON DELETE CASCADE,
    employer_id BIGINT REFERENCES employers(id) ON DELETE CASCADE,
    covered_amount INTEGER NOT NULL,
    obligation_months SMALLINT NOT NULL,
    contract_pdf_s3_url VARCHAR(500),
    status sponsorship_status_enum DEFAULT 'offered',
    otm_approved_by VARCHAR(100),
    otm_approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS internship_logs (
    id BIGSERIAL PRIMARY KEY,
    application_id BIGINT REFERENCES applications(id) ON DELETE CASCADE,
    student_id BIGINT REFERENCES students(id) ON DELETE CASCADE,
    visit_date DATE NOT NULL,
    hours_spent NUMERIC(4, 1) NOT NULL,
    tasks_performed TEXT NOT NULL,
    mentor_feedback TEXT,
    mentor_score SMALLINT CHECK(mentor_score BETWEEN 1 AND 5),
    verified_by_mentor BOOLEAN DEFAULT FALSE,
    certificate_s3_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ratings (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT REFERENCES jobs(id) ON DELETE CASCADE,
    from_user_id BIGINT REFERENCES users(id),
    to_user_id BIGINT REFERENCES users(id),
    role VARCHAR(30) NOT NULL,
    score SMALLINT CHECK(score BETWEEN 1 AND 5) NOT NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    actor_id BIGINT REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id BIGINT NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
