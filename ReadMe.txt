1. Install Anaconda or Miniconda:
https://conda.io/docs/user-guide/install/index.html

Short description for installing miniconda is given:

Download link for Miniconda with python 3.6.4 (64 bit):
https://repo.continuum.io/miniconda/Miniconda3-4.4.10-Linux-x86_64.sh
Download link for Miniconda with python 3.6.4 (32 bit):
https://repo.continuum.io/miniconda/Miniconda3-4.4.10-Linux-x86.sh

Run this command to start installation:
bash Miniconda3-4.4.10-Linux-x86_64.sh

2. After installation, add conda to your PATH:
export PATH="/home/USERNAME/miniconda3/bin:$PATH"

3. Clone this project:
git clone https://github.com/colonelfitz/deepfrost.git

4. Either add conda environment:
conda env create -f kappa_364_environment.yml

Or pip requirements:
pip install -r requirements.txt

In pythonanywhere, use:
pip3.6 install --user pwhich -r requirements.txt

5. Create a runner shell script startserver.sh:
gunicorn --log-level=DEBUG --bind 0.0.0.0:3000 --workers=1 deepfrost.wsgi:application --timeout=90 --error-logfile=gunicorn_deepfrost.log --capture-output

If run script is on parent url:
cd deepfrost && gunicorn --log-level=DEBUG --bind 0.0.0.0:3000 --workers=1 deepfrost.wsgi:application --timeout=90 --error-logfile=gunicorn_deepfrost.log --capture-output

Make shell file runnable:
sudo chmod u+x startserver.sh

Run project in the environment :-)


---------- More -----------
runtime.txt and Profile are used for deploying on heroku
