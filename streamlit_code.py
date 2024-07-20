import sqlite3
import google.generativeai as genai
import re
import streamlit as st
import tempfile
import os
import pandas as pd


def connect_to_db(db_path):
    """Connects to the SQLite database and returns the connection and cursor."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    return conn, cursor

def fetch_metadata(cursor):
    """Fetches the metadata of all tables in the SQLite database."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    metadata = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        metadata[table_name] = [
            {"name": column[1], "type": column[2], "notnull": column[3], "default_value": column[4], "primary_key": column[5]}
            for column in columns
        ]
    
    return metadata

def trim_sql_query(response_text):
    """Extracts the SQL query from the response text."""
    match = re.search(r'```sql\n(.*?)\n```', response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def ask_gemini(api_key, metadata, question, prompt):
    """Sends the metadata and question to Google Gemini and returns the generated SQL query."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    message = f"{prompt}\n\nMetadata: {metadata}\n\nQuestion: {question}"
    response = model.generate_content(message)

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
    except sqlite3.Error as e:
        st.error(f"SQL Error: {e}")
        return False

# Streamlit app
st.title("Talk to you SQLite Database")
st.text("Load your data in a simple SQLite Database and ask questions in natural language")
st.markdown(
    "Get an [API](https://ai.google.dev/gemini-api/docs/api-key) key from Google Gemini"
)
st.write("")
st.write("")
api_key = st.text_input("Enter your Google Gemini API key", type="password")
db_file = st.file_uploader("Upload your SQLite database file", type="db")
question = st.text_input("Enter your question")
prompt = """You are an expert in writing SQL queries. Based on the provided database metadata and user question, generate a SQL query to identify records with duplicate values in a specified column. The query should:

Clean the Data:

Remove common unwanted characters from the specified column. This includes removing:
Punctuation (e.g., commas, periods, dashes, slashes, parentheses, apostrophe, single quotes, double quotes)
Whitespace (e.g., spaces, carriage returns, newlines)
Quotation marks
Identify Duplicates:

Use a Common Table Expression (CTE) to clean the data and then identify duplicate values by counting occurrences of the cleaned values.
Ensure that the final query selects the original column and any other relevant columns that help in identifying the duplicate records.
Return Results:

The result should include the original column values and any other relevant columns from the table.

Based on the question consider this also: The records might not be actual duplicates, find the duplicate records in the column {Use from the question} only such that they only have special character differences or spaces or carriage returns, include all special characters to be removed before comparing like ,.()-/\ etc. Do not use regex replace as it doesn't work on the db. Remove them and then compare records for duplicates and return the only the duplicate records
"""

if st.button("Generate SQL Query"):
    if api_key and db_file and question:
        # Save the uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            temp_file.write(db_file.read())
            temp_file_path = temp_file.name

        # Connect to the SQLite database
        conn, cursor = connect_to_db(temp_file_path)

        # Fetch the metadata
        metadata = fetch_metadata(cursor)
        # st.write("Metadata fetched from the database:", metadata)

        # Ask Google Gemini to generate the SQL query
        query = ask_gemini(api_key, metadata, question, prompt)

        if query:
            # st.write("Generated SQL query:", query)
            # Validate and execute the SQL query
            if validate_sql(cursor, query):
                cursor.execute(query)
                result = cursor.fetchall()
                # Convert result to a DataFrame for better display
                df = pd.DataFrame(result, columns=[desc[0] for desc in cursor.description])
                st.dataframe(df)
            else:
                st.error("The generated SQL query is not valid.")
        else:
            st.error("Could not generate a valid SQL query.")

        # Close the database connection and remove the temporary file
        conn.close()
        os.remove(temp_file_path)
    else:
        st.error("Please provide all the required inputs.")
