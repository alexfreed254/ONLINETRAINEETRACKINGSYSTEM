from flask import Blueprint
portfolio = Blueprint('portfolio', __name__)
from app.portfolio import routes
