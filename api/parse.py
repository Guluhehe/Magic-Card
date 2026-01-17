from server import app

# Vercel serverless function entry point
def handler(request):
    return app(request.environ, lambda *args: None)
