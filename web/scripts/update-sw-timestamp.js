#!/usr/bin/env node
/**
 * Update Service Worker BUILD_TIME before each build
 * This ensures proper cache invalidation between deployments
 */

const fs = require('fs');
const path = require('path');

const SW_PATH = path.join(__dirname, '../public/sw.js');

try {
  let content = fs.readFileSync(SW_PATH, 'utf8');
  const buildTime = new Date().toISOString();

  // Replace the BUILD_TIME constant
  content = content.replace(
    /const BUILD_TIME = '[^']*';/,
    `const BUILD_TIME = '${buildTime}';`
  );

  fs.writeFileSync(SW_PATH, content, 'utf8');
  console.log(`[update-sw-timestamp] Updated BUILD_TIME to ${buildTime}`);
} catch (error) {
  console.error('[update-sw-timestamp] Error:', error.message);
  process.exit(1);
}
