import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { checkVersion } from '../check-version.mjs';

function fixture(t, { version = '2.2.1', skillVersion = version, lockVersion = version } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'shifu-release-version-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const skillDirectory = join(root, 'skills/ai-shifu-course-creator');
  mkdirSync(skillDirectory, { recursive: true });
  writeFileSync(join(root, 'package.json'), JSON.stringify({ name: '@ai-shifu/cli', version }));
  writeFileSync(join(root, 'package-lock.json'), JSON.stringify({
    name: '@ai-shifu/cli', version: lockVersion, packages: { '': { version: lockVersion } },
  }));
  writeFileSync(join(skillDirectory, 'SKILL.md'), `---\nname: ai-shifu-course-creator\nmetadata:\n  version: ${skillVersion}\n  version_management: standalone\n---\n\n# Course Creator\n`);
  return root;
}

test('checks the CLI, Skill, lockfile and selected release together', (t) => {
  assert.equal(checkVersion(fixture(t), 'v2.2.1'), '2.2.1');
});

test('rejects mismatched Skill metadata before publication', (t) => {
  assert.throws(() => checkVersion(fixture(t, { skillVersion: '2.2.0' })), /differs from Skill/);
});

test('rejects a tag for another release or an unsafe tag', (t) => {
  const root = fixture(t);
  for (const tag of ['v2.2.0', '2.2.1', 'v2.2.1;echo unsafe']) {
    assert.throws(() => checkVersion(root, tag), /Release tag/);
  }
});

test('rejects lockfile drift', (t) => {
  assert.throws(() => checkVersion(fixture(t, { lockVersion: '2.2.0' })), /package-lock.json/);
});

test('requires release versions', (t) => {
  assert.throws(() => checkVersion(fixture(t, { version: '2.2.1-beta.1' })), /release version/);
});
