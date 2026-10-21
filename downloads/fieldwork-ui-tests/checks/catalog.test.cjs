const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { selectCases, fixtureFor } = require('../miniapp/run.cjs');
const { literal, parseScript, symbolsIn, templateFacts } = require('../tools/source-index.cjs');
const root = path.resolve(__dirname, '..');
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'catalog.json'), 'utf8'));
const inventory = JSON.parse(fs.readFileSync(path.join(root, 'source-inventory.json'), 'utf8'));

test('every registered page is covered and all IDs are unique', () => {
  assert.equal(new Set(catalog.cases.map(item => item.id)).size, catalog.cases.length);
  assert.equal(catalog.metadata.cases, catalog.cases.length);
  for (const page of inventory.pages) {
    assert.ok(catalog.cases.some(item => item.route === page.route && item.category === 'render'));
    assert.match(page.sha256, /^[a-f0-9]{64}$/);
  }
  assert.equal(catalog.metadata.pages, inventory.pages.length);
});

test('source-derived definitions never claim execution', () => {
  for (const item of catalog.cases) {
    assert.equal(item.verification, 'not_executed');
    assert.ok(item.steps.length && item.expected.length && item.evidence.length);
    assert.ok(item.evidence.every(ref => !path.isAbsolute(ref.path) && ref.line > 0));
    assert.ok(inventory.pages.some(page => page.route === item.route));
  }
});

test('scripted controls use explicit supported actions and source selectors', () => {
  const actions = new Set(['visible', 'input', 'click', 'disabled', 'password_mode', 'toast']);
  for (const item of selectCases(catalog)) {
    assert.ok(item.operations.length);
    assert.equal(item.risk, 'read');
    for (const operation of item.operations) {
      assert.ok(actions.has(operation.action));
      if (operation.action !== 'toast') assert.match(operation.selector, /^[.#][a-zA-Z][\w-]*$/);
    }
  }
  assert.throws(() => selectCases(catalog, 'not-a-case'));
  assert.throws(() => selectCases(catalog, 'BIZ-sales-sellout'));
});

test('one conditional query scene per page includes configured conditions', () => {
  for (const page of inventory.pages.filter(item => item.search)) {
    const scenes = catalog.cases.filter(item => item.route === page.route && item.category === 'query');
    assert.equal(scenes.length, 1);
    assert.deepEqual(scenes[0].fields.map(field => field.key), (page.search.fields || []).filter(Boolean).map(field => field.key));
  }
});

test('fixtures require approval and matching nonempty batch IDs', () => {
  const item = { route: 'pages/example/info', requires_auth: true, requires_fixture: true };
  assert.ok(fixtureFor(item, {}, false).blocked);
  assert.ok(fixtureFor(item, {}, true).blocked);
  const data = { approved_for_test: true, batch_id: 'isolated-batch', pages: {
    [item.route]: { approved_for_test: true, batch_id: 'other-batch', params: { id: 123 } }
  } };
  assert.ok(fixtureFor(item, data, true).blocked);
  data.pages[item.route].batch_id = data.batch_id;
  assert.deepEqual(fixtureFor(item, data, true).params, { id: 123 });
  data.pages[item.route].params.id = '';
  assert.ok(fixtureFor(item, data, true).blocked);
});

test('literal parser resolves safe spreads but never evaluates executable code', () => {
  const ast = parseScript("const common = [{key: 'status'}]; const config = {fields: [...common], value: dangerous()};", 'fixture.ts');
  const symbols = symbolsIn(ast);
  assert.deepEqual(literal(symbols.get('config'), symbols), { fields: [{ key: 'status' }], value: null });
});

test('native camera and map are not mislabeled as automated coverage', () => {
  for (const item of catalog.cases.filter(item => /\/(watermark-camera|map)$/.test(item.route))) {
    assert.equal(item.automation, 'manual_native');
    assert.ok(!item.platforms.includes('h5'));
  }
});

test('client guards assert rejection or disabled state, not just HTTP 200', () => {
  for (const item of catalog.cases.filter(item => item.category === 'client_guard')) {
    assert.ok(item.operations.some(step => ['disabled', 'toast', 'password_mode'].includes(step.action)));
  }
});

test('installed source-matched uni automator has the launch API', () => {
  const { Automator } = require('@dcloudio/uni-automator');
  assert.equal(typeof new Automator().launch, 'function');
});

test('template indexing retains raw v-model expressions without compiler transforms', () => {
  const { parse } = require('@vue/compiler-sfc');
  const { descriptor } = parse('<template>\n<view class="page"><input v-model="form.password" /></view>\n</template>');
  const facts = templateFacts(descriptor.template.ast);
  assert.ok(facts.elements.some(element => element.model === 'form.password'));
  assert.equal(facts.rootLine, 2);
});

test('input JSON contains real login bindings and marks secrets and captcha', () => {
  const data = JSON.parse(fs.readFileSync(path.join(root, 'page-inputs.json'), 'utf8'));
  const login = data.pages.find(page => page.route === 'pages/login/index');
  assert.ok(login.fields.some(field => field.model === 'form.username'));
  assert.equal(login.fields.find(field => field.model === 'form.password').sensitive, true);
  assert.equal(login.fields.find(field => field.model === 'form.code').manual, true);
  assert.ok(login.fields.every(field => field.value === null));
});
