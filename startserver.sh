gunicorn --log-level=DEBUG --bind 127.0.0.1:8019 --workers=1 deepfrost.wsgi:application --timeout=90 --error-logfile=gunicorn_deepfrost.log --capture-output

