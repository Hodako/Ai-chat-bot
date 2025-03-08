import sys
import os

# Add the directory containing your main.py to the Python path
# Adjust the path if your main.py is in a different directory
sys.path.insert(0, os.path.dirname(__file__))

# Import your main application
from main import app as application

# For debugging purposes
if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple('localhost', 5000, application, use_debugger=True, use_reloader=True)p
