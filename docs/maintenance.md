# Subscription pipeline

## Source registry

`combine/sources.json` is the source of truth for provider names, formats, and URLs. The input files `clashsub.txt` and `v2raysub.txt` and the marked source lists in the English and Chinese guides are generated; edit the registry rather than those sections. Whenever a link leaves a generated subscription section, the generator appends its exact URL to that guide's existing `<!-- Archived Reference:` block. Disabled registry URLs are also included there. Existing archive entries are preserved and deduplicated; never discard a removed source URL.

Each source has a unique lowercase `id`, a display `name`, a boolean `enabled`, and a `formats` object containing `clash`, `v2ray`, or both. Every format needs a public HTTPS `url`. Credentials in source URLs are rejected. Optional `notes` explain disabled or historical sources. Each format may also set `enabled: false` and its own `notes`; this skips only that feed while leaving other formats active. Provider-level `enabled: false` skips every format. Disabled sources remain visible with their reasons in the health report. Disabling is a manual registry decision, not an automatic response to a single failed request.

```json
{
  "id": "example",
  "name": "Example",
  "enabled": true,
  "formats": {
    "clash": {
      "url": "https://example.com/fallback.yaml",
      "date_pattern": "https://example.com/{year}/{month}/{date}.yaml"
    }
  }
}
```

For dated feeds, `{year}` is four digits, `{month}` is two digits, and `{date}` is `YYYYMMDD`, using UTC. The refresher tries today, yesterday, and the day before, followed by the last usable URL and the configured fallback. It accepts a candidate only if parsing yields entries; an HTTP 200 HTML error page is insufficient. Static feeds use their configured URL. Disabled legacy guide sources are retained in the registry for reference and excluded from generated subscription lists.

## Commands

Run from the repository root. Set up the environment once:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

```sh
python -m combine.sources          # regenerate lists and guide sections, offline
python -m combine.sources --check  # fail on generated-file drift, offline
python -m unittest discover -s combine/tests -v
python -m combine.install_engine --output /tmp/mihomo
python -m combine.refresh --mihomo /tmp/mihomo  # validate with the engine before publication
python -m combine.refresh --output-dir /tmp/subscription-check
```

The isolated output option writes both subscriptions, a timestamp, and health reports into the chosen directory without changing the repository's published files or guides. `python combine/combine.py` delegates to the same refresh command. The old `.github/workflows/update.py` entry point now delegates to offline link generation.

## Validation and publication

Fetches run with four workers, TLS verification, a five-second connection timeout, and a twenty-second read timeout. Timeouts, connection failures, incomplete transfers, and HTTP 408, 429, 500, 502, 503, and 504 responses retry at most three request attempts with one- and two-second backoffs. Other HTTP failures, certificate errors, invalid UTF-8, and oversized responses are not retried. Downloads stream with a 5 MiB limit on decoded response bytes; a declared larger response is rejected before reading its body. Read timeouts apply between received chunks, not to the whole transfer. Source health distinguishes `fetch_failed`, `unusable` (downloaded but no recognized entries), and `parsed`. The detailed JSON includes attempted URLs, individual request attempts, HTTP status, failure category, received byte counts, and the last successful fetch time, without downloaded content or exception messages. The Markdown report shows the final HTTP result and total number of requests across candidate URLs.

Clash validation checks the proxy collection, required string fields, port ranges, and JSON-compatible values that can be encoded as UTF-8. Malformed Unicode entries are skipped so a bad upstream node cannot abort merging. Connection settings determine duplicate identity; source names do not. Generated names retain an upstream label (up to 64 characters) plus a 16-character connection ID. Duplicate copies choose the lexicographically smallest normalized label so source order does not change the result. Short-ID collisions extend the suffix. Labels or connection settings changing can change the displayed name; selection state from the earlier hash-only names may need to be set again after refresh. Blacklists apply to server/port pairs. V2Ray supports plain and base64 URI lists, deduplicating identical URI lines. Protocol checks also require credentials and cipher fields for SS/SSR, valid UUIDs for VMess/VLESS and TUIC v5, nonnegative VMess alterId, and correctly typed WebSocket headers and transport options. VMess JSON, SS user-info and legacy Base64, SSR payloads, and URI endpoints are decoded and checked before admission. Invalid entries are skipped; unknown Clash protocol types still receive structural checks and must pass the engine gate. URI support includes the hy2 alias. These checks do not exhaust every protocol option and do not test connectivity.

Both formats must produce nonempty merged outputs before either subscription is replaced. By default, each format must also retain at least 50% of the entry count in its currently published file. If either format falls below that threshold, both subscriptions and their timestamp are preserved while health reports show the attempted counts and blocking errors. The baseline counts structurally recognized entries in the published files without applying the new protocol filters, so stricter validation and repeated failed attempts do not lower the guard baseline. This guards against major source outages; it does not measure node quality or prevent smaller losses. For an intentional reduction, inspect the report and run `python -m combine.refresh --min-retained-ratio 0`. Values between 0 and 1 configure the threshold; empty outputs are always rejected. Individual files are replaced atomically. This is not a filesystem transaction across all files; an operating-system write failure can still interrupt local publication. GitHub publishes completed changes together in a commit.

`combine/.timestamp` advances only on successful publication. `combine/health.json` and `combine/health.md` are updated even when source failures prevent publication. Their current merged totals describe this attempt; `last_successful_publication` identifies the previous successful update. A successful fetch of an older dated feed does not establish freshness of its nodes.

The workflow uploads health reports as an artifact, commits the report even on a normal unsuccessful refresh, and then marks that run failed. Tests run before network access; missing dependencies, invalid registry configuration, and unexpected exceptions fail the job. Scheduled updates target this repository; forks can run manual updates. Commits use Codex as sole author. Publication uses at most three normal push attempts. After a rejected push, it fetches main and rebases the refresh commit before retrying. A rebase conflict aborts publication and leaves remote changes intact; no force push is used. The update checkout includes full history for rebasing.

## GitHub Actions runtime

Workflows use Ubuntu 24.04 and explicit official action releases: checkout 7.0.1, setup-python 7.0.0, and upload-artifact 7.0.2. Python remains 3.11. Both the normal checks and the subscription workflow are verified after upgrades.

## Remaining improvements

* Finish the installation-guide review: replace historical client instructions and verify third-party download and tutorial links. The initial pass adds official current-client downloads; full guide modernization remains open.
* Investigate unresolved providers and periodically recheck disabled feeds.

## Client-engine validation

Both workflows install official [Mihomo v1.19.32](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.32), pinned by release asset and SHA-256 digest. The installer supports Linux x86_64 and macOS arm64; other platforms can supply their own executable. The scheduled refresh requires `--mihomo` and runs the engine's `-t` configuration test against the complete merged Clash configuration in a temporary directory before either subscription or the timestamp is replaced. The engine may fetch required geodata during configuration parsing. A missing executable, rejection, or 90-second timeout preserves both published outputs and records failure in the health report. Engine output is suppressed to avoid exposing credentials in errors.

Local refreshes without `--mihomo` still perform protocol validation but record engine status as `not_requested`; use the command above to require it. CI tests the committed configuration independently. For a detailed engine error, run `mihomo -t -d /tmp/mihomo-check -f combine/clash.config.yaml` locally and keep any credential-bearing output private. The URI subscription receives protocol-field checks, not a full client-engine import test. Engine acceptance establishes compatibility with this Mihomo release, not every legacy Clash client or working node connections.

Protocol checks follow the [Mihomo proxy documentation](https://wiki.metacubex.one/en/config/proxies/); the test command is defined in the [pinned engine implementation](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/main.go).
