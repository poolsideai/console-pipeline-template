# First Pipeline Starter

A minimal Bridge SDK project with two steps:

1. **`build_research_brief`** (programmatic) — turns a topic into a structured brief with questions
2. **`investigate`** (agent) — passes the brief to a Poolside agent, parses the JSON output

This is the canonical Bridge pattern: programmatic step prepares context, agent step reasons over it.

## Prerequisites

- Python 3.11+
- `uv` (https://docs.astral.sh/uv/getting-started/installation/)
- Access to the `poolsideai/bridge-sdk` repo

## Setup

```bash
uv sync
```

That installs the Bridge SDK from GitHub and the project itself in editable mode.

## Validate locally

```bash
uv run bridge check
uv run bridge config get-dsl
```

`bridge check` confirms the SDK can discover the pipeline. `config get-dsl` prints the pipeline + step definitions as JSON, which is what Bridge indexes when you push.

## Run the programmatic step locally

```bash
uv run bridge run \
  --step build_research_brief \
  --input '{"input_data": {"topic": "incident response automation"}}' \
  --results '{}'
```

You should see the `ResearchBrief` printed as JSON.

## Important: set the agent name before running in Bridge

The agent step calls `BridgeExecutionClient.start_agent(prompt=..., agent_name=...)`. The bundle ships with a placeholder name `starter-agent`, **which does not exist in your tenant**. The agent step will fail with an unknown-agent error until you replace it with a real agent name.

**Find an agent name:** open the **Agents** page in Bridge Console. You have view permission on every agent in the tenant. Pick one and copy its exact name.

**Set it in the project:** open `first_pipeline/steps.py` and change the default in the `investigate` step:

```python
agent_name=os.environ.get("BRIDGE_AGENT_NAME", "starter-agent"),
                                                # ^^^^^^^^^^^^^^
                                                # replace with the agent name from the Agents page
```

Commit and push. The next index (manual via **+ Index** or automatic via the GitHub Action) will pick up the new agent name.

## Run the agent step locally

The agent step calls `BridgeExecutionClient.start_agent(...)`, which only works inside a Bridge sandbox or with the Bridge execution API reachable. Running it locally will produce a connection error — that is expected. You will run this step in Bridge once the repo is indexed.

## Push to Bridge

### A. Push the repo to GitHub

Create a private repo on GitHub (e.g. `<your-org>/first-pipeline-starter`) and push this project.

### B. Create a GitHub Personal Access Token

Bridge needs read access to your repo. Create a classic PAT in GitHub:

1. GitHub > **Settings** > **Developer settings** > **Personal access tokens** > **Tokens (classic)**
2. **Generate new token (classic)**
3. Scopes: tick **`repo`** (full) and **`write:packages`**
4. Set an expiration that matches your security policy
5. **Generate token** and copy the value (it is only shown once)

### C. Store the PAT as a credential in Bridge Console

1. Open Bridge Console: https://XYZ.poolsi.de/console
2. Go to **Security** > **Credentials** > **New Credential**
3. Fill in:
   - **Name**: an uppercase identifier, e.g. `XYZ_GITHUB_PAT` (this convention matches existing credentials in the tenant)
   - **Data**: paste the PAT value you copied above
4. **Save**. The credential appears in the list with a UUID.

### D. Register the repository in Bridge

1. Go to **Orchestration** > **Repositories** > **New Repository**
2. Fill in the form:
   - **Name**: `first-pipeline-starter` (short label, shown across the UI)
   - **Provider**: `GitHub`
   - **Remote URL**: `https://github.com/<your-org>/first-pipeline-starter.git`
   - **Default Branch**: `main`
   - **Username**: the GitHub username that owns the PAT
   - **Credential (PAT/Token)**: select the credential created in step C
3. **Save**. You land on the **Edit Repository** page. Note the **ID** shown near the top — you will need it for the GitHub Action.

### E. Index the main branch

Still on the **Edit Repository** page:

1. Scroll to **Index Commits**
2. Leave **Branch** as `main` and **Commit Hash** empty (uses the latest commit)
3. Click **+ Index**
4. Wait for the row in **Indexed Commits** to reach status `finished` (a few seconds for a small repo)

Bridge now knows about your pipeline and its steps.

### F. Run the pipeline from Console

1. Go to **Orchestration** > **Pipelines**
2. Find **`first_pipeline`** in the list and click into it
3. Trigger a run with this input:

   ```json
   {"topic": "incident response automation"}
   ```

4. The run will execute `build_research_brief` (programmatic, fast), then `investigate` (agent step, takes longer because it provisions a sandbox and invokes the agent)
5. Open the build to inspect each step's input, output, and agent trajectory

### G. (Optional) Auto-index on every push

The included GitHub Action (`.github/workflows/bridge-index.yml`) re-indexes the branch on every push, so you do not have to click **+ Index** in Console after each change.

#### G1. Create a Bridge API key

1. In Bridge Console, go to **Security** > **API Keys**
2. Click **Create API Key**
3. **Team**: select **developer** (the team your users belong to)
4. The key needs permission to call the commit indexing endpoints:
   - `POST /v0/bridge/repositories/{id}/commits` (trigger indexing)
   - `GET  /v0/bridge/repositories/{id}/commits/{commit_id}` (poll status until `finished`)

   These map to "read and create commits on Bridge repositories" in the permission group selector. If the **developer** team does not already include those, ask your Poolside contact to grant them before generating the key.
5. **Create** the key and copy the value (starts with `ps-`, shown once)

#### G2. Add the three secrets in GitHub

In the GitHub repo you pushed in step A:

1. **Settings** > **Secrets and variables** > **Actions** > **New repository secret**
2. Add each of the following, one secret at a time (click **Add secret** after each):

   | Secret name | Value |
   |-------------|-------|
   | `BRIDGE_REPOSITORY_ID` | The **ID** shown at the top of the **Edit Repository** page (from step D) |
   | `BRIDGE_API_TOKEN`     | The API key from G1 (the `ps-…` string) |
   | `BRIDGE_API_URL`       | `https://api.XYZ.poolsi.de` (your Poolside contact will confirm the exact value, typically `https://api.poolsi.de`) |

The next push to any branch will trigger `.github/workflows/bridge-index.yml`. Open the **Actions** tab in GitHub to watch the run. The action calls the Bridge indexing endpoint and polls until it reports `finished`, then writes the resulting `commit_id` as a workflow output.

## Files

```
first-pipeline-starter/
├── main.py                              # CLI entrypoint
├── pyproject.toml                       # deps + [tool.bridge] config
├── first_pipeline/
│   ├── __init__.py
│   └── steps.py                         # pipeline definition
└── .github/workflows/bridge-index.yml   # auto-index on push
```

## Next steps

- Add a third programmatic step that **validates** the agent's JSON output (extract fields, check completeness). Never trust raw agent output downstream.
- Replace the dummy questions in `build_research_brief` with real data fetched from your systems (CMDB, ITSM, Linear, etc.).
- Add credentials via `credential_bindings` on the agent step if it needs API tokens.
- Bind an eval with `@bridge_eval` to score the agent's findings on each run.

See the full SDK reference: https://github.com/poolsideai/bridge-sdk
