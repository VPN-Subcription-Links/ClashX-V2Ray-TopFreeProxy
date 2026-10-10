"""Install a pinned, checksum-verified official Mihomo binary for validation."""
import argparse
import gzip
import hashlib
import os
from pathlib import Path
import platform
import tempfile

import requests

VERSION = 'v1.19.32'
ASSETS = {
    ('Linux', 'x86_64'): ('mihomo-linux-amd64-compatible-v1.19.32.gz',
                         'ba3ce607747a07f948fc35780e108a4a7c7f552a38b9bd4d115f313ebcb89c20'),
    ('Darwin', 'arm64'): ('mihomo-darwin-arm64-v1.19.32.gz',
                         '3312a6780652c622890fd4357c6a853bbf865464fd047ac7b7f52dab8de18652'),
}


def install(destination):
    asset = ASSETS.get((platform.system(), platform.machine()))
    if asset is None:
        raise ValueError('Installer supports Linux x86_64 and macOS arm64; supply your own Mihomo binary on other platforms')
    name, expected = asset
    url = f'https://github.com/MetaCubeX/mihomo/releases/download/{VERSION}/{name}'
    data = bytearray()
    with requests.get(url, stream=True, timeout=(5, 30)) as response:
        response.raise_for_status()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > 50 * 1024 * 1024:
                raise ValueError('Mihomo download exceeds 50 MiB')
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Mihomo checksum mismatch')
    binary = gzip.decompress(data)
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write(binary)
    try:
        temporary.chmod(0o755)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(f'Installed Mihomo {VERSION}: {install(args.output)}')


if __name__ == '__main__':
    main()
