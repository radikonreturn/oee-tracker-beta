import sqlite3
from datetime import datetime, timedelta
import random

db_path = 'backend/data/oee.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Create Machines
machines = ['CNC-01', 'CNC-02', 'Assembly-Line-1', 'Packaging-1']
for m in machines:
    c.execute('''
        INSERT INTO machines (name, production_type, ideal_cycle_time_sec, target_oee, active) 
        SELECT ?, ?, ?, ?, ? 
        WHERE NOT EXISTS(SELECT 1 FROM machines WHERE name=?)
    ''', (m, 'Discrete', random.randint(30, 90), 85.0, True, m))

conn.commit()

# 2. Get Machine IDs
c.execute('SELECT id, name FROM machines')
m_ids = {name: id for id, name in c.fetchall()}

# 3. Generate Shift Data
shifts = ['Morning', 'Afternoon', 'Night']
operators = ['John Doe', 'Jane Smith', 'Mike Johnson', 'Sarah Williams']
dates = [(datetime.now() - timedelta(days=i)).date().strftime('%Y-%m-%d') for i in range(14)]

for d in dates:
    for m_name, m_id in m_ids.items():
        if m_name not in machines: continue # Only populate our test machines
        for s in shifts:
            total = random.randint(800, 1500)
            rej = random.randint(10, 100)
            ict = random.randint(30, 90)
            
            c.execute('''
                INSERT INTO shifts 
                (date, shift_type, machine_id, operator_name, planned_time_min, total_parts, rejected_parts, rework_parts, ideal_cycle_time_sec, data_source, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (d, s, m_id, random.choice(operators), 480, total, rej, 0, ict, 'Mock Data', datetime.now(), datetime.now()))
            
            shift_id = c.lastrowid
            
            # 4. Generate random downtime events
            if random.random() > 0.5:
                c.execute('INSERT INTO downtime_events (shift_id, category, subcategory, duration_min) VALUES (?, ?, ?, ?)', 
                          (shift_id, 'Planned Stop', 'Setup', random.randint(10, 45)))
            if random.random() > 0.3:
                c.execute('INSERT INTO downtime_events (shift_id, category, subcategory, duration_min) VALUES (?, ?, ?, ?)', 
                          (shift_id, 'Unplanned Breakdown', 'Breakdown', random.randint(15, 90)))

conn.commit()
print('Mock data successfully injected into the database!')
