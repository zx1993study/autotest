const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { indexSource } = require('./source-index.cjs');
const root = path.resolve(process.argv[2]);
const output = path.resolve(__dirname, '..');
const snapshot = JSON.parse(fs.readFileSync(path.join(output, 'platform-snapshot.json'), 'utf8').replace(/^\uFEFF/, ''));
const inventory = indexSource(root, snapshot.routes);
inventory.repository = 'https://github.com/xnous-ai/Fieldwork-management';
inventory.commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
fs.writeFileSync(path.join(output, 'source-inventory.json'), JSON.stringify(inventory, null, 2));
console.log(JSON.stringify({ routes: inventory.routes.length, components: Object.keys(inventory.components).length,
  parseErrors: Object.values(inventory.components).filter(item => item.error).map(item => ({ source: item.source, error: item.error })) }));
