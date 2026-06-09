import re

with open("backend/app/services/sandbox.py", "r") as f:
    content = f.read()

search = """        if self.mock_mode:
            logger.info(f"[SIMULATOR] Executing Kali command: {' '.join(command)}")
            # Custom mock outputs for testing
            cmd_str = " ".join(command)
            if "nmap" in cmd_str:
                return 0, "Host: 172.20.0.3 (fc-target)\\nPORT     STATE SERVICE\\n8000/tcp open  http\\n"
            elif "sqlmap" in cmd_str:
                return 0, "[INFO] POST parameter 'username' is vulnerable to SQL injection (DBMS: SQLite)"
            elif "nuclei" in cmd_str:
                return 0, "[CVE-2021-44228] Critical Apache Log4j RCE vulnerability detected"
            elif "curl" in cmd_str:
                return 0, "HTTP/1.1 200 OK\\nServer: BaseHTTP"
            return 0, f"Simulated output for: {cmd_str}\""""

replace = """        if self.mock_mode:
            logger.warning(f"Simulated executing Kali command has been disabled to preserve demo integrity. Tool unavailable: {' '.join(command)}")
            return 1, "Tool execution unavailable." """

if search in content:
    content = content.replace(search, replace)
    with open("backend/app/services/sandbox.py", "w") as f:
        f.write(content)
    print("Patched sandbox.py for simulator command execution")
else:
    print("Search string not found in sandbox.py")
