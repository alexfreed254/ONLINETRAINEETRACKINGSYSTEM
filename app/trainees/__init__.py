from flask import Blueprint
trainees = Blueprint('trainees', __name__)
from app.trainees import routes
