# Cellar DB & API application
Monitor your wine/beer cellar contents.

## Contents
* General project information
* Reference to important docs
* Preliminaries concerning DB setup
* Setting up after cloning the repo


## General project information
This project lends it existence to the desire of an administrative support tool for my private wine fridge. I'm using 
it to store and age both wines and beers, but haven't been able to properly keep track of what's in there. More 
importantly, I've recently come across a few bottles that should have been downed when they were still at their peak. 
Instead, they were downed past their peak. Which is, rather obviously, an ill investment regarding the pleasure derived 
from this hobby.

This application is built to prevent exactly that and assist in keeping track of what bottles you have stored in your 
private climate controlled storage unit. The way it is designed allows for multiple users of the application (i.e., 
wine/beer owners) simultaneously leveraging the app's benefits from wherever they are. Yet, further development for 
that to happen is required. At this moment, the API service can only be run and accessed from your localhost. Updates 
hereon will follow soon!

Cheers,\
Rogier


## Reference to important docs
There's a bunch of packages that this project relies on, which deserve an honourable mention. The foremost two are 
FastAPI for the API service and MariaDB as the supporting DBMS.

On another thread, notable mentions are pytest, which is used as the testing framework, SQLlite used as a substitute to 
MariaDB within the testing scope and (quite naturally) pydantic for validating the data that flows through the API. 
Finally, JWT is used for the encoding and decoding of API access tokens.

Docs refs:
* FastAPI
  * https://fastapi.tiangolo.com
  * https://fastapi.tiangolo.com/tutorial/testing/
* MariaDB
  * https://mariadb.com
  * https://dlm.mariadb.com/2531428/Connectors/java/connector-java-3.0.8/mariadb-java-client-3.0.8.jar
* Notables
  * https://docs.pytest.org/en/7.1.x/contents.html
  * https://www.sqlite.org/index.html
  * https://docs.pydantic.dev/latest/concepts/models/
  * https://pyjwt.readthedocs.io/en/stable/index.html


## Preliminaries concerning DB setup
Create your preferred kind of virtual environment to run all your scripts in and make sure to link it to the repo in 
your IDE. Also, use the second link provided at the MariaDB refs to download the driver jar used by the python scripts 
to connect to the MariaDB DB service. The MariaDB service itself should be installed with brew by 
"brew install mariadb". The DB service can arbitrarily be started or stopped by using the "brew services start mariadb" 
and "brew services start mariadb" commands respectively.

Start the DB service and create a DB user that is specifically meant to be used by the API. Save the credentials for 
later and make sure that this user has all possible privileges as long as you're only running the service locally.

## Setting up after cloning the repo
After cloning the repo, create a 'drivers' directory on the same level as 'src' and move the previously installed 
MariaDB driver .jar file to this dir.

When scanning through the constants.py file in src/api/, you'll see that some constants are derived from a yaml file. 
Create a file called 'env.yml' directly in the 'src' directory and a 'test_env.yml' file in the 'src/tests/' directory. 
The env.yml file will actually be used by the API. The test_env.yml file is used within the scope of code tests. For 
simplicity's sake, it is advised to use rather simple user credentials for the testing scope e.g., admin:admin. 
Both of these files should contain the following information:
* DB_USER
  * The MariaDB username of your python mariadb user.
  * Should be a string.
* DB_PW
  * The MariaDB password of your python mariadb user. Its hash will be saved in the DB, not as a plain PW. This 
    password will simultaneously be used as the password for your personal API user.
  * Should be a string.
* DB_USER_NAME
  * Username of your personal API user. This username is unique for all API users (wine/beer owners).
  * Should be a string.
* JWT_KEY
  * Algorithm key for both decoding/encoding API access tokens.
  * Should be a string.
* JWT_ALGORITHM
  * The preferred encoding/decoding algorithm.
  * Should be a string.
* ACCESS_TOKEN_EXPIRATION_MIN
  * Duration in minutes of which debugging tokens are valid.
  * Should be an integer.

