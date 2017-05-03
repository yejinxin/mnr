#!/bin/bash 
. ~/.bash_profile
workon prod
python manage.py auto_recover
