import os
import string
import random
import base64
import importlib

from typing import Annotated
from datetime import datetime, timedelta, timezone

import fastapi.openapi.utils
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi_pagination import add_pagination
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.responses import RedirectResponse, Response

app = FastAPI(title='Wine Cellar API',
              description='API to access your wine cellar data',
              version="0.1.0")#,
              # docs_url=None, redoc_url=None, openapi_url=f"/drink_your_wine")
add_pagination(app)


@app.get('/')
async def root():
    return {"message": "Welcome to the wine API."}

