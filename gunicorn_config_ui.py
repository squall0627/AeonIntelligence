# gunicorn_config_api.py
bind = "0.0.0.0:8000"
workers = 1

# Logging configuration
accesslog = "/Users/squall/Logs/AeonIntelligence/ui/access.log"  # Path to access log file
errorlog = "/Users/squall/Logs/AeonIntelligence/ui/error.log"    # Path to error log file
loglevel = "info"                  # Log level (debug, info, warning, error, critical)