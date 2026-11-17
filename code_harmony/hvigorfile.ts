import { appTasks } from '@ohos/hvigor-ohos-plugin';
import { execFileSync } from 'child_process';

try {
  execFileSync(process.execPath, ['scripts/update-backend-config.mjs'], { stdio: 'inherit' });
} catch (err) {
  console.warn(`[ai-interview] failed to update backend config: ${String(err)}`);
}

export default {
  system: appTasks, /* Built-in plugin of Hvigor. It cannot be modified. */
  plugins: []       /* Custom plugin to extend the functionality of Hvigor. */
}
