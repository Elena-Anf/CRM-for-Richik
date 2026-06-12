"""Passenger WSGI entry point for Timeweb hosting.
Timeweb использует Passenger для запуска Python-приложений.
Этот файл должен находиться в корне проекта.
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app

# Passenger ожидает переменную 'application'
application = app
