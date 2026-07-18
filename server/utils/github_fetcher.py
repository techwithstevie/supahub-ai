import httpx
from typing import Optional

async def fetch_user_repos(username: str, token: Optional[str] = None):
    headers = {"Authorization": f"token {token}"} if token else {}
    async with httpx.AsyncClient() as client:
        repos_res = await client.get(
            f"https://api.github.com/users/{username}/repos?sort=updated&per_page=20",
            headers=headers
        )
        user_res = await client.get(
            f"https://api.github.com/users/{username}",
            headers=headers
        )
        repos = repos_res.json()
        user = user_res.json()

        repo_details = []
        for repo in repos:
            if repo.get("fork"):
                continue
            langs_res = await client.get(repo["languages_url"], headers=headers)
            repo_details.append({
                "name": repo["name"],
                "description": repo.get("description", ""),
                "languages": list(langs_res.json().keys()),
                "stars": repo["stargazers_count"],
                "topics": repo.get("topics", []),
                "updated_at": repo["updated_at"],
                "url": repo["html_url"]
            })

    return {"user": user, "repos": repo_details}