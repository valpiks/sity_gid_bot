from database.config import host, user, password, db_name
import asyncpg

DATABASE_URL = f"postgresql://{user}:{password}@{host}:5432/{db_name}"


async def create_table():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        subscribed BOOLEAN DEFAULT FALSE,
        preferences TEXT DEFAULT '',
        latitude FLOAT DEFAULT NULL,
        longitude FLOAT DEFAULT NULL
    )
    ''')
        
        await conn.close()
        
        print("[INFO] Table created successfully")
    
    except Exception as ex:
        print("[ERROR] Error while working with PostgreSQL:", ex)

