import pyodbc

def connect_to_db(server, database, username, password):
    """Connects to the SQL Server database and returns the connection and cursor."""
    connection_string = (
        r"DRIVER={ODBC Driver 18 for SQL Server};"
        r"SERVER=" + server + ";"
        r"DATABASE=" + database + ";"
        r"UID=" + username + ";"
        r"PWD=" + password + ";"
    )
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        print("Connection successful!")
        return conn, cursor
    except pyodbc.Error as e:
        print(f"Error connecting to database: {e}")
        return None, None

# Replace with your actual connection details
server = "54.186.200.213"  # Replace with your SQL Server address
database = "CATALOG_DEMO"  # Replace with your database name
username = "mss_demo"  # Replace with your username
password = "Mssdemo!123"  # Replace with your password

conn, cursor = connect_to_db(server, database, username, password)
if conn and cursor:
    # Perform database operations
    conn.close()