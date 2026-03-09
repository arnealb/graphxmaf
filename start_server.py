# start_server.py
from os import environ
from microsoft_agents.hosting.aiohttp import start_agent_process, CloudAdapter
from aiohttp.web import Request, Response, Application, run_app

def start_server(agent_application, auth_configuration=None):
    async def entry_point(req: Request) -> Response:
        return await start_agent_process(req, req.app["agent_app"], req.app["adapter"])

    app = Application()
    app["agent_app"] = agent_application
    app["adapter"] = agent_application.adapter
    app.router.add_post("/api/messages", entry_point)
    app.router.add_get("/api/messages", lambda _: Response(text="OK"))
    run_app(app, host="0.0.0.0", port=int(environ.get("PORT", 3978)))