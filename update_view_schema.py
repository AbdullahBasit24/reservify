import pyodbc

def update_view():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ReservifyDB;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()

    sql = """
    CREATE OR ALTER VIEW vw_UserBookingDetails
    AS
    SELECT
        b.booking_id,
        b.user_id,
        u.full_name,
        u.email,
        s.service_title,
        s.service_category,
        b.booking_date,
        b.status,
        b.pickup_location,
        b.dropoff_location
    FROM Bookings b
    JOIN Users u ON b.user_id = u.user_id
    JOIN Services s ON b.service_id = s.service_id;
    """
    
    try:
        cursor.execute(sql)
        conn.commit()
        print("View vw_UserBookingDetails updated successfully.")
    except Exception as e:
        print(f"Error updating view: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_view()
