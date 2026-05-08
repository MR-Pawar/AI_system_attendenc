from supabase import create_client, Client
from config import settings

# ── Supabase Client ────────────────────────────────
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_db() -> Client:
    """Return the Supabase client instance."""
    return supabase


# ──────────────────────────────────────────────────────────────────────────────
# DATABASE SCHEMA  –  Run this SQL once in your Supabase SQL Editor
# Project: https://xuduzaibuefetuvbzgpb.supabase.co
# ──────────────────────────────────────────────────────────────────────────────
SCHEMA_SQL = """
-- ── Enable UUID extension ──────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── CLASSES table ──────────────────────────────────
CREATE TABLE IF NOT EXISTS classes (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    class_name  VARCHAR(100) NOT NULL,
    subject     VARCHAR(100) NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── STUDENTS table ─────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    roll_number   VARCHAR(30)  UNIQUE NOT NULL,
    class         VARCHAR(100),
    face_encoding TEXT,
    email         VARCHAR(100),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── ATTENDANCE table ───────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    date        DATE    NOT NULL DEFAULT CURRENT_DATE,
    time        TIME    NOT NULL DEFAULT CURRENT_TIME,
    status      VARCHAR(10) NOT NULL DEFAULT 'present'
                    CHECK (status IN ('present', 'absent', 'late')),
    confidence  FLOAT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (student_id, date)
);

-- ── Indexes ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_students_roll     ON students(roll_number);
CREATE INDEX IF NOT EXISTS idx_attendance_date   ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_attendance_stu    ON attendance(student_id);
"""
