import os
from enum import Enum
from typing import Iterable, NamedTuple

import httpx
from discohook import Choice, Client, Embed, Interaction, StringOption, command
from thefuzz import fuzz

QUERY = (
    """query searchResults($search_string: String!, $type: SearchType!, $num: Int!) {
    search(type: $type, query: $search_string, first: $num) {
        nodes {
            ... on Discussion {
                title
                number
                url
                repository {
                    name
                }
            }
            ... on Issue {
                title
                number
                url
                repository {
                    name
                }
            }
            ... on PullRequest {
                title
                number
                url
                repository {
                    name
                }
            }
        }
    }
}""".replace(
        "    ", ""
    )
    .replace("\n}", "}")
    .strip()
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
repos_cache = []


class GitHubResultType(Enum):
    """Maps a type option to the corresponding GitHub search filter."""

    ISSUE = "is:issue"
    PULL_REQUEST = "is:pr"
    DISCUSSION = ""  # Discussion ignores the 'is:' filter


class GitHubSearchResult(NamedTuple):
    """Represents an issue, pull request, or discussion as part of a GitHub search result."""

    title: str
    number: int
    url: str
    repository: str


def format_search_results(results: Iterable[GitHubSearchResult]) -> list[str]:
    formatted_results = []
    for result in results:
        formatted_results.append(f"[{result.repository}#{result.number}]({result.url}): {result.title}")
    return formatted_results


@command(
    name="github",
    description="Search GitHub.",
    options=[
        StringOption(
            name="type",
            description="Type of result to search for.",
            required=True,
            choices=[Choice(type.name, type.name) for type in GitHubResultType],
        ),
        StringOption(
            name="query",
            description="What to search for.",
        ),
        StringOption(
            name="repository",
            description="The repository to search in.",
            autocomplete=True,
        ),
    ],
)
async def github(interaction: Interaction, type: str, query: str, repository: str):
    if not GITHUB_TOKEN:
        await interaction.response("GitHub token has not been provided.", ephemeral=True)
        return
    result_type = GitHubResultType[type.upper()]
    if repository:
        search_string = f"repo:deta/{repository}"
    else:
        search_string = "org:deta"
    search_string += f" {query or ''} {result_type.value}"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.github.com/graphql",
            json={
                "query": QUERY,
                "variables": {
                    "search_string": search_string,
                    # The API doesn't distinguish between issues and PRs here.
                    "type": result_type.name
                    if result_type == GitHubResultType.DISCUSSION
                    else GitHubResultType.ISSUE.name,
                    "num": 5,
                },
            },
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json",
            },
        )
    results = []
    if response.status_code == 200:
        try:
            nodes = [
                GitHubSearchResult(
                    title=node["title"],
                    number=node["number"],
                    url=node["url"],
                    repository=node["repository"]["name"],
                )
                for node in response.json()["data"]["search"]["nodes"]
            ]
            results = format_search_results(nodes)
        except KeyError:
            pass
    if results:
        # TODO: configurable color
        await interaction.response(embed=Embed(title="Search Results", description="\n".join(results), color=0xEE4196))
    else:
        await interaction.response("No results found.", ephemeral=True)


@github.autocomplete("repository")
async def autocomplete_repository(interaction: Interaction, value: str):
    if not repos_cache:
        async with httpx.AsyncClient() as client:
            print("FETCHING REPOS")
            response = await client.get("https://api.github.com/orgs/deta/repos?sort=updated")
            if response.status_code == 200:
                repos_cache.extend(response.json())
    choices = []
    for repo in repos_cache:
        name = repo["name"]
        ratio = fuzz.ratio(name, value.lower())
        if len(choices) < 25 < ratio:
            choices.append(Choice(name=name, value=name))
    await interaction.autocomplete(choices)


def setup(client: Client):
    client.add_commands(github)
