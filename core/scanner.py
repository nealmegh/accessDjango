import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import copy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.by import By

import uuid
from playwright.sync_api import sync_playwright
from .rule_metadata import RULE_METADATA
from .llm_suggester import suggest_fix_with_llm
from django.conf import settings


# def fetch_html(url):
#     try:
#         response = requests.get(url, timeout=10)
#         response.raise_for_status()
#         return response.text
#     except Exception:
#         return None

def fetch_html(url):
    from playwright.sync_api import sync_playwright
    import sys
    import io

    # Patch sys.stderr for Gunicorn compatibility
    if not hasattr(sys.stderr, "fileno"):
        sys.stderr = io.StringIO()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-web-security"
                ]
            )

            context = browser.new_context(
                java_script_enabled=True,
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
            )

            page = context.new_page()

            # Inject bot evasion script
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
            """)

            # 🔍 Logging handlers
            page.on("console", lambda msg: print(f"[Console] {msg.type.upper()}: {msg.text}"))
            page.on("requestfailed", lambda req: print(f"[Request FAILED] {req.url}"))
            page.on("pageerror", lambda err: print(f"[Page ERROR] {err}"))

            print(f"[INFO] Visiting {url}")
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(8000)

            # Optional re-evaluation of inline scripts
            page.evaluate("""
                document.querySelectorAll('script').forEach(s => {
                    if (s.innerText.includes('popupclick') || s.innerText.includes('countdown')) {
                        try { eval(s.innerText); }
                        catch (e) { console.warn('Eval failed:', e); }
                    }
                });
            """)

            page.evaluate("""
                try {
                    if (typeof countdown === 'function') {
                        countdown();
                        setInterval(countdown, 1000);
                    }
                } catch (e) {
                    console.log("Countdown not found", e);
                }
            """)

            html = page.evaluate("document.documentElement.outerHTML")

            # 📸 Save screenshot for verification
            page.screenshot(path="/tmp/page.png", full_page=True)

            browser.close()
            return html

    except Exception as e:
        print(f"[Playwright ERROR] {e}")
        return None


# def check_alt_text(soup):
#     issues = []
#     for img in soup.find_all('img'):
#         if not img.get('alt'):
#             original_html = str(img)
#
#             # ✅ Fix: use Python's copy module
#             img_copy = copy.copy(img)
#             img_copy['alt'] = 'Description of the image'
#             fixed_html = str(img_copy)
#
#             issues.append({
#                 'type': 'Missing Alt Text',
#                 'element': original_html,
#                 'suggestion': fixed_html
#             })
#     return issues

def check_alt_text(soup):
    issues = []
    for img in soup.find_all('img'):
        if not img.get('alt'):
            original_html = str(img)
            img_copy = copy.copy(img)
            img_copy['alt'] = 'Description of the image'
            fixed_html = str(img_copy)

            ai_fix = None
            if getattr(settings, "USE_LLM", False):
                try:
                    ai_fix = suggest_fix_with_llm("Image is missing alt text", original_html)
                except Exception as e:
                    ai_fix = f"LLM suggestion failed: {e}"

            issues.append({
                'type': 'Missing Alt Text',
                'element': original_html,
                'suggestion': fixed_html,
                'ai_suggestion': ai_fix
            })
    return issues

def check_unordered_list_structure(soup):
    issues = []
    for el in soup.find_all(['div', 'p']):
        text = el.get_text().strip()
        if any(bullet in text for bullet in ['•', '-', '*']):
            if not el.find('ul') and not el.find('li'):
                issues.append({
                    'type': 'Possible Improper List',
                    'element': str(el),
                    'suggestion': 'Use semantic <ul> and <li> tags for lists.'
                })
    return issues

def extract_hex(style, key):
    match = re.search(f'{key}\s*:\s*(#[0-9a-fA-F]{{3,6}})', style)
    return match.group(1) if match else None

def check_color_contrast(soup):
    issues = []
    for el in soup.find_all(style=True):
        style = el['style']
        fg = extract_hex(style, 'color')
        bg = extract_hex(style, 'background-color')

        if fg and bg:
            try:
                fg_rgb = hex_to_rgb(fg)
                bg_rgb = hex_to_rgb(bg)
                ratio = contrast_ratio(fg_rgb, bg_rgb)
                if ratio < 4.5:
                    issues.append({
                        'type': 'Low Color Contrast',
                        'element': str(el),
                        'suggestion': f'Contrast ratio is {ratio}:1 (WCAG AA requires 4.5:1). Improve contrast between {fg} and {bg}.'
                    })
            except Exception:
                continue
    return issues

def run_accessibility_scan(url):
    html = fetch_html(url)
    if not html:
        return {'error': 'Failed to fetch the URL or invalid content'}

    soup = BeautifulSoup(html, 'html.parser')

    results = (
        check_alt_text(soup) +
        check_unordered_list_structure(soup) +
        check_color_contrast(soup)
    )

    # Count by type
    by_type = {}
    for r in results:
        key = r['type']
        by_type[key] = by_type.get(key, 0) + 1

    summary = {
        'total_issues': len(results),
        'by_type': by_type,
        'total_structural': len(soup.find_all(['header', 'footer', 'nav', 'section', 'article', 'ul', 'li'])),
        'total_aria': len(soup.find_all(attrs={"aria-label": True}))
    }

    return {
        'summary': summary,
        'details': results
    }


# def run_accessibility_scan_with_dom_capture(url):
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         context = browser.new_context()
#         page = context.new_page()
#         page.goto(url, wait_until="load")
#         # page.wait_for_timeout(5000)
#
#         # Inject axe-core
#         page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
#         results = page.evaluate("""async () => await axe.run(document, {
#             runOnly: {
#                 type: 'rule',
#                 values: ['color-contrast', 'image-alt', 'list']
#             }
#         })""")
#
#         # Add issue annotations
#         for issue in results['violations']:
#             for node in issue['nodes']:
#                 for target in node['target']:
#                     try:
#                         issue_id = issue['id'].replace('"', '').replace("'", "")
#                         js = f"""
#                         (el) => {{
#                             el.setAttribute("data-issue", "{issue_id}");
#                             el.classList.add("access-issue");
#                         }}
#                         """
#                         page.eval_on_selector(target, js)
#                     except:
#                         continue
#
#         # Inject styles for annotations
#         highlight_css = """
#         .access-issue { outline: 3px dashed red !important; position: relative; }
#         .access-issue::after {
#             content: attr(data-issue);
#             position: absolute;
#             background: red;
#             color: white;
#             font-size: 12px;
#             padding: 2px 4px;
#             top: -10px;
#             right: 0;
#             z-index: 9999;
#         }
#         """
#         page.add_style_tag(content=highlight_css)
#
#         # Get the updated DOM after JS execution
#         final_html = page.evaluate("document.documentElement.outerHTML")
#
#         # Fix broken CSS and script paths to absolute URLs
#         soup = BeautifulSoup(final_html, 'html.parser')
#         for tag in soup.find_all(['link', 'script', 'img']):
#             attr = 'href' if tag.name == 'link' else 'src'
#             if tag.has_attr(attr):
#                 tag[attr] = urljoin(url, tag[attr])
#         final_html = str(soup)
#
#         # Build a basic summary
#         summary = {
#             'total_issues': sum(len(v['nodes']) for v in results['violations']),
#             'by_type': {v['id']: len(v['nodes']) for v in results['violations']},
#             'total_structural': final_html.count('<ul'),
#             'total_aria': final_html.count('aria-')
#         }
#
#         # Close browser
#         browser.close()
#
#         scan_id = str(uuid.uuid4())
#         return {"summary": summary, "details": results['violations']}, final_html, scan_id

# Utility functions
#
# def run_accessibility_scan_with_dom_capture(url):
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         context = browser.new_context()
#         page = context.new_page()
#         page.goto(url, wait_until="load")
#
#         # Inject axe-core and run
#         page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
#         axe_results = page.evaluate("""async () => await axe.run(document, {
#             runOnly: {
#                 type: 'rule',
#                 values: ['color-contrast', 'image-alt', 'list']
#             }
#         })""")
#
#         # Inject issue markers into DOM
#         for issue in axe_results['violations']:
#             for node in issue['nodes']:
#                 for target in node['target']:
#                     try:
#                         issue_id = issue['id'].replace('"', '').replace("'", "")
#                         js = f"""
#                         (el) => {{
#                             el.setAttribute("data-issue", "{issue_id}");
#                             el.classList.add("access-issue");
#                         }}
#                         """
#                         page.eval_on_selector(target, js)
#                     except:
#                         continue
#
#         # Style the highlights
#         page.add_style_tag(content="""
#             .access-issue { outline: 3px dashed red !important; position: relative; }
#             .access-issue::after {
#                 content: attr(data-issue);
#                 position: absolute;
#                 background: red;
#                 color: white;
#                 font-size: 12px;
#                 padding: 2px 4px;
#                 top: -10px;
#                 right: 0;
#                 z-index: 9999;
#             }
#         """)
#
#         # Get updated HTML
#         final_html = page.evaluate("document.documentElement.outerHTML")
#
#         # ✅ Now parse it with BeautifulSoup and apply custom checks
#         soup = BeautifulSoup(final_html, 'html.parser')
#         # from .scanner import check_alt_text, check_color_contrast, check_unordered_list_structure
#
#         static_results = (
#             check_alt_text(soup) +
#             check_unordered_list_structure(soup) +
#             check_color_contrast(soup)
#         )
#
#         # Rewrite relative URLs in DOM snapshot
#         for tag in soup.find_all(['link', 'script', 'img']):
#             attr = 'href' if tag.name == 'link' else 'src'
#             if tag.has_attr(attr):
#                 tag[attr] = urljoin(url, tag[attr])
#         final_html = str(soup)
#
#         # Count issues
#         all_results = static_results
#         for issue in all_results:
#             metadata = RULE_METADATA.get(issue["type"])
#             if metadata:
#                 issue["why"] = metadata["why"]
#                 issue["wcag"] = metadata["wcag"]
#
#         by_type = {}
#         for r in all_results:
#             key = r['type']
#             by_type[key] = by_type.get(key, 0) + 1
#
#         summary = {
#             'total_issues': len(all_results),
#             'by_type': by_type,
#             'total_structural': len(soup.find_all(['header', 'footer', 'nav', 'section', 'article', 'ul', 'li'])),
#             'total_aria': len(soup.find_all(attrs={"aria-label": True}))
#         }
#
#         browser.close()
#         scan_id = str(uuid.uuid4())
#
#         return {"summary": summary, "details": all_results}, final_html, scan_id


def run_accessibility_scan_with_dom_capture(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="load")

        # Grab JS-rendered DOM
        final_html = page.evaluate("document.documentElement.outerHTML")
        soup = BeautifulSoup(final_html, 'html.parser')

        # Run static accessibility checks
        static_results = (
            check_alt_text(soup) +
            check_unordered_list_structure(soup) +
            check_color_contrast(soup)
        )

        # Inject data-issue markers
        for issue in static_results:
            try:
                html_str = issue["element"]
                issue_id = issue["type"].lower().replace(" ", "-")
                match = soup.find(lambda tag: str(tag).strip() == html_str.strip())
                if match:
                    match['data-issue'] = issue_id
                    match['class'] = match.get('class', []) + ['access-issue']
            except Exception:
                continue

        # Inject per-type CSS for highlights
        # style_tag = soup.new_tag("style")
        highlight_css = """
        .access-issue {
          outline: 3px dashed #dc3545 !important;
          position: relative;
        }

        .access-issue::after {
          content: attr(data-issue);
          position: absolute;
          font-size: 12px;
          padding: 2px 6px;
          border-radius: 4px;
          top: -10px;
          right: 0;
          z-index: 9999;
          font-family: sans-serif;
          white-space: nowrap;
          color: #fff;
          background-color: #dc3545;
        }

        /* 🟠 Missing Alt Text */
        [data-issue="missing-alt-text"] {
          outline-color: red !important;
        }
        [data-issue="missing-alt-text"]::after {
          background-color: red;
        }

        /* 🔴 Low Color Contrast */
        [data-issue="low-color-contrast"] {
          outline-color: orange !important;
        }
        [data-issue="low-color-contrast"]::after {
          background-color: orange;
        }

        /* 🔵 Improper List */
        [data-issue="possible-improper-list"] {
          outline-color: blue !important;
        }
        [data-issue="possible-improper-list"]::after {
          background-color: blue;
        }
        """

        # # Inject into <head>
        # if soup.head:
        #     soup.head.append(style_tag)
        # else:
        #     head_tag = soup.new_tag("head")
        #     head_tag.append(style_tag)
        #     soup.insert(0, head_tag)

        # Finalize HTML
        # final_html = str(soup)

        page.add_style_tag(content=highlight_css)

        # 3. Inject markers for static results via JS
        for idx, issue in enumerate(static_results):
            issue_id = issue["type"].lower().replace(" ", "-")

            # Parse element snippet with BeautifulSoup to find key attrs
            snippet_soup = BeautifulSoup(issue["element"], 'html.parser')
            el = snippet_soup.find()  # get first tag

            if not el:
                continue

            # Build JS selector string, e.g., for img by src
            if el.name == 'img' and el.has_attr('src'):
                src = el['src'].replace('"', '\\"')
                js = f"""
                (() => {{
                    const matches = Array.from(document.querySelectorAll('img[src="{src}"]'));
                    matches.forEach(el => {{
                        el.setAttribute('data-issue', '{issue_id}');
                        el.classList.add('access-issue');
                    }});
                }})();
                """
            else:
                # fallback: try to find by tag + text content
                text = el.get_text().strip().replace('"', '\\"')
                tag = el.name
                js = f"""
                (() => {{
                    const matches = Array.from(document.querySelectorAll('{tag}')).filter(el => el.textContent.trim() === "{text}");
                    matches.forEach(el => {{
                        el.setAttribute('data-issue', '{issue_id}');
                        el.classList.add('access-issue');
                    }});
                }})();
                """

            try:
                page.evaluate(js)
            except Exception as e:
                print(f"Failed to inject marker for issue {idx}: {e}")

        # Get the updated DOM after JS execution
        final_html = page.evaluate("document.documentElement.outerHTML")

        # Fix broken CSS and script paths to absolute URLs
        soup = BeautifulSoup(final_html, 'html.parser')
        for tag in soup.find_all(['link', 'script', 'img']):
            attr = 'href' if tag.name == 'link' else 'src'
            if tag.has_attr(attr):
                tag[attr] = urljoin(url, tag[attr])
        final_html = str(soup)

        # Attach rule metadata
        for issue in static_results:
            metadata = RULE_METADATA.get(issue["type"])
            if metadata:
                issue["why"] = metadata["why"]
                issue["wcag"] = metadata["wcag"]

        # Build summary
        all_results = static_results
        by_type = {}
        for r in all_results:
            key = r['type']
            by_type[key] = by_type.get(key, 0) + 1

        summary = {
            'total_issues': len(all_results),
            'by_type': by_type,
            'total_structural': len(soup.find_all(['header', 'footer', 'nav', 'section', 'article', 'ul', 'li'])),
            'total_aria': len(soup.find_all(attrs={"aria-label": True}))
        }

        browser.close()
        scan_id = str(uuid.uuid4())

        return {"summary": summary, "details": all_results}, final_html, scan_id


def hex_to_rgb(hex_color):
    hex_color = hex_color.strip().lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return r, g, b

def luminance(r, g, b):
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r_lum, g_lum, b_lum = map(channel, (r, g, b))
    return 0.2126 * r_lum + 0.7152 * g_lum + 0.0722 * b_lum

def contrast_ratio(fg_rgb, bg_rgb):
    L1 = luminance(*fg_rgb)
    L2 = luminance(*bg_rgb)
    return round((max(L1, L2) + 0.05) / (min(L1, L2) + 0.05), 2)

