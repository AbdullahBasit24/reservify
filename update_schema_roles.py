import pyodbc
import hashlib

def update_schema_and_roles():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ReservifyDB;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()

    try:
        # Existing mapping found:
        # 1: Customer
        # 2: Provider
        # 3: Admin
        
        # We can stick to these. Let's just ensure they are named nicely if we want.
        # But 'Customer', 'Provider', 'Admin' are fine.
        
        # 2. Add user_id to Providers table if not exists
        print("Checking Providers table schema...")
        cursor.execute("SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Providers' AND COLUMN_NAME = 'user_id'")
        if not cursor.fetchone():
            print("Adding user_id column to Providers...")
            cursor.execute("ALTER TABLE Providers ADD user_id INT")
            cursor.execute("""
                ALTER TABLE Providers 
                ADD CONSTRAINT FK_Providers_Users FOREIGN KEY (user_id) REFERENCES Users(user_id)
            """)
            # Use filtered index to allow multiple NULLs
            cursor.execute("CREATE UNIQUE INDEX UX_Providers_UserId ON Providers(user_id) WHERE user_id IS NOT NULL")
        else:
            print("user_id column already exists in Providers.")

        # 3. Seed an Admin User
        print("Seeding Admin user...")
        admin_email = "admin@reservify.com"
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        
        # Role ID 3 is Admin
        cursor.execute("SELECT user_id FROM Users WHERE email = ?", (admin_email,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO Users (full_name, email, password_hash, role_id)
                VALUES ('System Admin', ?, ?, 3)
            """, (admin_email, admin_pass))
            print("Admin user created.")
        else:
            print("Admin user already exists.")

        conn.commit()
        print("Schema and Data updated successfully.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema_and_roles()
