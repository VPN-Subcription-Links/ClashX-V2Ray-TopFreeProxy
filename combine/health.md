# Subscription source status / 订阅来源状态

Checked (UTC): 2026-11-25T00:29:37Z

Published this run: no; previous outputs retained

Last successful publication (UTC): 2026-11-23T20:00:15Z

Status describes fetching and parsing only. Node connectivity has not been tested.
状态仅表示获取与解析结果，不代表节点可连接。

| Source | Format | Status | Parsed entries | HTTP | Detail | Requests |
| --- | --- | --- | ---: | ---: | --- | ---: |
| Mfuu | v2ray | parsed | 10 | 200 | — | 1 |
| Anaer | clash | parsed | 1770 | 200 | — | 1 |
| Pojiezhiyuanjun | v2ray | parsed | 149 | 200 | — | 1 |
| Ermaozi | clash | parsed | 381 | 200 | — | 1 |
| Ermaozi | v2ray | unusable | 0 | 200 | no_recognized_entries | 1 |
| Learnhard-cn | clash | parsed | 28 | 200 | — | 1 |
| Learnhard-cn | v2ray | parsed | 8 | 200 | — | 1 |
| OpenRunner | clash | parsed | 24 | 200 | — | 2 |
| Xrayfree | clash | parsed | 28 | 200 | — | 1 |
| Xrayfree | v2ray | parsed | 28 | 200 | — | 1 |
| Zhuhai Free Nodes | clash | parsed | 38 | 200 | — | 1 |
| Zhuhai Free Nodes | v2ray | parsed | 4 | 200 | — | 1 |
| Free18 | clash | parsed | 166 | 200 | — | 1 |
| Free18 | v2ray | parsed | 166 | 200 | — | 1 |
| Free Nodes | v2ray | parsed | 16 | 200 | — | 1 |

Detailed fetch attempts and last usable URLs: [health.json](health.json).

The merged totals exclude duplicate entries and blacklisted Clash endpoints.

Merged Clash entries: 2414; V2Ray entries: 380.

| Format | Previously published entries | This attempt |
| --- | ---: | ---: |
| clash | 2932 | 2414 |
| v2ray | 1124 | 380 |

Minimum retained ratio: 0.5.

## Refresh errors / 刷新错误

* v2ray entries dropped from 1124 to 380; minimum retained ratio is 0.5. Preserving both subscriptions; verify source failures or use --min-retained-ratio 0 for an intentional reduction.

Mihomo configuration validation: passed.

Engine validation checks configuration compatibility, not node connectivity.

## Disabled sources / 已停用来源

Retained for reference; skipped during refresh. Re-enable in the registry after verification.
保留来源记录；刷新时跳过。确认可用后可在目录中重新启用。

| Source | Format | Reason |
| --- | --- | --- |
| NodeFree | clash | 2026-10-10 UTC: fetch_failed in two live checks; no parsed entries. Re-enable after verifying the feed. |
| NodeFree | v2ray | 2026-10-10 UTC: fetch_failed in two live checks; no parsed entries. Re-enable after verifying the feed. |
| Mfuu | clash | 2026-10-10 UTC: replacement endpoint from provider documentation; HTTP 200, 0 parsed entries. Node connectivity not tested. Invalid YAML: unescaped quotes in a node name; retained disabled. |
| Pojiezhiyuanjun | clash | 2026-10-10 UTC: unusable in two live checks; no parsed entries. Re-enable after verifying the feed. |
| Oslook | clash | 2026-10-10 UTC: fetch_failed in two live checks; no parsed entries. Re-enable after verifying the feed. |
| Vveg26 | clash | 2026-10-10 UTC: fetch_failed in two live checks; no parsed entries. Re-enable after verifying the feed. |
| Vveg26 | v2ray | 2026-10-10 UTC: fetch_failed in two live checks; no parsed entries. Re-enable after verifying the feed. |
| Aiboboxx | v2ray | 2026-10-10 UTC: fetch_failed in two live checks; no parsed entries. Re-enable after verifying the feed. |
| OpenRunner | v2ray | 2026-10-10 UTC: replacement endpoint from provider documentation; HTTP 200, 0 parsed entries. Node connectivity not tested. |
| Freefq | v2ray | 2026-10-10 UTC: replacement endpoint from provider documentation; HTTP 410, 0 parsed entries. Node connectivity not tested. |
| V2RayShare | clash | 2026-10-10 UTC: HTTP 200 and 21 parsed entries; feed last committed 2026-09-23T08:48:30Z. Node connectivity not tested. Held inactive because the feed has not been updated since September 23; verify freshness before enabling. |
| V2RayShare | v2ray | 2026-10-10 UTC: HTTP 200 and 22 parsed entries; feed last committed 2026-09-23T08:48:30Z. Node connectivity not tested. Held inactive because the feed has not been updated since September 23; verify freshness before enabling. |
