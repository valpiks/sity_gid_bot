import psycopg2
from config import host, user, password, db_name

connection = None

try:
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name,
        options="-c client_encoding=utf8"
    )
    connection.autocommit = True


    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        server_version = cursor.fetchone()
        print(f"Server version: {server_version[0]}")


    with connection.cursor() as cursor:
        cursor.execute("""CREATE TABLE users(
                       id serial PRIMARY KEY,
                       first_name varchar(50) NOT NULL,
                       nick_name varchar(50) NOT NULL);"""
        )
        
        print("[INFO] Table created successfully")
    

except Exception as ex:
    print("[error] Error while working with PostgreSQL:", ex)
finally:
    if connection:
        connection.close() 
        print("Connection closed.")