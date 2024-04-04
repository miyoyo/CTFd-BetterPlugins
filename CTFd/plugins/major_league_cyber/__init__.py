from flask import Flask, redirect, session, abort
from werkzeug.wrappers import Response
from CTFd.utils.plugins.oauth import OAuthProvider, OAuthException
from CTFd.utils import get_app_config, get_config
from CTFd.utils.config.visibility import registration_visible
from CTFd.utils.helpers import error_for
from CTFd.models import Users, Teams, db
from CTFd.utils.modes import TEAMS_MODE
from CTFd.cache import clear_team_session, clear_user_session
from CTFd.auth import OAUTH_PROVIDERS
import requests

def load(flask: Flask):
    OAUTH_PROVIDERS.append(MajorLeagueCyber())

class MajorLeagueCyber(OAuthProvider):
    def canLogin(self):
        return get_config("registration_visibility") == "mlc"
    
    def onDelete(self, user):
        return True
    
    def onLogin(self) -> Response:
        endpoint = (
            get_app_config("OAUTH_AUTHORIZATION_ENDPOINT")
            or get_config("oauth_authorization_endpoint")
            or "https://auth.majorleaguecyber.org/oauth/authorize"
        )

        if get_config("user_mode") == "teams":
            scope = "profile team"
        else:
            scope = "profile"

        client_id = get_app_config("OAUTH_CLIENT_ID") or get_config("oauth_client_id")

        if client_id is None:
            raise OAuthException(
                "OAuth Settings not configured. "
                "Ask your CTF administrator to configure MajorLeagueCyber integration.")
        

        redirect_url = "{endpoint}?response_type=code&client_id={client_id}&scope={scope}&state={state}".format(
            endpoint=endpoint, client_id=client_id, scope=scope, state=session["nonce"]
        )
        
        return redirect(redirect_url)

    def onRedirect(self, code) -> Users:
        url = (
            get_app_config("OAUTH_TOKEN_ENDPOINT")
            or get_config("oauth_token_endpoint")
            or "https://auth.majorleaguecyber.org/oauth/token"
        )

        client_id = get_app_config("OAUTH_CLIENT_ID") or get_config("oauth_client_id")
        client_secret = get_app_config("OAUTH_CLIENT_SECRET") or get_config(
            "oauth_client_secret"
        )
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
        }
        token_request = requests.post(url, data=data, headers=headers)

        if token_request.status_code != requests.codes.ok:
            raise OAuthException("OAuth token retrieval failure")
        
        token = token_request.json()["access_token"]
        user_url = (
            get_app_config("OAUTH_API_ENDPOINT")
            or get_config("oauth_api_endpoint")
            or "https://api.majorleaguecyber.org/user"
        )

        headers = {
            "Authorization": "Bearer " + str(token),
            "Content-type": "application/json",
        }
        api_data = requests.get(url=user_url, headers=headers).json()

        user_id = api_data["id"]
        user_name = api_data["name"]
        user_email = api_data["email"]

        user = Users.query.filter_by(email=user_email).first()
        if user is None:
            if (not registration_visible()) and (not self.canLogin()):
                raise OAuthException("User registration is not enabled")
            
            # Respect the user count limit
            num_users_limit = int(get_config("num_users", default=0))
            num_users = Users.query.filter_by(banned=False, hidden=False).count()
            if num_users_limit and num_users >= num_users_limit:
                raise OAuthException(f"Reached the maximum number of users ({num_users_limit}).")
                
            user = Users(
                name=user_name,
                email=user_email,
                oauth_id=user_id,
                verified=True,
            )
            db.session.add(user)
            db.session.commit()
                

        if get_config("user_mode") == TEAMS_MODE and user.team_id is None:
            team_id = api_data["team"]["id"]
            team_name = api_data["team"]["name"]

            team = Teams.query.filter_by(oauth_id=team_id).first()
            if team is None:
                num_teams_limit = int(get_config("num_teams", default=0))
                num_teams = Teams.query.filter_by(
                    banned=False, hidden=False
                ).count()
                if num_teams_limit and num_teams >= num_teams_limit:
                    abort(
                        403,
                        description=f"Reached the maximum number of teams ({num_teams_limit}). Please join an existing team.",
                    )

                team = Teams(name=team_name, oauth_id=team_id, captain_id=user.id)
                db.session.add(team)
                db.session.commit()
                clear_team_session(team_id=team.id)

            team_size_limit = get_config("team_size", default=0)
            if team_size_limit and len(team.members) >= team_size_limit:
                plural = "" if team_size_limit == 1 else "s"
                size_error = "Teams are limited to {limit} member{plural}.".format(
                    limit=team_size_limit, plural=plural
                )
                raise OAuthException(size_error)

            team.members.append(user)
            db.session.commit()

        if user.oauth_id is None:
            user.oauth_id = user_id
            user.verified = True
            db.session.commit()
            clear_user_session(user_id=user.id)

        return user