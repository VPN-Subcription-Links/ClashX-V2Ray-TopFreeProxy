import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / '.github/workflows/publish.sh'


class PublicationTests(unittest.TestCase):
    def test_publication_races_and_conflicts(self):
        for scenario in ('clean', 'race', 'conflict', 'repeated'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                remote, worker, other = (root / name for name in ('remote.git', 'worker', 'other'))
                real_git = shutil.which('git')
                env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1',
                           GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_AUTHOR_NAME='Codex', GIT_AUTHOR_EMAIL='codex@openai.com',
                           GIT_COMMITTER_NAME='Codex', GIT_COMMITTER_EMAIL='codex@openai.com')
                def git(*args, cwd=root):
                    return subprocess.run([real_git, *args], cwd=cwd, env=env,
                                          capture_output=True, text=True, check=True).stdout.strip()
                git('init', '--bare', '--initial-branch=main', str(remote))
                git('clone', str(remote), str(worker))
                (worker / 'output').write_text('original\n')
                (worker / 'notes').write_text('original\n')
                git('add', '.', cwd=worker)
                git('commit', '-m', 'initial', cwd=worker)
                git('push', 'origin', 'main', cwd=worker)
                git('clone', str(remote), str(other))
                (worker / 'output').write_text('refreshed\n')
                git('add', '.', cwd=worker)
                git('commit', '-m', 'refresh', cwd=worker)
                wrapper = root / 'bin'
                wrapper.mkdir()
                hook = wrapper / 'git'
                hook.write_text(f'''#!{shutil.which('python3')}
import os, pathlib, subprocess, sys
real = {real_git!r}
if sys.argv[1:2] == ['push']:
    counter = pathlib.Path({str(root / 'attempts')!r})
    n = int(counter.read_text()) + 1 if counter.exists() else 1
    counter.write_text(str(n))
    scenario = {scenario!r}
    if scenario == 'repeated' or (n == 1 and scenario in ('race', 'conflict')):
        other = pathlib.Path({str(other)!r})
        target = 'output' if scenario == 'conflict' else 'notes'
        (other / target).write_text('concurrent ' + str(n) + '\\n')
        for args in [('add', '.'), ('commit', '-m', 'concurrent ' + str(n)), ('push', 'origin', 'main')]:
            subprocess.run([real, *args], cwd=other, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
os.execv(real, [real, *sys.argv[1:]])
''')
                hook.chmod(0o755)
                result = subprocess.run(['bash', str(SCRIPT)], cwd=worker,
                                        env=dict(env, PATH=str(wrapper) + os.pathsep + env['PATH']),
                                        capture_output=True, text=True)
                attempts = int((root / 'attempts').read_text())
                if scenario in ('clean', 'race'):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(attempts, 1 if scenario == 'clean' else 2)
                    self.assertEqual(git('show', 'main:output', cwd=remote), 'refreshed')
                    if scenario == 'race':
                        self.assertEqual(git('show', 'main:notes', cwd=remote), 'concurrent 1')
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(attempts, 1 if scenario == 'conflict' else 3)
                    self.assertEqual(git('show', 'main:output', cwd=remote),
                                     'concurrent 1' if scenario == 'conflict' else 'original')
                    self.assertFalse((worker / '.git/rebase-merge').exists())
