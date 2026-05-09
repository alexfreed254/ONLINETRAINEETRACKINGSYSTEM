from flask import Blueprint
trainee_dash = Blueprint("trainee_dash", __name__)
from app.trainee_dash import routes