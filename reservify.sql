CREATE DATABASE ReservifyDB;
GO

USE ReservifyDB;
GO


CREATE TABLE Roles (
    role_id INT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);


CREATE TABLE Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone_number VARCHAR(20) NULL,
    password_hash VARCHAR(256) NOT NULL,
    role_id INT NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),

    CONSTRAINT FK_Users_Roles
        FOREIGN KEY (role_id)
        REFERENCES Roles(role_id)
);

-- Migration: add phone number to Users
IF COL_LENGTH('Users', 'phone_number') IS NULL
BEGIN
    ALTER TABLE Users ADD phone_number VARCHAR(20) NULL;
END


CREATE TABLE Providers (
    provider_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT UNIQUE, -- Link to Users table
    provider_name VARCHAR(100) NOT NULL,
    contact VARCHAR(50),
    created_at DATETIME DEFAULT GETDATE(),

    CONSTRAINT FK_Providers_Users
        FOREIGN KEY (user_id)
        REFERENCES Users(user_id)
);


CREATE TABLE Locations (
    location_id INT IDENTITY(1,1) PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    area VARCHAR(50),
    address VARCHAR(200)
);
ALTER TABLE Locations
ADD country VARCHAR(50) NOT NULL DEFAULT 'Pakistan';



CREATE TABLE Services (
    service_id INT IDENTITY(1,1) PRIMARY KEY,
    provider_id INT NOT NULL,
    service_category VARCHAR(20) NOT NULL
        CHECK (service_category IN ('Hotel', 'Ride', 'Event', 'Flight')),
    service_title VARCHAR(100) NOT NULL,
    base_price DECIMAL(10,2) NOT NULL,
    location_id INT NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),

    CONSTRAINT FK_Services_Providers
        FOREIGN KEY (provider_id)
        REFERENCES Providers(provider_id),

    CONSTRAINT FK_Services_Locations
        FOREIGN KEY (location_id)
        REFERENCES Locations(location_id)
);


CREATE TABLE HotelDetails (
    hotel_id INT IDENTITY(1,1) PRIMARY KEY,
    service_id INT NOT NULL UNIQUE,
    star_rating INT CHECK (star_rating BETWEEN 1 AND 5),
    amenities VARCHAR(500),

    CONSTRAINT FK_Hotel_Service
        FOREIGN KEY (service_id)
        REFERENCES Services(service_id)
);


CREATE TABLE Rooms (
    room_id INT IDENTITY(1,1) PRIMARY KEY,
    hotel_id INT NOT NULL,
    room_type VARCHAR(50),
    price_per_night DECIMAL(10,2) NOT NULL,
    availability_status VARCHAR(20)
        CHECK (availability_status IN ('Available', 'Booked')),

    CONSTRAINT FK_Rooms_Hotel
        FOREIGN KEY (hotel_id)
        REFERENCES HotelDetails(hotel_id)
);


CREATE TABLE Vehicles (
    vehicle_id INT IDENTITY(1,1) PRIMARY KEY,
    vehicle_type VARCHAR(20)
        CHECK (vehicle_type IN ('Car', 'Bike')),
    model VARCHAR(50),
    plate_number VARCHAR(20) UNIQUE
);


CREATE TABLE RideDetails (
    ride_id INT IDENTITY(1,1) PRIMARY KEY,
    service_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    driver_license VARCHAR(50) NOT NULL,

    CONSTRAINT FK_Ride_Service
        FOREIGN KEY (service_id)
        REFERENCES Services(service_id),

    CONSTRAINT FK_Ride_Vehicle
        FOREIGN KEY (vehicle_id)
        REFERENCES Vehicles(vehicle_id)
);


CREATE TABLE EventDetails (
    event_id INT IDENTITY(1,1) PRIMARY KEY,
    service_id INT NOT NULL UNIQUE,
    event_date DATE NOT NULL,
    duration_hours INT CHECK (duration_hours > 0),
    capacity INT CHECK (capacity > 0),

    CONSTRAINT FK_Event_Service
        FOREIGN KEY (service_id)
        REFERENCES Services(service_id)
);


CREATE TABLE FlightDetails (
    flight_id INT IDENTITY(1,1) PRIMARY KEY,
    service_id INT NOT NULL,
    airline VARCHAR(50) NOT NULL,
    flight_number VARCHAR(20) NOT NULL,
    departure_airport VARCHAR(10),
    arrival_airport VARCHAR(10),
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    seat_class VARCHAR(20)
        CHECK (seat_class IN ('Economy', 'Business', 'First')),
    price DECIMAL(10,2) NULL,

    CONSTRAINT FK_Flight_Service
        FOREIGN KEY (service_id)
        REFERENCES Services(service_id)
);

-- Migration: add price to FlightDetails
IF COL_LENGTH('FlightDetails', 'price') IS NULL
BEGIN
    ALTER TABLE FlightDetails ADD price DECIMAL(10,2) NULL;
END

CREATE TABLE Bookings (
    booking_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    service_id INT NOT NULL,

    room_id INT NULL,
    ride_id INT NULL,
    event_id INT NULL,
    flight_id INT NULL,

    booking_date DATETIME DEFAULT GETDATE(),
    status VARCHAR(20)
        CHECK (status IN ('Booked', 'Cancelled', 'Completed')),
    
    pickup_location VARCHAR(100),
    dropoff_location VARCHAR(100),

    CONSTRAINT FK_Bookings_User
        FOREIGN KEY (user_id)
        REFERENCES Users(user_id),

    CONSTRAINT FK_Bookings_Service
        FOREIGN KEY (service_id)
        REFERENCES Services(service_id),

    CONSTRAINT FK_Bookings_Room
        FOREIGN KEY (room_id)
        REFERENCES Rooms(room_id),

    CONSTRAINT FK_Bookings_Ride
        FOREIGN KEY (ride_id)
        REFERENCES RideDetails(ride_id),

    CONSTRAINT FK_Bookings_Event
        FOREIGN KEY (event_id)
        REFERENCES EventDetails(event_id),

    CONSTRAINT FK_Bookings_Flight
        FOREIGN KEY (flight_id)
        REFERENCES FlightDetails(flight_id)
);


CREATE TABLE Payments (
    payment_id INT IDENTITY(1,1) PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(30),
    payment_date DATETIME DEFAULT GETDATE(),

    CONSTRAINT FK_Payments_Booking
        FOREIGN KEY (booking_id)
        REFERENCES Bookings(booking_id)
);


CREATE INDEX idx_services_category ON Services(service_category);
CREATE INDEX idx_bookings_user ON Bookings(user_id);
CREATE INDEX idx_users_email ON Users(email);


--TRIGGERS
CREATE TRIGGER trg_CapitalizeUserName
ON Users
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE u
    SET full_name =
        UPPER(LEFT(i.full_name, 1)) +
        SUBSTRING(i.full_name, 2, LEN(i.full_name))
    FROM Users u
    JOIN inserted i ON u.user_id = i.user_id
    WHERE LEFT(i.full_name, 1) COLLATE Latin1_General_CS_AS
          BETWEEN 'a' AND 'z';
END;

--
CREATE TRIGGER trg_CapitalizeFullName
ON Users
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE u
    SET full_name =
        (
            SELECT STRING_AGG(
                UPPER(LEFT(value, 1)) +
                LOWER(SUBSTRING(value, 2, LEN(value))),
                ' '
            )
            FROM STRING_SPLIT(i.full_name, ' ')
        )
    FROM Users u
    JOIN inserted i ON u.user_id = i.user_id;
END;



--PROCEDURES

CREATE OR ALTER PROCEDURE sp_RegisterUser
    @full_name      VARCHAR(100),
    @email          VARCHAR(100),
    @password_hash  VARCHAR(256)
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (SELECT 1 FROM Users WHERE email = @email)
    BEGIN
        SELECT 0 AS success, 'Email already exists' AS message;
        RETURN;
    END

    INSERT INTO Users (full_name, email, password_hash, role_id)
    VALUES (@full_name, @email, @password_hash, 1);

    SELECT 1 AS success, 'User registered successfully' AS message;
END;
GO


CREATE OR ALTER PROCEDURE sp_GetUserForLogin
    @email VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT user_id, full_name, password_hash, role_id
    FROM Users
    WHERE email = @email;
END;
GO

--VIEWS
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
GO

SELECT * FROM vw_UserBookingDetails

CREATE OR ALTER VIEW vw_ServicesByLocation
AS
SELECT
    s.service_id,
    s.service_title,
    s.service_category,
    s.base_price,
    l.country,
    l.city,
    l.area,
    p.provider_name
FROM Services s
JOIN Locations l ON s.location_id = l.location_id
JOIN Providers p ON s.provider_id = p.provider_id;
GO





--TESTING

--HOTEL INSERTION
INSERT INTO Providers (provider_name, contact)
VALUES ('Marriott Hotel Karachi', '021-35680000');

INSERT INTO Services
(provider_id, service_category, service_title, base_price, location_id)
VALUES
(2, 'Hotel', 'Marriott Karachi', 28000, 2);

DECLARE @serviceId INT = SCOPE_IDENTITY();
INSERT INTO HotelDetails
(service_id, star_rating, amenities)
VALUES
(@serviceId, 5, 'Free WiFi, Pool, Gym, Spa, Breakfast');

DECLARE @serviceId INT = SCOPE_IDENTITY();
INSERT INTO Rooms
(hotel_id, room_type, price_per_night, availability_status)
VALUES
(
    (SELECT hotel_id FROM HotelDetails WHERE service_id = @serviceId),
    'Executive Suite',
    35000,
    'Available'
),
(
    (SELECT hotel_id FROM HotelDetails WHERE service_id = @serviceId),
    'Deluxe Room',
    30000,
    'Available'
);

INSERT INTO Locations (country, city, area, address)
VALUES ('Pakistan', 'Karachi', 'Clifton', 'Block 5, Clifton');

INSERT INTO Services
(service_title, service_category, base_price, provider_id, location_id)
VALUES
(
    'Ocean Pearl Hotel',
    'Hotel',
    28000,
    1,
    SCOPE_IDENTITY()
);

DECLARE @serviceId INT = SCOPE_IDENTITY();
INSERT INTO HotelDetails (service_id, hotel_name, star_rating)
VALUES (@serviceId, 'Ocean Pearl Hotel', 5);

DECLARE @hotelId INT =
(
    SELECT hotel_id
    FROM HotelDetails
    WHERE service_id = @serviceId
);

INSERT INTO Rooms
(hotel_id, room_type, price_per_night, availability_status)
VALUES
(@hotelId, 'Executive Suite', 35000, 'Available'),
(@hotelId, 'Deluxe Room', 30000, 'Available');


--ADDING MORE DATA
USE ReservifyDB;
GO

/* ===============================
   PROVIDERS
   =============================== */
INSERT INTO Providers (provider_name, contact) VALUES
('Pearl Continental', '042-111-505-505'),
('AirVista Airlines', '021-111-786-786'),
('GoSwift Rides', '0300-1234567'),
('EventHub PK', '0311-9988776');

/* ===============================
   LOCATIONS
   =============================== */
INSERT INTO Locations (city, area, address) VALUES
('Lahore', 'Gulberg', 'Main Boulevard'),
('Lahore', 'DHA', 'Phase 5'),
('Karachi', 'Clifton', 'Sea View Road'),
('Islamabad', 'Blue Area', 'Jinnah Avenue');

/* ===============================
   HOTELS
   =============================== */
INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES
(1, 'Hotel', 'PC Lahore Gulberg', 22000, 1),
(1, 'Hotel', 'PC Lahore DHA', 25000, 2);

INSERT INTO HotelDetails (service_id, star_rating, amenities)
VALUES
(1, 5, 'WiFi, Pool, Gym, Spa'),
(2, 5, 'WiFi, Gym, Breakfast');

INSERT INTO Rooms (hotel_id, room_type, price_per_night, availability_status)
VALUES
(1, 'Deluxe', 24000, 'Available'),
(1, 'Executive', 30000, 'Available'),
(2, 'Standard', 26000, 'Available'),
(2, 'Suite', 35000, 'Available');

/* ===============================
   FLIGHTS
   =============================== */
INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES
(2, 'Flight', 'AirVista AV101 LHR → ISB', 18000, 1),
(2, 'Flight', 'AirVista AV202 KHI → LHR', 22000, 3);

INSERT INTO FlightDetails
(service_id, airline, flight_number, departure_airport, arrival_airport, departure_time, arrival_time, seat_class, price)
VALUES
(3, 'AirVista', 'AV101', 'LHR', 'ISB', '2025-02-10 09:00', '2025-02-10 10:15', 'Economy', 18000),
(4, 'AirVista', 'AV202', 'KHI', 'LHR', '2025-02-11 14:30', '2025-02-11 16:45', 'Business', 22000);

/* ===============================
   RIDES
   =============================== */
INSERT INTO Vehicles (vehicle_type, model, plate_number) VALUES
('Car', 'Toyota Corolla', 'LHR-2345'),
('Bike', 'Honda CD70', 'LHR-7788');

INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES
(3, 'Ride', 'GoSwift Car Ride', 800, 1),
(3, 'Ride', 'GoSwift Bike Ride', 350, 1);

INSERT INTO RideDetails (service_id, vehicle_id, driver_license)
VALUES
(5, 1, 'DL-LHR-998877'),
(6, 2, 'DL-LHR-112233');

/* ===============================
   EVENTS
   =============================== */
INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES
(4, 'Event', 'Sufi Night – Abida Parveen', 4500, 3),
(4, 'Event', 'Tech Conference 2025', 6000, 4);

INSERT INTO EventDetails (service_id, event_date, duration_hours, capacity)
VALUES
(7, '2025-03-15', 4, 5000),
(8, '2025-04-20', 8, 1200);




--BASIC DATA INSERTION TEST
INSERT INTO Roles VALUES
(1, 'Customer'),
(2, 'Provider'),
(3, 'Admin');


INSERT INTO Users (full_name, email, password_hash, role_id)
VALUES
('Ali Khan', 'ali@email.com', 'HASHED123', 1),
('Sara Ahmed', 'sara@email.com', 'HASHED456', 2);


INSERT INTO Providers (provider_name, contact)
VALUES ('Pearl Continental Hotel', '042-1234567');

INSERT INTO Locations (city, area, address)
VALUES ('Lahore', 'Gulberg', 'Main Boulevard');


INSERT INTO Services
(provider_id, service_category, service_title, base_price, location_id)
VALUES
(1, 'Hotel', 'PC Lahore', 25000, 1);


INSERT INTO HotelDetails (service_id, star_rating, amenities)
VALUES (1, 5, 'WiFi, Pool, Gym');


INSERT INTO Rooms (hotel_id, room_type, price_per_night, availability_status)
VALUES (1, 'Deluxe', 30000, 'Available');



-- Additional Dummy Services ------------------------------------------

-- 1. New Flight Service (KHI -> ISB)
INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES (@airProviderId, 'Flight', 'AirVista AV505 KHI-ISB', 22000, @karachiLoc);
SET @flightServiceId = SCOPE_IDENTITY();

INSERT INTO FlightDetails (service_id, airline, flight_number, departure_airport, arrival_airport, departure_time, arrival_time, seat_class, price)
VALUES (@flightServiceId, 'AirVista', 'AV505', 'KHI', 'ISB', '2025-01-20T14:00:00', '2025-01-20T16:00:00', 'Business', 22000);

-- 2. New Ride Service (Bike in Lahore)
INSERT INTO Vehicles (vehicle_type, model, plate_number)
VALUES ('Bike', 'Honda CD70', 'LHR-5566');
SET @rideVehicleId = SCOPE_IDENTITY();

INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES (@rideProviderId, 'Ride', 'GoSwift Bike Ride', 350, @lahoreLoc);
SET @rideServiceId = SCOPE_IDENTITY();

INSERT INTO RideDetails (service_id, vehicle_id, driver_license)
VALUES (@rideServiceId, @rideVehicleId, 'DL-11223344');

-- 3. New Event Service (Concert in Karachi)
INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES (@eventProviderId, 'Event', 'Sufi Night - Abida Parveen', 4500, @stadiumLoc);
SET @eventServiceId = SCOPE_IDENTITY();

INSERT INTO EventDetails (service_id, event_date, duration_hours, capacity)
VALUES (@eventServiceId, '2025-03-05', 4, 5000);

-- --------------------------------------------------------------------


SELECT
    s.service_title,
    h.star_rating,
    r.room_type,
    r.price_per_night
FROM Services s
JOIN HotelDetails h ON s.service_id = h.service_id
JOIN Rooms r ON h.hotel_id = r.hotel_id;


SELECT
    u.full_name,
    s.service_title,
    b.booking_date,
    b.status
FROM Bookings b
JOIN Users u ON b.user_id = u.user_id
JOIN Services s ON b.service_id = s.service_id;


--should fail (invalid room id)
INSERT INTO Bookings (user_id, service_id, room_id, status)
VALUES (1, 1, 1, 'Booked');


INSERT INTO Payments (booking_id, amount, payment_method)
VALUES (1, 30000, 'Credit Card');


--should fail (invalid service category)
INSERT INTO Services
(provider_id, service_category, service_title, base_price, location_id)
VALUES (1, 'Taxi', 'Invalid Service', 1000, 1);


--should fail (star rating out of range)
INSERT INTO HotelDetails (service_id, star_rating)
VALUES (1, 10);


--should fail (duplicate email)
INSERT INTO Users (full_name, email, password_hash, role_id)
VALUES ('Test', 'ali@email.com', 'HASH', 1);


--SQL Injection Test (should not return all users)
SELECT * FROM Users WHERE email = 'test@email.com' OR '1'='1';


SELECT * FROM Users

--most booked service
SELECT
    s.service_title,
    COUNT(*) AS total_bookings
FROM Bookings b
JOIN Services s ON b.service_id = s.service_id
GROUP BY s.service_title;


--revenue by category
SELECT
    s.service_category,
    SUM(p.amount) AS revenue
FROM Payments p
JOIN Bookings b ON p.booking_id = b.booking_id
JOIN Services s ON b.service_id = s.service_id
GROUP BY s.service_category;

SELECT * FROM Users
SELECT * FROM Bookings
SELECT * FROM RideDetails

SELECT u.full_name, u.email, b.booking_id, b.booking_date
FROM Users u
JOIN Bookings b ON b.user_id = u.user_id


--TESTING
SELECT service_id, service_title
FROM Services
WHERE service_category = 'Hotel';

SELECT service_id, hotel_id
FROM HotelDetails;

SELECT hotel_id, room_id
FROM Rooms;

DECLARE @hotelServiceId INT;
DECLARE @hotelId INT;

INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES (1, 'Hotel', 'PC Karachi', 23000, 3);

SET @hotelServiceId = SCOPE_IDENTITY();

INSERT INTO HotelDetails (service_id, star_rating, amenities)
VALUES (@hotelServiceId, 5, 'WiFi, Pool');

SET @hotelId = SCOPE_IDENTITY();

INSERT INTO Rooms (hotel_id, room_type, price_per_night, availability_status)
VALUES
(@hotelId, 'Deluxe', 26000, 'Available'),
(@hotelId, 'Suite', 35000, 'Available');

DECLARE @rideServiceId INT;
DECLARE @vehicleId INT;

INSERT INTO Vehicles (vehicle_type, model, plate_number)
VALUES ('Car', 'Toyota Yaris', 'LHR-9988');

SET @vehicleId = SCOPE_IDENTITY();

INSERT INTO Services (provider_id, service_category, service_title, base_price, location_id)
VALUES (3, 'Ride', 'GoSwift Yaris Ride', 900, 1);

SET @rideServiceId = SCOPE_IDENTITY();

INSERT INTO RideDetails (service_id, vehicle_id, driver_license)
VALUES (@rideServiceId, @vehicleId, 'DL-55667788');

SELECT
    s.service_id,
    r.room_id,
    r.room_type
FROM Rooms r
JOIN HotelDetails h ON r.hotel_id = h.hotel_id
JOIN Services s ON h.service_id = s.service_id;

/* ROLE-BASED ACCESS AND CONTROL PROCEDURES (App-integrated RBAC using Users.role_id) */

-- Seed Roles (Customer=1, Provider=2, Admin=3)
IF NOT EXISTS (SELECT 1 FROM Roles WHERE role_id = 1)
    INSERT INTO Roles(role_id, role_name) VALUES (1, 'Customer');
IF NOT EXISTS (SELECT 1 FROM Roles WHERE role_id = 2)
    INSERT INTO Roles(role_id, role_name) VALUES (2, 'Provider');
IF NOT EXISTS (SELECT 1 FROM Roles WHERE role_id = 3)
    INSERT INTO Roles(role_id, role_name) VALUES (3, 'Admin');
GO

-- Login helper used by app
CREATE OR ALTER PROCEDURE sp_GetUserForLogin
    @Email VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT user_id, full_name, password_hash, role_id
    FROM Users
    WHERE email = @Email;
END
GO

-- Registration helper used by app
CREATE OR ALTER PROCEDURE sp_RegisterUser
    @FullName VARCHAR(100),
    @Email VARCHAR(100),
    @PasswordHash VARCHAR(256),
    @Phone VARCHAR(20) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM Users WHERE email = @Email)
    BEGIN
        SELECT 0 AS ok, 'Email already registered' AS msg;
        RETURN;
    END
    INSERT INTO Users (full_name, email, password_hash, role_id, phone_number)
    VALUES (@FullName, @Email, @PasswordHash, 1, @Phone);
    SELECT 1 AS ok, 'Registered' AS msg;
END
GO

-- Add Service (Provider or Admin)
CREATE OR ALTER PROCEDURE sp_AddService
    @ActingUserId INT,
    @Category VARCHAR(20),
    @Title VARCHAR(100),
    @BasePrice DECIMAL(10,2),
    @City VARCHAR(50),
    @Airline VARCHAR(50) = NULL,
    @FlightNumber VARCHAR(20) = NULL,
    @DepartureAirport VARCHAR(10) = NULL,
    @ArrivalAirport VARCHAR(10) = NULL,
    @DepartureTime DATETIME = NULL,
    @SeatClass VARCHAR(20) = NULL,
    @VehicleType VARCHAR(20) = NULL,
    @VehicleModel VARCHAR(50) = NULL,
    @VehiclePlate VARCHAR(20) = NULL,
    @EventDate DATE = NULL,
    @DurationHours INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @role INT = (SELECT role_id FROM Users WHERE user_id = @ActingUserId);
    IF @role NOT IN (2,3) 
        RAISERROR('Unauthorized: only Provider or Admin can add services.', 16, 1);

    DECLARE @provider_id INT = 
        CASE WHEN @role = 2 
             THEN (SELECT provider_id FROM Providers WHERE user_id = @ActingUserId)
             ELSE (SELECT TOP 1 provider_id FROM Providers ORDER BY provider_id) -- admin: default to first provider if not specified
        END;
    IF @provider_id IS NULL RAISERROR('Provider profile not found for acting user.', 16, 1);

    DECLARE @location_id INT = (SELECT TOP 1 location_id FROM Locations WHERE city = @City ORDER BY location_id);
    IF @location_id IS NULL 
    BEGIN
        INSERT INTO Locations(city) VALUES(@City);
        SET @location_id = SCOPE_IDENTITY();
    END

    INSERT INTO Services(provider_id, service_category, service_title, base_price, location_id)
    VALUES (@provider_id, @Category, @Title, @BasePrice, @location_id);
    DECLARE @service_id INT = SCOPE_IDENTITY();

    IF @Category = 'Hotel'
    BEGIN
        INSERT INTO HotelDetails(service_id, star_rating, amenities)
        VALUES (@service_id, 3, 'WiFi');
    END
    ELSE IF @Category = 'Ride'
    BEGIN
        IF @VehicleType IS NULL SET @VehicleType = 'Car';
        IF @VehicleModel IS NULL SET @VehicleModel = 'Generic';
        IF @VehiclePlate IS NULL SET @VehiclePlate = CONCAT('PLT-', @service_id);
        INSERT INTO Vehicles(vehicle_type, model, plate_number) VALUES(@VehicleType, @VehicleModel, @VehiclePlate);
        DECLARE @vehicle_id INT = SCOPE_IDENTITY();
        INSERT INTO RideDetails(service_id, vehicle_id, driver_license) VALUES(@service_id, @vehicle_id, CONCAT('DL-', @VehiclePlate));
    END
    ELSE IF @Category = 'Event'
    BEGIN
        IF @EventDate IS NULL SET @EventDate = GETDATE();
        IF @DurationHours IS NULL SET @DurationHours = 2;
        INSERT INTO EventDetails(service_id, event_date, duration_hours, capacity)
        VALUES(@service_id, @EventDate, @DurationHours, 1000);
    END
    ELSE IF @Category = 'Flight'
    BEGIN
        IF @Airline IS NULL SET @Airline = 'Unknown';
        IF @FlightNumber IS NULL SET @FlightNumber = CONCAT('FL-', @service_id);
        IF @DepartureAirport IS NULL SET @DepartureAirport = 'LHE';
        IF @ArrivalAirport IS NULL SET @ArrivalAirport = 'KHI';
        IF @DepartureTime IS NULL SET @DepartureTime = DATEADD(HOUR, 2, GETDATE());
        IF @SeatClass IS NULL SET @SeatClass = 'Economy';
        INSERT INTO FlightDetails(service_id, airline, flight_number, departure_airport, arrival_airport, departure_time, arrival_time, seat_class, price)
        VALUES(@service_id, @Airline, @FlightNumber, @DepartureAirport, @ArrivalAirport, @DepartureTime, DATEADD(HOUR, 2, @DepartureTime), @SeatClass, @BasePrice);
    END
END
GO

-- Edit Service (Provider owns service or Admin)
CREATE OR ALTER PROCEDURE sp_EditService
    @ActingUserId INT,
    @ServiceId INT,
    @NewTitle VARCHAR(100),
    @NewBasePrice DECIMAL(10,2),
    @NewCity VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @role INT = (SELECT role_id FROM Users WHERE user_id = @ActingUserId);
    DECLARE @acting_provider INT = (SELECT provider_id FROM Providers WHERE user_id = @ActingUserId);
    DECLARE @service_provider INT = (SELECT provider_id FROM Services WHERE service_id = @ServiceId);
    IF @role = 2 AND (@acting_provider IS NULL OR @acting_provider <> @service_provider)
        RAISERROR('Unauthorized: providers can edit only their own services.', 16, 1);

    DECLARE @location_id INT = (SELECT TOP 1 location_id FROM Locations WHERE city = @NewCity ORDER BY location_id);
    IF @location_id IS NULL
    BEGIN
        INSERT INTO Locations(city) VALUES(@NewCity);
        SET @location_id = SCOPE_IDENTITY();
    END

    UPDATE Services
    SET service_title = @NewTitle,
        base_price = @NewBasePrice,
        location_id = @location_id
    WHERE service_id = @ServiceId;
END
GO

-- Delete Service (Provider owns service or Admin)
CREATE OR ALTER PROCEDURE sp_DeleteService
    @ActingUserId INT,
    @ServiceId INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @role INT = (SELECT role_id FROM Users WHERE user_id = @ActingUserId);
    DECLARE @acting_provider INT = (SELECT provider_id FROM Providers WHERE user_id = @ActingUserId);
    DECLARE @service_provider INT = (SELECT provider_id FROM Services WHERE service_id = @ServiceId);
    IF @role = 2 AND (@acting_provider IS NULL OR @acting_provider <> @service_provider)
        RAISERROR('Unauthorized: providers can delete only their own services.', 16, 1);

    DELETE FROM Bookings WHERE service_id = @ServiceId;
    DELETE FROM FlightDetails WHERE service_id = @ServiceId;
    DELETE FROM EventDetails WHERE service_id = @ServiceId;
    -- Rooms via HotelDetails
    DECLARE @hotel_id INT = (SELECT hotel_id FROM HotelDetails WHERE service_id = @ServiceId);
    IF @hotel_id IS NOT NULL
    BEGIN
        DELETE FROM Rooms WHERE hotel_id = @hotel_id;
        DELETE FROM HotelDetails WHERE service_id = @ServiceId;
    END
    -- Ride Details and Vehicles
    DELETE v
    FROM Vehicles v
    WHERE v.vehicle_id IN (SELECT vehicle_id FROM RideDetails WHERE service_id = @ServiceId);
    DELETE FROM RideDetails WHERE service_id = @ServiceId;
    DELETE FROM Services WHERE service_id = @ServiceId;
END
GO

-- Book a Service (Customer or Admin)
CREATE OR ALTER PROCEDURE sp_BookService
    @ActingUserId INT,
    @ServiceId INT,
    @RoomId INT = NULL,
    @RideId INT = NULL,
    @EventId INT = NULL,
    @FlightId INT = NULL,
    @Pickup VARCHAR(100) = NULL,
    @Dropoff VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @role INT = (SELECT role_id FROM Users WHERE user_id = @ActingUserId);
    IF @role NOT IN (1,3) RAISERROR('Unauthorized: only Customers or Admin can book.', 16, 1);

    INSERT INTO Bookings (user_id, service_id, room_id, ride_id, event_id, flight_id, pickup_location, dropoff_location, status)
    VALUES (@ActingUserId, @ServiceId, @RoomId, @RideId, @EventId, @FlightId, @Pickup, @Dropoff, 'Booked');
END
GO

-- Update Profile (Self or Admin)
CREATE OR ALTER PROCEDURE sp_UpdateUserProfile
    @ActingUserId INT,
    @TargetUserId INT,
    @FullName VARCHAR(100),
    @Email VARCHAR(100),
    @Phone VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @role INT = (SELECT role_id FROM Users WHERE user_id = @ActingUserId);
    IF @ActingUserId <> @TargetUserId AND @role <> 3
        RAISERROR('Unauthorized: only self or Admin can update profile.', 16, 1);

    UPDATE Users
    SET full_name = @FullName,
        email = @Email,
        phone_number = @Phone
    WHERE user_id = @TargetUserId;
END
GO

SELECT room_id, availability_status FROM Rooms;

SELECT * FROM Bookings
