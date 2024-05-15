# import MySQLdb
from flask_mysqldb import MySQLdb

# MySQL Configuration
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'db_rice'

def create_db():
    # Connect to MySQL
    conn = MySQLdb.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()

    # Create database
    cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(DB_NAME))
    conn.commit()

    # Switch to the database
    cursor.execute("USE {}".format(DB_NAME))

    # Create users tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) UNIQUE NOT NULL,
            fname VARCHAR(100) NOT NULL,
            mname VARCHAR(100) NOT NULL,
            lname VARCHAR(100) NOT NULL,
            password VARCHAR(100) NOT NULL
        )
    """)
    conn.commit()


    cursor.close()
    conn.close()