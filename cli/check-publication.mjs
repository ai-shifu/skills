/** Keep an older release from replacing the public npm latest dist-tag. */
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const stableVersion = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const root = fileURLToPath(new URL('../', import.meta.url));

export function assertPublicationVersion(version, latest) {
  if (!stableVersion.test(version)) throw new Error('Publication requires a stable CLI version.');
  if (latest === null) return;
  if (typeof latest !== 'string' || !stableVersion.test(latest)) {
    throw new Error('npm latest is not a stable version; inspect the dist-tag before publishing.');
  }
  const candidate = version.split('.').map(BigInt);
  const published = latest.split('.').map(BigInt);
  for (let i = 0; i < candidate.length; i++) {
    if (candidate[i] > published[i]) return;
    if (candidate[i] < published[i]) {
      throw new Error(`Refusing to replace npm latest ${latest} with older CLI ${version}.`);
    }
  }
}

export function npmLatest(result) {
  if (result.error) throw result.error;
  let value;
  try {
    value = JSON.parse(result.stdout);
  } catch {
    throw new Error('Cannot read npm latest: registry lookup did not return JSON.');
  }
  if (result.status === 0) {
    if (typeof value !== 'string') throw new Error('Cannot read npm latest: missing dist-tag.');
    return value;
  }
  // A missing public package is expected on its first publication. Authentication,
  // connectivity, and every other registry failure must stop the publication.
  if (value?.error?.code === 'E404') return null;
  throw new Error(`Cannot read npm latest: ${value?.error?.code || result.status || result.signal}.`);
}

export function checkPublication(execute = spawnSync) {
  const packageInfo = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));
  const npmEntry = process.env.npm_execpath;
  const command = npmEntry?.endsWith('.js') ? process.execPath : 'npm';
  const prefix = npmEntry?.endsWith('.js') ? [npmEntry] : [];
  const result = execute(command, [...prefix, 'view', packageInfo.name, 'dist-tags.latest', '--json',
    '--registry=https://registry.npmjs.org'], { encoding: 'utf8', timeout: 30_000 });
  const latest = npmLatest(result);
  assertPublicationVersion(packageInfo.version, latest);
  return { version: packageInfo.version, latest };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const { version, latest } = checkPublication();
    console.log(`npm publication permitted: ${version} (latest: ${latest ?? 'first publication'}).`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
