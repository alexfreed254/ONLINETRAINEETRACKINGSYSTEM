-- ============================================================
-- RLS FIX + SEED DATA
-- Run this in Supabase SQL Editor
-- ============================================================

-- Enable RLS on reference tables
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE competencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_views ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Departments are publicly readable" ON departments;
DROP POLICY IF EXISTS "Courses are publicly readable" ON courses;
DROP POLICY IF EXISTS "Competencies are publicly readable" ON competencies;
DROP POLICY IF EXISTS "Service role manages departments" ON departments;
DROP POLICY IF EXISTS "Service role manages courses" ON courses;

-- Public read for reference data (needed for registration form)
CREATE POLICY "Departments are publicly readable" ON departments FOR SELECT USING (true);
CREATE POLICY "Courses are publicly readable"     ON courses     FOR SELECT USING (true);
CREATE POLICY "Competencies are publicly readable" ON competencies FOR SELECT USING (true);

-- ============================================================
-- SEED DEPARTMENTS
-- ============================================================
INSERT INTO departments (name, code, description) VALUES
    ('Electrical Engineering',  'EE',  'Electrical installation and maintenance'),
    ('Mechanical Engineering',  'ME',  'Mechanical systems and fabrication'),
    ('Information Technology',  'IT',  'Software development and networking'),
    ('Civil Engineering',       'CE',  'Construction and structural engineering'),
    ('Automotive Engineering',  'AE',  'Vehicle mechanics and diagnostics'),
    ('Welding & Fabrication',   'WF',  'Metal welding and fabrication'),
    ('Plumbing',                'PL',  'Plumbing and pipe fitting'),
    ('Carpentry',               'CA',  'Woodwork and furniture making')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- SEED COURSES — linked to their department
-- ============================================================
INSERT INTO courses (name, code, duration_months, description, is_active, department_id)
SELECT 'Certificate in Electrical Installation', 'CEI',  24, 'Domestic and industrial electrical installation', true, id
FROM departments WHERE code = 'EE'
ON CONFLICT (code) DO UPDATE SET department_id = EXCLUDED.department_id;

INSERT INTO courses (name, code, duration_months, description, is_active, department_id)
SELECT 'Diploma in Mechanical Engineering', 'DME', 36, 'Mechanical systems design and maintenance', true, id
FROM departments WHERE code = 'ME'
ON CONFLICT (code) DO UPDATE SET department_id = EXCLUDED.department_id;

INSERT INTO courses (name, code, duration_months, description, is_active, department_id)
SELECT 'Certificate in ICT', 'CICT', 24, 'Information and communication technology', true, id
FROM departments WHERE code = 'IT'
ON CONFLICT (code) DO UPDATE SET department_id = EXCLUDED.department_id;

INSERT INTO courses (name, code, duration_months, description, is_active, department_id)
SELECT 'Certificate in Civil Engineering', 'CCE', 24, 'Building and construction technology', true, id
FROM departments WHERE code = 'CE'
ON CONFLICT (code) DO UPDATE SET department_id = EXCLUDED.department_id;

INSERT INTO courses (name, code, duration_months, description, is_active, department_id)
SELECT 'Certificate in Automotive Engineering', 'CAE', 24, 'Motor vehicle mechanics', true, id
FROM departments WHERE code = 'AE'
ON CONFLICT (code) DO UPDATE SET department_id = EXCLUDED.department_id;

INSERT INTO courses (name, code, duration_months, description, is_active, department_id)
SELECT 'Certificate in Welding', 'CW', 18, 'Arc and MIG welding techniques', true, id
FROM departments WHERE code = 'WF'
ON CONFLICT (code) DO UPDATE SET department_id = EXCLUDED.department_id;

INSERT INTO courses (name, code, duration_months, description, is_active, department_id)
SELECT 'Certificate in Plumbing', 'CP', 18, 'Plumbing and sanitation systems', true, id
FROM departments WHERE code = 'PL'
ON CONFLICT (code) DO UPDATE SET department_id = EXCLUDED.department_id;

INSERT INTO courses (name, code, duration_months, description, is_active, department_id)
SELECT 'Certificate in Carpentry', 'CC', 18, 'Furniture making and joinery', true, id
FROM departments WHERE code = 'CA'
ON CONFLICT (code) DO UPDATE SET department_id = EXCLUDED.department_id;

-- ============================================================
-- VERIFY
-- ============================================================
SELECT
    d.name AS department,
    d.code AS dept_code,
    c.name AS course,
    c.code AS course_code
FROM departments d
LEFT JOIN courses c ON c.department_id = d.id
ORDER BY d.name, c.name;
