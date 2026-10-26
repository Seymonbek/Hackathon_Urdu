-- SQLITE LOCAL / STANDALONE COMPATIBLE DDL
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    role TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    lang TEXT DEFAULT 'uz',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    phone_number TEXT,
    region TEXT,
    university TEXT,
    faculty TEXT NOT NULL,
    major TEXT NOT NULL,
    course INTEGER NOT NULL,
    course_label TEXT,
    is_contract BOOLEAN DEFAULT 1,
    yearly_tuition_amount INTEGER DEFAULT 0,
    gpa_score REAL DEFAULT 0.00,
    interests TEXT DEFAULT '[]',
    skills TEXT DEFAULT '[]',
    location_lat REAL,
    location_lon REAL,
    location_name TEXT,
    max_distance_km REAL DEFAULT 5.0,
    schedule_busy TEXT DEFAULT '{}',
    buffer_min INTEGER DEFAULT 45,
    work_formats TEXT DEFAULT '["offline_shift","remote_task","state_internship"]',
    min_pay INTEGER DEFAULT 0,
    transport_cost INTEGER DEFAULT 0,
    trust_score INTEGER DEFAULT 100,
    is_adult_confirmed BOOLEAN DEFAULT 1,
    verified_student BOOLEAN DEFAULT 0,
    exam_from DATE,
    exam_to DATE,
    internship_status TEXT DEFAULT 'none',
    resume_s3_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    org_type TEXT NOT NULL,
    category TEXT NOT NULL,
    address TEXT NOT NULL,
    district TEXT NOT NULL,
    lat REAL,
    lon REAL,
    contact_phone TEXT NOT NULL,
    contact_person TEXT NOT NULL,
    is_verified BOOLEAN DEFAULT 0,
    offers_tuition_sponsorship BOOLEAN DEFAULT 0,
    rating REAL DEFAULT 5.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id INTEGER REFERENCES employers(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    listing_type TEXT NOT NULL,
    category TEXT NOT NULL,
    work_format TEXT NOT NULL,
    lat REAL,
    lon REAL,
    slots_needed INTEGER DEFAULT 1,
    filled_count INTEGER DEFAULT 0,
    target_majors TEXT DEFAULT '[]',
    min_course_required INTEGER DEFAULT 1,
    min_gpa_required REAL DEFAULT 0.00,
    required_skills TEXT DEFAULT '[]',
    job_date DATE,
    start_time TEXT,
    end_time TEXT,
    total_hours REAL,
    pay_amount INTEGER DEFAULT 0,
    pay_unit TEXT DEFAULT 'per_shift',
    pay_method TEXT DEFAULT 'cash',
    pay_timing TEXT DEFAULT 'daily',
    tuition_coverage_percent INTEGER DEFAULT 0,
    work_obligation_years INTEGER DEFAULT 0,
    duties TEXT NOT NULL,
    perks TEXT DEFAULT '[]',
    is_urgent BOOLEAN DEFAULT 0,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    match_score REAL NOT NULL,
    is_backup BOOLEAN DEFAULT 0,
    backup_rank INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    reject_reason TEXT,
    student_confirmed_at TIMESTAMP,
    employer_confirmed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, student_id)
);

CREATE TABLE IF NOT EXISTS tuition_sponsorships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    employer_id INTEGER REFERENCES employers(id) ON DELETE CASCADE,
    covered_amount INTEGER NOT NULL,
    obligation_months INTEGER NOT NULL,
    contract_pdf_s3_url TEXT,
    status TEXT DEFAULT 'offered',
    otm_approved_by TEXT,
    otm_approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS internship_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    visit_date DATE NOT NULL,
    hours_spent REAL NOT NULL,
    tasks_performed TEXT NOT NULL,
    mentor_feedback TEXT,
    mentor_score INTEGER,
    verified_by_mentor BOOLEAN DEFAULT 0,
    certificate_s3_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    from_user_id INTEGER REFERENCES users(id),
    to_user_id INTEGER REFERENCES users(id),
    role TEXT NOT NULL,
    score INTEGER NOT NULL,
    tags TEXT DEFAULT '[]',
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
