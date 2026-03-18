import pyodbc
from datetime import datetime, timedelta
import random

def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ReservifyDB;"
        "Trusted_Connection=yes;"
    )

def reset_and_populate():
    conn = get_connection()
    cursor = conn.cursor()

    print("Cleaning up old data...")
    # Delete dependent tables first
    cursor.execute("DELETE FROM Payments")
    cursor.execute("DELETE FROM Bookings")
    cursor.execute("DELETE FROM Rooms")
    cursor.execute("DELETE FROM HotelDetails")
    cursor.execute("DELETE FROM RideDetails")
    cursor.execute("DELETE FROM EventDetails")
    cursor.execute("DELETE FROM FlightDetails")
    cursor.execute("DELETE FROM Services")
    
    # We can keep Users, Roles, Providers, Locations if we want, but let's refresh Locations and Providers to be sure
    # But Locations are referenced by Services, so safe to delete Services first.
    # Locations might be referenced by Users? No, Users table doesn't have location_id.
    
    # Let's ensure Locations are what we want
    cursor.execute("DELETE FROM Locations")
    cursor.execute("DBCC CHECKIDENT ('Locations', RESEED, 0)")
    
    cities = ['Lahore', 'Karachi', 'Islamabad']
    loc_map = {} # city -> location_id
    
    for city in cities:
        cursor.execute("INSERT INTO Locations (city, area, address, country) VALUES (?, ?, ?, ?)", 
                       (city, 'Downtown', f'Main Blvd, {city}', 'Pakistan'))
        cursor.execute("SELECT @@IDENTITY")
        loc_map[city] = cursor.fetchone()[0]
        
    # Providers
    cursor.execute("DELETE FROM Providers")
    cursor.execute("DBCC CHECKIDENT ('Providers', RESEED, 0)")
    
    providers = ['PC Hotels', 'Hotel One', 'Marriott', 'Serena', 'GoSwift', 'Uber', 'Careem', 'PIA', 'AirBlue', 'TicketMaster']
    prov_map = {}
    for p in providers:
        cursor.execute("INSERT INTO Providers (provider_name, contact) VALUES (?, ?)", (p, '111-222-333'))
        cursor.execute("SELECT @@IDENTITY")
        prov_map[p] = cursor.fetchone()[0]

    # Vehicles (Reset and Populate for Rides)
    # We need to handle FKs if any... RideDetails referenced Vehicles. We deleted RideDetails.
    cursor.execute("DELETE FROM Vehicles")
    cursor.execute("DBCC CHECKIDENT ('Vehicles', RESEED, 0)")
    
    # Create a pool of vehicles
    vehicle_types = {
        'Car': [('Toyota Yaris', 'LEV-101'), ('Toyota Corolla', 'LEV-102'), ('Honda Civic', 'LEV-103'), ('Suzuki Alto', 'LEV-104')],
        'Bike': [('Honda 125', 'LEM-201'), ('Yamaha YBR', 'LEM-202'), ('United 70', 'LEM-203')]
    }
    
    vehicle_ids = {'Car': [], 'Bike': []}
    
    for v_model, v_plate in vehicle_types['Car']:
        cursor.execute("INSERT INTO Vehicles (vehicle_type, model, plate_number) VALUES ('Car', ?, ?)", (v_model, v_plate))
        cursor.execute("SELECT @@IDENTITY")
        vehicle_ids['Car'].append(cursor.fetchone()[0])
        
    for v_model, v_plate in vehicle_types['Bike']:
        cursor.execute("INSERT INTO Vehicles (vehicle_type, model, plate_number) VALUES ('Bike', ?, ?)", (v_model, v_plate))
        cursor.execute("SELECT @@IDENTITY")
        vehicle_ids['Bike'].append(cursor.fetchone()[0])

    print("Populating Services...")

    # --- HOTELS ---
    # Lahore: PC Hotel, Hotel One
    # Karachi: Marriott, PC Hotel
    # Islamabad: Serena, Marriott
    
    hotel_config = [
        ('Lahore', 'PC Hotel', 'PC Hotels'),
        ('Lahore', 'Hotel One', 'Hotel One'),
        ('Karachi', 'Pearl Continental', 'PC Hotels'),
        ('Karachi', 'Marriott Hotel', 'Marriott'),
        ('Islamabad', 'Serena Hotel', 'Serena'),
        ('Islamabad', 'Marriott Hotel', 'Marriott')
    ]
    
    for city, title, prov in hotel_config:
        lid = loc_map[city]
        pid = prov_map[prov]
        price = 25000 if 'PC' in title or 'Serena' in title or 'Marriott' in title else 15000
        
        cursor.execute("""
            INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
            VALUES (?, 'Hotel', ?, ?, ?)
        """, (pid, title, price, lid))
        cursor.execute("SELECT @@IDENTITY")
        sid = cursor.fetchone()[0]
        
        # HotelDetails
        cursor.execute("INSERT INTO HotelDetails (service_id, star_rating, amenities) VALUES (?, 5, 'WiFi, Pool, Gym')", (sid,))
        cursor.execute("SELECT @@IDENTITY")
        hid = cursor.fetchone()[0]
        
        # Rooms
        cursor.execute("INSERT INTO Rooms (hotel_id, room_type, price_per_night, availability_status) VALUES (?, 'Deluxe Room', ?, 'Available')", (hid, price))
        cursor.execute("INSERT INTO Rooms (hotel_id, room_type, price_per_night, availability_status) VALUES (?, 'Executive Suite', ?, 'Available')", (hid, price * 1.5))

    # --- RIDES ---
    # For EACH city, add "City Car Ride" and "City Bike Ride"
    # User requirement: "option to choose bike ride and car ride, and the drop-down menu should show available vehicles"
    
    for city in cities:
        lid = loc_map[city]
        
        # 1. Car Ride Service
        cursor.execute("""
            INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
            VALUES (?, 'Ride', ?, 500, ?)
        """, (prov_map['GoSwift'], f"{city} Car Ride", lid))
        cursor.execute("SELECT @@IDENTITY")
        sid_car = cursor.fetchone()[0]
        
        # Add multiple vehicles to this ONE service
        # Using Car IDs 0 and 1 for simplicity (reusing vehicles across cities for demo, or we could create unique ones)
        # Let's just use the pool.
        for i, vid in enumerate(vehicle_ids['Car']):
            cursor.execute("""
                INSERT INTO RideDetails (service_id, vehicle_id, driver_license)
                VALUES (?, ?, ?)
            """, (sid_car, vid, f"DL-CAR-{city}-{i}"))
            
        # 2. Bike Ride Service
        cursor.execute("""
            INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
            VALUES (?, 'Ride', ?, 200, ?)
        """, (prov_map['GoSwift'], f"{city} Bike Ride", lid))
        cursor.execute("SELECT @@IDENTITY")
        sid_bike = cursor.fetchone()[0]
        
        for i, vid in enumerate(vehicle_ids['Bike']):
            cursor.execute("""
                INSERT INTO RideDetails (service_id, vehicle_id, driver_license)
                VALUES (?, ?, ?)
            """, (sid_bike, vid, f"DL-BIKE-{city}-{i}"))

    # --- EVENTS ---
    # 1 Event per city
    events = [
        ('Lahore', 'Sufi Night', 'TicketMaster', 4),
        ('Karachi', 'Food Festival', 'TicketMaster', 8),
        ('Islamabad', 'Tech Summit', 'TicketMaster', 6)
    ]
    
    for city, title, prov, dur in events:
        lid = loc_map[city]
        pid = prov_map[prov]
        cursor.execute("""
            INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
            VALUES (?, 'Event', ?, 3000, ?)
        """, (pid, title, lid))
        cursor.execute("SELECT @@IDENTITY")
        sid = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO EventDetails (service_id, event_date, duration_hours, capacity)
            VALUES (?, ?, ?, 500)
        """, (sid, datetime.now() + timedelta(days=10), dur))

    # --- FLIGHTS ---
    # Routes:
    # LHR -> KHI, ISB
    # KHI -> LHR, ISB
    # ISB -> LHR, KHI
    
    flight_routes = [
        # Origin: Lahore
        {'src': 'Lahore', 'dst': 'Karachi', 'prov': 'PIA', 'num': 'PK-302'},
        {'src': 'Lahore', 'dst': 'Islamabad', 'prov': 'AirBlue', 'num': 'PA-401'},
        
        # Origin: Karachi
        {'src': 'Karachi', 'dst': 'Lahore', 'prov': 'PIA', 'num': 'PK-303'},
        {'src': 'Karachi', 'dst': 'Islamabad', 'prov': 'AirBlue', 'num': 'PA-202'},
        
        # Origin: Islamabad
        {'src': 'Islamabad', 'dst': 'Lahore', 'prov': 'PIA', 'num': 'PK-404'},
        {'src': 'Islamabad', 'dst': 'Karachi', 'prov': 'AirBlue', 'num': 'PA-505'}
    ]
    
    seat_classes = ['Economy', 'Business', 'First']
    
    for route in flight_routes:
        src = route['src']
        dst = route['dst']
        prov = route['prov']
        fnum = route['num']
        
        lid = loc_map[src]
        pid = prov_map[prov]
        
        # Create ONE service per route (e.g., "Flight to Karachi")
        cursor.execute("""
            INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
            VALUES (?, 'Flight', ?, 15000, ?)
        """, (pid, f"Flight to {dst}", lid))
        cursor.execute("SELECT @@IDENTITY")
        sid = cursor.fetchone()[0]
        
        # Add details for EACH class and Multiple Timings
        # Morning Flight
        base_time_morning = datetime.now() + timedelta(days=5, hours=9) # 09:00 AM
        for s_class in seat_classes:
            cursor.execute("""
                INSERT INTO FlightDetails (service_id, airline, flight_number, departure_airport, arrival_airport, departure_time, arrival_time, seat_class)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sid, prov, fnum, src[:3].upper(), dst[:3].upper(), base_time_morning, base_time_morning + timedelta(hours=2), s_class))
            
        # Evening Flight (different flight number usually, but same service title)
        base_time_evening = datetime.now() + timedelta(days=5, hours=18) # 06:00 PM
        fnum_eve = fnum + "E"
        for s_class in seat_classes:
            cursor.execute("""
                INSERT INTO FlightDetails (service_id, airline, flight_number, departure_airport, arrival_airport, departure_time, arrival_time, seat_class)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sid, prov, fnum_eve, src[:3].upper(), dst[:3].upper(), base_time_evening, base_time_evening + timedelta(hours=2), s_class))

    conn.commit()
    conn.close()
    print("Database successfully updated!")

if __name__ == "__main__":
    reset_and_populate()
