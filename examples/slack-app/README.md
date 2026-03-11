# Slack MCP — Databricks App Bundle

A self-contained MCP server for the Slack Web API, deployed as a Databricks App. Generated from [`../slack-openapi.yaml`](../slack-openapi.yaml) using `uc-mcp generate`.

## Tools (21)

| Category | Tools |
|---|---|
| **Auth** | `auth_test` |
| **Chat** | `chat_postMessage`, `chat_update`, `chat_delete`, `chat_getPermalink`, `chat_postEphemeral` |
| **Conversations** | `conversations_list`, `conversations_info`, `conversations_history`, `conversations_replies`, `conversations_members`, `conversations_join` |
| **Users** | `users_list`, `users_info`, `users_getPresence` |
| **Reactions** | `reactions_add`, `reactions_remove`, `reactions_get` |
| **Search** | `search_messages` |
| **Files** | `files_list`, `files_info` |

> `conversations_list` covers both channels and DMs — pass `types=public_channel`, `types=private_channel`, `types=im`, or `types=mpim` to filter.

## How This Was Generated

```bash
# 1. Start from the full Slack Web API OpenAPI spec (archived, read-only)
#    https://github.com/slackapi/slack-api-specs

# 2. Extract the 21 most useful operations into a curated spec
#    (see examples/slack-openapi.yaml)

# 3. Generate the Databricks App bundle
uc-mcp generate examples/slack-openapi.yaml \
  --connection slack \
  --name slack \
  -o examples/slack-app
```

To regenerate after modifying `slack-openapi.yaml`:

```bash
uc-mcp generate examples/slack-openapi.yaml --connection slack --name slack -o examples/slack-app
```

## Prerequisites

- A Databricks workspace with a UC connection named `slack` pointing to the Slack API
- [Databricks CLI](https://docs.databricks.com/en/dev-tools/cli/index.html) installed and configured
- [uv](https://docs.astral.sh/uv/) installed

## Deploy

```bash
cd examples/slack-app
databricks bundle deploy
databricks bundle run
```

The app will be available at your Databricks Apps URL with the MCP endpoint at `/mcp`.

## Auth

The app handles three auth scenarios automatically:

| Scenario | Mechanism |
|---|---|
| Databricks Apps (user-facing) | `X-Forwarded-Access-Token` → per-user `WorkspaceClient` |
| Model Serving | Model Serving credentials context |
| Local dev / service principal | Default `WorkspaceClient()` from environment |

All Slack API calls are proxied through the `slack` UC connection — your Slack token lives in the connection, not in the app.
