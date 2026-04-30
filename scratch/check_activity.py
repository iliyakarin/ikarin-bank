
import asyncio
from database import SessionLocal
from models.user import User
from clickhouse_utils import get_ch_client, CH_DB

async def check_activity():
    async with SessionLocal() as db:
        user = (await db.execute(User.__table__.select().limit(1))).first()
        if not user:
            print("No user found")
            return
        
        user_id = user.id
        print(f"Checking activity for user_id: {user_id}")
        
        ch = get_ch_client()
        query = f"SELECT category, action, title, event_time FROM {CH_DB}.activity_events WHERE user_id = {user_id} ORDER BY event_time DESC LIMIT 5"
        result = ch.query(query)
        print("ClickHouse Results:")
        for row in result.result_rows:
            print(row)

if __name__ == "__main__":
    asyncio.run(check_activity())
