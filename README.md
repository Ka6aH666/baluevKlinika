
python -m venv myenv

myenv\Scripts\activate

pip install -r requirements.txt

cd ClinicBALUEV

python manage.py makemigrations

python manage.py migrate

python manage.py runserver

python manage.py createsuperuser