from mcp.server.fastmcp import FastMCP
import os
import logging
import requests
from azure.identity import ClientSecretCredential

logging.basicConfig(level=logging.INFO)
logging.info("Starting Microsoft Graph MCP server")

mcp = FastMCP("graph")

# ======================
# CONFIG
# ======================

TENANT_ID = os.environ["TENANT_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]


credential = ClientSecretCredential(
    tenant_id=TENANT_ID,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

def get_access_token():
    token = credential.get_token("https://graph.microsoft.com/.default")
    return token.token


# ======================
# TOOLS
# ======================

@mcp.tool()
def get_users() -> list[dict]:
    """
    Fetch all users from Microsoft Graph.
    """
    token = get_access_token()
    print(token)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    r = requests.get(
        "https://graph.microsoft.com/v1.0/users",
        headers=headers
    )

    r.raise_for_status()

    data = r.json().get("value", [])

    simplified = [
        {
            "id": u.get("id"),
            "displayName": u.get("displayName"),
            "mail": u.get("mail"),
            "userPrincipalName": u.get("userPrincipalName"),
        }
        for u in data
    ]

    return simplified


@mcp.tool()
def get_user_by_id(user_id: str) -> dict:
    """
    Fetch a specific user by ID.
    """
    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    r = requests.get(
        f"https://graph.microsoft.com/v1.0/users/{user_id}",
        headers=headers
    )

    r.raise_for_status()

    return r.json()


# ======================
# ENTRYPOINT
# ======================

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
