from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import requests
from pydantic import BaseModel, Field, PrivateAttr, model_validator

from app.processors.integrations.github.types import GithubSecret
from app.processors.utils import download_file


class GithubClient(BaseModel):
    """Super simple Github API client. Allows a bit more flexibility than PyGithub."""

    secret: GithubSecret
    per_page: int = Field(default=100)

    _url: str = PrivateAttr()
    _headers: dict[str, str] = PrivateAttr()

    @model_validator(mode="after")
    def define_base_url_and_headers(self) -> "GithubClient":
        self._url = "https://api.github.com"
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.secret.token}",
        }
        return self

    def execute_simple_get_request(self, url: str) -> list[dict[str, Any]]:
        """
        Execute simple GET request to Github REST API.
        """
        resp = requests.get(url, headers=self._headers)
        if resp.status_code != 200:
            error_msg = f"Failed to fetch data from {url} with status code {resp.status_code}: {resp.text}"
            raise Exception(error_msg)
        data = resp.json()
        if isinstance(data, dict):
            return [data] if data else []
        elif isinstance(data, list):
            return data
        else:
            raise Exception(
                f"Unrecognized return type for GET request {url}: {data.__class__.__name__}"
            )

    def paginate_api_request(
        self, url: str, params: dict[str, Any]
    ) -> Generator[list[dict[str, Any]], None, None]:
        """
        Handle pagination with the Github REST API.
        """
        has_more = True
        page = 1
        while has_more:
            params["page"] = page
            resp = requests.get(url, headers=self._headers, params=params)

            # Handle errors
            if resp.status_code != 200:
                error_msg = f"Failed to fetch data from {url} with status code {resp.status_code}: {resp.text}"
                raise Exception(error_msg)
            data = resp.json()
            yield data

            # Check if there are more
            headers_link = resp.headers.get("link", "")
            if headers_link and 'rel="next"' in headers_link:
                has_more = True
                page += 1
            else:
                has_more = False

    def get_repos(self) -> list[dict[str, Any]]:
        """
        Retrieve GitHub repositories using the GitHub REST API.
        """
        all_repos: list[dict[str, Any]] = []

        # Default params
        params: dict[str, Any] = {"per_page": self.per_page}

        # Github response is paginated - iterate through all of the pages. This
        # shouldn't take too long.
        if self.secret.org_name:
            url = f"{self._url}/org/repos"
        else:
            url = f"{self._url}/user/repos"
        all_repos_generator = self.paginate_api_request(url, params)
        for repos_page in all_repos_generator:
            for repo in repos_page:
                all_repos.append(repo)
        return all_repos

    def convert_str_timestamp_to_iso(self, since: str) -> str:
        """
        Github's `since` parameter must be the time formatted according to ISO.
        """
        since_ts = float(since)
        return datetime.fromtimestamp(since_ts).isoformat()

    def get_pull_requests(
        self, repo_full_name: str, since: str | None
    ) -> Generator[list[dict[str, Any]], None, None]:
        """
        Retrieve pull requests for a specific repository.
        """
        url = f"{self._url}/repos/{repo_full_name}/pulls"
        params = {"state": "all", "per_page": self.per_page}
        if since:
            params["since"] = self.convert_str_timestamp_to_iso(since)
        return self.paginate_api_request(url, params)

    def get_issues(
        self, repo_full_name: str, since: str | None
    ) -> Generator[list[dict[str, Any]], None, None]:
        """
        Retrieve issues for a specific repository.
        """
        url = f"{self._url}/repos/{repo_full_name}/issues"
        params = {
            "filter": "all",
            "state": "all",
            "per_page": self.per_page,
        }
        if since:
            params["since"] = self.convert_str_timestamp_to_iso(since)
        return self.paginate_api_request(url, params)

    def get_user(self, login: str) -> dict[str, Any]:
        """
        Get user information
        """
        url = f"{self._url}/users/{login}"
        data = self.execute_simple_get_request(url)

        # The API should throw an error if the user is not found. Just in case...
        if not data:
            raise Exception(f"Could not find Github user with login `{login}`!")
        return data[0]

    def download_file(self, url: str, local_path: Path):
        """
        Thin wrapper around the `download_file` utility. Really only exists to
        avoid using this class's private headers attribute from outside the class.
        """
        return download_file(
            url=url,
            headers=self._headers,
            local_file=local_path,
        )
