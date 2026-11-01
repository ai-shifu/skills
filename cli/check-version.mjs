#!/usr/bin/env node
/** Verify that npm and the primary Skill describe the same release. */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const releaseVersion = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const repositoryRoot = fileURLToPath(new URL('../', import.meta.url));

export function checkVersion(root = repositoryRoot, tag) {
  const metadata = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));
  if (metadata.name !== '@ai-shifu/cli' || !releaseVersion.test(metadata.version ?? '')) {
    throw new Error('Expected @ai-shifu/cli with a release version in package.json');
  }
  const skill = readFileSync(resolve(root, 'skills/ai-shifu-course-creator/SKILL.md'), 'utf8').replace(/\r\n/g, '\n');
  const frontmatter = /^---\n([\s\S]*?)\n---(?:\n|$)/.exec(skill)?.[1];
  const block = /^metadata:[ \t]*\n((?:[ \t]+[^\n]*(?:\n|$))*)/m.exec(frontmatter ?? '')?.[1];
  const version = /^  version: *["']?([0-9]+\.[0-9]+\.[0-9]+)["']? *$/m.exec(block ?? '')?.[1];
  if (version !== metadata.version) {
    throw new Error(`CLI version ${metadata.version} differs from Skill version ${version ?? '(missing)'}`);
  }
  if (tag !== undefined && tag !== `v${version}`) {
    throw new Error(`Release tag ${tag} differs from package and Skill version v${version}`);
  }
  const lock = JSON.parse(readFileSync(resolve(root, 'package-lock.json'), 'utf8'));
  if (lock.name !== metadata.name || lock.version !== version || lock.packages?.['']?.version !== version) {
    throw new Error('package-lock.json version differs from the CLI and Skill version');
  }
  return version;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    if (process.argv.length > 3) throw new Error('Usage: node cli/check-version.mjs [vX.Y.Z]');
    const version = checkVersion(repositoryRoot, process.argv[2] === '--quiet' ? undefined : process.argv[2]);
    if (process.argv[2] !== '--quiet') console.log(version);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
