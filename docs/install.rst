Install
=========
running postgres inside docker:
docker run --name postgres9.6.3-alpine -p 5432:5432 -e POSTGRES_PASSWORD=mypassword -d postgres:9.6.3

then connect using command line terminal over network port
psql -h localhost -p 5432  -U postgres --password
mypassword

create role and database for app:

sql> create role myapp with CREATEDB LOGIN PASSWORD 'mypassword'
sql> create database mydatabase

don't forget to migrate and create superuser
python manage.py migrate

modified the database configuration to point to postgres install
linux:
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://vmsareus:mypassword@localhost:5432/vmsareus'),
}

home: use default?

