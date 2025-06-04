import requests

def suggest_fix_with_llm(issue_description, html_snippet):
    prompt = f"""
You are an expert in web accessibility and HTML. The following HTML has an issue.

Issue: {issue_description}
HTML:
{html_snippet}

Explain the problem briefly and suggest a corrected version of the HTML.
Respond in this format:
---
Reason: <why it's a problem>
Fix: <fixed HTML code>
---
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }
        )
        result = response.json().get("response", "")
        return result.strip()
    except Exception as e:
        return f"LLM error: {e}"
