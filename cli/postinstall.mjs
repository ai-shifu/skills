import { setup } from './installer.mjs';

// A local development npm install must not change the developer's Skills.
// npx installation uses the explicit `install` command instead.
if (process.env.npm_config_global === 'true') {
  try {
    setup();
  } catch (error) {
    process.stderr.write(`AI-Shifu installation failed: ${error.message}\nRetry the installation or run shifu setup.\n`);
    process.exitCode = 1;
  }
}
