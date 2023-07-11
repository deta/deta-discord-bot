import os
from enum import Enum
from typing import Iterable, NamedTuple

import httpx
from discohook import Choice, Client, Embed, Interaction, StringOption, command
from thefuzz import fuzz

QUERY = (
    """query searchResults($search_string: String!, $type: SearchType!, $max: Int!) {
    search(type: $type, query: $search_string, first: $max) {
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

    def __str__(self):
        return self.name.replace("_", " ").title()


class GitHubSearchResult(NamedTuple):
    """Represents an issue, pull request, or discussion as part of a GitHub search result."""

    title: str
    number: int
    url: str
    repository: str

    def __str__(self):
        return f"[{self.repository}#{self.number}]({self.url}): {self.title}"


# FIXME: 'result type' is not a descriptive variable or type name
async def search_github(search_string: str, type: GitHubResultType, max: int = 5) -> list[GitHubSearchResult]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.github.com/graphql",
            json={
                "query": QUERY,
                "variables": {
                    "search_string": search_string,
                    # The API doesn't distinguish between issues and PRs here.
                    "type": type.name
                    if type == GitHubResultType.DISCUSSION
                    else GitHubResultType.ISSUE.name,
                    "max": max,
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
            results = [
                GitHubSearchResult(
                    title=node["title"],
                    number=node["number"],
                    url=node["url"],
                    repository=node["repository"]["name"],
                )
                for node in response.json()["data"]["search"]["nodes"]
            ]
        except KeyError:
            pass
    return results


async def get_repos(org: str) -> list[dict]:
    print("repos cache before: ", repos_cache)
    if not repos_cache:
        async with httpx.AsyncClient() as client:
            print("FETCHING REPOS")
            response = await client.get(
                url=f"https://api.github.com/orgs/{org}/repos?sort=updated",
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                },
            )
            if response.status_code == 200:
                repos_cache.extend(response.json())
    print("repos cache after: ", repos_cache)
    return repos_cache


def create_search_results_embed(
    results: Iterable[GitHubSearchResult],
    result_type: GitHubResultType,
    query: str,
    repository: str,
) -> Embed:
    # TODO: configurable color
    embed = Embed(title="GitHub Search Results", color=0xEE4196)
    embed.add_field("Organization", "deta", inline=True)
    embed.add_field("Repository", repository or "All", inline=True)
    embed.add_field("Type", str(result_type), inline=True)
    embed.add_field("Query", f"`{query}`", inline=True)
    embed.add_field("Results", "\n".join(map(str, results)))
    return embed


@command(
    name="github",
    description="Search GitHub.",
    options=[
        StringOption(
            name="type",
            description="Type of result to search for.",
            required=True,
            choices=[Choice(str(type), type.name) for type in GitHubResultType],
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
    try:
        result_type = GitHubResultType[type.upper()]
    except KeyError:
        await interaction.response("Invalid value for parameter 'type'.", ephemeral=True)
        return
    if repository:
        search_string = f"repo:deta/{repository}"
    else:
        search_string = "org:deta"
    search_string += f" {query or ''} {result_type.value}"
    results = await search_github(search_string, result_type)
    if results:
        await interaction.response(embed=create_search_results_embed(results, result_type, query, repository))
    else:
        await interaction.response("No results found.", ephemeral=True)


@github.autocomplete("repository")
async def autocomplete_repository(interaction: Interaction, value: str):
    repos = await get_repos("deta")
    choices = []
    for repo in repos:
        name = repo["name"]
        ratio = fuzz.ratio(name, value.lower())
        if len(choices) < 25 < ratio:
            choices.append(Choice(name=name, value=name))
    await interaction.autocomplete(choices)


def setup(client: Client):
    client.add_commands(github)