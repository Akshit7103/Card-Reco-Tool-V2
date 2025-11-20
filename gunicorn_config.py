# Gunicorn configuration for Render deployment
import os

# Bind to the PORT environment variable
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Worker configuration
workers = 1  # Free tier: 1 worker to save memory
worker_class = "sync"
worker_connections = 10

# Timeout configuration (increased for long processing)
timeout = 300  # 5 minutes (was 30 seconds)
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Process naming
proc_name = "card-reco-tool"

# Preload app for memory efficiency
preload_app = False  # Set to False to avoid memory issues on free tier
