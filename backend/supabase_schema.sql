-- ═══════════════════════════════════════════════════════════════
--  AI Face Attendance — Supabase SQL Schema (Updated)
--  New fields: department, year, section in students table
--  Run this in: Supabase → SQL Editor → Paste → Run
-- ═══════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Drop existing tables (clean setup)
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS classes;

-- ─────────────────────────────────────────────────
-- CLASSES table
-- ─────────────────────────────────────────────────
CREATE TABLE classes (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    class_name  VARCHAR(100) NOT NULL,
    subject     VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ─────────────────────────────────────────────────
-- STUDENTS table  ← department, year, section ADDED
-- ─────────────────────────────────────────────────
CREATE TABLE students (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    roll_number   VARCHAR(30)  UNIQUE NOT NULL,
    department    VARCHAR(50),          -- BCA | B.com | BSc
    year          VARCHAR(20),          -- 1st | 2nd | 3rd
    section       VARCHAR(5),           -- A | B
    class         VARCHAR(100),         -- legacy / optional
    face_encoding TEXT,
    email         VARCHAR(100),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- ─────────────────────────────────────────────────
-- ATTENDANCE table
-- ─────────────────────────────────────────────────
CREATE TABLE attendance (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    date        DATE        DEFAULT CURRENT_DATE,
    time        TIME        DEFAULT CURRENT_TIME,
    status      VARCHAR(10) DEFAULT 'present'
                CHECK (status IN ('present','absent','late')),
    confidence  FLOAT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (student_id, date)
);

-- ─────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────
CREATE INDEX idx_students_roll       ON students(roll_number);
CREATE INDEX idx_students_dept       ON students(department);
CREATE INDEX idx_students_year       ON students(year);
CREATE INDEX idx_students_section    ON students(section);
CREATE INDEX idx_attendance_date     ON attendance(date);
CREATE INDEX idx_attendance_student  ON attendance(student_id);

-- ─────────────────────────────────────────────────
-- DISABLE RLS  (important!)
-- ─────────────────────────────────────────────────
ALTER TABLE classes    DISABLE ROW LEVEL SECURITY;
ALTER TABLE students   DISABLE ROW LEVEL SECURITY;
ALTER TABLE attendance DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────
-- SAMPLE CLASSES
-- ─────────────────────────────────────────────────
INSERT INTO classes (class_name, subject) VALUES
    ('BCA 1st A',  'Computer Science'),
    ('BCA 1st B',  'Computer Science'),
    ('BCA 2nd A',  'Computer Science'),
    ('BCA 2nd B',  'Computer Science'),
    ('BCA 3rd A',  'Computer Science'),
    ('BCA 3rd B',  'Computer Science'),
    ('B.com 1st A','Commerce'),
    ('B.com 1st B','Commerce'),
    ('B.com 2nd A','Commerce'),
    ('B.com 2nd B','Commerce'),
    ('B.com 3rd A','Commerce'),
    ('B.com 3rd B','Commerce'),
    ('BSc 1st A',  'Science'),
    ('BSc 1st B',  'Science'),
    ('BSc 2nd A',  'Science'),
    ('BSc 2nd B',  'Science'),
    ('BSc 3rd A',  'Science'),
    ('BSc 3rd B',  'Science');

-- ─────────────────────────────────────────────────
-- VERIFY
-- ─────────────────────────────────────────────────
SELECT 'classes'   AS table_name, COUNT(*) AS rows FROM classes
UNION ALL
SELECT 'students',   COUNT(*) FROM students
UNION ALL
SELECT 'attendance', COUNT(*) FROM attendance;
