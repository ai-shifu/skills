import { prepareRuntime } from './installer.mjs';

try {
  prepareRuntime(process.argv[2]);
} catch (error) {
  process.stderr.write(`AI-Shifu runtime: ${error.message}\n`);
  process.exitCode = 1;
}
