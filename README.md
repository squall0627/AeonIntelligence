# Run the app on gunicorn
pipenv run gunicorn -c gunicorn_config_api.py api.translator_app:translator_app
pipenv run streamlit run app.py


# Run the gunicorn as daemon
## Load the plist file
launchctl load ~/Library/LaunchAgents/com.aeon.intelligence.gunicorn.plist
## Start the service
launchctl start com.aeon.intelligence.gunicorn
## Stop the service
launchctl stop com.aeon.intelligence.gunicorn
## Verify the Service
launchctl list | grep gunicorn


# Install nginx
## on linux
sudo apt-get install nginx
## on mac
brew install nginx

# Verify nginx is installed
nginx -v

# Start nginx
## on linux
sudo systemctl start nginx
## on mac
brew services start nginx