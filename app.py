from flask import Flask, render_template, request, redirect, session, flash
from db import get_connection
import hashlib

app = Flask(__name__)
app.secret_key = "reservify_secret_key"   # required for sessions


def fetch_locations(cursor):
    cursor.execute("SELECT DISTINCT city FROM Locations ORDER BY city")
    return [r[0] for r in cursor.fetchall()]

def ensure_phone_column(cursor):
    cursor.execute("SELECT COL_LENGTH('Users', 'phone_number')")
    row = cursor.fetchone()
    if not row or row[0] is None:
        cursor.execute("ALTER TABLE Users ADD phone_number VARCHAR(20) NULL")
    cursor.execute("""
        UPDATE Users
        SET phone_number = COALESCE(phone_number, '0300-0000000')
        WHERE phone_number IS NULL OR phone_number = ''
    """)

def ensure_flight_price_column(cursor):
    cursor.execute("SELECT COL_LENGTH('FlightDetails', 'price')")
    row = cursor.fetchone()
    if not row or row[0] is None:
        cursor.execute("ALTER TABLE FlightDetails ADD price DECIMAL(10,2) NULL")


def fetch_services(cursor, category=None, city=None):
    country = session.get("country")
    
    conditions = []
    params = []

    if category:
        conditions.append("s.service_category = ?")
        params.append(category)

    if country:
        conditions.append("l.country = ?")
        params.append(country)

    if city:
        conditions.append("l.city = ?")
        params.append(city)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    cursor.execute(f"""
        SELECT
            s.service_id,
            s.service_title,
            s.service_category,
            s.base_price,
            l.city,
            l.area,
            l.address,
            p.provider_name
        FROM Services s
        JOIN Providers p ON s.provider_id = p.provider_id
        JOIN Locations l ON s.location_id = l.location_id
        {where_clause}
        ORDER BY s.service_category, s.service_title
    """, params)

    rows = cursor.fetchall()
    return [
        {
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "price": r[3],
            "city": r[4],
            "area": r[5],
            "address": r[6],
            "provider": r[7],
        }
        for r in rows
    ]


def fetch_detail_options(cursor):
    # -------- HOTELS --------
    cursor.execute("""
        SELECT
            s.service_id,
            r.room_id,
            r.room_type,
            r.price_per_night
        FROM Rooms r
        JOIN HotelDetails h ON r.hotel_id = h.hotel_id
        JOIN Services s ON h.service_id = s.service_id
        WHERE r.availability_status = 'Available'
    """)

    hotel_options = {}
    for sid, rid, rtype, price in cursor.fetchall():
        hotel_options.setdefault(sid, []).append({
            "id": rid,
            "label": f"{rtype} - Rs {price:.0f}"
        })

    # -------- FLIGHTS --------
    cursor.execute("""
        SELECT
            s.service_id,
            f.flight_id,
            f.flight_number,
            f.departure_airport,
            f.arrival_airport,
            f.seat_class,
            f.departure_time,
            f.arrival_time
        FROM FlightDetails f
        JOIN Services s ON f.service_id = s.service_id
    """)

    flight_options = {}
    for sid, fid, fnum, dep, arr, seat, dtime, atime in cursor.fetchall():
        dt_str = dtime.strftime("%d %b")
        time_str = dtime.strftime("%H:%M")
        flight_options.setdefault(sid, []).append({
            "id": fid,
            "class": seat,
            "time": time_str,
            "date": dt_str,
            "number": fnum
        })

    # -------- EVENTS --------
    cursor.execute("""
        SELECT
            s.service_id,
            e.event_id,
            e.event_date,
            e.duration_hours
        FROM EventDetails e
        JOIN Services s ON e.service_id = s.service_id
    """)

    event_options = {}
    for sid, eid, dt, dur in cursor.fetchall():
        event_options.setdefault(sid, []).append({
            "id": eid,
            "label": f"{dt} • {dur} hrs"
        })

    # -------- RIDES --------
    cursor.execute("""
        SELECT
            s.service_id,
            r.ride_id,
            v.model,
            v.plate_number
        FROM RideDetails r
        JOIN Services s ON r.service_id = s.service_id
        JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
    """)

    ride_options = {}
    for sid, rid, model, plate in cursor.fetchall():
        ride_options.setdefault(sid, []).append({
            "id": rid,
            "label": f"{model} ({plate})"
        })

    return hotel_options, flight_options, event_options, ride_options


# ---------------- HOME ----------------
@app.route("/")
@app.route("/")
def home():
    country = session.get("country")
    city = request.args.get("city")


    conn = get_connection()
    cursor = conn.cursor()

    locations = fetch_locations(cursor)

    cursor.execute("""
        SELECT
            service_id,
            service_title,
            service_category,
            base_price,
            country,
            city,
            area,
            provider_name
        FROM vw_ServicesByLocation
        WHERE
            (? IS NULL OR country = ?)
        AND (? IS NULL OR city = ?)
        ORDER BY service_title
    """, (country, country, city, city))

    rows = cursor.fetchall()
    conn.close()

    services = [
        {
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "price": r[3],
            "country": r[4],
            "city": r[5],
            "area": r[6],
            "provider": r[7],
        }
        for r in rows
    ]

    return render_template(
        "index.html",
        services=services,
        country=country,
        city=city,
        locations=locations,
        user=session.get("user")
    )

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cursor = conn.cursor()

        try:
            try:
                ensure_phone_column(cursor)
                cursor.execute(
                    "EXEC sp_RegisterUser ?, ?, ?, ?",
                    (full_name, email, password_hash, phone)
                )
                result = cursor.fetchone()
                conn.commit()
                if result and result[0] == 1:
                    return redirect("/login")
                else:
                    flash(result[1] if result else "Registration failed", "error")
                    return redirect("/signup")
            except Exception:
                ensure_phone_column(cursor)
                cursor.execute("""
                    INSERT INTO Users (full_name, email, password_hash, role_id, phone_number)
                    VALUES (?, ?, ?, 1, ?)
                """, (full_name, email, password_hash, phone))
                conn.commit()
                return redirect("/login")
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
            return redirect("/signup")
        finally:
            conn.close()

    return render_template("signup.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("EXEC sp_GetUserForLogin ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            user_id, full_name, stored_hash, role_id = row
            if stored_hash == password_hash:
                session["user"] = full_name
                session["user_id"] = user_id
                session["role_id"] = role_id
                
                if role_id == 3:
                    return redirect("/admin/dashboard")
                elif role_id == 2:
                    return redirect("/provider/dashboard")
                else:
                    return redirect("/")
        
        flash("Invalid credentials. Please try again.", "error")
        return redirect("/login")

    return render_template("login.html")

# ---------------- BOOKING ----------------
@app.route("/book", methods=["POST"])
def book():
    service_id = request.form.get("service_id")
    email = request.form.get("email")

    if not service_id or not email:
        return redirect("/?error=Missing+service+or+email")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM Users WHERE email = ?", (email,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return redirect("/?error=User+not+found")

    cursor.execute("SELECT service_category FROM Services WHERE service_id = ?", (service_id,))
    cat_row = cursor.fetchone()
    if not cat_row:
        conn.close()
        return redirect("/?error=Service+not+found")

    user_id = user_row[0]
    category = cat_row[0]
    room_id = request.form.get("room_id")
    flight_id = request.form.get("flight_id")
    event_id = request.form.get("event_id")
    ride_id = request.form.get("ride_id")

    # Ride locations
    pickup = request.form.get("pickup")
    dropoff = request.form.get("dropoff")

    try:
        if category == "Hotel":
            cursor.execute("""
                INSERT INTO Bookings (user_id, service_id, room_id, status)
                VALUES (?, ?, ?, 'Booked')
            """, (user_id, int(service_id), int(room_id) if room_id else None))
        elif category == "Flight":
            cursor.execute("""
                INSERT INTO Bookings (user_id, service_id, flight_id, status)
                VALUES (?, ?, ?, 'Booked')
            """, (user_id, int(service_id), int(flight_id) if flight_id else None))
        elif category == "Event":
            cursor.execute("""
                INSERT INTO Bookings (user_id, service_id, event_id, status)
                VALUES (?, ?, ?, 'Booked')
            """, (user_id, int(service_id), int(event_id) if event_id else None))
        elif category == "Ride":
            cursor.execute("""
                INSERT INTO Bookings (user_id, service_id, ride_id, pickup_location, dropoff_location, status)
                VALUES (?, ?, ?, ?, ?, 'Booked')
            """, (user_id, int(service_id), int(ride_id) if ride_id else None, pickup, dropoff))
        else:
            cursor.execute("""
                INSERT INTO Bookings (user_id, service_id, status)
                VALUES (?, ?, 'Booked')
            """, (user_id, int(service_id)))

        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        return redirect("/?error=Booking+failed")

    conn.close()
    return redirect("/?msg=Booking+created")


# --------------- VIEW BOOKINGS ----------
@app.route("/my-bookings")
def my_bookings():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            booking_id,
            service_title,
            service_category,
            booking_date,
            status,
            pickup_location,
            dropoff_location
        FROM vw_UserBookingDetails
        WHERE user_id = ?
        ORDER BY booking_date DESC
    """, (session["user_id"],))

    bookings = [
        {
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "date": r[3],
            "status": r[4],
            "pickup": r[5],
            "dropoff": r[6]
        }
        for r in cursor.fetchall()
    ]

    conn.close()

    return render_template("bookings.html",
                           bookings=bookings,
                           user=session.get("user"))




# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- CATEGORY PAGES ----------------
@app.route("/hotels")
def hotels():
    city = request.args.get("city")
    conn = get_connection()
    cursor = conn.cursor()
    locations = fetch_locations(cursor)
    services = fetch_services(cursor, "Hotel", city=city)
    hotel_options, _, _, _ = fetch_detail_options(cursor)
    conn.close()
    return render_template("hotels.html",
                           services=services,
                           hotel_options=hotel_options,
                           locations=locations,
                           city=city,
                           message=request.args.get("msg"),
                           error=request.args.get("error"),
                           user=session.get("user"))


@app.route("/flights")
def flights():
    city = request.args.get("city")
    conn = get_connection()
    cursor = conn.cursor()
    locations = fetch_locations(cursor)
    services = fetch_services(cursor, "Flight", city=city)
    _, flight_options, _, _ = fetch_detail_options(cursor)
    conn.close()
    return render_template("flights.html",
                           services=services,
                           flight_options=flight_options,
                           locations=locations,
                           city=city,
                           message=request.args.get("msg"),
                           error=request.args.get("error"),
                           user=session.get("user"))


@app.route("/events")
def events():
    city = request.args.get("city")
    conn = get_connection()
    cursor = conn.cursor()
    locations = fetch_locations(cursor)
    services = fetch_services(cursor, "Event", city=city)
    _, _, event_options, _ = fetch_detail_options(cursor)
    conn.close()
    return render_template("events.html",
                           services=services,
                           event_options=event_options,
                           locations=locations,
                           city=city,
                           message=request.args.get("msg"),
                           error=request.args.get("error"),
                           user=session.get("user"))


@app.route("/rides")
def rides():
    city = request.args.get("city")
    conn = get_connection()
    cursor = conn.cursor()
    locations = fetch_locations(cursor)
    services = fetch_services(cursor, "Ride", city=city)
    _, _, _, ride_options = fetch_detail_options(cursor)
    conn.close()
    return render_template("rides.html",
                           services=services,
                           ride_options=ride_options,
                           locations=locations,
                           city=city,
                           message=request.args.get("msg"),
                           error=request.args.get("error"),
                           user=session.get("user"))


# ---------------- CANCEL BOOKING ----------------
@app.route("/cancel-booking/<int:booking_id>")
def cancel_booking(booking_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Verify ownership
        cursor.execute("SELECT user_id FROM Bookings WHERE booking_id = ?", (booking_id,))
        row = cursor.fetchone()
        if not row:
             return redirect("/my-bookings?error=Booking+not+found")
        
        if row[0] != session["user_id"] and session.get("role_id") != 3: # Allow owner or Admin
             return redirect("/my-bookings?error=Unauthorized")

        cursor.execute("UPDATE Bookings SET status = 'Cancelled' WHERE booking_id = ?", (booking_id,))
        conn.commit()
    except Exception as e:
        print(e)
        return redirect("/my-bookings?error=Cancellation+failed")
    finally:
        conn.close()

    return redirect("/my-bookings?msg=Booking+cancelled")


# ---------------- SETTINGS & ROLES ----------------
@app.route("/settings")
def settings():
    return render_template("settings.html", user=session.get("user"))

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        ensure_phone_column(cursor)
        if request.method == "POST":
            full_name = request.form["full_name"]
            email = request.form["email"]
            phone = request.form["phone"]
            try:
                cursor.execute("""
                    UPDATE Users SET full_name = ?, email = ?, phone_number = ?
                    WHERE user_id = ?
                """, (full_name, email, phone, session["user_id"]))
                conn.commit()
                session["user"] = full_name
                flash("Profile updated successfully", "success")
                return redirect("/profile")
            except Exception as e:
                conn.rollback()
                flash(f"Update failed: {e}", "error")
                return redirect("/profile")
        cursor.execute("SELECT full_name, email, phone_number FROM Users WHERE user_id = ?", (session["user_id"],))
        row = cursor.fetchone()
        user_info = {
            "full_name": row[0],
            "email": row[1],
            "phone_number": row[2] if len(row) > 2 else ""
        }
        cursor.execute("""
            SELECT
                booking_id,
                service_title,
                service_category,
                booking_date,
                status,
                pickup_location,
                dropoff_location
            FROM vw_UserBookingDetails
            WHERE user_id = ?
            ORDER BY booking_date DESC
        """, (session["user_id"],))
        bookings = [
            {
                "id": r[0],
                "title": r[1],
                "category": r[2],
                "date": r[3],
                "status": r[4],
                "pickup": r[5],
                "dropoff": r[6]
            }
            for r in cursor.fetchall()
        ]
        return render_template("profile.html", user_info=user_info, bookings=bookings)
    except Exception as e:
        conn.rollback()
        flash(f"Failed to load/update profile: {e}", "error")
        return redirect("/")
    finally:
        conn.close()
@app.route("/provider/signup", methods=["GET", "POST"])
def provider_signup():
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        provider_name = request.form["provider_name"]
        contact = request.form["contact"]
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Create User (Role 2 = Provider)
            cursor.execute("""
                INSERT INTO Users (full_name, email, password_hash, role_id)
                VALUES (?, ?, ?, 2)
            """, (full_name, email, password_hash))
            cursor.execute("SELECT @@IDENTITY")
            user_id = cursor.fetchone()[0]
            
            # Create Provider Profile
            cursor.execute("""
                INSERT INTO Providers (user_id, provider_name, contact)
                VALUES (?, ?, ?)
            """, (user_id, provider_name, contact))
            
            conn.commit()
            flash("Provider account created! Please login.", "success")
            return redirect("/login")
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
        finally:
            conn.close()

    return render_template("provider_signup.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role_id") != 3:
        return redirect("/login")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Fetch all users
    cursor.execute("SELECT user_id, full_name, email, role_id, created_at FROM Users")
    users = cursor.fetchall()
    
    cursor.execute("""
        SELECT s.service_id, s.service_title, s.service_category, s.base_price, p.provider_name
        FROM Services s
        JOIN Providers p ON s.provider_id = p.provider_id
        ORDER BY s.service_category, s.service_title
    """)
    services = cursor.fetchall()
    
    conn.close()
    return render_template("admin_dashboard.html", users=users, services=services, user=session.get("user"))

@app.route("/admin/delete-user/<int:user_id>")
def delete_user(user_id):
    if session.get("role_id") != 3:
        return redirect("/login")
        
    if user_id == session["user_id"]:
        return redirect("/admin/dashboard?error=Cannot+delete+yourself")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Delete dependent data logic would be complex. 
        # For now, simple delete (might fail if constraints exist)
        # We need to handle constraints (Bookings, Providers, etc.)
        # Ideally, soft delete or cascade. 
        # Let's try to delete providers/bookings linked to user first.
        cursor.execute("DELETE FROM Bookings WHERE user_id = ?", (user_id,))
        # If they are a provider, delete services?
        cursor.execute("SELECT provider_id FROM Providers WHERE user_id = ?", (user_id,))
        prov = cursor.fetchone()
        if prov:
            pid = prov[0]
            # Delete services logic... too risky for a simple button without confirmation/cascade logic.
            # Let's just try deleting User and catch error.
            # But Providers table has FK to Users.
            cursor.execute("DELETE FROM Providers WHERE user_id = ?", (user_id,))
            
        cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return redirect(f"/admin/dashboard?error=Delete+failed:+{e}")
    finally:
        conn.close()
        
    return redirect("/admin/dashboard?msg=User+deleted")

@app.route("/dashboard-redirect")
def dashboard_redirect():
    if "user_id" not in session:
        return redirect("/")
    
    role = session.get("role_id")
    if role == 3: # Admin
        return redirect("/admin/dashboard")
    elif role == 2: # Provider
        return redirect("/provider/dashboard")
    else: # User
        return redirect("/")

@app.route("/provider/dashboard")
def provider_dashboard():
    if session.get("role_id") != 2:
        return redirect("/login")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get Provider ID
    cursor.execute("SELECT provider_id FROM Providers WHERE user_id = ?", (session["user_id"],))
    prov = cursor.fetchone()
    if not prov:
        return "Provider profile not found."
    
    provider_id = prov[0]
    
    # Fetch Services
    cursor.execute("""
        SELECT service_id, service_title, service_category, base_price, location_id 
        FROM Services WHERE provider_id = ?
    """, (provider_id,))
    services = cursor.fetchall()
    
    conn.close()
    return render_template("provider_dashboard.html", services=services, user=session.get("user"))

@app.route("/provider/add-service", methods=["GET", "POST"])
def add_service():
    if session.get("role_id") != 2:
        return redirect("/login")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    if request.method == "POST":
        category = request.form["category"]
        title = request.form["title"]
        price = request.form["price"]
        city = request.form["city"]
        
        # Get location_id
        cursor.execute("SELECT location_id FROM Locations WHERE city = ?", (city,))
        loc = cursor.fetchone()
        loc_id = loc[0] if loc else 1
             
        # Get Provider ID
        cursor.execute("SELECT provider_id FROM Providers WHERE user_id = ?", (session["user_id"],))
        pid = cursor.fetchone()[0]
        
        try:
            # 1. Insert Service
            cursor.execute("""
                INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
                VALUES (?, ?, ?, ?, ?)
            """, (pid, category, title, price, loc_id))
            cursor.execute("SELECT @@IDENTITY")
            service_id = cursor.fetchone()[0]

            # 2. Insert Details based on Category
            if category == "Hotel":
                cursor.execute("""
                    INSERT INTO HotelDetails (service_id, star_rating, amenities)
                    VALUES (?, ?, ?)
                """, (service_id, 3, 'WiFi'))
                cursor.execute("SELECT hotel_id FROM HotelDetails WHERE service_id = ?", (service_id,))
                hotel_id = cursor.fetchone()[0]

                # Insert Rooms
                types = request.form.getlist("room_type[]")
                prices = request.form.getlist("room_price[]")
                
                for r_type, r_price in zip(types, prices):
                    if r_type and r_price:
                        cursor.execute("""
                            INSERT INTO Rooms (hotel_id, room_type, price_per_night, availability_status)
                            VALUES (?, ?, ?, 'Available')
                        """, (hotel_id, r_type, r_price))

            elif category == "Ride":
                v_types = request.form.getlist("vehicle_type[]")
                v_models = request.form.getlist("vehicle_model[]")
                v_plates = request.form.getlist("plate_number[]")
                
                for v_type, v_model, v_plate in zip(v_types, v_models, v_plates):
                    if v_model and v_plate:
                        # Insert Vehicle
                        cursor.execute("""
                            INSERT INTO Vehicles (vehicle_type, model, plate_number, capacity)
                            VALUES (?, ?, ?, 4)
                        """, (v_type, v_model, v_plate))
                        cursor.execute("SELECT @@IDENTITY")
                        vehicle_id = cursor.fetchone()[0]

                        # Insert RideDetails
                        dl = f"DL-{v_plate}"
                        cursor.execute("""
                            INSERT INTO RideDetails (service_id, vehicle_id, driver_license)
                            VALUES (?, ?, ?)
                        """, (service_id, vehicle_id, dl))

            elif category == "Event":
                e_date = request.form.get("event_date")
                duration = request.form.get("duration", 2)
                if not e_date:
                     import datetime
                     e_date = datetime.date.today()

                cursor.execute("""
                    INSERT INTO EventDetails (service_id, event_date, duration_hours)
                    VALUES (?, ?, ?)
                """, (service_id, e_date, duration))

            elif category == "Flight":
                airline = request.form.get("airline", "Unknown")
                f_num = request.form.get("flight_number", "FL-000")
                dep = request.form.get("dep_airport", "LHE")
                arr = request.form.get("arr_airport", "KHI")
                d_time = request.form.get("dep_time") 
                
                if not d_time:
                    import datetime
                    d_time = datetime.datetime.now()
                
                d_time_str = str(d_time).replace("T", " ")
                
                # Get classes
                classes = request.form.getlist("seat_class[]")
                prices = request.form.getlist("class_price[]")
                ensure_flight_price_column(cursor)
                
                for seat, cost in zip(classes, prices):
                    cursor.execute("""
                        INSERT INTO FlightDetails (service_id, flight_number, airline, departure_airport, arrival_airport, departure_time, arrival_time, seat_class, price)
                        VALUES (?, ?, ?, ?, ?, ?, DATEADD(hour, 2, ?), ?, ?)
                    """, (service_id, f_num, airline, dep, arr, d_time_str, d_time_str, seat, cost))

            conn.commit()
            flash("Service added successfully!", "success")
            return redirect("/provider/dashboard")

        except Exception as e:
            conn.rollback()
            flash(f"Error adding service: {e}", "error")
            return redirect("/provider/add-service")
        finally:
            conn.close()

    locations = fetch_locations(cursor)
    conn.close()
    return render_template("add_service.html", locations=locations, user=session.get("user"))

@app.route("/provider/edit-service/<int:service_id>", methods=["GET", "POST"])
def edit_service(service_id):
    if session.get("role_id") not in (2, 3):
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    if session.get("role_id") == 2:
        cursor.execute("SELECT provider_id FROM Services WHERE service_id = ?", (service_id,))
        row = cursor.fetchone()
        if not row:
            return redirect("/provider/dashboard?error=Not+found")
        cursor.execute("SELECT provider_id FROM Providers WHERE user_id = ?", (session["user_id"],))
        pid = cursor.fetchone()[0]
        if row[0] != pid:
            return redirect("/provider/dashboard?error=Unauthorized")

    if request.method == "POST":
        try:
            # Update basic info
            title = request.form["title"]
            price = request.form["price"]
            city = request.form["city"]
            
            cursor.execute("SELECT location_id FROM Locations WHERE city = ?", (city,))
            loc_row = cursor.fetchone()
            loc_id = loc_row[0] if loc_row else 1

            cursor.execute("""
                UPDATE Services 
                SET service_title = ?, base_price = ?, location_id = ?
                WHERE service_id = ?
            """, (title, price, loc_id, service_id))

            category = request.form["category"]
            
            if category == "Hotel":
                # Update HotelDetails basic info
                cursor.execute("""
                    UPDATE HotelDetails SET hotel_name = ?, city = ?
                    WHERE service_id = ?
                """, (title, city, service_id))
                
                cursor.execute("SELECT hotel_id FROM HotelDetails WHERE service_id = ?", (service_id,))
                hotel_id = cursor.fetchone()[0]
                
                # Handle Rooms
                r_ids = request.form.getlist("room_id[]")
                r_types = request.form.getlist("room_type[]")
                r_prices = request.form.getlist("room_price[]")
                
                for rid, rtype, rprice in zip(r_ids, r_types, r_prices):
                    if rtype and rprice:
                        if rid == "new":
                            cursor.execute("""
                                INSERT INTO Rooms (hotel_id, room_type, price_per_night, availability_status)
                                VALUES (?, ?, ?, 'Available')
                            """, (hotel_id, rtype, rprice))
                        else:
                            cursor.execute("""
                                UPDATE Rooms SET room_type = ?, price_per_night = ?
                                WHERE room_id = ?
                            """, (rtype, rprice, rid))

            elif category == "Ride":
                # Handle Vehicles
                d_ids = request.form.getlist("ride_detail_id[]")
                v_types = request.form.getlist("vehicle_type[]")
                v_models = request.form.getlist("vehicle_model[]")
                v_plates = request.form.getlist("plate_number[]")
                
                for did, vtype, vmodel, vplate in zip(d_ids, v_types, v_models, v_plates):
                    if vmodel and vplate:
                        if did == "new":
                            # Insert new Vehicle & RideDetail
                            cursor.execute("INSERT INTO Vehicles (vehicle_type, model, plate_number) VALUES (?, ?, ?)", (vtype, vmodel, vplate))
                            cursor.execute("SELECT @@IDENTITY")
                            vid = cursor.fetchone()[0]
                            cursor.execute("INSERT INTO RideDetails (service_id, vehicle_id, driver_name) VALUES (?, ?, ?)", (service_id, vid, session["user"]))
                        else:
                            # Update Vehicle via RideDetail
                            cursor.execute("SELECT vehicle_id FROM RideDetails WHERE ride_id = ?", (did,))
                            vid = cursor.fetchone()[0]
                            cursor.execute("""
                                UPDATE Vehicles SET vehicle_type = ?, model = ?, plate_number = ?
                                WHERE vehicle_id = ?
                            """, (vtype, vmodel, vplate, vid))

            elif category == "Flight":
                airline = request.form["airline"]
                f_num = request.form["flight_number"]
                dep = request.form["dep_airport"]
                arr = request.form["arr_airport"]
                d_time = request.form["dep_time"].replace("T", " ")
                
                f_ids = request.form.getlist("flight_detail_id[]")
                classes = request.form.getlist("seat_class[]")
                prices = request.form.getlist("class_price[]")
                
                for fid, seat, cost in zip(f_ids, classes, prices):
                    if seat and cost:
                        if fid == "new":
                            cursor.execute("""
                                INSERT INTO FlightDetails (service_id, flight_number, airline, departure_airport, arrival_airport, departure_time, arrival_time, seat_class, price)
                                VALUES (?, ?, ?, ?, ?, ?, DATEADD(hour, 2, ?), ?, ?)
                            """, (service_id, f_num, airline, dep, arr, d_time, d_time, seat, cost))
                        else:
                            cursor.execute("""
                                UPDATE FlightDetails 
                                SET flight_number=?, airline=?, departure_airport=?, arrival_airport=?, departure_time=?, arrival_time=DATEADD(hour, 2, ?), seat_class=?, price=?
                                WHERE flight_id = ?
                            """, (f_num, airline, dep, arr, d_time, d_time, seat, cost, fid))

            conn.commit()
            flash("Service updated!", "success")
            if session.get("role_id") == 3:
                return redirect("/admin/dashboard")
            return redirect("/provider/dashboard")
        except Exception as e:
            conn.rollback()
            flash(f"Update failed: {e}", "error")
            if session.get("role_id") == 3:
                return redirect(f"/admin/edit-service/{service_id}")
            return redirect(f"/provider/edit-service/{service_id}")
        finally:
            conn.close()

    # GET - Fetch Data
    cursor.execute("""
        SELECT s.service_id, s.service_category, s.service_title, s.base_price, l.city 
        FROM Services s JOIN Locations l ON s.location_id = l.location_id 
        WHERE s.service_id = ?
    """, (service_id,))
    s_row = cursor.fetchone()
    service = {
        "id": s_row[0], "category": s_row[1], "title": s_row[2], "price": s_row[3], "city": s_row[4]
    }
    
    details = []
    if service["category"] == "Hotel":
        cursor.execute("""
            SELECT r.room_id, r.room_type, r.price_per_night 
            FROM Rooms r JOIN HotelDetails h ON r.hotel_id = h.hotel_id 
            WHERE h.service_id = ?
        """, (service_id,))
        for r in cursor.fetchall():
            details.append({"id": r[0], "type": r[1], "price": r[2]})
            
    elif service["category"] == "Ride":
        cursor.execute("""
            SELECT rd.ride_id, v.vehicle_type, v.model, v.plate_number 
            FROM RideDetails rd JOIN Vehicles v ON rd.vehicle_id = v.vehicle_id 
            WHERE rd.service_id = ?
        """, (service_id,))
        for r in cursor.fetchall():
            details.append({"id": r[0], "type": r[1], "model": r[2], "plate": r[3]})

    elif service["category"] == "Flight":
        ensure_flight_price_column(cursor)
        cursor.execute("""
            SELECT flight_id, airline, flight_number, departure_airport, arrival_airport, departure_time, seat_class, price 
            FROM FlightDetails WHERE service_id = ?
        """, (service_id,))
        rows = cursor.fetchall()
        for r in rows:
            # Format time for input datetime-local
            dt = r[5].strftime('%Y-%m-%dT%H:%M') if r[5] else ''
            details.append({
                "id": r[0], "airline": r[1], "number": r[2], "dep": r[3], "arr": r[4], 
                "time": dt, "class": r[6], "price": r[7]
            })

    elif service["category"] == "Event":
         cursor.execute("SELECT event_id, event_date, duration_hours FROM EventDetails WHERE service_id = ?", (service_id,))
         r = cursor.fetchone()
         if r:
             details.append({"id": r[0], "date": str(r[1]), "duration": r[2]})

    locations = fetch_locations(cursor)
    conn.close()
    
    return render_template("edit_service.html", service=service, details=details, locations=locations, is_admin=(session.get('role_id')==3))

@app.route("/provider/delete-sub-item/<type>/<int:id>/<int:service_id>")
def delete_sub_item(type, id, service_id):
    if session.get("role_id") != 2:
        return redirect("/login")
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if type == "room":
            cursor.execute("DELETE FROM Rooms WHERE room_id = ?", (id,))
        elif type == "ride":
            # Get vehicle id to delete it too? Or keep it?
            # RideDetails links to Vehicle. If we delete RideDetail, Vehicle is orphaned.
            cursor.execute("SELECT vehicle_id FROM RideDetails WHERE ride_id = ?", (id,))
            vid = cursor.fetchone()[0]
            cursor.execute("DELETE FROM RideDetails WHERE ride_id = ?", (id,))
            cursor.execute("DELETE FROM Vehicles WHERE vehicle_id = ?", (vid,))
        elif type == "flight":
            cursor.execute("DELETE FROM FlightDetails WHERE flight_id = ?", (id,))
            
        conn.commit()
        flash("Item removed.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error removing item: {e}", "error")
    finally:
        conn.close()
        
    return redirect(f"/provider/edit-service/{service_id}")


@app.route("/provider/delete-service/<int:service_id>")
def delete_service(service_id):
    if session.get("role_id") != 2:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check ownership
        cursor.execute("SELECT provider_id FROM Services WHERE service_id = ?", (service_id,))
        row = cursor.fetchone()
        if not row:
            return redirect("/provider/dashboard?error=Service+not+found")
            
        # Get current provider id
        cursor.execute("SELECT provider_id FROM Providers WHERE user_id = ?", (session["user_id"],))
        pid = cursor.fetchone()[0]
        
        if row[0] != pid:
             return redirect("/provider/dashboard?error=Unauthorized")

        # Delete linked data
        # 1. Bookings
        cursor.execute("DELETE FROM Bookings WHERE service_id = ?", (service_id,))
        
        # 2. Details
        cursor.execute("SELECT service_category FROM Services WHERE service_id = ?", (service_id,))
        cat = cursor.fetchone()[0]
        
        if cat == "Hotel":
            # Get HotelID
            cursor.execute("SELECT hotel_id FROM HotelDetails WHERE service_id = ?", (service_id,))
            h_rows = cursor.fetchall()
            for h in h_rows:
                cursor.execute("DELETE FROM Rooms WHERE hotel_id = ?", (h[0],))
            cursor.execute("DELETE FROM HotelDetails WHERE service_id = ?", (service_id,))
            
        elif cat == "Ride":
            cursor.execute("DELETE FROM RideDetails WHERE service_id = ?", (service_id,))
            
        elif cat == "Event":
            cursor.execute("DELETE FROM EventDetails WHERE service_id = ?", (service_id,))
            
        elif cat == "Flight":
            cursor.execute("DELETE FROM FlightDetails WHERE service_id = ?", (service_id,))
            
        # 3. Service
        cursor.execute("DELETE FROM Services WHERE service_id = ?", (service_id,))
        
        conn.commit()
        flash("Service deleted.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Delete failed: {e}", "error")
    finally:
        conn.close()
        
    return redirect("/provider/dashboard")

@app.route("/admin/delete-sub-item/<type>/<int:id>/<int:service_id>")
def admin_delete_sub_item(type, id, service_id):
    if session.get("role_id") != 3:
        return redirect("/login")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if type == "room":
            cursor.execute("DELETE FROM Rooms WHERE room_id = ?", (id,))
        elif type == "ride":
            cursor.execute("SELECT vehicle_id FROM RideDetails WHERE ride_id = ?", (id,))
            vid = cursor.fetchone()[0]
            cursor.execute("DELETE FROM RideDetails WHERE ride_id = ?", (id,))
            cursor.execute("DELETE FROM Vehicles WHERE vehicle_id = ?", (vid,))
        elif type == "flight":
            cursor.execute("DELETE FROM FlightDetails WHERE flight_id = ?", (id,))
        conn.commit()
        flash("Item removed.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error removing item: {e}", "error")
    finally:
        conn.close()
    return redirect(f"/admin/edit-service/{service_id}")

@app.route("/admin/delete-service/<int:service_id>")
def admin_delete_service(service_id):
    if session.get("role_id") != 3:
        return redirect("/login")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Bookings WHERE service_id = ?", (service_id,))
        cursor.execute("SELECT service_category FROM Services WHERE service_id = ?", (service_id,))
        cat_row = cursor.fetchone()
        if not cat_row:
            return redirect("/admin/dashboard?error=Service+not+found")
        cat = cat_row[0]
        if cat == "Hotel":
            cursor.execute("SELECT hotel_id FROM HotelDetails WHERE service_id = ?", (service_id,))
            h_rows = cursor.fetchall()
            for h in h_rows:
                cursor.execute("DELETE FROM Rooms WHERE hotel_id = ?", (h[0],))
            cursor.execute("DELETE FROM HotelDetails WHERE service_id = ?", (service_id,))
        elif cat == "Ride":
            cursor.execute("DELETE FROM RideDetails WHERE service_id = ?", (service_id,))
        elif cat == "Event":
            cursor.execute("DELETE FROM EventDetails WHERE service_id = ?", (service_id,))
        elif cat == "Flight":
            cursor.execute("DELETE FROM FlightDetails WHERE service_id = ?", (service_id,))
        cursor.execute("DELETE FROM Services WHERE service_id = ?", (service_id,))
        conn.commit()
        flash("Service deleted.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Delete failed: {e}", "error")
    finally:
        conn.close()
    return redirect("/admin/dashboard")

@app.route("/admin/edit-service/<int:service_id>", methods=["GET", "POST"])
def admin_edit_service(service_id):
    if session.get("role_id") != 3:
        return redirect("/login")
    return edit_service(service_id)
@app.route("/admin/user-bookings/<int:user_id>")
def admin_user_bookings(user_id):
    if session.get("role_id") != 3:
        return redirect("/login")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get User Name
    cursor.execute("SELECT full_name FROM Users WHERE user_id = ?", (user_id,))
    u_row = cursor.fetchone()
    target_user_name = u_row[0] if u_row else "Unknown User"

    cursor.execute("""
        SELECT
            booking_id,
            service_title,
            service_category,
            booking_date,
            status,
            pickup_location,
            dropoff_location
        FROM vw_UserBookingDetails
        WHERE user_id = ?
        ORDER BY booking_date DESC
    """, (user_id,))

    bookings = [
        {
            "id": r[0],
            "title": r[1],
            "category": r[2],
            "date": r[3],
            "status": r[4],
            "pickup": r[5],
            "dropoff": r[6]
        }
        for r in cursor.fetchall()
    ]
    conn.close()

    # Reuse bookings.html but pass a flag or just let the admin use the existing cancel button
    # The cancel_booking route already allows role_id=3 to cancel.
    # We just need to render the page.
    # Note: bookings.html might say "My Bookings", we might want to pass a title.
    return render_template("bookings.html", 
                           bookings=bookings, 
                           user=session.get("user"), 
                           page_title=f"Bookings for {target_user_name}",
                           is_admin=True)

@app.route("/admin/edit-user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if session.get("role_id") != 3:
        return redirect("/login")
        
    conn = get_connection()
    cursor = conn.cursor()
    
    ensure_phone_column(cursor)
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        phone = request.form.get("phone")
        # If password provided
        password = request.form.get("password")
        
        try:
            if password and password.strip():
                p_hash = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute("""
                    UPDATE Users SET full_name = ?, email = ?, phone_number = ?, password_hash = ?
                    WHERE user_id = ?
                """, (full_name, email, phone, p_hash, user_id))
            else:
                cursor.execute("""
                    UPDATE Users SET full_name = ?, email = ?, phone_number = ?
                    WHERE user_id = ?
                """, (full_name, email, phone, user_id))
            conn.commit()
            flash("User updated successfully.", "success")
            return redirect("/admin/dashboard")
        except Exception as e:
            conn.rollback()
            flash(f"Update failed: {e}", "error")
            
    # GET
    cursor.execute("SELECT full_name, email, phone_number FROM Users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return redirect("/admin/dashboard?error=User+not+found")
        
    return render_template("edit_user.html", user_id=user_id, full_name=row[0], email=row[1], phone=row[2])

if __name__ == "__main__":
    app.run(debug=True)
