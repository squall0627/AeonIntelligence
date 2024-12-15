# Run the app on gunicorn
pipenv run gunicorn -c gunicorn_config_api.py api.translator_app:translator_app
pipenv run gunicorn -c gunicorn_config_ui.py streamlit_wrapper:app

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