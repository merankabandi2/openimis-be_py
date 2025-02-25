class OauthAuditTrailMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if hasattr(request, 'auth') and request.auth:
            token = request.auth
            # For client credentials tokens with application
            if hasattr(token, 'application') and token.application.user:
                # Set the application's system user as the request user
                request.user = token.application.user
        
        return self.get_response(request)