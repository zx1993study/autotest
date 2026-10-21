const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const { installGuard, readGuard, restoreGuard } = require('../miniapp/network-guard.cjs');
const { verifyGuard, cleanup } = require('../miniapp/run.cjs');
const { disabled } = require('../miniapp/source-page.cjs');

function sandbox(response = { statusCode: 200, data: { code: 200 } }) {
  const app = {};
  const forwarded = [];
  const request = options => {
    forwarded.push(options);
    options.success?.(response);
    options.complete?.(response);
    return { abort() {} };
  };
  const upload = () => { throw new Error('Must not upload'); };
  const context = vm.createContext({ wx: { request, uploadFile: upload }, getApp: () => app });
  const evaluate = (fn, ...args) => {
    context.__args = args;
    return vm.runInContext(`(${fn.toString()})(...__args)`, context);
  };
  evaluate(installGuard);
  return { context, app, forwarded, request, upload, evaluate };
}

for (const method of ['POST', 'PUT', 'PATCH', 'DELETE']) test(`blocks ${method} without forwarding`, () => {
  const state = sandbox();
  let failed = false;
  state.context.wx.request({ url: 'https://example.invalid/business/orders?token=private', method, fail() { failed = true; } });
  assert.equal(state.forwarded.length, 0);
  assert.equal(failed, true);
  assert.equal(state.app.__fieldworkUITestGuard.blocked[0].path, '/business/orders');
  assert.ok(!JSON.stringify(state.evaluate(readGuard)).includes('private'));
});

test('forwards a read and preserves callbacks', () => {
  const state = sandbox();
  let complete = false;
  state.context.wx.request({ url: 'https://example.invalid/list', complete() { complete = true; } });
  assert.equal(state.forwarded.length, 1);
  assert.equal(complete, true);
  assert.equal(state.evaluate(readGuard).pending, 0);
});

test('HTTP 200 with business failure remains a failure', () => {
  const state = sandbox({ statusCode: 200, data: { code: 500, success: false } });
  state.context.wx.request({ url: 'https://example.invalid/list' });
  assert.equal(state.evaluate(readGuard).errors.length, 1);
});

test('blocks uploads and restores both original APIs', () => {
  const state = sandbox();
  state.context.wx.uploadFile({ url: 'https://example.invalid/upload' });
  assert.equal(state.evaluate(readGuard).blocked[0].method, 'UPLOAD');
  state.evaluate(restoreGuard);
  assert.equal(state.context.wx.request, state.request);
  assert.equal(state.context.wx.uploadFile, state.upload);
  assert.equal(state.app.__fieldworkUITestGuard, undefined);
});

test('refuses duplicate guard installation', () => {
  const state = sandbox();
  assert.throws(() => state.evaluate(installGuard));
});

test('does not restore another run\'s guard', () => {
  const state = sandbox();
  state.evaluate(restoreGuard, 'another-run');
  assert.ok(state.app.__fieldworkUITestGuard);
  assert.notEqual(state.context.wx.request, state.request);
});

test('partially installed guard can be restored after readonly upload API rejects assignment', () => {
  const app = {};
  const request = () => undefined;
  const wx = { request };
  Object.defineProperty(wx, 'uploadFile', { value() {}, writable: false });
  const context = vm.createContext({ wx, getApp: () => app });
  assert.throws(() => vm.runInContext(`(${installGuard.toString()})()`, context));
  vm.runInContext(`(${restoreGuard.toString()})()`, context);
  assert.equal(wx.request, request);
  assert.equal(app.__fieldworkUITestGuard, undefined);
});

test('cleanup still restores network and disconnects if restoring the toast fails', async () => {
  const calls = [];
  await assert.rejects(cleanup({
    restoreUniMethod: async () => { throw new Error('toast cleanup failed'); },
    callUniMethod: async () => calls.push('storage'),
    evaluate: async () => calls.push('guard'),
    disconnect: async () => calls.push('disconnect')
  }, 'owner', true));
  assert.deepEqual(calls, ['storage', 'guard', 'disconnect']);
});

test('missing boolean properties cannot satisfy an unmasked-password assertion', () => {
  assert.throws(() => disabled(undefined));
  assert.throws(() => disabled(null));
  assert.equal(disabled(false), false);
  assert.equal(disabled('true'), true);
});

test('runtime probe detects an ineffective request guard', async () => {
  const state = sandbox();
  await verifyGuard({
    callUniMethod: async (_, options) => state.context.wx.request(options),
    evaluate: async (fn, ...args) => state.evaluate(fn, ...args)
  });
  assert.equal(state.evaluate(readGuard).blocked.length, 0);
  await assert.rejects(verifyGuard({
    callUniMethod: async () => undefined,
    evaluate: async () => ({ blocked: [] })
  }), /did not intercept/);
});
