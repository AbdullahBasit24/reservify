import pyodbc

def drop_flight_unique_constraint():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ReservifyDB;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()

    # Find the constraint name
    cursor.execute("""
        SELECT name
        FROM sys.key_constraints
        WHERE parent_object_id = OBJECT_ID('FlightDetails')
          AND type = 'UQ'
    """)
    row = cursor.fetchone()
    if row:
        constraint_name = row[0]
        print(f"Found UNIQUE constraint: {constraint_name}. Dropping it...")
        cursor.execute(f"ALTER TABLE FlightDetails DROP CONSTRAINT {constraint_name}")
        conn.commit()
        print("Constraint dropped.")
    else:
        print("No UNIQUE constraint found on FlightDetails (or it's already gone).")

    conn.close()

if __name__ == "__main__":
    drop_flight_unique_constraint()
