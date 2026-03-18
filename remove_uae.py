import pyodbc

def remove_uae():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ReservifyDB;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()

    try:
        # Find UAE locations
        cursor.execute("SELECT location_id FROM Locations WHERE country = 'UAE'")
        uae_locs = [row[0] for row in cursor.fetchall()]

        if not uae_locs:
            print("No UAE locations found.")
            return

        print(f"Found UAE location IDs: {uae_locs}")

        # Check for services
        placeholders = ','.join('?' * len(uae_locs))
        cursor.execute(f"SELECT service_id FROM Services WHERE location_id IN ({placeholders})", uae_locs)
        services = [row[0] for row in cursor.fetchall()]

        if services:
            print(f"Found {len(services)} services in UAE. Deleting dependent details...")
            svc_placeholders = ','.join('?' * len(services))
            
            # Delete details
            cursor.execute(f"DELETE FROM HotelDetails WHERE service_id IN ({svc_placeholders})", services)
            cursor.execute(f"DELETE FROM FlightDetails WHERE service_id IN ({svc_placeholders})", services)
            cursor.execute(f"DELETE FROM RideDetails WHERE service_id IN ({svc_placeholders})", services)
            cursor.execute(f"DELETE FROM EventDetails WHERE service_id IN ({svc_placeholders})", services)
            cursor.execute(f"DELETE FROM Bookings WHERE service_id IN ({svc_placeholders})", services)
            
            # Delete services
            cursor.execute(f"DELETE FROM Services WHERE service_id IN ({svc_placeholders})", services)
            print("Deleted services.")

        # Delete locations
        cursor.execute(f"DELETE FROM Locations WHERE location_id IN ({placeholders})", uae_locs)
        print("Deleted UAE locations.")
        
        conn.commit()

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    remove_uae()
