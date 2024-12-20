# Run the app on gunicorn
pipenv run gunicorn -c gunicorn_config_api.py api.translator_app:translator_app

# Run the streamlit app
pipenv run streamlit run app.py


# Run the App as daemon(on Mac)
## Load the plist file
launchctl load ~/Library/LaunchAgents/com.aeon.intelligence.gunicorn.plist
launchctl load ~/Library/LaunchAgents/com.aeon.intelligence.ui.plist
## Start the service
launchctl start com.aeon.intelligence.gunicorn
launchctl start com.aeon.intelligence.ui
## Stop the service
launchctl stop com.aeon.intelligence.gunicorn
launchctl stop com.aeon.intelligence.ui
## Verify the Service
launchctl list | grep com.aeon.intelligence.gunicorn
launchctl list | grep com.aeon.intelligence.ui


# Install nginx
## on Linux
sudo apt-get install nginx
## on Mac
brew install nginx

# Verify nginx is installed
nginx -v

# Start nginx
## on Linux
sudo systemctl start nginx
## on Mac
brew services start nginx