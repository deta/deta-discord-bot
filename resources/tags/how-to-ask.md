---
title: How to ask for help
---

- Search the [documentation](https://deta.space/docs) before creating a post as it often answers the question.
- Search your question in both #help-me and #feedback before posting.
- Be specific about what you need help with. Include an explanation of the problem, a code sample (if code is involved), and the error message (if you got one).
- Format your code and error messages using [code blocks](https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-#h_01GY0DAKGXDEHE263BCAYEGFJA).
- Don't share code or error messages as screenshots, because those helping often need to copy parts of the code or error.
- Mention the runtime (Python, Node, Go, etc) in the beginning while describing the problem.
- Include your Spacefile.
- Be respectful to the people who are trying to help and try to provide necessary information as much as possible.
- The post should be related to Deta.
- Low-effort questions such as "help me fix this" will not be answered.
- Don't ping @team unless the issue is critical, or involves security, abuse, or service uptime.

Python Discord has a wonderful guide on asking good questions [here](https://www.pythondiscord.com/pages/guides/pydis-guides/asking-good-questions/).

Example question:

> **Request to app returns unauthorized**
> Product: Space
> Runtime: Python
> Description: I am trying to make a request to a private route in my app from outside of Space, but I am receiving a `401 Unauthorized` response. I am using Python and FastAPI for the backend. How can I resolve this?
> 
> Server route handler:
> ```py
> @app.post("/my-route")
> async def my_route(data):
>     return 201, data
> ```
> Request code:
> ```py
> ...
> headers = {
>     "X-Space-App-Key": "my space app key",
>     "Content-Type": "application/json",
> }
> r = requests.post(url="https://example.deta.app/my-route", headers=headers, json=data)
> ```
> Spacefile:
> ```yaml
> v: 0
> micros:
>   - name: my-app
>     src: .
>     engine: python3.9
>     primary: true
> ```
