from database.config import host, user, password, db_name
import asyncpg

DATABASE_URL = f"postgresql://{user}:{password}@{host}:5432/{db_name}"


async def create_table():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            subscribed BOOLEAN DEFAULT FALSE,
            preferences TEXT DEFAULT '',
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION
        );
        """)

        # Создаем таблицу events, если её нет
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            data TEXT NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT
        );
        """)

        await conn.close()
        
        print("[INFO] Table created successfully")
    
    except Exception as ex:
        print("[ERROR] Error while working with PostgreSQL:", ex)

