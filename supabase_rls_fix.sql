-- ============================================================
-- RLS FIX: Run this in Supabase SQL Editor
-- Makes departments and courses publicly readable
-- so the registration form dropdowns work
-- ============================================================

-- Enable RLS on reference tables (if not already)
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE competencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_views ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Departments are publicly readable" ON departments;
DROP POLICY IF EXISTS "Courses are publicly readable" ON courses;
DROP POLICY IF EXISTS "Competencies are publicly readable" ON competencies;

-- Allow anyone (including unauthenticated) to read reference data
CREATE POLICY "Departments are publicly readable" ON departments FOR SELECT USING (true);
CREATE POLICY "Courses are publicly readable" ON courses FOR SELECT USING (true);
CREATE POLICY "Competencies are publicly readable" ON competencies FOR SELECT USING (true);

-- Allow service role to manage departments and courses
CREATE POLICY "Service role manages departments" ON departments FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role manages courses" ON courses FOR ALL USING (true) WITH CHECK (true);

-- ============================================================
-- SEED DATA - Run only if tables are empty
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

INSERT INTO courses (name, code, duration_months, description, is_active) VALUES
    ('Certificate in Electrical Installation', 'CEI',  24, 'Domestic and industrial electrical installation', true),
    ('Diploma in Mechanical Engineering',      'DME',  36, 'Mechanical systems design and maintenance',       true),
    ('Certificate in ICT',                     'CICT', 24, 'Information and communication technology',        true),
    ('Certificate in Civil Engineering',       'CCE',  24, 'Building and construction technology',            true),
    ('Certificate in Automotive Engineering',  'CAE',  24, 'Motor vehicle mechanics',                         true),
    ('Certificate in Welding',                 'CW',   18, 'Arc and MIG welding techniques',                  true),
    ('Certificate in Plumbing',                'CP',   18, 'Plumbing and sanitation systems',                 true),
    ('Certificate in Carpentry',               'CC',   18, 'Furniture making and joinery',                    true)
ON CONFLICT (code) DO NOTHING;

-- Verify
SELECT 'departments' as table_name, count(*) as rows FROM departments
UNION ALL
SELECT 'courses', count(*) FROM courses;
