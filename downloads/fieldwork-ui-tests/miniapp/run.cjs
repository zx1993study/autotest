const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { SourcePage, poll } = require('./source-page.cjs');
const { installGuard, readGuard, restoreGuard } = require('./network-guard.cjs');
const root = path.resolve(__dirname, '..');

function selectCases(catalog, selected = '') {
  const cases = catalog.cases.filter(item => item.automation === 'scripted' && item.platforms.includes('mp-weixin'));
  if (!selected) return cases;
  const ids = new Set(selected.split(',').filter(Boolean));
  if ([...ids].some(id => !cases.some(item => item.id === id))) throw new Error('Unknown or non-scripted FW_CASE_IDS');
  return cases.filter(item => ids.has(item.id));
}

function fixtureFor(item, fixtures, sessionReady) {
  if (item.requires_auth && !sessionReady) return { blocked: 'Requires manual login in developer tools' };
  if (!item.requires_fixture) return { params: {} };
  const entry = fixtures.pages?.[item.route];
  const valid = fixtures.approved_for_test === true && fixtures.batch_id
    && entry?.approved_for_test === true && entry.batch_id === fixtures.batch_id;
  if (!valid || !entry.params || !Object.keys(entry.params).length || Object.values(entry.params).some(value => value === '')) {
    return { blocked: 'Missing approved current-batch route parameters' };
  }
  return { params: entry.params };
}

async function settle(program) {
  let state;
  await poll(async () => {
    state = await program.evaluate(readGuard);
    return state.pending === 0 && Date.now() - state.changed >= 500;
  });
  if (state.blocked.length) throw new Error('Blocked a business write request; case cannot pass');
  if (state.errors.length) throw new Error('Read request failed or returned a business rejection');
}

function launchOptions(source, cli) {
  if (!source || !fs.existsSync(path.join(source, 'src/pages.json'))) throw new Error('Set FW_MINI_SOURCE to the FieldNovaMini checkout');
  if (!cli || !fs.existsSync(cli)) throw new Error('Set FW_WECHAT_CLI to the installed WeChat developer-tools CLI');
  require.resolve('@dcloudio/vite-plugin-uni', { paths: [source] });
  if (process.env.VITE_APP_ENV && process.env.VITE_APP_ENV !== 'test') throw new Error('Only VITE_APP_ENV=test is supported');
  return { platform: 'mp-weixin', projectPath: source, cliPath: source, host: '127.0.0.1',
    port: 9520, timeout: 60000, compile: true, silent: true,
    'mp-weixin': { cliPath: cli, launch: true, teardown: 'disconnect', remote: false } };
}

async function verifyGuard(program) {
  try {
    await program.callUniMethod('request', { url: 'http://127.0.0.1:9/__guard_probe__', method: 'POST' });
  } catch {}
  const guard = await program.evaluate(readGuard);
  if (!guard.blocked.some(item => item.path === '/__guard_probe__' && item.method === 'POST')) {
    throw new Error('Write guard did not intercept uni.request; refusing to run cases');
  }
  await program.evaluate(readGuard, true);
}

async function runCase(program, item, fixtures) {
  const precondition = fixtureFor(item, fixtures, process.env.FW_MINI_SESSION_READY === '1');
  if (precondition.blocked) return { id: item.id, status: 'blocked', reason: precondition.blocked };
  try {
    await settle(program);
    await program.evaluate(readGuard, true);
    await program.callUniMethod('removeStorageSync', '__fw_ui_toast__');
    const page = new SourcePage(program, item.route);
    await page.open(precondition.params);
    for (const operation of item.operations) await page.execute(operation);
    await settle(program);
    await page.assertRoute();
    return { id: item.id, status: 'passed', scope: item.category };
  } catch (error) {
    return { id: item.id, status: 'failed', reason: error.message };
  }
}

async function cleanup(program, owner, toastMocked) {
  try {
    if (toastMocked) await program.restoreUniMethod('showToast');
  } finally {
    try {
      await program.callUniMethod('removeStorageSync', '__fw_ui_toast__');
    } finally {
      try { await program.evaluate(restoreGuard, owner); }
      finally { await program.disconnect(); }
    }
  }
}

function writeReport(cases, results, revision) {
  const directory = path.join(root, 'artifacts');
  fs.mkdirSync(directory, { recursive: true });
  const complete = cases.map(item => results.find(result => result.id === item.id)
    || { id: item.id, status: 'not_run', reason: 'Stopped after failure or setup error' });
  fs.writeFileSync(path.join(directory, 'miniapp-results.json'), JSON.stringify({
    revision, executed_at: new Date().toISOString(), results: complete
  }, null, 2));
  if (complete.some(item => item.status !== 'passed')) process.exitCode = 1;
}

async function main() {
  const catalog = JSON.parse(fs.readFileSync(path.join(root, 'catalog.json'), 'utf8'));
  const cases = selectCases(catalog, process.env.FW_CASE_IDS);
  if (process.argv.includes('--list')) {
    process.stdout.write(cases.map(item => `${item.id}\t${item.title}`).join('\n') + '\n');
    return;
  }
  const source = process.env.FW_MINI_SOURCE && path.resolve(process.env.FW_MINI_SOURCE);
  const options = launchOptions(source, process.env.FW_WECHAT_CLI);
  const fixtures = process.env.FW_FIXTURES ? JSON.parse(fs.readFileSync(process.env.FW_FIXTURES, 'utf8')) : {};
  process.env.VITE_APP_ENV = 'test';
  process.env.UNI_PLATFORM = 'mp-weixin';
  process.chdir(source);
  const { Automator } = require('@dcloudio/uni-automator');
  const program = await new Automator().launch(options);
  const results = [];
  const guardOwner = randomUUID();
  let toastMocked = false;
  try {
    await program.evaluate(installGuard, guardOwner);
    await verifyGuard(program);
    await program.mockUniMethod('showToast', function (options) { wx.setStorageSync('__fw_ui_toast__', options.title); });
    toastMocked = true;
    for (const item of cases) {
      const result = await runCase(program, item, fixtures);
      results.push(result);
      process.stdout.write(`${result.id}: ${result.status}\n`);
      if (result.status === 'failed') break;
    }
  } finally {
    try { await cleanup(program, guardOwner, toastMocked); }
    finally { writeReport(cases, results, catalog.metadata.source.revision); }
  }
}

if (require.main === module) main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 2; });
module.exports = { fixtureFor, selectCases, settle, runCase, launchOptions, verifyGuard, cleanup };
