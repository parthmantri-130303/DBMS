-- CampusKhoj Database Seed Data
-- Source of truth: Docs/05_backend_schema.md & Docs/01_PRD_product_requirements.md

-- ----------------------------------------------------------------------------
-- 1. Campuses
-- ----------------------------------------------------------------------------
INSERT INTO campuses (campus_id, campus_name, code) VALUES
(1, 'Kondhwa Campus', 'KON'),
(2, 'Bibwewadi Campus', 'BIB')
ON DUPLICATE KEY UPDATE campus_name=VALUES(campus_name), code=VALUES(code);

-- ----------------------------------------------------------------------------
-- 2. Roles
-- ----------------------------------------------------------------------------
INSERT INTO roles (role_id, role_name) VALUES
(1, 'STUDENT'),
(2, 'SECURITY'),
(3, 'CAMPUS_ADMIN'),
(4, 'SUPER_ADMIN')
ON DUPLICATE KEY UPDATE role_name=VALUES(role_name);

-- ----------------------------------------------------------------------------
-- 3. Categories
-- ----------------------------------------------------------------------------
INSERT INTO categories (category_id, category_name, description, icon) VALUES
(1, 'Electronics', 'Phones, laptops, chargers, cables, earbuds, calculators', 'laptop'),
(2, 'Identification & Cards', 'College ID, library cards, metro cards, licenses', 'id-card'),
(3, 'Wallets & Purses', 'Wallets, purses, pouches with currency or cards', 'wallet'),
(4, 'Bags & Backpacks', 'College bags, laptop bags, totes, gym bags', 'briefcase'),
(5, 'Books & Stationery', 'Notebooks, textbooks, pencil pouches, drafting tools', 'book-open'),
(6, 'Keys', 'Bike keys, room keys, hostel locker keys', 'key'),
(7, 'Clothing & Accessories', 'Jackets, watches, glasses, umbrellas, caps', 'shirt'),
(8, 'Bottles & Containers', 'Water bottles, thermoses, lunch boxes', 'coffee'),
(9, 'Others', 'Miscellaneous items not classified above', 'help-circle')
ON DUPLICATE KEY UPDATE category_name=VALUES(category_name), description=VALUES(description), icon=VALUES(icon);

-- ----------------------------------------------------------------------------
-- 4. Locations (Campus specific with Composite Key (location_id, campus_id))
-- ----------------------------------------------------------------------------
-- Kondhwa Campus (campus_id = 1)
INSERT INTO locations (location_id, campus_id, location_name, room_or_spot, building, floor, description, sort_order, is_active) VALUES
(101, 1, 'Kondhwa Security Desk', 'Security Desk', 'Main Building', 'Ground Floor', 'Security checkpoint at main entrance gate', 1, 1),
(102, 1, 'Central Library Kondhwa', 'Central Library', 'Main Building', '2nd Floor', 'Silent reading and digital library hall', 2, 1),
(103, 1, 'Computer Center Lab 101', 'Computer Center Lab 101', 'Engineering Block', '1st Floor', 'High-performance computing laboratory', 3, 1),
(104, 1, 'Electronics Lab 204', 'Electronics Lab 204', 'Engineering Block', '2nd Floor', 'Analog & Digital circuits laboratory', 4, 1),
(105, 1, 'Mechanical Workshop', 'Mechanical Workshop', 'Workshop Block', 'Ground Floor', 'Fitting, machining and welding shop', 5, 1),
(106, 1, 'Kondhwa Cafeteria', 'Kondhwa Cafeteria', 'Student Center', 'Ground Floor', 'Main student dining cafeteria', 6, 1),
(107, 1, 'Badminton Court & Gym', 'Badminton Court & Gym', 'Sports Complex', 'Ground Floor', 'Indoor sports hall and fitness room', 7, 1),
(108, 1, 'Seminar Hall 1', 'Seminar Hall 1', 'Main Building', '3rd Floor', 'Auditorium and presentation hall', 8, 1),
(109, 1, 'Boys Hostel Block A Common Room', 'Common Room', 'Hostel Block A', 'Ground Floor', 'Hostel recreation lounge', 9, 1),
(110, 1, 'Two-Wheeler Parking Area', 'Two-Wheeler Parking Area', 'South Gate', 'Open Ground', 'Student scooter and bike parking bay', 10, 1),
(111, 1, 'Other / Not sure (Kondhwa)', 'Other / Not sure', 'Other', 'Various', 'Custom spot described by student', 11, 1)
ON DUPLICATE KEY UPDATE location_name=VALUES(location_name), room_or_spot=VALUES(room_or_spot), building=VALUES(building), is_active=1;

-- Bibwewadi Campus (campus_id = 2)
INSERT INTO locations (location_id, campus_id, location_name, room_or_spot, building, floor, description, sort_order, is_active) VALUES
(201, 2, 'Building 1', 'Building 1', 'Building 1', 'Multiple Floors', 'Academic block Building 1', 1, 1),
(202, 2, 'Building 2', 'Building 2', 'Building 2', 'Multiple Floors', 'Academic block Building 2', 2, 1),
(203, 2, 'Building 3', 'Building 3', 'Building 3', 'Multiple Floors', 'Laboratories block Building 3', 3, 1),
(204, 2, 'Building 4', 'Building 4', 'Building 4', 'Multiple Floors', 'Lecture halls block Building 4', 4, 1),
(205, 2, 'Fruit Canteen', 'Fruit Canteen', 'Canteen Area', 'Ground Floor', 'Campus fresh fruit and juice canteen', 5, 1),
(206, 2, 'Kiosk Cafe', 'Kiosk Cafe', 'Campus Plaza', 'Ground Floor', 'Central campus cafe kiosk', 6, 1),
(207, 2, 'Nescafe', 'Nescafe', 'Campus Plaza', 'Ground Floor', 'Nescafe coffee and snack corner', 7, 1),
(208, 2, 'Parking', 'Parking', 'Parking Area', 'Ground Floor', 'Two-wheeler and vehicle parking bay', 8, 1),
(209, 2, '-1 (Basement -1)', '-1 (Basement -1)', 'Basement Block', 'Basement -1', 'Lower level parking and lab area -1', 9, 1),
(210, 2, '-2 (Basement -2)', '-2 (Basement -2)', 'Basement Block', 'Basement -2', 'Deep underground level -2', 10, 1),
(211, 2, 'Boat Club', 'Boat Club', 'Lake Side', 'Ground Floor', 'Campus lake recreation and boat club area', 11, 1),
(212, 2, 'Student Section', 'Student Section', 'Admin Block', 'Ground Floor', 'Student administration and office section', 12, 1),
(213, 2, 'Staff Canteen', 'Staff Canteen', 'Staff Block', 'Ground Floor', 'Faculty and staff dining cafeteria', 13, 1),
(214, 2, 'Poonawalla Bakery', 'Poonawalla Bakery', 'Food Court', 'Ground Floor', 'Campus bakery and confectionery outlet', 14, 1),
(215, 2, 'Paratha House', 'Paratha House', 'Food Court', 'Ground Floor', 'Hot paratha food court joint', 15, 1),
(216, 2, 'Other / Not sure (Bibwewadi)', 'Other / Not sure', 'Other', 'Various', 'Custom spot described by student', 16, 1)
ON DUPLICATE KEY UPDATE location_name=VALUES(location_name), room_or_spot=VALUES(room_or_spot), building=VALUES(building), is_active=1;

-- ----------------------------------------------------------------------------
-- 5. Development & Rehearsal Demo Staff Accounts
-- ATTENTION: FOR DEVELOPMENT, TESTING & DEMO REHEARSALS ONLY.
-- In production, delete these rows or run `python manage.py purge-demo-staff`.
-- Create production staff using:
--   python manage.py create-admin --username <user> --name <name> --role <role> --password <strong_pwd>
-- ----------------------------------------------------------------------------
INSERT INTO users (user_id, prn, staff_username, name, email, phone, password_hash, must_change_password, role_id, campus_id, status, profile_completed) VALUES
(1, NULL, 'admin', 'Super Admin', 'admin@campuskhoj.vit.edu', '9876543210', '$2b$12$RB5sX1yqZLKSY80nJKd03ujw5PBbynvzJ1mJnNKMk4LRzhos86vYq', 0, 4, NULL, 'ACTIVE', 1),
(2, NULL, 'admin_kon', 'Dr. Joshi (Kondhwa Admin)', 'admin.kon@campuskhoj.vit.edu', '9876543211', '$2b$12$RB5sX1yqZLKSY80nJKd03ujw5PBbynvzJ1mJnNKMk4LRzhos86vYq', 0, 3, 1, 'ACTIVE', 1),
(3, NULL, 'admin_bib', 'Prof. Kulkarni (Bibwewadi Admin)', 'admin.bib@campuskhoj.vit.edu', '9876543212', '$2b$12$RB5sX1yqZLKSY80nJKd03ujw5PBbynvzJ1mJnNKMk4LRzhos86vYq', 0, 3, 2, 'ACTIVE', 1),
(4, NULL, 'security_kon', 'Mr. Patil (Kondhwa Desk)', 'security.kon@campuskhoj.vit.edu', '9876543213', '$2b$12$RB5sX1yqZLKSY80nJKd03ujw5PBbynvzJ1mJnNKMk4LRzhos86vYq', 0, 2, 1, 'ACTIVE', 1),
(5, NULL, 'security_bib', 'Mr. Shinde (Bibwewadi Desk)', 'security.bib@campuskhoj.vit.edu', '9876543214', '$2b$12$RB5sX1yqZLKSY80nJKd03ujw5PBbynvzJ1mJnNKMk4LRzhos86vYq', 0, 2, 2, 'ACTIVE', 1)
ON DUPLICATE KEY UPDATE staff_username=VALUES(staff_username), name=VALUES(name);

