from enum import Enum
from typing import List

import httpx
from discohook import Choice, Interaction, StringOption, command
from thefuzz import fuzz

QUERY = """query searchResults($search_string: String!, $type: SearchType!, $num: Int!) {
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
}""".replace("    ", "").replace("\n}", "}").lstrip()


class GithubResultType(Enum):
    ISSUE = "is:issue"
    PULL_REQUEST = "is:pr"
    DISCUSSION = ""  # Discussion ignores the 'is:' filter


async def search_github(
    search_string: str,
    type: GithubResultType,  # The API doesn't distinguish between issues and PRs here.
    num: int = 5,
) -> List[str]:
    if type == GithubResultType.ISSUE or type == GithubResultType.PULL_REQUEST:
        type_string = "ISSUE"
    elif type == GithubResultType.DISCUSSION:
        type_string = "DISCUSSION"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.github.com/graphql",
            json={
                "query": QUERY,
                "variables": {
                    "search_string": search_string,
                    "type": type_string,
                    "num": num,
                },
            },
            headers={
                # "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json",
            },
        )
    if response.status_code != 200:
        return []
    body = await response.json()
    try:
        results = body["data"]["search"]["nodes"]
    except KeyError:
        return []
    return [f"[#{result['number']}]({result['url']}): {result['title']}" for result in results]


@command(
    name="github",
    description="Search github.",
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
            choices=[Choice(type.name, type.name) for type in GithubResultType],
        ),
    ],
)
async def github_command_handler(interaction: Interaction, topic: str, repository: str, type: str):
    type_ = GithubResultType(type)
    search_string = f"repo:{repository} {topic or ''} {type_}"
    results = await search_github(search_string, type_)
    if results:
        await interaction.response(embeds=[list_embed_builder(results)])
    else:
        await interaction.response("No results found.", ephemeral=True)


def list_embed_builder(x):
    raise NotImplementedError()


@github_command_handler.autocomplete("repository")
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


# async def search_discussions({
#     name: 'discussion',
#     description: 'Search for a discussion on github.',
#     global: true,

#     options: [
#         {
#             name= 'repository',
#             description: 'The repository to search within',
#             type= 'Integer',
#             choices: [
#                 {
#                     name: 'SvelteKit',
#                     value: Repos.SVELTE_KIT,
#                 },
#             ],
#             required: true,
#         },
#         {
#             name: 'topic',
#             description: 'What to search for',
#             type= 'String',
#         },
#     ],

#     run: async ({ interaction }) =>
#         await github_command_handler(interaction, GithubResultType.DISCUSSION),
# })


# async def search_issues({
#     name: 'issue',
#     description: 'Search for an issue on github',
#     global: true,

#     options: [
#         {
#             name: 'repository',
#             description: 'The repository to search within',
#             type= 'Integer',
#             choices: [
#                 {
#                     name: 'Svelte',
#                     value: Repos.SVELTE,
#                 },
#                 {
#                     name: 'SvelteKit',
#                     value: Repos.SVELTE_KIT,
#                 },
#                 {
#                     name: 'Language Tools',
#                     value: Repos.LANGUAGE_TOOLS,
#                 },
#             ],
#             required: true,
#         },
#         {
#             name: 'topic',
#             description: 'What to search for',
#             type= 'String',
#         },
#     ],

#     run: async ({ interaction }) =>
#         await github_command_handler(interaction, GithubResultType.ISSUE),
# });


# async def serach_pull_requests({
#     name: 'pr',
#     description: 'Search for a pull request on github',
#     global: true,

#     options: [
#         {
#             name: 'repository',
#             description: 'The repository to search within',
#             type= 'Integer',
#             choices: [
#                 {
#                     name: 'Svelte',
#                     value: Repos.SVELTE,
#                 },
#                 {
#                     name: 'SvelteKit',
#                     value: Repos.SVELTE_KIT,
#                 },
#                 {
#                     name: 'RFCs',
#                     value: Repos.RFCS,
#                 },
#                 {
#                     name: 'Language Tools',
#                     value: Repos.LANGUAGE_TOOLS,
#                 },
#             ],
#             required: true,
#         },
#         {
#             name: 'topic',
#             description: 'What to search for',
#             type= 'String',
#         },
#     ],

#     run: async ({ interaction }) =>
#         await github_command_handler(
#             interaction,
#             GithubResultType.PULL_REQUEST,
#         ),
# });
