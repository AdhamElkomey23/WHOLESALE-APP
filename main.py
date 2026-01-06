from app import app

# Vercel requires the app to be exposed at module level
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
