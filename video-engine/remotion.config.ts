import { Config } from '@remotion/cli/config';
import {existsSync} from 'node:fs';

Config.setVideoImageFormat('jpeg');
Config.setConcurrency(4);
// The routine image provides this exact headless shell. Other hosts leave browser
// discovery to Remotion instead of failing on a Linux-only path before composition
// loading can begin.
const routineBrowser = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
if (existsSync(routineBrowser)) {
  Config.setBrowserExecutable(routineBrowser);
}
Config.setChromeMode('headless-shell');
