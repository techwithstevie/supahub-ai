from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urlparse

import httpx

from models.job_schemas import (
    HiringTeamMember,
    JobSource,
    LinkedInJobDetails,
    ParseJobUrlResponse,
)

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Canonical section headers we care about (order matters for splitting)
_SECTION_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    (
        "compensation",
        (
            "compensation",
            "pay range",
            "base pay",
            "salary",
        ),
    ),
    (
        "location",
        (
            "location",
            "locations",
        ),
    ),
    (
        "primary_responsibilities",
        (
            "primary responsibilities",
            "responsibilities",
            "what you'll do",
            "what you will do",
            "the role",
            "role overview",
        ),
    ),
    (
        "candidate_qualifications",
        (
            "candidate qualifications",
            "qualifications",
            "requirements",
            "what we're looking for",
            "what we are looking for",
            "minimum qualifications",
            "preferred qualifications",
        ),
    ),
    (
        "why_join",
        (
            "why join this opportunity",
            "why join",
            "why you'll love",
            "why you will love",
            "benefits of joining",
        ),
    ),
    (
        "about_company",
        (
            "about the company",
            "about us",
            "about our company",
            # "About Acme" handled via regex about_<name>
        ),
    ),
    (
        "benefits",
        (
            "benefits found in job post",
            "benefits",
            "perks",
            "what we offer",
        ),
    ),
    (
        "requirements_added_by_poster",
        (
            "requirements added by the job poster",
            "requirements added by job poster",
            "poster requirements",
            "skills and experience",
        ),
    ),
]

_ABOUT_COMPANY_RE = re.compile(
    r"^about\s+(.+)$",
    re.I,
)

_NA = "N/A"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clean_text(s: str) -> str:
    s = unescape(s or "")
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p\s*>", "\n", s, flags=re.I)
    s = re.sub(r"</li\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "• ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _meta(html: str, *keys: str) -> str:
    for key in keys:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(key)}["\']',
            rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(key)}["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                return _clean_text(m.group(1))
    return ""


def _tag_text(html: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.I | re.S)
    if not m:
        return ""
    return _clean_text(m.group(1))


def _is_linkedin(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return "linkedin.com" in host


def _normalize_header(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower().rstrip(":"))


def _match_section_key(header_line: str) -> str | None:
    h = _normalize_header(header_line)
    if not h or len(h) > 80:
        return None

    # About <Company Name>
    m = _ABOUT_COMPANY_RE.match(h)
    if m:
        rest = m.group(1).strip()
        if rest and rest not in {"the job", "this job", "the role"}:
            # "about the job" is the container, not company
            if rest != "the job":
                return "about_company"

    for key, aliases in _SECTION_ALIASES:
        for alias in aliases:
            if h == alias or h.startswith(alias + " "):
                return key
    return None


def _extract_plain_description(html: str) -> str:
    """Pull largest plausible job description text blob from HTML."""
    candidates: list[str] = []

    # Common LinkedIn description containers (class names change; keep loose)
    patterns = [
        r'class=["\'][^"\']*description__text[^"\']*["\'][^>]*>(.*?)</div>',
        r'class=["\'][^"\']*show-more-less-html__markup[^"\']*["\'][^>]*>(.*?)</div>',
        r'class=["\'][^"\']*jobs-description[^"\']*["\'][^>]*>(.*?)</div>',
        r'class=["\'][^"\']*jobs-box__html-content[^"\']*["\'][^>]*>(.*?)</div>',
        r'id=["\']job-details["\'][^>]*>(.*?)</div>',
        r'data-test-id=["\']job-details[^"\']*["\'][^>]*>(.*?)</section>',
        r"<article[^>]*>(.*?)</article>",
    ]
    for pat in patterns:
        for m in re.finditer(pat, html, re.I | re.S):
            t = _clean_text(m.group(1))
            if len(t) > 120:
                candidates.append(t)

    # JSON-LD description
    for block in _json_ld_blocks(html):
        for job in _walk_jobposting(block):
            desc = job.get("description")
            if isinstance(desc, str) and len(desc) > 80:
                candidates.append(_clean_text(desc))

    if not candidates:
        # og:description fallback
        og = _meta(html, "og:description", "description")
        if og:
            candidates.append(og)

    if not candidates:
        return ""
    return max(candidates, key=len)


def _json_ld_blocks(html: str) -> list[Any]:
    blocks: list[Any] = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            blocks.extend(data)
        else:
            blocks.append(data)
    return blocks


def _walk_jobposting(obj: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        t = obj.get("@type")
        types = t if isinstance(t, list) else [t]
        if any("jobposting" in str(x).lower() for x in types if x):
            found.append(obj)
        for v in obj.values():
            found.extend(_walk_jobposting(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_walk_jobposting(item))
    return found


def _split_sections(description: str) -> dict[str, str]:
    """
    Split 'About the job' body on known headers into structured fields.
    """
    if not description:
        return {}

    lines = description.split("\n")
    # Also split on markdown-ish bold headers left as plain text
    expanded: list[str] = []
    for line in lines:
        expanded.append(line)
    lines = expanded

    # Find header indices
    headers: list[tuple[int, str, str]] = []  # idx, key, original
    for i, line in enumerate(lines):
        key = _match_section_key(line)
        if key:
            headers.append((i, key, line.strip()))

    # If no headers found, try splitting on inline "Header\n" patterns inside long lines
    if not headers:
        # Insert breaks before known headers in a single blob
        blob = description
        for _key, aliases in _SECTION_ALIASES:
            for alias in aliases:
                blob = re.sub(
                    rf"(?i)(?<!\n)({re.escape(alias)})\s*[:\n]",
                    r"\n\1\n",
                    blob,
                )
        blob = re.sub(r"(?i)(?<!\n)(about\s+[A-Z][^\n]{2,40})\s*", r"\n\1\n", blob)
        lines = [ln.strip() for ln in blob.split("\n")]
        headers = []
        for i, line in enumerate(lines):
            key = _match_section_key(line)
            if key:
                headers.append((i, key, line.strip()))

    sections: dict[str, str] = {}
    if not headers:
        sections["primary_responsibilities"] = description.strip() or _NA
        return sections

    for hi, (idx, key, _orig) in enumerate(headers):
        start = idx + 1
        end = headers[hi + 1][0] if hi + 1 < len(headers) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        if not body:
            body = _NA
        # Prefer first non-empty; if duplicate keys, append
        if key in sections and sections[key] not in ("", _NA):
            if body != _NA:
                sections[key] = (sections[key] + "\n\n" + body).strip()
        else:
            sections[key] = body

    return sections


def _extract_hiring_team(html: str, plain: str) -> list[HiringTeamMember]:
    """
    Parse 'Meet the hiring team' / 'People you can reach out to'.
    """
    members: list[HiringTeamMember] = []
    seen: set[str] = set()

    def add(name: str, title: str = "", profile_url: str = "", degree: str = "", extra: str = "") -> None:
        name = _clean_text(name)
        if not name or name.lower() in {"meet the hiring team", "hiring team"}:
            return
        key = name.lower()
        if key in seen:
            return
        seen.add(key)
        members.append(
            HiringTeamMember(
                name=name or _NA,
                title=_clean_text(title) or _NA,
                profile_url=profile_url.strip(),
                connection_degree=_clean_text(degree),
                extra=_clean_text(extra),
            )
        )

    # Slice HTML around hiring team markers
    markers = [
        r"meet the hiring team",
        r"people you can reach out to",
        r"hiring team",
        r"job poster",
    ]
    slices: list[str] = []
    lower = html.lower()
    for mk in markers:
        pos = lower.find(mk)
        if pos != -1:
            slices.append(html[pos : pos + 8000])

    search_blobs = slices or [html]

    for blob in search_blobs:
        # Profile links with names
        for m in re.finditer(
            r'href=["\'](https?://(?:www\.)?linkedin\.com/in/[^"\']+)["\'][^>]*>(.*?)</a>',
            blob,
            re.I | re.S,
        ):
            url = m.group(1).split("?")[0]
            name = _clean_text(m.group(2))
            if len(name) < 2 or len(name) > 80:
                continue
            # Look ahead for title near the anchor
            tail = blob[m.end() : m.end() + 400]
            title = ""
            degree = ""
            tm = re.search(
                r'class=["\'][^"\']*headline[^"\']*["\'][^>]*>(.*?)</',
                tail,
                re.I | re.S,
            )
            if tm:
                title = _clean_text(tm.group(1))
            if not title:
                tm2 = re.search(
                    r"<p[^>]*>(.*?)</p>",
                    tail,
                    re.I | re.S,
                )
                if tm2:
                    cand = _clean_text(tm2.group(1))
                    if cand and cand.lower() != name.lower() and len(cand) < 120:
                        title = cand
            dm = re.search(r"\b([123]rd|[123]st|[123]nd|3rd)\b", tail, re.I)
            if dm:
                degree = dm.group(1)
            add(name, title=title, profile_url=url, degree=degree)

        # data attributes sometimes used
        for m in re.finditer(
            r'data-anonymize=["\']person-name["\'][^>]*>([^<]+)<',
            blob,
            re.I,
        ):
            add(m.group(1))

    # Plain-text fallback under "Meet the hiring team"
    if not members and plain:
        m = re.search(
            r"meet the hiring team\s*(.+?)(?:people you can|similar jobs|about the company|$)",
            plain,
            re.I | re.S,
        )
        if m:
            block = m.group(1).strip()
            # lines: Name / Title pairs
            lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
            i = 0
            while i < len(lines):
                name = lines[i]
                title = lines[i + 1] if i + 1 < len(lines) else ""
                # skip if looks like a section header
                if _match_section_key(name):
                    break
                if len(name) < 60 and not name.lower().startswith("http"):
                    add(name, title=title if title and not _match_section_key(title) else "")
                    i += 2 if title and not _match_section_key(title) else 1
                else:
                    i += 1

    return members


def _title_company_from_page(html: str) -> tuple[str, str]:
    og_title = _meta(html, "og:title", "twitter:title") or _tag_text(html, "title")
    company = ""
    role = ""

    for block in _json_ld_blocks(html):
        for job in _walk_jobposting(block):
            role = role or str(job.get("title") or "").strip()
            org = job.get("hiringOrganization")
            if isinstance(org, dict):
                company = company or str(org.get("name") or "").strip()
            elif isinstance(org, str):
                company = company or org.strip()

    if og_title:
        # "Role | Company | LinkedIn" or "Role - Company"
        parts = re.split(r"\s*[|\-–—]\s*", og_title)
        parts = [
            p.strip()
            for p in parts
            if p.strip() and p.strip().lower() not in {"linkedin", "job"}
        ]
        if parts:
            role = role or parts[0]
        if len(parts) >= 2:
            company = company or parts[1]

    # topcard selectors (best-effort)
    if not company:
        m = re.search(
            r'class=["\'][^"\']*topcard__org-name-link[^"\']*["\'][^>]*>([^<]+)<',
            html,
            re.I,
        )
        if m:
            company = _clean_text(m.group(1))
    if not company:
        m = re.search(
            r'class=["\'][^"\']*job-details-jobs-unified-top-card__company-name[^"\']*["\'][^>]*>(.*?)</div>',
            html,
            re.I | re.S,
        )
        if m:
            company = _clean_text(m.group(1))
    if not role:
        m = re.search(
            r'class=["\'][^"\']*topcard__title[^"\']*["\'][^>]*>([^<]+)<',
            html,
            re.I,
        )
        if m:
            role = _clean_text(m.group(1))
    if not role:
        m = re.search(
            r'class=["\'][^"\']*job-details-jobs-unified-top-card__job-title[^"\']*["\'][^>]*>(.*?)</div>',
            html,
            re.I | re.S,
        )
        if m:
            role = _clean_text(m.group(1))

    role = re.sub(r"\s*\|\s*LinkedIn.*$", "", role, flags=re.I).strip()
    return role, company


def _location_from_page(html: str, sections: dict[str, str]) -> str:
    if sections.get("location") and sections["location"] != _NA:
        return sections["location"].split("\n")[0].strip()

    for block in _json_ld_blocks(html):
        for job in _walk_jobposting(block):
            loc = job.get("jobLocation")
            if isinstance(loc, dict):
                addr = loc.get("address") or {}
                if isinstance(addr, dict):
                    bits = [
                        str(addr.get("addressLocality") or "").strip(),
                        str(addr.get("addressRegion") or "").strip(),
                        str(addr.get("addressCountry") or "").strip(),
                    ]
                    line = ", ".join(b for b in bits if b)
                    if line:
                        return line
            if job.get("jobLocationType") == "TELECOMMUTE":
                return "Remote"

    m = re.search(
        r'class=["\'][^"\']*topcard__flavor--bullet[^"\']*["\'][^>]*>([^<]+)<',
        html,
        re.I,
    )
    if m:
        return _clean_text(m.group(1))
    m = re.search(
        r'class=["\'][^"\']*jobs-unified-top-card__bullet[^"\']*["\'][^>]*>([^<]+)<',
        html,
        re.I,
    )
    if m:
        return _clean_text(m.group(1))
    return ""


def _build_details(sections: dict[str, str], hiring: list[HiringTeamMember]) -> LinkedInJobDetails:
    def g(key: str) -> str:
        val = (sections.get(key) or "").strip()
        return val if val else _NA

    team = hiring if hiring else []
    return LinkedInJobDetails(
        compensation=g("compensation"),
        location=g("location"),
        primary_responsibilities=g("primary_responsibilities"),
        candidate_qualifications=g("candidate_qualifications"),
        why_join=g("why_join"),
        about_company=g("about_company"),
        benefits=g("benefits"),
        requirements_added_by_poster=g("requirements_added_by_poster"),
        hiring_team=team,
    )


def _details_to_notes(details: LinkedInJobDetails) -> str:
    """Readable notes blob for agents + UI."""
    parts: list[str] = ["About the job", ""]

    def add(label: str, value: str) -> None:
        parts.append(label)
        parts.append(value if value else _NA)
        parts.append("")

    add("Compensation", details.compensation)
    add("Location", details.location)
    add("Primary Responsibilities", details.primary_responsibilities)
    add("Candidate Qualifications", details.candidate_qualifications)
    add("Why Join This Opportunity", details.why_join)
    add("About Company", details.about_company)
    add("Benefits found in job post", details.benefits)
    add("Requirements added by the job poster", details.requirements_added_by_poster)

    parts.append("Meet the hiring team")
    team = details.hiring_team_or_na()
    for person in team:
        line = person.name
        if person.title and person.title != _NA:
            line += f" — {person.title}"
        if person.connection_degree:
            line += f" ({person.connection_degree})"
        if person.profile_url:
            line += f" | {person.profile_url}"
        if person.extra:
            line += f" | {person.extra}"
        parts.append(line)

    return "\n".join(parts).strip()


async def parse_job_url(url: str) -> ParseJobUrlResponse:
    url = (url or "").strip()
    if not url:
        raise ValueError("url is required")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url

    now = _now()
    warnings: list[str] = []
    raw: dict[str, Any] = {}

    if not _is_linkedin(url):
        raise ValueError(
            "Only LinkedIn job URLs are supported right now. "
            "Paste a link like https://www.linkedin.com/jobs/view/..."
        )

    html = ""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=25.0,
            headers={
                "User-Agent": _UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            resp = await client.get(url)
            raw["status_code"] = resp.status_code
            html = resp.text or ""
            if resp.status_code >= 400:
                warnings.append(f"LinkedIn returned HTTP {resp.status_code}")
    except Exception as exc:
        warnings.append(f"Could not fetch LinkedIn page: {exc}")
        html = ""

    if not html:
        warnings.append(
            "Empty page body — LinkedIn may require login. "
            "Try copying from an open job tab or use a public jobs/view link."
        )

    role_title, company = _title_company_from_page(html)
    description = _extract_plain_description(html)
    raw["description_len"] = len(description)

    # Prefer text after "About the job" when present
    about_m = re.search(
        r"about the job\s*(.+)$",
        description,
        re.I | re.S,
    )
    about_body = about_m.group(1).strip() if about_m else description

    sections = _split_sections(about_body)
    hiring = _extract_hiring_team(html, description + "\n" + about_body)

    # If qualifications got swallowed by requirements poster, keep both keys
    details = _build_details(sections, hiring)
    location = _location_from_page(html, sections) or (
        details.location if details.location != _NA else "Remote"
    )
    if details.location == _NA and location:
        details.location = location

    salary = details.compensation if details.compensation != _NA else ""
    # short salary line for top-level field
    if salary and len(salary) > 120:
        salary_range = salary.split("\n")[0][:120]
    else:
        salary_range = salary

    notes = _details_to_notes(details)

    confidence = 0.2
    if role_title:
        confidence += 0.2
    if company:
        confidence += 0.15
    filled_sections = sum(
        1
        for v in (
            details.compensation,
            details.primary_responsibilities,
            details.candidate_qualifications,
            details.why_join,
            details.about_company,
            details.benefits,
            details.requirements_added_by_poster,
        )
        if v and v != _NA
    )
    confidence += min(0.45, filled_sections * 0.07)
    if hiring:
        confidence += 0.1
    confidence = round(min(confidence, 0.98), 2)

    if filled_sections == 0:
        warnings.append(
            "Could not split About the job headers. LinkedIn often blocks "
            "anonymous fetches — open the job while logged in and retry, or "
            "paste may need a public jobs/view URL."
        )

    if not hiring:
        # explicit N/A team for UI
        details.hiring_team = []

    return ParseJobUrlResponse(
        job_url=url,
        company=company,
        role_title=role_title,
        location=location or "Remote",
        source=JobSource.linkedin,
        salary_range=salary_range,
        notes=notes,
        applied_date=now.date(),
        applied_at=now,
        confidence=confidence,
        warnings=warnings,
        linkedin_details=details,
        raw=raw,
    )