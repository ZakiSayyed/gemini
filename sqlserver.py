import pyodbc
import google.generativeai as genai
import re

def connect_to_db(server, database, username, password):
    """Connects to the SQL Server database and returns the connection and cursor."""
    connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    return conn, cursor

def fetch_metadata(cursor):
    """Fetches the metadata of all tables in the SQL Server database."""
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES;")
    tables = cursor.fetchall()
    
    metadata = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY "
                       f"FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}';")
        columns = cursor.fetchall()
        metadata[table_name] = [
            {"name": column[0], "type": column[1], "notnull": column[2], "default_value": column[3], "primary_key": column[4]}
            for column in columns
        ]
    
    return metadata

def trim_sql_query(response_text):
    """Extracts the SQL query from the response text."""
    # Regular expression to capture SQL code between ```sql and ```
    match = re.search(r'```sql\n(.*?)\n```', response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def ask_gemini(api_key, metadata, question, prompt):
    """Sends the metadata and question to Google Gemini and returns the generated SQL query."""
    # Configure the API key
    genai.configure(api_key=api_key)

    # Create a generative model instance
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Construct the message with metadata, question, and prompt
    message = f"{prompt}\n\nMetadata: {metadata}\n\nQuestion: {question}"
    print(message)
    # Send the message
    response = model.generate_content(message)
    print(response)
    # Extract and trim the SQL query
    try:
        response_text = response.candidates[0].content.parts[0].text.strip()
        query = trim_sql_query(response_text)
        return query
    except (AttributeError, IndexError):
        return None

def validate_sql(cursor, query):
    """Validates the SQL query by trying to execute it."""
    try:
        cursor.execute(query)
        return True
    except pyodbc.Error as e:
        print(f"SQL Error: {e}")
        return False

def main():
    server = "54.186.200.213"  # Replace with your SQL Server address
    database = "CATALOG_DEMO"  # Replace with your database name
    username = "mss_demo"  # Replace with your username
    password = "Mssdemo!123"  # Replace with your password

    api_key = "AIzaSyDhfVAr1gfC5Tq88_VEwpiNbrwSUNYE_wY"  # Replace with your Google Gemini API key

    prompt = """You are an expert in writing SQL queries. Based on the provided database metadata and user question, generate a SQL query to identify records with duplicate values in a specified column. The query should:

    Clean the Data:

    Remove common unwanted characters from the specified column. This includes removing:
    Punctuation (e.g., commas, periods, dashes, slashes, parentheses)
    Whitespace (e.g., spaces, carriage returns, newlines)
    Quotation marks

    Identify Duplicates:

    Use a Common Table Expression (CTE) to clean the data and then identify duplicate values by counting occurrences of the cleaned values.
    Ensure that the final query selects the original column and any other relevant columns that help in identifying the duplicate records.

    Return Results:

    The result should include the original column values and any other relevant columns from the table.

    Based on the question consider this also: The records might not be actual duplicates, find the duplicate records in the column {Use from the question} only such that they only have special character differences or spaces or carriage returns, include all special characters to be removed before comparing like ,.()-/\ etc. Do not use regex replace as it doesn't work on the db. Remove them and then compare records for duplicates and return the only the duplicate records
    """


    # Connect to the SQL Server database
    conn, cursor = connect_to_db(server, database, username, password)

    # Fetch the metadata
    metadata = fetch_metadata(cursor)
    print("Metadata fetched from the database:", metadata)

    # Get the user's question
    question = input("Enter your question: ")

    # Ask Google Gemini to generate the SQL query
    query = ask_gemini(api_key, metadata, question, prompt)

    if query:
        print("Generated SQL query:", query)
        # Validate and execute the SQL query
        if validate_sql(cursor, query):
            cursor.execute(query)
            result = cursor.fetchall()
            print("Query result:", result)
        else:
            print("The generated SQL query is not valid.")
    else:
        print("Could not generate a valid SQL query.")

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
