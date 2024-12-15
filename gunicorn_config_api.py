# gunicorn_config_api.py
bind = "0.0.0.0:5002"
workers = 2

# Logging configuration
accesslog = "/Users/squall/Logs/AeonIntelligence/api/access.log"  # Path to access log file
errorlog = "/Users/squall/Logs/AeonIntelligence/api/error.log"    # Path to error log file
loglevel = "info"                  # Log level (debug, info, warning, error, critical)