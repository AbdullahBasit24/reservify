import pyodbc

def add_booking_columns():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ReservifyDB;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()

    # Check if columns exist
    cursor.execute("SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Bookings' AND COLUMN_NAME = 'pickup_location'")
    if not cursor.fetchone():
        print("Adding pickup_location column...")
        cursor.execute("ALTER TABLE Bookings ADD pickup_location VARCHAR(100)")
    
    cursor.execute("SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Bookings' AND COLUMN_NAME = 'dropoff_location'")
    if not cursor.fetchone():
        print("Adding dropoff_location column...")
        cursor.execute("ALTER TABLE Bookings ADD dropoff_location VARCHAR(100)")

    conn.commit()
    conn.close()
    print("Schema updated successfully.")

if __name__ == "__main__":
    add_booking_columns()
