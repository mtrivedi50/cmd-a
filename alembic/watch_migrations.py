import logging
import subprocess
from threading import Timer

from watchfiles import watch

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# Debounce timer (in seconds)
DEBOUNCE_INTERVAL = 1.0

timer = None

def run_migrations():
    logging.info("Running `alembic upgrade head`...")
    try:
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        logging.info("Migration applied successfully:\n%s", result.stdout)
    except subprocess.CalledProcessError as e:
        logging.error("Migration failed:\n%s", e.stderr)

def debounce_run():
    global timer
    if timer:
        timer.cancel()
    timer = Timer(DEBOUNCE_INTERVAL, run_migrations)
    timer.start()


if __name__ == "__main__":
    logging.info("📡 Watching /alembic/versions for changes...")
    for changes in watch('/alembic/versions'):
        logging.info("🔄 Detected file changes: %s", changes)
        debounce_run()
