# Free web search for Brainwave ARC

Brainwave ARC defaults to `WEB_SEARCH_PROVIDER=free`. No paid web-search
provider is called in this mode, even when Brave or Serper keys are present.

## Without signing up

No search key is needed for the DuckDuckGo fallback. This path uses public
DuckDuckGo endpoints rather than a supported guaranteed-availability API, so
results can be incomplete, rate-limited, or blocked.

## Recommended: Tavily Free

1. Create a **Researcher / Free** account at https://app.tavily.com/.
2. Copy your API key (do not commit it or paste it in chat).
3. Set `TAVILY_API_KEY=...` in your deployment's server-side `.env`.
4. Leave `WEB_SEARCH_PROVIDER=free`.
5. Restart the API and worker containers so they load the new environment.
6. Add `TAVILY_API_KEY` to GitHub **Settings > Secrets and variables >
   Actions > New repository secret** for workflow verification.
7. Run **Live Integration Smoke** on `main`. Full manual verification also
   requires a configured Groq key.

Tavily advertises **1,000 credits/month with no credit card** on its Free
plan. A basic search costs one credit; API quotas can change. When free
credits are exhausted, Tavily rejects requests until the allowance resets
(or the account upgrades), and free mode falls back to DuckDuckGo.

The credentials used for GitHub Actions **do not automatically configure a
separately deployed app**. Configure the deployment environment too.

**Important:** To avoid charges, keep the Tavily account on Free and do
not opt in to Pay As You Go. `free` is a provider allowlist, **not** a
billing enforcement mechanism for a Tavily account that has been upgraded.

Other modes remain opt-in: `auto` allows configured Brave, Tavily, and
Serper; `tavily` uses Tavily only and fails closed if unavailable.

Sources:
- https://www.tavily.com/pricing
- https://docs.tavily.com/documentation/api-reference/endpoint/search
