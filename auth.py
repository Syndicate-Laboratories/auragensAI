import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import redirect, session, url_for

load_dotenv()

oauth = OAuth()
auth0 = oauth.register(
    'auth0',
    client_id=env.get('AUTH0_CLIENT_ID'),
    client_secret=env.get('AUTH0_CLIENT_SECRET'),
    api_base_url=f'https://{env.get("AUTH0_DOMAIN")}',
    access_token_url=f'https://{env.get("AUTH0_DOMAIN")}/oauth/token',
    authorize_url=f'https://{env.get("AUTH0_DOMAIN")}/authorize',
    client_kwargs={
        'scope': 'openid profile email',
        'response_type': 'code',
        'audience': f'https://{env.get("AUTH0_DOMAIN")}/userinfo'
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
) 