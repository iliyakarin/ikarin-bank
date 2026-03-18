import os
import sys
import clickhouse_connect
from dotenv import load_dotenv

def render_xml_config():
    """Renders setup-admin.xml from template if env vars are present."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # In container: /app/scripts/ -> /app/init-db/ is ../init-db/
    # On host: backend/scripts/ -> init-db/ is ../../init-db/
    
    potential_paths = [
        os.path.join(script_dir, "..", "init-db", "setup-admin.xml.template"),
        os.path.join(script_dir, "..", "..", "init-db", "setup-admin.xml.template")
    ]
    
    template_path = next((p for p in potential_paths if os.path.exists(p)), None)
    if not template_path:
        return

    output_path = template_path.replace(".template", "")
    
    admin_user = os.getenv("CLICKHOUSE_ADMIN_USER")
    admin_pass = os.getenv("CLICKHOUSE_ADMIN_PASSWORD")
    
    if not admin_user or not admin_pass:
        print("Error: CLICKHOUSE_ADMIN_USER and CLICKHOUSE_ADMIN_PASSWORD must be set.")
        return

    print(f"Rendering {output_path} from template...")
    with open(template_path, "r") as f:
        content = f.read()
    
    content = content.replace("${CLICKHOUSE_ADMIN_USER}", admin_user)
    content = content.replace("${CLICKHOUSE_ADMIN_PASSWORD}", admin_pass)
    
    with open(output_path, "w") as f:
        f.write(content)

def apply_sql(env_file_path=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if not env_file_path:
        if not os.getenv("CLICKHOUSE_HOST"):
            potential_root_env = os.path.join(script_dir, "..", "..", ".env.dev")
            if os.path.exists(potential_root_env):
                env_file_path = potential_root_env
                load_dotenv(env_file_path)
    else:
        if os.path.exists(env_file_path):
            load_dotenv(env_file_path)
    
    # Try to render XML before connecting
    render_xml_config()

    host = os.getenv("CLICKHOUSE_HOST")
    port_str = os.getenv("CLICKHOUSE_PORT")
    
    if not host or not port_str:
        print("Error: CLICKHOUSE_HOST and CLICKHOUSE_PORT must be set.")
        return
    port = int(port_str)
    
    # Try admin credentials (required now, no fallbacks)
    admin_user = os.getenv("CLICKHOUSE_ADMIN_USER")
    admin_pass = os.getenv("CLICKHOUSE_ADMIN_PASSWORD")
    
    if not admin_user or not admin_pass:
        print("Error: CLICKHOUSE_ADMIN_USER and CLICKHOUSE_ADMIN_PASSWORD must be set.")
        return
    
    # Audit logger info
    audit_user = os.getenv("AUDIT_LOGGER_USER")
    audit_pass = os.getenv("AUDIT_LOGGER_PASSWORD")
    
    if not audit_user or not audit_pass:
        print("Error: AUDIT_LOGGER_USER or AUDIT_LOGGER_PASSWORD not set in environment.")
        return

    print(f"Connecting to ClickHouse at {host}:{port} as admin '{admin_user}'...")
    try:
        client = clickhouse_connect.get_client(host=host, port=port, username=admin_user, password=admin_pass)
    except Exception as e:
        print(f"Failed to connect as admin: {e}")
        # Attempt fallback to primary CLICKHOUSE_USER if specifically configured
        user = os.getenv("CLICKHOUSE_USER")
        password = os.getenv("CLICKHOUSE_PASSWORD")
        if user and password:
            print(f"Attempting fallback to CLICKHOUSE_USER: {user}...")
            try:
                client = clickhouse_connect.get_client(host=host, port=port, username=user, password=password)
            except Exception as e2:
                print(f"Final connection attempt failed: {e2}")
                return
        else:
            print(f"Connection failed and no CLICKHOUSE_USER/PASSWORD fallback configured: {e}")
            return
    
    sql_path = os.path.join(script_dir, "setup_restricted_users.sql")
    if not os.path.exists(sql_path):
        print(f"Error: {sql_path} not found.")
        return

    with open(sql_path, "r") as f:
        sql = f.read()
    
    sql = sql.replace("${AUDIT_LOGGER_USER}", audit_user)
    sql = sql.replace("${AUDIT_LOGGER_PASSWORD}", audit_pass)
    
    print(f"Applying SQL for user: {audit_user}...")
    
    # Split by semicolon and execute
    raw_statements = [s.strip() for s in sql.split(";") if s.strip()]
    
    success_count = 0
    total_run = 0
    for stmt in raw_statements:
        # Strip all lines starting with --
        lines = stmt.split("\n")
        clean_lines = [l for l in lines if not l.strip().startswith("--")]
        clean_stmt = "\n".join(clean_lines).strip()
        
        if clean_stmt:
            total_run += 1
            try:
                client.command(clean_stmt)
                success_count += 1
                print(f"Success: {clean_stmt.splitlines()[0][:50]}...")
            except Exception as e:
                print(f"Error executing statement: {clean_stmt.splitlines()[0][:50]}...\nReason: {e}")

    print(f"Successfully executed {success_count}/{total_run} statements.")

if __name__ == "__main__":
    arg_env = sys.argv[1] if len(sys.argv) > 1 else None
    apply_sql(arg_env)
