import os

import httpx
import yaml
from discohook import (
    Button,
    ButtonStyle,
    Choice,
    Client,
    Embed,
    Interaction,
    PartialEmoji,
    StringOption,
    View,
)
from thefuzz import fuzz

APPLICATION_ID = os.getenv("APPLICATION_ID")
APPLICATION_TOKEN = os.getenv("APPLICATION_TOKEN")
APPLICATION_PUBLIC_KEY = os.getenv("APPLICATION_PUBLIC_KEY")
REPOSITORY_URL = os.getenv("REPOSITORY_URL")
GIT_BRANCH = os.getenv("GIT_BRANCH", "main")

if not (
    APPLICATION_ID and APPLICATION_TOKEN and APPLICATION_PUBLIC_KEY and REPOSITORY_URL
):
    raise ValueError("missing environment variables")

app = Client(
    application_id=APPLICATION_ID,
    token=APPLICATION_TOKEN,
    public_key=APPLICATION_PUBLIC_KEY,
)


@app.on_error
async def on_error(i: Interaction, error: Exception):
    if i.responded:
        await i.followup(f"```py\nError: {error}\n```", ephemeral=True)
    else:
        await i.response(f"```py\nError: {error}\n```", ephemeral=True)


@app.command(
    name="docs",
    description="Search Deta docs.",
    options=[
        StringOption(
            name="query",
            description="Search query.",
            required=True,
            autocomplete=True,
        )
    ],
)
async def docs(i: Interaction, *, query: str):
    hit = httpx.get(f"https://teletype.deta.dev/search?q={query}&l=1").json()["hits"][0]
    button = Button(
        label="Open docs page",
        url=hit["url"],
        style=ButtonStyle.link,
        emoji=PartialEmoji(name="deta", id="1047502818208137336"),
    )
    view = View()
    view.add_buttons(button)
    embed = Embed(
        title="Deta Docs",
        description=f"[{hit['fragments']}]({hit['url']})",
        color=0xEE4196,
    )
    await i.response(embed=embed, view=view)


@docs.autocomplete(name="query")
async def docs_autocomplete(i: Interaction, value: str):
    hits = httpx.get(f"https://teletype.deta.dev/search?q={value}&l=25").json()["hits"]
    await i.autocomplete(
        choices=[Choice(name=hit["fragments"], value=hit["fragments"]) for hit in hits]
    )


@app.command(
    name="tag",
    description="Display a tag.",
    options=[
        StringOption(
            name="name",
            description="Tag name.",
            required=True,
            autocomplete=True,
        )
    ],
)
async def tag(i: Interaction, name: str):
    if not name.endswith(".md"):
        name = f"{name}.md"
    try:
        with open(f"resources/tags/{name}", "r") as file:
            data = file.read()
    except FileNotFoundError as exc:
        raise ValueError(f"tag '{name}' not found") from exc
    if data.startswith("---"):
        _, meta, content = data.split("---", 2)
        metadata = yaml.safe_load(meta)
    else:
        raise ValueError(f"failed to parse tag '{name}'")
    title = metadata.get("title")
    delete_button = Button(label="🗑️", custom_id="delete", style=ButtonStyle.grey)
    edit_button = Button(
        label="✏️ Edit",
        url=f"{REPOSITORY_URL}/blob/{GIT_BRANCH}/resources/tags/{name}",
        style=ButtonStyle.link,
    )
    view = View()
    view.add_buttons(edit_button, delete_button)

    @delete_button.on_interaction
    async def on_submit(i: Interaction):
        await i.message.delete()  # type: ignore

    embed = Embed(title=title, description=content, color=0xEE4196)
    await i.response(embed=embed, view=view)


@tag.autocomplete(name="name")
async def tag_autocomplete(i: Interaction, value: str):
    filenames = os.listdir("resources/tags")
    choices = []
    for filename in filenames:
        name = filename.replace(".md", "")
        ratio = fuzz.ratio(name, value.lower())
        if len(choices) < 25 < ratio:
            choices.append(Choice(name=name, value=filename))
    await i.autocomplete(choices)