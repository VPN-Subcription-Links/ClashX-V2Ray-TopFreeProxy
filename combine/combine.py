import requests
import urllib3
import yaml
import os

from typing import Any, Dict, List, Optional

# Change the current working directory to the directory where this script resides
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ignore InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# initiate file names
clash_output_tpl: str = './clash.config.template.yaml'
clash_output_file: str = './clash.config.yaml'
v2ray_output_file: str = './v2ray.config.txt'

# clash links
clash_url_list: List[str] = list()
file = open('./clashsub.txt', 'r')
links: List[str] = file.readlines()
[clash_url_list.append(l.strip()) for l in links]
file.close()

# v2ray links
v2ray_url_list: List[str] = list()
file = open('./v2raysub.txt', 'r')
links: List[str] = file.readlines()
[v2ray_url_list.append(l.strip()) for l in links]
file.close()

# blacklist
blacklist: List[str] = list(map(lambda l: l.strip().split(':'), open('./blacklists.txt').readlines()))


# get content of a html
def fetch_html(url: str):
    try:
        resp: requests.Response = requests.get(url, verify=False, timeout=10)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            print(f'[!] Got HTTP Status Code {resp.status_code}')
            return None
        return resp.text
    except Exception as expt:
        print(url)
        print(expt)
        return None


# merge clash config files
def merge_clash(configs: List[str]) -> str:
    config_template: Dict[str, Any] = yaml.safe_load(open(clash_output_tpl).read())
    proxies: List[Dict[str, Any]] = []
    for i in range(len(configs)):
        try:
            tmp_config: Dict[str, Any] = yaml.safe_load(configs[i])
        except Exception:
            print(f'[!] Failed to Load a YAML')
            continue

        if 'proxies' not in tmp_config: continue
        for j in range(len(tmp_config['proxies'])):
            proxy: Dict[str, Any] = tmp_config['proxies'][j]
            if any(filter(lambda p: p[0] == proxy['server'] and str(p[1]) == str(proxy['port']), blacklist)): continue
            if any(filter(lambda p: p['server'] == proxy['server'] and p['port'] == proxy['port'], proxies)): continue
            proxy['name'] = proxy['name'] + f'_{i}@{j}'
            proxies.append(proxy)
    node_names: List[str] = list(map(lambda n: n['name'], proxies))
    config_template['proxies'] = proxies
    for grp in config_template['proxy-groups']:
        if 'xxx' in grp['proxies']:
            grp['proxies'].remove('xxx')
            grp['proxies'].extend(node_names)

    return yaml.safe_dump(config_template, indent=1, allow_unicode=True)


# merge v2ray config files
def merge_v2ray(configs: List[Optional[str]]) -> str:
    return '\n'.join(filter(None, configs))


def main():
    print(f'[+] Got {len(clash_url_list)} Clash URLs, {len(v2ray_url_list)} V2Ray URLs')

    # store html associated with each link
    clash_configs: List[str] = list(map(lambda u: fetch_html(u), clash_url_list))
    v2ray_configs: List[str] = list(map(lambda u: fetch_html(u), v2ray_url_list))

    # merge clash / v2ray configs
    clash_merged: str = merge_clash(clash_configs)
    v2ray_merged: str = merge_v2ray(v2ray_configs)

    # write output files
    with open(clash_output_file, 'w') as f:
        f.write(clash_merged)
    with open(v2ray_output_file, 'w') as f:
        f.write(v2ray_merged)


if __name__ == '__main__':
    main()
