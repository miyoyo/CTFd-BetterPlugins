from werkzeug.wrappers import Response
from CTFd.models import Users
.
class OAuthProvider:
    def canLogin(self) -> bool:
        """
        Verifies if this login method is enabled or not
        """
        raise NotImplementedError()
    
    def onLogin(self) -> Response:
        """
        Prepares the redirect URL that the user will be sent to
        """
        raise NotImplementedError()
    
    def onRedirect(self, code) -> Users:
        """
        Called when the oauth callback is accessed, convert the response into an user.
        """
        raise NotImplementedError()
    
    def onDelete(self, user) -> bool:
        """
        Callback to clean up when the user is deleted
        """
        raise NotImplementedError()

class OAuthException(Exception):
    pass