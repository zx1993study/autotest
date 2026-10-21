const test = require('node:test');
const assert = require('node:assert/strict');
const { templateFacts, literal, symbolsIn, parseScript } = require('../tools/source-index.cjs');

test('hidden legacy inputs are not marked usable', () => {
  const facts = templateFacts('<div><el-form v-if="false"><el-input v-model="q.name" placeholder="old"/></el-form><unified-list-toolbar page-name="Warehouse"/></div>');
  assert.equal(facts.fields[0].hidden, true);
  assert.equal(facts.toolbars[0].name, 'Warehouse');
});
test('Element UI fields preserve dialog and form evidence', () => {
  const facts = templateFacts('<div><img src="/logo.png"><el-dialog title="Add"><el-form ref="form" :model="form"><el-form-item label="Name" prop="name"><el-input v-model="form.name" placeholder="Name"/></el-form-item></el-form></el-dialog></div>');
  assert.equal(facts.fields[0].dialog, 'Add');
  assert.equal(facts.fields[0].prop, 'name');
  assert.equal(facts.fields[0].form.ref, 'form');
});
test('static config resolves spreads but never executes expressions', () => {
  const ast = parseScript('const shared=[{key:"id"}]; const config={fields:[...shared], unsafe: process.exit(1)};', 'fixture.js');
  const symbols = symbolsIn(ast);
  assert.deepEqual(literal(symbols.get('config'), symbols), { fields: [{ key: 'id' }], unsafe: null });
});
