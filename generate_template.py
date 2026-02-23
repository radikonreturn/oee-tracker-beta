import pandas as pd

def generate_template(filename="OEE_Tracker_template.xlsx"):
    # Define columns for the Excel template based on ingestion logic and schemas
    columns = [
        "Date",                # e.g., 2024-03-20
        "Shift",               # e.g., Day vs Night
        "Machine Name",        # Matching machine in db
        "Operator",            # Operator Name
        "Planned Time (Min)",  # e.g., 480
        "Total Parts",         # Total pieces produced
        "Rejected Parts",      # Scrap/bad pieces
        "Rework Parts",        # Parts requiring rework
        "Downtime Category",   # General category of downtime (e.g., Unplanned)
        "Downtime Reason",     # Specific reason for downtime (e.g., Tool Change)
        "Downtime (Min)",      # Duration of the downtime event
        "Downtime Notes"       # Optional notes
    ]

    # Sample rows providing data entry examples
    sample_data = [
        ["2024-03-20", "Day", "CNC-01", "John Doe", 480, 500, 10, 2, "Planned", "Setup", 30, "Initial calibration"],
        ["2024-03-20", "Night", "Press-02", "Jane Smith", 480, 1200, 45, 0, "Unplanned", "Jam", 15, "Cleared jam in feeder"],
        ["2024-03-21", "Day", "Assembly-Line-1", "Bob Lee", 480, 300, 5, 5, "", "", 0, ""]
    ]

    # Create a DataFrame
    df = pd.DataFrame(sample_data, columns=columns)

    # Export to Excel
    df.to_excel(filename, index=False)
    print(f"Generated Excel template: {filename}")

if __name__ == "__main__":
    generate_template()
