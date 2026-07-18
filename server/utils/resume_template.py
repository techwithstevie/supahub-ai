from __future__ import annotations

import re
from urllib.parse import urlparse

from models.schemas import EducationItem, ProjectItem, ResumeDocument

_QUOTE_CHARS = "\"'“”‘’"

_SCHOOL_URLS: dict[str, str] = {
    "coding temple": "https://www.codingtemple.com/",
    "jackson memorial high school": "https://www.jacksonsd.org/",
}


def _clean_summary(text: str) -> str:
    s = (text or "").strip()
    return s.strip(_QUOTE_CHARS).strip()


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _normalize_url(raw: str, kind: str = "web") -> str:
    value = (raw or "").strip()
    if not value:
        return ""

    lower = value.lower()

    if lower.startswith(("http://", "https://", "mailto:", "tel:")):
        return value

    if kind == "email" or (
        "@" in value and " " not in value and "linkedin." not in lower
    ):
        email = value.removeprefix("mailto:")
        return f"mailto:{email}"

    if kind == "phone":
        digits = re.sub(r"[^\d+]", "", value)
        return f"tel:{digits}" if digits else ""

    if kind == "linkedin":
        if "linkedin.com" in lower:
            return value if lower.startswith("http") else f"https://{value.lstrip('/')}"
        slug = value.rstrip("/").split("/")[-1]
        return f"https://www.linkedin.com/in/{slug}"

    if kind == "github":
        if "github.com" in lower:
            return value if lower.startswith("http") else f"https://{value.lstrip('/')}"
        slug = value.rstrip("/").split("/")[-1]
        return f"https://github.com/{slug}"

    return f"https://{value.lstrip('/')}"


def _html_a(href: str, label: str, external: bool = True) -> str:
    if not href:
        return _esc(label)
    rel = ' rel="noopener noreferrer"' if external and href.startswith("http") else ""
    target = ' target="_blank"' if external and href.startswith("http") else ""
    return f'<a href="{_esc(href)}"{target}{rel}>{_esc(label)}</a>'


def _md_link(href: str, label: str) -> str:
    if not href:
        return label
    return f"[{label}]({href})"


def _contact_items(doc: ResumeDocument) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    if doc.phone:
        items.append((_normalize_url(doc.phone, "phone"), doc.phone, "phone"))
    if doc.email:
        items.append((_normalize_url(doc.email, "email"), doc.email, "email"))
    if doc.linkedin:
        items.append((_normalize_url(doc.linkedin, "linkedin"), "LinkedIn", "linkedin"))
    if doc.github:
        items.append((_normalize_url(doc.github, "github"), "GitHub", "github"))
    if doc.portfolio:
        items.append((_normalize_url(doc.portfolio, "web"), "Portfolio", "portfolio"))
    return items


def _project_links(proj: ProjectItem) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    for link in proj.links or []:
        label = (getattr(link, "label", None) or "Link").strip()
        url = (getattr(link, "url", None) or "").strip()
        if not url and label.lower() in {"code", "repo", "github"} and proj.repo_url:
            url = proj.repo_url
        if url:
            out.append((_normalize_url(url, "web"), label or "Link"))

    if proj.repo_url:
        repo_href = _normalize_url(proj.repo_url, "web")
        if repo_href and not any(h == repo_href for h, _ in out):
            out.insert(0, (repo_href, "Code"))

    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for href, label in out:
        if href and href not in seen:
            seen.add(href)
            unique.append((href, label))
    return unique


def _education_url(edu: EducationItem) -> str:
    if edu.url:
        return _normalize_url(edu.url, "web")
    key = (edu.school or "").strip().lower()
    return _SCHOOL_URLS.get(key, "")


def render_markdown(doc: ResumeDocument) -> str:
    lines: list[str] = []
    lines.append(f"# {(doc.full_name or '').upper()}")

    contact_bits = [
        _md_link(href, label) for href, label, _kind in _contact_items(doc)
    ]
    lines.append("  |  ".join(contact_bits))
    lines.append("")
    lines.append(f"## {(doc.target_title or '').upper()}")
    if doc.headline_tech:
        lines.append("  •  ".join(doc.headline_tech))
    lines.append("")
    if doc.summary:
        lines.append(f'"{_clean_summary(doc.summary)}"')
    lines.append("")
    lines.append("---")
    lines.append("## SKILLS")
    for cat in doc.skills:
        lines.append(f"**{cat.category}:**  {', '.join(cat.items)}")
    lines.append("")
    lines.append("---")
    lines.append("## EXPERIENCE")
    for exp in doc.experience:
        company = (exp.company or "").upper()
        if exp.company_url:
            company_md = _md_link(_normalize_url(exp.company_url, "web"), company)
        else:
            company_md = f"**{company}**"
        lines.append(
            f"{company_md} — {exp.title}  |  {exp.location}  |  {exp.start} – {exp.end}"
        )
        for bullet in exp.bullets:
            lines.append(f"● {bullet}")
        lines.append("")
    lines.append("---")
    lines.append("## PROJECTS")
    for proj in doc.projects:
        link_bits = [_md_link(h, lab) for h, lab in _project_links(proj)]
        name_bit = f"**{proj.name}**"
        if link_bits:
            name_bit = f"{name_bit}  |  " + "  |  ".join(link_bits)
        lines.append(name_bit)
        if proj.stack:
            lines.append(", ".join(proj.stack))
        for bullet in proj.bullets:
            lines.append(f"● {bullet}")
        lines.append("")
    if doc.education:
        lines.append("---")
        lines.append("## EDUCATION")
        for edu in doc.education:
            href = _education_url(edu)
            school = _md_link(href, edu.school) if href else f"**{edu.school}**"
            year = f"  ({edu.year})" if edu.year else ""
            lines.append(f"{school}  —  {edu.credential}{year}")
    return "\n".join(lines).strip() + "\n"


def render_html(doc: ResumeDocument) -> str:
    contact_html_parts: list[str] = []
    for href, label, kind in _contact_items(doc):
        external = kind not in {"email", "phone"}
        contact_html_parts.append(_html_a(href, label, external=external))
    contact_html = '  <span class="sep">|</span>  '.join(contact_html_parts)

    tech = "  •  ".join(_esc(t) for t in doc.headline_tech)
    summary = _esc(_clean_summary(doc.summary))

    skills_html = "\n".join(
        '<div class="skill-row">'
        f'<span class="skill-cat">{_esc(cat.category)}:</span> '
        f'<span class="skill-items">{_esc(", ".join(cat.items))}</span>'
        "</div>"
        for cat in doc.skills
    )

    exp_parts: list[str] = []
    for exp in doc.experience:
        company_label = (exp.company or "").upper()
        company_href = _normalize_url(exp.company_url or "", "web")
        if company_href:
            company_html = (
                f'<span class="company">{_html_a(company_href, company_label)}</span>'
            )
        else:
            company_html = f'<span class="company">{_esc(company_label)}</span>'
        bullets = "".join(f"<li>{_esc(b)}</li>" for b in exp.bullets)
        exp_parts.append(
            f"""
        <div class="block">
          <div class="block-head">
            {company_html}
            <span class="meta"> — {_esc(exp.title)}  |  {_esc(exp.location)}  |  {_esc(exp.start)} – {_esc(exp.end)}</span>
          </div>
          <ul class="bullets">{bullets}</ul>
        </div>
        """
        )
    exp_html = "\n".join(exp_parts)

    proj_parts: list[str] = []
    for proj in doc.projects:
        plinks = _project_links(proj)
        link_html = ""
        if plinks:
            link_html = "  |  " + "  |  ".join(_html_a(h, lab) for h, lab in plinks)
        primary = plinks[0][0] if plinks else ""
        name_html = _html_a(primary, proj.name) if primary else _esc(proj.name)
        stack = _esc(", ".join(proj.stack))
        bullets = "".join(f"<li>{_esc(b)}</li>" for b in proj.bullets)
        proj_parts.append(
            f"""
        <div class="block">
          <div class="block-head">
            <span class="company">{name_html}</span>
            <span class="meta">{link_html}</span>
          </div>
          <div class="stack">{stack}</div>
          <ul class="bullets">{bullets}</ul>
        </div>
        """
        )
    proj_html = "\n".join(proj_parts)

    edu_parts: list[str] = []
    for edu in doc.education:
        href = _education_url(edu)
        if href:
            school_html = f"<strong>{_html_a(href, edu.school)}</strong>"
        else:
            school_html = f"<strong>{_esc(edu.school)}</strong>"
        year = f"  ({_esc(edu.year)})" if edu.year else ""
        edu_parts.append(
            f'<div class="edu-row">{school_html}  —  {_esc(edu.credential)}{year}</div>'
        )
    edu_html = "\n".join(edu_parts)

    name = _esc(doc.full_name or "")
    title = _esc(doc.target_title or "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{name} — Resume</title>
<style>
  @page {{ margin: 0.55in 0.65in; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Calibri", "Segoe UI", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.35;
    color: #111;
    background: #fff;
  }}
  .page {{
    max-width: 8.5in;
    margin: 0 auto;
    padding: 0.5in 0.65in;
  }}
  a {{
    color: #0b57d0;
    text-decoration: none;
  }}
  a:hover {{ text-decoration: underline; }}
  .name {{
    text-align: center;
    font-size: 18pt;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin: 0 0 4px 0;
  }}
  .contact {{
    text-align: center;
    font-size: 9.5pt;
    color: #222;
    margin-bottom: 10px;
  }}
  .contact .sep {{
    color: #666;
    margin: 0 0.15em;
  }}
  .title {{
    text-align: center;
    font-size: 12pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin: 0 0 4px 0;
  }}
  .tech-line {{
    text-align: center;
    font-size: 9.5pt;
    color: #222;
    margin-bottom: 10px;
  }}
  .summary {{
    font-style: italic;
    text-align: left;
    margin: 0 0 12px 0;
    color: #1a1a1a;
  }}
  .section {{
    font-size: 10.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid #222;
    margin: 14px 0 8px 0;
    padding-bottom: 2px;
  }}
  .skill-row {{ margin: 2px 0; }}
  .skill-cat {{
    display: inline-block;
    min-width: 5.2rem;
    font-weight: 700;
  }}
  .block {{ margin-bottom: 10px; }}
  .block-head {{ margin-bottom: 2px; }}
  .company {{ font-weight: 700; }}
  .meta {{ font-weight: 400; }}
  .stack {{
    font-size: 9.5pt;
    color: #333;
    margin: 1px 0 2px 0;
  }}
  ul.bullets {{
    margin: 2px 0 0 0;
    padding-left: 1.1rem;
  }}
  ul.bullets li {{ margin: 2px 0; }}
  .edu-row {{ margin: 3px 0; }}
</style>
</head>
<body>
  <div class="page">
    <h1 class="name">{name}</h1>
    <div class="contact">{contact_html}</div>
    <div class="title">{title}</div>
    <div class="tech-line">{tech}</div>
    <p class="summary">"{summary}"</p>

    <div class="section">Skills</div>
    {skills_html}

    <div class="section">Experience</div>
    {exp_html}

    <div class="section">Projects</div>
    {proj_html}

    <div class="section">Education</div>
    {edu_html}
  </div>
</body>
</html>
"""