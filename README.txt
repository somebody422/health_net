# HealthNet by Salud Synergy

HealthNet is an electronic medical records system built by Salud Synergy. It
can manage an arbitrary number of patients, and can scale to handle any number
of hospitals.

## Deploying

After obtaining the code for HealthNet, deploying it is a fairly
straightforward process. Open a command prompt, go to the directory in which
you've downloaded the source code, and run the following commands.

> python manage.py makemigrations
> python manage.py migrate
> python manage.py runserver

## Creating your first admin

Once the site is running, direct your browser at the site and it will prompt
you to create an admin. Fill out the fields, and when you finish the site will
redirect you to the dashboard, logged in as this admin. You MUST create a
hospital and doctor now in that order (the buttons for which are on the
dashboard), or patients will be unable to register.

## Known bugs and disclaimers

Salud Synergy is not responsible for any outside changes made to the HealthNET
software.

Known bug: Dashboard produces an error when logged in as a superuser created
through the shell.

## Cross Team Testing Files

These are the files located in public_html/Release-2-beta/cross-team-testing:



## Test Liaison

Name:
Email:

