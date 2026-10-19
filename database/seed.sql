-- =====================================================================
-- UoN Student Marketplace - demo seed data
-- Demo accounts (documented in the setup guide):
--   admin@uon.edu.au    / Admin@123     (administrator)
--   madhavi@uon.edu.au  / Student@123   (student)
--   dhimanshi@uon.edu.au / Student@123  (student)
--   hari@uon.edu.au     / Student@123   (student)
--   akshaya@uon.edu.au  / Student@123   (student)
--   sankeerth@uon.edu.au / Student@123  (student)
-- =====================================================================

INSERT INTO users (email, password_hash, first_name, last_name, phone, role, status, created_at) VALUES
('admin@uon.edu.au',    'scrypt:32768:8:1$8irTd9OWAaorzUTX$2dc88a882bdecfeb3783caac50ba2bbd6e6d621105e36431aac03cd22b7afb10058eccecaeea5d538652a95022c0ffcb7c7ff0ae2a9495130d1797bfe2206c2d',   'Nora',    'Admin',    '+61 2 4913 0000', 'admin',   'active', '2026-09-08 09:00:00'),
('madhavi@uon.edu.au',  'scrypt:32768:8:1$aWg0JUTweCekNm5k$f8cb33245f15bc789cbcc97057f3ff4b44be4bd6240217a4574f863f3c6191c0fe5b2ee655cd7d5ef31e171c4b63f0a62c82451055d10d9395845d815f353c59', 'Madhavi', 'G',        '+61 400 100 001', 'student', 'active', '2026-09-08 10:15:00'),
('dhimanshi@uon.edu.au','scrypt:32768:8:1$aWg0JUTweCekNm5k$f8cb33245f15bc789cbcc97057f3ff4b44be4bd6240217a4574f863f3c6191c0fe5b2ee655cd7d5ef31e171c4b63f0a62c82451055d10d9395845d815f353c59', 'Dhimanshi','S',       '+61 400 100 002', 'student', 'active', '2026-09-09 11:20:00'),
('hari@uon.edu.au',     'scrypt:32768:8:1$aWg0JUTweCekNm5k$f8cb33245f15bc789cbcc97057f3ff4b44be4bd6240217a4574f863f3c6191c0fe5b2ee655cd7d5ef31e171c4b63f0a62c82451055d10d9395845d815f353c59', 'Hari',    'K',        '+61 400 100 003', 'student', 'active', '2026-09-09 14:05:00'),
('akshaya@uon.edu.au',  'scrypt:32768:8:1$aWg0JUTweCekNm5k$f8cb33245f15bc789cbcc97057f3ff4b44be4bd6240217a4574f863f3c6191c0fe5b2ee655cd7d5ef31e171c4b63f0a62c82451055d10d9395845d815f353c59', 'Akshaya', 'R',        '+61 400 100 004', 'student', 'active', '2026-09-10 09:40:00'),
('sankeerth@uon.edu.au','scrypt:32768:8:1$aWg0JUTweCekNm5k$f8cb33245f15bc789cbcc97057f3ff4b44be4bd6240217a4574f863f3c6191c0fe5b2ee655cd7d5ef31e171c4b63f0a62c82451055d10d9395845d815f353c59', 'Sankeerth','P',       '+61 400 100 005', 'student', 'active', '2026-09-10 16:30:00');

INSERT INTO categories (category_id, name, description, is_archived) VALUES
(1, 'Goods',      'Everyday second-hand goods and household items', 0),
(2, 'Housing',    'Accommodation-related listings and household setups', 0),
(3, 'Transport',  'Bicycles, scooters, helmets and transport gear', 0),
(4, 'Services',   'Student-offered services: tutoring, moving, photography', 0),
(5, 'Textbooks',  'Course textbooks and study material', 0),
(6, 'Electronics','Laptops, monitors, calculators and gadgets', 0);

INSERT INTO listings (listing_id, user_id, category_id, title, description, price, condition, location, status, created_at, updated_at) VALUES
(1, 2, 5, 'STAT1070 Statistics textbook', 'STAT1070 Data Analysis textbook, used for one semester. All pages intact, a few pencil notes in the first three chapters. Great reference for the final exam. Pickup near Callaghan campus or Newcastle City.', 35.0, 'Good', 'Callaghan', 'active', '2026-09-21 10:00:00', '2026-09-21 10:00:00'),
(2, 3, 1, 'Study desk with drawer', 'Solid timber study desk with one deep drawer. 120cm wide, perfect for a student room. Selling because I am moving interstate at the end of the trimester. Pick up only from Stockton.', 45.0, 'Fair', 'Stockton', 'active', '2026-09-22 09:30:00', '2026-09-22 09:30:00'),
(3, 4, 6, 'HP laptop 16GB RAM i5', 'Reliable HP laptop, i5 11th gen, 16GB RAM, 512GB SSD. Battery holds about 5 hours. Comes with the original charger and a sleeve. Perfect first laptop for uni work.', 620.0, 'Like new', 'Newcastle City', 'active', '2026-09-23 15:45:00', '2026-09-23 15:45:00'),
(4, 5, 3, 'Mountain bike with new tyres', 'Strong mountain bike, new tyres and brakes serviced last month. Two years old, some frame scratches. Ideal for riding between Callaghan and Warabrook station.', 180.0, 'Good', 'Callaghan', 'active', '2026-09-24 08:20:00', '2026-09-24 08:20:00'),
(5, 6, 1, 'Mini fridge for student room', 'Compact 60L fridge, runs quietly and cleanly. Fits a student room perfectly. Selling because my flat came with a big fridge. Pickup from Honeysuckle.', 70.0, 'Good', 'Honeysuckle', 'active', '2026-09-25 12:10:00', '2026-09-25 12:10:00'),
(6, 2, 6, 'Casio scientific calculator', 'Casio fx-82AU Plus II, approved for exams. Barely used, keeps in the box with the manual. Selling because I finished the stats units.', 18.0, 'Like new', 'Callaghan', 'active', '2026-09-26 09:00:00', '2026-09-26 09:00:00'),
(7, 3, 4, 'Private tutoring - statistics and maths', 'PhD student offering tutoring for STAT1070, MATH1110 and MATH1120. $30/hour, first half hour free. Held at the library or online. Message me to book a time.', 30.0, 'New', 'Callaghan', 'active', '2026-09-26 14:30:00', '2026-09-26 14:30:00'),
(8, 4, 2, 'Bedside table with lamp', 'White bedside table with a working lamp included. Clean and no damage. Moving to a furnished flat, so it needs a new home. Pickup from Charlestown.', 25.0, 'Good', 'Charlestown', 'active', '2026-09-27 10:15:00', '2026-09-27 10:15:00'),
(9, 5, 5, 'COMP6900 software engineering notes', 'Complete printed COMP6900 lecture notes plus my own summary sheets for every week. Bound and highlighted. Helped me score HD. Digital copies included.', 15.0, 'Like new', 'Ourimbah', 'active', '2026-09-27 16:40:00', '2026-09-27 16:40:00'),
(10, 6, 3, 'Electric scooter', 'Electric scooter, 25 km/h, range about 22 km. Charges fully in 3 hours. Includes lock and charger. Selling because I now live on campus.', 290.0, 'Good', 'Newcastle City', 'active', '2026-09-28 09:05:00', '2026-09-28 09:05:00'),
(11, 2, 1, 'Office chair, ergonomic', 'Ergonomic mesh office chair with lumbar support and adjustable armrests. Very comfortable for long study sessions. One small stain on the seat (shown in photo).', 55.0, 'Good', 'Callaghan', 'active', '2026-09-28 11:30:00', '2026-09-28 11:30:00'),
(12, 3, 6, '27-inch monitor 1440p', 'Dell 27-inch QHD monitor, IPS panel, HDMI and DisplayPort cables included. No dead pixels. Perfect for coding and spreadsheets.', 160.0, 'Like new', 'Stockton', 'active', '2026-09-28 13:20:00', '2026-09-28 13:20:00'),
(13, 4, 1, 'Free moving boxes (10)', 'Ten sturdy moving boxes, free to anyone who can pick them up from Honeysuckle this week. Various sizes, all in good shape. First in first served.', 0.0, 'Good', 'Honeysuckle', 'active', '2026-09-28 15:00:00', '2026-09-28 15:00:00'),
(14, 5, 4, 'Furniture assembly service', 'I assemble flat-pack furniture quickly. $25 per item, tools included. I have a ute for pickups if needed. Weekends preferred, message me for a quote.', 25.0, 'New', 'Newcastle City', 'active', '2026-09-28 17:45:00', '2026-09-28 17:45:00'),
(15, 6, 5, 'Nursing textbook bundle (4 books)', 'Bundle of four first-year nursing textbooks, all recent editions. Over $400 new. Selling as a bundle only. Pickup from Ourimbah campus.', 120.0, 'Good', 'Ourimbah', 'active', '2026-09-28 18:30:00', '2026-09-28 18:30:00'),
(16, 2, 3, 'Bike helmet and lights set', 'Helmet (size M) with front and rear USB lights. Barely used, no crashes. Perfect safety starter kit for a new bike.', 30.0, 'Like new', 'Callaghan', 'active', '2026-09-28 19:10:00', '2026-09-28 19:10:00'),
(17, 3, 1, 'Bookshelf, 5 tiers', 'Five-tier bookshelf, holds all my textbooks with room to spare. Easy to pull apart for transport. Pickup from Stockton, help available.', 40.0, 'Good', 'Stockton', 'archived', '2026-09-28 19:50:00', '2026-09-28 19:55:00'),
(18, 4, 6, 'Wireless noise cancelling headphones', 'Over-ear noise cancelling headphones, great for the library. Battery still lasts 25+ hours. Includes case and cable.', 95.0, 'Good', 'Charlestown', 'sold', '2026-09-28 20:30:00', '2026-09-28 21:00:00');

INSERT INTO listing_images (listing_id, file_path, is_primary, uploaded_at) VALUES
(1,  'seed_stat1070.png',       1, '2026-09-21 10:00:00'),
(2,  'seed_desk.png',           1, '2026-09-22 09:30:00'),
(3,  'seed_laptop.png',         1, '2026-09-23 15:45:00'),
(4,  'seed_bike.png',           1, '2026-09-24 08:20:00'),
(5,  'seed_fridge.png',         1, '2026-09-25 12:10:00'),
(6,  'seed_calculator.png',     1, '2026-09-26 09:00:00'),
(7,  'seed_tutoring.png',       1, '2026-09-26 14:30:00'),
(8,  'seed_bedside.png',        1, '2026-09-27 10:15:00'),
(9,  'seed_notes.png',          1, '2026-09-27 16:40:00'),
(10, 'seed_scooter.png',        1, '2026-09-28 09:05:00'),
(11, 'seed_chair.png',          1, '2026-09-28 11:30:00'),
(12, 'seed_monitor.png',        1, '2026-09-28 13:20:00'),
(13, 'seed_boxes.png',          1, '2026-09-28 15:00:00'),
(14, 'seed_assembly.png',       1, '2026-09-28 17:45:00'),
(15, 'seed_nursing.png',        1, '2026-09-28 18:30:00'),
(16, 'seed_helmet.png',         1, '2026-09-28 19:10:00'),
(17, 'seed_bookshelf.png',      1, '2026-09-28 19:50:00'),
(18, 'seed_headphones.png',     1, '2026-09-28 20:30:00');

INSERT INTO favourites (user_id, listing_id, created_at) VALUES
(2, 3, '2026-09-27 09:00:00'),
(2, 12, '2026-09-28 08:00:00'),
(3, 4, '2026-09-27 10:00:00'),
(4, 1, '2026-09-27 11:00:00'),
(5, 10, '2026-09-28 09:30:00'),
(6, 2, '2026-09-28 10:00:00');

-- Demo conversations (BR-05: only buyer + seller can access)
INSERT INTO conversations (conversation_id, listing_id, buyer_id, created_at) VALUES
(1, 3, 2, '2026-09-27 12:00:00'),   -- Madhavi asks Hari about the laptop
(2, 4, 5, '2026-09-27 13:30:00'),   -- Akshaya asks Hari about the bike
(3, 1, 4, '2026-09-28 10:00:00');   -- Hari asks Madhavi about the textbook

INSERT INTO messages (conversation_id, sender_id, body, sent_at, is_read) VALUES
(1, 2, 'Hi! Is the laptop still available? And is there any warranty left on it?', '2026-09-27 12:01:00', 1),
(1, 4, 'Hi Madhavi, yes it is available. It is out of warranty but I can show you everything working when you come.', '2026-09-27 12:20:00', 1),
(1, 2, 'Great. Would Saturday morning near the library work?', '2026-09-27 13:00:00', 0),
(2, 5, 'Hey, does the bike come with a lock?', '2026-09-27 13:31:00', 1),
(2, 4, 'Hi Akshaya, the bike does not include a lock, but there is a helmet and light set listed on the marketplace!', '2026-09-27 14:00:00', 0),
(3, 4, 'Hi, is the STAT1070 textbook still the current edition?', '2026-09-28 10:01:00', 1),
(3, 2, 'Hi Hari, yes it is the current edition and the lecture content matches.', '2026-09-28 10:30:00', 0);

-- Demo reports (FR-11 / FR-12): two open, one resolved with audit trail
INSERT INTO reports (report_id, listing_id, reporter_id, reason, details, status, resolved_by, resolved_at, resolution_note, created_at) VALUES
(1, 10, 3, 'Safety concern', 'The seller offers to post the scooter without meeting, which feels unsafe for a marketplace exchange.', 'open', NULL, NULL, NULL, '2026-09-28 16:00:00'),
(2, 7, 6, 'Wrong category or spam', 'This tutoring service is listed under Services but the tutor posted the same ad four times today.', 'open', NULL, NULL, NULL, '2026-09-28 17:10:00'),
(3, 18, 2, 'Inappropriate content', 'The headphone photo contained a phone number written on paper, which is not allowed.', 'resolved', 1, '2026-09-28 21:30:00', 'Seller confirmed the phone number was a typo and replaced the photo. Listing allowed to stay.', '2026-09-28 20:50:00');

INSERT INTO audit_log (admin_id, action, entity_type, entity_id, details, created_at) VALUES
(1, 'REVIEW_REPORT', 'report', '3', 'Spoke with both parties; seller corrected the photo.', '2026-09-28 21:20:00'),
(1, 'RESOLVE_REPORT', 'report', '3', 'Report resolved, no breach remained after correction.', '2026-09-28 21:30:00');

INSERT INTO email_log (recipient, subject, body, status, sent_at) VALUES
('madhavi@uon.edu.au', 'New message - HP laptop 16GB RAM i5', 'Hi Madhavi, you have a new message about "HP laptop 16GB RAM i5" on the UoN Student Marketplace.', 'simulated', '2026-09-27 12:20:00'),
('hari@uon.edu.au', 'New message - HP laptop 16GB RAM i5', 'Hi Hari, you have a new message about "HP laptop 16GB RAM i5" on the UoN Student Marketplace.', 'simulated', '2026-09-27 13:00:00');
