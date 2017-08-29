# VMsAreUs

| maintainer | version |
|:-----------|:--------|
| Dave Green | initial |

## Overview  

This application is for the creation and management of vms required during
the development process.  Anyone with a JIRA account should be able to log in
and request a VM created using one of the pre-defined templates provided by DevOps.  

* [App construction details](../notes.md#history-of-app-creation)
* [Web server config information](../notes.md#web-server-configuration)
* [VMware integration](../notes.md#vmware-details-for-creating-systems)

    
## History of app creation
1. create virtualenv with python 3.5 base
2. setup cookiecutter and create initial template
    ```
    pip install coookiecutter
    cookiecutter https://github.com/pydanny/cookiecutter-django
    ```
    cookie cutter and django template docs: 
    * [cookiecutter](https://github.com/audreyr/cookiecutter)
    * [django template](https://github.com/pydanny/cookiecutter-django)
    
3. setup required python modules
    ```
    pip install -r requirements/local.txt
    ```

4. run a database either in docker or in os as a service

    ```
    docker run --name local-postgres9.3.6 -p 5432:5432 -e POSTGRES_PASSWORD=??????? -d  postgres:9.3.6
     
    psql -h localhost -p 5432  -U postgres --password
    
    create role vmsareus with CREATEDB LOGIN PASSWORD 'mypassword';
    create database vmsareus;
    ```
5. setup redis
    ```
    docker run --name some-redis -p 6379:6379 -d redis
    ```
    
6. let django create the database schema and create system admin account

    ```
    python manage.py makemigrations
    python manage.py migrate
    
    python manage.py createsuperuser
    
    ```  

7. run a local celery worker if on development machine
    ```
    celery -A vmsareus.taskapp worker -l info
    ```
    
## VMWare details for creating Systems

VMWare has a body of code in Python with examples for coding against VMware rest endpoints.
* [python examples](https://github.com/vmware/pyvmomi)
* [api docs](https://vdc-download.vmware.com/vmwb-repository/dcr-public/6b586ed2-655c-49d9-9029-bc416323cb22/fa0b429a-a695-4c11-b7d2-2cbc284049dc/doc/index.html)

Combining these examples with some of our own process, we created routines that can create
a new development VM on demand with a given number of Cores and Memory.

## How are the VMs configured for "development"?
 
http://devhelp.lebanon.cd-adapco.com/secure/attachment/10140/setupws.sh

## Web Server Configuration

I found [these instructions](https://www.digitalocean.com/community/tutorials/how-to-serve-django-applications-with-apache-and-mod_wsgi-on-centos-7) useful in setting up my app server

1. install  virtualenv
    ```command
    curl -O https://pypi.python.org/packages/source/v/virtualenv/virtualenv-15.0.0.tar.gz
    tar xvfz virtualenv-15.0.0.tar.gz
    cd virtualenv-15.0.0
    sudo python setup.py install
    ```
2. install redis
    ```command
    sudo yum install redis
    sudo systemctl start redis
    sudo systemctl enable redis
    ```
    
3. install postgres
    ```
    yum install postgresql-server
    postgresql-setup initdb
    sudo systemctl enable postgresql.service
    sudo systemctl start postgresql.service
    ```

4. login as postgres and set up db

    ```postgresql
    # sudo su - postgres
    # psql 
    create role vmsareus with CREATEDB LOGIN PASSWORD 'chunkybacon';
    create database vmsareus;
    ```

    by default, postgres is only going to listen to local unix socket connections.  to enable network connections, you must make the following edit to file:  
    ``` /var/lib/pgsql/data/postgresql.conf ```
   
    ```
    listen_addresses = '*'          # what IP address(es) to listen on;
    ```
    then you can control who can connect by editing ```/var/lib/pgsql/data/pg_hba.conf```

    ```
    # "local" is for Unix domain socket connections only
    local vmsareus vmsareus trust
    
    local all postgres ident
    host vmsareus vmsareus 0.0.0.0 0.0.0.0 md5
    ```

5. setup apache server
    ```commandline
    yum install httpd mod_wsgi
    sudo setenforce 0
    sudo systemctl start httpd
    sudo systemctl enable httpd
    ```

6. setup app deployment directories:
    ```
    mkdir 
    ```
 
7. create virtualenv for the project
    ```
    cd /var/app/current 
    virtualenv vmsareus_env
    ```
8.  checkout code into /var/app/current/<project>

9. edit ```/etc/httpd/conf.d/django.conf``` to contain:

    ```
    Alias /static /var/app/current/vmsareus/vmsareus/static
    <Directory "/var/app/current/vmsareus/vmsareus/static">
        Require all granted
    </Directory>
    
    <Directory "/var/app/current/vmsareus/config">
        <Files "wsgi.py">
            Require all granted
        </Files>
    </Directory>
    
    WSGIDaemonProcess vmsareus python-path=/var/app/current/vmsareus:/var/app/current/vmsareus_env/lib/python2.7/site-packages
    WSGIProcessGroup vmsareus
    WSGIScriptAlias / /var/app/current/vmsareus/config/wsgi.py

10. daemonize celery
    1. get DEFAULT init.d script
        ```
        sudo wget https://raw.githubusercontent.com/celery/celery/master/extra/generic-init.d/celeryd
        chmod 755 /etc/init.d/celeryd
        ```
    2. create the file /etc/init.d
        ```
        CELERY_BIN="/var/app/current/vmsareus_env/bin/celery"

        # App instance to use
        CELERY_APP="vmsareus.taskapp"
        
        # Where to chdir at start.
        CELERYD_CHDIR="/var/app/current/vmsareus"
        
        # Extra command-line arguments to the worker
        CELERYD_OPTS="--concurrency=8"
        
        # %n will be replaced with the first part of the nodename.
        CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
        CELERYD_PID_FILE="/var/run/celery/%n.pid"
        
        # Workers should run as an unprivileged user.
        #   You need to create this user manually (or you can choose
        #   a user/group combination that already exists (e.g., nobody).
        CELERYD_USER="davidg"
        CELERYD_GROUP="davidg"
        
        # If enabled pid and log directories will be created if missing,
        # and owned by the userid/group configured.
        CELERY_CREATE_DIRS=1
        
        export SECRET_KEY="foobar"
        export MY_SPECIAL_VARIABLE="my production variable"
        export MY_OTHERSPECIAL_VARIABLE="my other production variable"
        ```
        
    3. test the script
        ```
        sudo /etc/init.d/celeryd start
        sudo /etc/init.d/celeryd status
        sudo /etc/init.d/celeryd stop
        
        # if it is good to go
        sudo systemctl enable celeryd
        ```
