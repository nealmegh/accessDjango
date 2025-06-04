# core/rule_metadata.py
RULE_METADATA = {
    "Missing Alt Text": {
        "why": "Adding descriptive alt text to images ensures that screen readers can convey the content to visually impaired users. It also helps when images fail to load, and improves SEO.",
        "wcag": {
            "label": "WCAG 2.1 — Success Criterion 1.1.1: Non-text Content (H37)",
            "url": "https://www.w3.org/WAI/WCAG21/Techniques/html/H37",
            "description": "This rule requires that all informative images include alternative text."
        }
    },
    "Low Color Contrast": {
        "why": "Low contrast makes text hard to read for people with low vision or color blindness. Improving contrast ensures better readability and user comfort.",
        "wcag": {
            "label": "WCAG 2.1 — Success Criterion 1.4.3: Contrast (Minimum)",
            "url": "https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html",
            "description": "This rule requires a contrast ratio of at least 4.5:1 for normal text."
        }
    },
    "Possible Improper List": {
        "why": "Using semantic list elements (<ul>, <li>) helps assistive technologies understand structure, improving navigation and clarity for screen reader users.",
        "wcag": {
            "label": "WCAG 2.1 — Success Criterion 1.3.1: Info and Relationships",
            "url": "https://www.w3.org/WAI/WCAG21/Techniques/html/H48",
            "description": "Content should be structured semantically to convey relationships."
        }
    }
}
