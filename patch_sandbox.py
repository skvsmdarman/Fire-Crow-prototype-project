with open("backend/app/services/sandbox.py", "r") as f:
    content = f.read()

search = """        # Stop and remove containers
        for cid in (target_container_id, kali_container_id):
            if cid:
                try:
                    container = client.containers.get(cid)
                    container.stop(timeout=5)
                    container.remove(force=True)
                    logger.info(f"Removed container {cid}")
                except Exception:
                    pass

        # Remove bridge network
        if network_name:
            try:
                network = client.networks.get(network_name)
                network.remove()
                logger.info(f"Removed network {network_name}")
            except Exception:
                pass"""

replace = """        # Stop and remove containers
        for cid in (target_container_id, kali_container_id):
            if cid:
                try:
                    container = client.containers.get(cid)
                    container.stop(timeout=5)
                    container.remove(force=True)
                    logger.info(f"Removed container {cid}")
                except Exception as e:
                    logger.warning(f"Failed to cleanly remove container {cid}: {e}")

        # Remove bridge network
        if network_name:
            try:
                network = client.networks.get(network_name)
                network.remove()
                logger.info(f"Removed network {network_name}")
            except Exception as e:
                logger.warning(f"Failed to cleanly remove network {network_name}: {e}")"""

if search in content:
    content = content.replace(search, replace)
    with open("backend/app/services/sandbox.py", "w") as f:
        f.write(content)
    print("Patched sandbox.py")
else:
    print("Search string not found in sandbox.py")
