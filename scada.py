import os
import shutil
import pandas as pd
from datetime import datetime
from database import SessionLocal, Shift, Machine, DowntimeEvent, QualityDefect, ImportLog

IMPORT_DIR = os.path.join(os.path.dirname(__file__), "data", "scada_import")
PROCESSED_DIR = os.path.join(IMPORT_DIR, "processed")

def setup_directories():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

def process_scada_csvs():
    setup_directories()
    db = SessionLocal()
    
    files = [f for f in os.listdir(IMPORT_DIR) if f.endswith(".csv")]
    
    for file in files:
        filepath = os.path.join(IMPORT_DIR, file)
        try:
            df = pd.read_csv(filepath)
            
            # Required columns validation
            req_cols = ["machine_name", "date", "shift", "planned_time_min", 
                        "total_parts", "rejected_parts", "rework_parts", 
                        "downtime_category", "downtime_subcategory", "downtime_duration_min"]
            
            if not all(col in df.columns for col in req_cols):
                raise ValueError("Missing required columns in CSV")
                
            success_count = 0
            # Basic grouping by shift to insert bulk
            grouped = df.groupby(["machine_name", "date", "shift", "planned_time_min", "total_parts", "rejected_parts", "rework_parts"])
            
            for (m_name, s_date, s_type, pt_min, t_parts, rej_parts, rew_parts), group in grouped:
                machine = db.query(Machine).filter(Machine.name == m_name).first()
                if not machine:
                    # Log warning but skip
                    db.add(ImportLog(source="CSV Watcher", filename=file, status="Failed", message=f"Unknown machine: {m_name}"))
                    continue
                
                s_date_obj = pd.to_datetime(s_date).date()
                
                existing = db.query(Shift).filter(
                    Shift.machine_id == machine.id,
                    Shift.date == s_date_obj,
                    Shift.shift_type == s_type
                ).first()
                
                if existing:
                    # Conflict: mark both
                    existing.data_source = "Both"
                    db.add(ImportLog(source="CSV Watcher", filename=file, status="Conflict", message=f"Shift exists for {m_name} on {s_date_obj} ({s_type}). Flagged as 'Both'."))
                else:
                    existing = Shift(
                        machine_id=machine.id,
                        date=s_date_obj,
                        shift_type=s_type,
                        planned_time_min=float(pt_min),
                        total_parts=int(t_parts),
                        rejected_parts=int(rej_parts),
                        rework_parts=int(rew_parts),
                        operator_name="SCADA_SYSTEM",
                        data_source="SCADA"
                    )
                    db.add(existing)
                    db.flush()
                
                for _, row in group.iterrows():
                    d_cat = row.get("downtime_category")
                    d_sub = row.get("downtime_subcategory")
                    d_dur = row.get("downtime_duration_min")
                    
                    if d_cat and d_sub and d_dur > 0:
                        db.add(DowntimeEvent(
                            shift_id=existing.id,
                            category=str(d_cat),
                            subcategory=str(d_sub),
                            duration_min=float(d_dur),
                            notes="Auto-imported via SCADA"
                        ))
                
                success_count += 1
            
            db.commit()
            db.add(ImportLog(source="CSV Watcher", filename=file, status="Success", message=f"Imported {success_count} shifts."))
            
            # Move to processed
            shutil.move(filepath, os.path.join(PROCESSED_DIR, file))
            db.commit()
            
        except Exception as e:
            db.rollback()
            db.add(ImportLog(source="CSV Watcher", filename=file, status="Failed", message=str(e)))
            db.commit()
            
    db.close()
