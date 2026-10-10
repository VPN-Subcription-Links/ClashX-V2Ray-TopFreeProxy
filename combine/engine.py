"""Run Mihomo's configuration test without exposing upstream credentials."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


class EngineValidationError(ValueError):
    pass


def validate_clash(content, executable):
    executable = shutil.which(str(executable))
    if executable is None:
        raise EngineValidationError('Mihomo executable not found; previous subscriptions retained')
    with tempfile.TemporaryDirectory(prefix='subscription-validation-') as directory:
        config = Path(directory) / 'config.yaml'
        config.write_text(content, encoding='utf-8')
        try:
            # Test mode parses configuration and exits; it does not start a proxy.
            result = subprocess.run([executable, '-t', '-d', directory, '-f', str(config)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=90, check=False)
        except subprocess.TimeoutExpired:
            raise EngineValidationError('Mihomo configuration test timed out; previous subscriptions retained') from None
        except OSError:
            raise EngineValidationError('Mihomo could not run; previous subscriptions retained') from None
        if result.returncode:
            raise EngineValidationError(f'Mihomo configuration test failed (exit {result.returncode}); previous subscriptions retained')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--mihomo', default='mihomo')
    args = parser.parse_args()
    try:
        validate_clash(args.config.read_text(encoding='utf-8'), args.mihomo)
    except EngineValidationError as exc:
        print(str(exc))
        return 1
    print('Mihomo configuration test passed. Node connectivity was not tested.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
