import pyodbc

def wipe_data():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ReservifyDB;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()

    try:
        # Delete dependent data first
        cursor.execute("DELETE FROM Bookings")
        cursor.execute("DELETE FROM Rooms")
        cursor.execute("DELETE FROM HotelDetails")
        cursor.execute("DELETE FROM FlightDetails")
        cursor.execute("DELETE FROM RideDetails")
        cursor.execute("DELETE FROM EventDetails")
        cursor.execute("DELETE FROM Services")
        cursor.execute("DELETE FROM Providers")
        
        conn.commit()
        print("Data wiped.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    wipe_data()
