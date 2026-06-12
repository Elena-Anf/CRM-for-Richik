from app.models.client import Client
from app.models.pet import Pet
from app.models.master import Master
from app.models.service import Service
from app.models.appointment import Appointment
from app.models.user import User
from app.models.google_calendar import GoogleCalendarSettings
from app.models.payout import MasterPayout
from app.models.breed import Breed
from app.models.global_setting import GlobalSetting

all_models = [Client, Pet, Master, Service, Appointment, User, GoogleCalendarSettings, MasterPayout, Breed, GlobalSetting]
