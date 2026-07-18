from typing import Any, Optional

import httpx


async def fetch_user_repos(
    username: str, token: Optional[str] = None
) -> dict[str, Any]:
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        user_res = await client.get(
            f"https://api.github.com/users/{username}",
            headers=headers,
        )
        user_res.raise_for_status()
        user = user_res.json()

        repos_res = await client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 20},
            headers=headers,
        )
        repos_res.raise_for_status()
        repos = repos_res.json()

        repo_details: list[dict[str, Any]] = []
        for repo in repos:
            if repo.get("fork"):
                continue

            languages: list[str] = []
            languages_url = repo.get("languages_url")
            if languages_url:
                langs_res = await client.get(languages_url, headers=headers)
                if langs_res.status_code == 200:
                    languages = list(langs_res.json().keys())

            repo_details.append(
                {
                    "name": repo.get("name", ""),
                    "description": repo.get("description") or "",
                    "languages": languages,
                    "stars": repo.get("stargazers_count", 0),
                    "topics": repo.get("topics") or [],
                    "updated_at": repo.get("updated_at", ""),
                    "url": repo.get("html_url", ""),
                }
            )

    return {"user": user, "repos": repo_details}