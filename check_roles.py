import pyodbc

def check_roles():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ReservifyDB;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Roles")
    for row in cursor.fetchall():
        print(row)
    conn.close()

if __name__ == "__main__":
    check_roles()
