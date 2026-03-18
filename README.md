# Reservify: Multi-Service Booking System

## Overview
Reservify is a database-driven booking platform that allows users to book hotels, flights, rides, and events within a single system. The project is built using SQL Server for database management and Flask for backend integration, with a simple web interface for user interaction.

## Objectives
- Design a normalized relational database for multiple service domains
- Implement secure user authentication and role-based access
- Provide a unified booking system across different service types
- Demonstrate advanced SQL concepts in a real-world application

## Key Features
- Multi-service support: hotel, flight, ride, and event booking
- Role-based access control for customers, providers, and admins
- Secure authentication with hashed passwords
- Booking and payment management system
- Location-based service filtering
- Scalable and modular database design

## Database Design
- Fully normalized schema up to Third Normal Form (3NF)
- Core entities include Users, Providers, Services, Locations, and Bookings
- Separate detail tables for each service type:
  - HotelDetails and Rooms
  - FlightDetails
  - RideDetails and Vehicles
  - EventDetails
- Proper use of primary keys and foreign key constraints to maintain data integrity

## Advanced SQL Features
- Views for simplified data retrieval:
  - `vw_UserBookingDetails`
  - `vw_ServicesByLocation`
- Stored procedures for core operations:
  - User registration and login
  - Service creation, update, and deletion
  - Booking management
- Triggers for automatic data formatting and validation
- Indexes for optimized query performance

## System Architecture
- Backend: Flask (Python) with pyodbc
- Database: Microsoft SQL Server
- Frontend: HTML and CSS
- Follows a basic MVC pattern where:
  - Views (SQL) handle data abstraction
  - Flask manages business logic
  - Frontend displays user-friendly data

## How It Works
1. Users register and log in to the system
2. Services are listed based on category and location
3. Users select a service and create a booking
4. Payment details are recorded and linked to bookings
5. Users can view their booking history through simplified views

## Unique Aspect
Unlike typical booking platforms that focus on a single domain, Reservify integrates ride booking along with hotels, flights, and events, making it a more comprehensive service platform.

## Scalability Potential
- Integration with external APIs for real-time hotel and flight data
- Deployment on cloud infrastructure
- Support for concurrent users and high traffic
- Expansion into microservices-based architecture

## Technologies Used
- SQL Server
- Flask (Python)
- pyodbc
- HTML and CSS

## Conclusion
Reservify demonstrates strong database design principles and practical implementation of a multi-service booking system. It highlights the use of advanced SQL features along with backend integration to build a scalable and maintainable application.