# Subscription discovery — 2026-10-10

Candidate URLs were found in the providers' own repositories and tested with the bounded downloader and existing parsers. Accepted feeds were HTTP 200, nonempty, and last committed on the day of this review. Connectivity and full client compatibility were not tested. Entry counts are a snapshot, not a guarantee of future availability.

| Provider | Format | Parsed entries | Additional entries versus previous output | Last feed commit (UTC) | Decision |
| --- | --- | ---: | ---: | --- | --- |
| [V2RayShare](https://raw.githubusercontent.com/firefoxmmx2/v2rayshare_subcription/main/subscription/clash_sub.yaml) | clash | 21 | 21 | 2026-09-23T08:48:30Z | Inactive: older feed |
| [V2RayShare](https://raw.githubusercontent.com/firefoxmmx2/v2rayshare_subcription/main/subscription/vray_sub.txt) | v2ray | 22 | 22 | 2026-09-23T08:48:30Z | Inactive: older feed |
| [Zhuhai Free Nodes](https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/clash_config.yaml) | clash | 32 | 30 | 2026-10-10T05:42:50Z | Enabled |
| [Zhuhai Free Nodes](https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/nodes.txt) | v2ray | 4 | 4 | 2026-10-10T05:42:50Z | Enabled |
| [Free18](https://raw.githubusercontent.com/free18/v2ray/main/c.yaml) | clash | 203 | 198 | 2026-10-10T04:38:19Z | Enabled |
| [Free18](https://raw.githubusercontent.com/free18/v2ray/main/v.txt) | v2ray | 215 | 215 | 2026-10-10T04:37:58Z | Enabled |
| [Free Nodes](https://raw.githubusercontent.com/free-nodes/v2rayfree/main/sub) | v2ray | 578 | 578 | 2026-10-10T05:08:08Z | Enabled |

Additional counts compare each candidate independently with the previous outputs; they do not account for overlap between candidates. Final merged counts are in [source health](../combine/health.md).

V2RayShare parsed successfully, but its September 23 feed commits were older than the other candidates. It is retained disabled in the registry and in each relevant guide's Archived Reference block. This is a manual admission decision for this review, not an automatic source-expiration policy.

## Provider endpoint follow-up

Provider repositories were checked for redirects and replacement URLs, rather than treating failures at old endpoints as permanent provider inactivity. Credits include historical contributions; current feed status is tracked separately.

| Provider | Finding | Decision |
| --- | --- | --- |
| Mfuu | [clash](https://raw.githubusercontent.com/mfuu/FreeProxies/master/sub.yaml): HTTP 200, 0 parsed entries | Disabled pending usable content |
| Mfuu | [v2ray](https://raw.githubusercontent.com/mfuu/FreeProxies/master/sub): HTTP 200, 463 parsed entries | Enabled |
| Learnhard-cn | [clash](https://raw.githubusercontent.com/vxiaov/free_proxies/main/clash/clash.provider.yaml): HTTP 200, 28 parsed entries | Enabled |
| Xrayfree | [clash](https://www.xrayvip.com/free.yaml): HTTP 200, 56 parsed entries | Enabled |
| Xrayfree | [v2ray](https://www.xrayvip.com/free.txt): HTTP 200, 56 parsed entries | Enabled |
| Freefq | [v2ray](https://bulinkbulink.com/freefq/free/master/v2): HTTP 410, 0 parsed entries | Disabled pending usable content |
| OpenRunner | [clash](https://free.datiya.com/uploads/20261010-clash.yaml): HTTP 200, 14 parsed entries | Enabled |
| OpenRunner | [v2ray](https://free.datiya.com/uploads/20261010-v2ray.txt): HTTP 200, 0 parsed entries | Disabled pending usable content |

Mfuu moved to [FreeProxies](https://github.com/mfuu/FreeProxies); its current Clash feed contains invalid YAML. Learnhard moved to [Vxiaov free_proxies](https://github.com/vxiaov/free_proxies). Oslook redirects to [OpenRunner](https://github.com/OpenRunner/clash-freenode), whose dated feeds now use free.datiya.com. Aiboboxx redirects to [Free Nodes](https://github.com/free-nodes/v2rayfree), already enabled in the registry; duplicate historical entries remain disabled. Freefq's documented replacement returned HTTP 410. NodeFree remains unresolved and Vveg26's historical repository returned 404. No connectivity claims are made. Replaced subscription and credit URLs are preserved in the relevant guides' Archived Reference blocks.

The first combined refresh exposed malformed Unicode in an upstream Clash entry. The parser now rejects nodes that cannot be encoded as UTF-8, with a regression test covering names and connection values.
