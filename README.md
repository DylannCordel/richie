# Installing FUN CMS

This document aims to list all needed steps to have a working `FUN CMS` installation.


## Installing a fresh server

### Version

You need a `Ubuntu 16.04 Xenial Xerus` (the latest LTS version) fresh installation.

If you are using another operating system or distribution, you can use [`Vagrant`](https://docs.vagrantup.com/v2/getting-started/index.html) to get a running Ubuntu 16.04 server in seconds.


### System update

Be sure to have fresh packages on the server (kernel, libc, ssl patches...):
post
```sh
sudo apt-get -y update
sudo apt-get -y dist-upgrade
```


## Database part

For a start, we will be using the sqllite3 database.


## Application part

### Python and other requirements

We use `Python 3.5` which is the one installed by default in `Ubuntu 16.04`.


### The virtualenv

We choose to run our application in a virtual environment and manage our Python dependencies using `pipenv` which you can install with pip:

```sh
pip install pipenv
```

You can now open a new shell with the virtualenv activated:

```sh
pipenv shell
```

Note that all the required Python packages are automatically installed the first time you run this command.


### Settings

You can create a settings file for your personal use in the project's settings folder.

If you name it `local.py`, it will not be commited to the project and its content will automatically be applied as overrides in all the other settings files.

```sh
tee fun_portal/settings/local.py << 'EOF'
# your customizations here:
# ...
EOF
```


### Run server

Make sure your database is up-to-date before running the application the first time and after each modification to your models:

```sh
python manage.py migrate
```


You should now be able to start Django and view the site at [localhost:8000](http://localhost:8000)

```sh
python manage.py runserver
```