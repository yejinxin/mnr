#!/bin/bash 
. ~/.bashrc
workon prod
python manage.py checkapp
