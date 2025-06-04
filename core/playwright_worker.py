import sys
import json
from core.scanner import fetch_html

if __name__ == "__main__":
    url = sys.argv[1]
    html = fetch_html(url)
    print(json.dumps({"html": html}))
