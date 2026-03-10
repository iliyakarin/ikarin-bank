import os
import sys
import clickhouse_connect
from dotenv import load_dotenv

def apply_sql(env_file=".env.dev"):
    if not os.path.exists(env_file):
        print(f"Error: {env_file} not found.")
        return

    load_dotenv(env_file)
    
    # ClickHouse admin connection info (prioritize local if running outside docker)
    # If running inside docker, CLICKHOUSE_HOST=clickhouse will work.
    # If running locally, we might need localhost. 
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", 8123))
    user = os.getenv("CLICKHOUSE_USER")
    password = os.getenv("CLICKHOUSE_PASSWORD", "")
    
    # Audit logger info
    audit_user = os.getenv("AUDIT_LOGGER_USER")
    audit_pass = os.getenv("AUDIT_LOGGER_PASSWORD")
    
    if not audit_user or not audit_pass:
        print("Error: AUDIT_LOGGER_USER or AUDIT_LOGGER_PASSWORD not set in environment.")
        return

    print(f"Connecting to ClickHouse at {host}:{port} as {user}...")
    try:
        client = clickhouse_connect.get_client(host=host, port=port, username=user, password=password)
    except Exception as e:
        print(f"Failed to connect to ClickHouse: {e}")
        print("Tip: If running outside Docker, ensure ports are forwarded or CLICKHOUSE_HOST=localhost.")
        return
    
    sql_path = "scripts/setup_restricted_users.sql"
    if not os.path.exists(sql_path):
        print(f"Error: {sql_path} not found.")
        return

    with open(sql_path, "r") as f:
        sql = f.read()
    
    # Perform variable interpolation
    sql = sql.replace("${AUDIT_LOGGER_USER}", audit_user)
    sql = sql.replace("${AUDIT_LOGGER_PASSWORD}", audit_pass)
    
    print(f"Applying SQL for user: {audit_user}...")
    
    # Split by semicolon and execute
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    
    success_count = 0
    for stmt in statements:
        try:
            # Skip comments
            if not stmt.startswith("--"):
                client.command(stmt)
                success_count += 1
        except Exception as e:
            print(f"Error executing statement: {stmt[:100]}...\nReason: {e}")

    print(f"Successfully executed {success_count}/{len(statements)} statements.")

if __name__ == "__main__":
    target_env = sys.argv[1] if len(sys.argv) > 1 else ".env.dev"
    apply_sql(target_env)
