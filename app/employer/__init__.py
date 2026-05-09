from flask import Blueprint
employer = Blueprint('employer', __name__)
from app.employer import routes
