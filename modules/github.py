from enum import Enum

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
            }
            ... on Issue {
                title
                number
                url
            }
            ... on PullRequest {
                title
                number
                url
            }
        }
    }
}""".replace(
        "    ", ""
    )
    .replace("\n}", "}")
    .lstrip()
)


class GitHubResultType(Enum):
    """Maps the type option to the GitHub search filter."""

    ISSUE = "is:issue"
    PULL_REQUEST = "is:pr"
    DISCUSSION = ""  # Discussion ignores the 'is:' filter


@command(
    name="github",
    description="Search GitHub.",
    options=[
        StringOption(
            name="topic",
            description="What to search for.",
        ),
        StringOption(
            name="repository",
            description="The repository to search in.",
            required=True,
            autocomplete=True,
        ),
        StringOption(
            name="type",
            description="Type of result to search for.",
            required=True,
            choices=[Choice(type.name, type.name) for type in GitHubResultType],
        ),
    ],
)
async def github(interaction: Interaction, topic: str, repository: str, type: str):
    result_type = GitHubResultType[type.upper()]
    search_string = f"repo:{repository} {topic or ''} {result_type.value}"
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
                "Content-Type": "application/json",
            },
        )
    results = []
    if response.status_code == 200:
        body = await response.json()
        try:
            results = [
                f"[#{result['number']}]({result['url']}): {result['title']}"
                for result in body["data"]["search"]["nodes"]
            ]
        except KeyError:
            pass
    if results:
        # TODO: configurable color
        await interaction.response(embed=Embed(title="placeholder", description="\n".join(results), color=0xEE4196))
    else:
        await interaction.response("No results found.", ephemeral=True)


@github.autocomplete("repository")
async def autocomplete_repository(interaction: Interaction, value: str):
    async with httpx.AsyncClient() as client:
        # TODO: implement cache
        print("FETCHING REPOS")
        repos = await client.get("https://api.github.com/orgs/deta/repos?sort=updated")
    choices = []
    for repo in repos.json():
        name = repo["name"]
        ratio = fuzz.ratio(name, value.lower())
        if len(choices) < 25 < ratio:
            choices.append(Choice(name=name, value=name))
    await interaction.autocomplete(choices)


def setup(client: Client):
    client.add_commands(github)
