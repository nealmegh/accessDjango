"""
WSGI config for accessTool project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import os
import sys
import io
from django.core.wsgi import get_wsgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accessTool.settings')
#
# application = get_wsgi_application()

# 🩹 Patch stderr for Playwright + Apache/mod_wsgi compatibility
if not hasattr(sys.stderr, "fileno"):
    sys.stderr = io.StringIO()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accessTool.settings')

# from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
