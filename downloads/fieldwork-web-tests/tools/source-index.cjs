const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { createRequire } = require('node:module');
let local = createRequire(path.resolve(__dirname, '../package.json'));
try { local.resolve('typescript'); } catch { local = createRequire(path.resolve(__dirname, '../../../frontend/package.json')); }
const ts = local('typescript');
const { parse: parseSfc } = local('@vue/compiler-sfc');
const { baseParse } = local('@vue/compiler-dom');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const keyOf = node => node?.text || node?.escapedText;

function walk(node, visit) { visit(node); ts.forEachChild(node, child => walk(child, visit)); }
function parseScript(source, file) { return ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS); }
function symbolsIn(ast) {
  const result = new Map();
  walk(ast, node => { if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name)) result.set(node.name.text, node.initializer); });
  return result;
}
function literal(node, symbols = new Map(), seen = new Set()) {
  if (!node) return null;
  if (ts.isStringLiteralLike(node)) return node.text;
  if (ts.isNumericLiteral(node)) return Number(node.text);
  if (node.kind === ts.SyntaxKind.TrueKeyword) return true;
  if (node.kind === ts.SyntaxKind.FalseKeyword) return false;
  if (ts.isIdentifier(node) && symbols.has(node.text) && !seen.has(node.text))
    return literal(symbols.get(node.text), symbols, new Set([...seen, node.text]));
  if (ts.isArrayLiteralExpression(node)) return node.elements.flatMap(item => ts.isSpreadElement(item)
    ? literal(item.expression, symbols, seen) || [] : [literal(item, symbols, seen)]);
  if (!ts.isObjectLiteralExpression(node)) return null;
  const result = {};
  for (const property of node.properties) {
    if (ts.isSpreadAssignment(property)) Object.assign(result, literal(property.expression, symbols, seen));
    else if (ts.isPropertyAssignment(property)) result[keyOf(property.name)] = literal(property.initializer, symbols, seen);
  }
  return result;
}
const attr = (node, name) => node.props?.find(p => p.type === 6 && p.name === name)?.value?.content;
const directive = (node, name) => node.props?.find(p => p.type === 7 && p.name === name)?.exp?.content;
const binding = (node, name) => node.props?.find(p => p.type === 7 && p.name === 'bind' && p.arg?.content === name)?.exp?.content;
function text(node) { return (node.children || []).map(c => c.type === 2 ? c.content : c.type === 1 ? text(c) : '').join('').replace(/\s+/g, ' ').trim(); }

function templateFacts(template) {
  const result = { fields: [], buttons: [], tables: [], toolbars: [], roots: [] };
  const voidTags = new Set('area,base,br,col,embed,hr,img,input,link,meta,param,source,track,wbr'.split(','));
  const ast = baseParse(template, { isVoidTag: tag => voidTags.has(tag), onError(error) { throw error; } });
  function visit(node, context = {}) {
    if (node.type !== 1) { for (const child of node.children || []) visit(child, context); return; }
    const condition = directive(node, 'if');
    const ctx = { ...context, hidden: context.hidden || condition === 'false',
      repeated: context.repeated || !!directive(node, 'for'),
      conditions: [...(context.conditions || []), ...(condition ? [condition] : [])] };
    if (node.tag === 'el-dialog') ctx.dialog = attr(node, 'title') || binding(node, 'title') || 'dialog';
    if (node.tag === 'el-form') ctx.form = { ref: attr(node, 'ref'), model: binding(node, 'model') };
    if (node.tag === 'el-form-item') ctx.field = { label: attr(node, 'label'), prop: attr(node, 'prop') };
    const evidence = { line: node.loc.start.line, hidden: !!ctx.hidden, repeated: !!ctx.repeated, conditions: ctx.conditions };
    if (node.tag === 'unified-list-toolbar') result.toolbars.push({ name: attr(node, 'page-name'), expression: binding(node, 'page-name'), ...evidence });
    if (node.tag === 'el-table' && !ctx.dialog) {
      ctx.table = { data: binding(node, 'data'), headers: [], ...evidence };
      result.tables.push(ctx.table);
    }
    if (node.tag === 'el-table-column' && ctx.table && attr(node, 'label') && !condition)
      ctx.table.headers.push(attr(node, 'label'));
    if (node.tag === 'el-button') result.buttons.push({ text: text(node), handler: directive(node, 'on') || node.props.find(p => p.type === 7 && p.name === 'on')?.exp?.content, dialog: ctx.dialog, ...evidence });
    if (directive(node, 'model')) result.fields.push({ tag: node.tag, model: directive(node, 'model'),
      placeholder: attr(node, 'placeholder'), type: attr(node, 'type'), readonly: node.props.some(p => p.name === 'readonly'),
      label: ctx.field?.label, prop: ctx.field?.prop, form: ctx.form, dialog: ctx.dialog, ...evidence });
    if (!context.form && !context.dialog && attr(node, 'class')) result.roots.push(attr(node, 'class').split(' ')[0]);
    for (const child of node.children || []) visit(child, ctx);
  }
  visit(ast);
  return result;
}

function scriptFacts(script, filename, root) {
  const ast = parseScript(script, filename), symbols = symbolsIn(ast), rules = [], api = [], listCalls = new Set();
  walk(ast, node => {
    if (ts.isMethodDeclaration(node) && keyOf(node.name) === 'getList') walk(node, child => {
      if (ts.isCallExpression(child) && ts.isIdentifier(child.expression)) listCalls.add(child.expression.text);
    });
    if (ts.isPropertyAssignment(node) && /rules$/i.test(keyOf(node.name) || '') && ts.isObjectLiteralExpression(node.initializer))
      rules.push({ name: keyOf(node.name), fields: literal(node.initializer, symbols) });
    if (!ts.isImportDeclaration(node) || !node.moduleSpecifier.text.startsWith('@/api/')) return;
    const relative = 'src/' + node.moduleSpecifier.text.slice(2) + '.js';
    const target = path.join(root, relative);
    if (!fs.existsSync(target)) return;
    const apiAst = parseScript(fs.readFileSync(target, 'utf8'), relative);
    walk(apiAst, child => {
      if (!ts.isFunctionDeclaration(child)) return;
      walk(child, call => {
        if (!ts.isCallExpression(call) || call.expression.getText(apiAst) !== 'request') return;
        const config = literal(call.arguments[0]);
        if (config?.url) api.push({ function: keyOf(child.name), url: config.url, method: config.method || 'get', source: relative });
      });
    });
  });
  const unique = [...new Map(api.map(item => [item.function + item.url, item])).values()];
  return { rules, api: unique, list_api: unique.filter(item => listCalls.has(item.function)
    && (item.method || 'get').toLowerCase() === 'get') };
}

function staticRoutes(root) {
  const ast = parseScript(fs.readFileSync(path.join(root, 'src/router/index.js'), 'utf8'), 'router.js');
  const symbols = symbolsIn(ast), result = [];
  function routes(array, parent = '') {
    if (!array || !ts.isArrayLiteralExpression(array)) return;
    for (const node of array.elements) {
      if (!ts.isObjectLiteralExpression(node)) continue;
      const props = Object.fromEntries(node.properties.filter(ts.isPropertyAssignment).map(p => [keyOf(p.name), p.initializer]));
      const child = literal(props.path) || '';
      const route = child.startsWith('/') ? child : parent.replace(/\/$/, '') + '/' + child;
      let component;
      if (props.component) walk(props.component, n => {
        if (ts.isStringLiteralLike(n) && n.text.startsWith('@/views/')) component = n.text.slice(8);
      });
      if (component) result.push({ route, component, title: literal(props.meta)?.title || route });
      routes(props.children, route);
    }
  }
  routes(symbols.get('constantRoutes')); routes(symbols.get('dynamicRoutes'));
  return result;
}

function indexSource(root, dynamic) {
  const configSource = fs.readFileSync(path.join(root, 'src/utils/unifiedListConfig.js'), 'utf8');
  const configAst = parseScript(configSource, 'unifiedListConfig.js'), symbols = symbolsIn(configAst);
  const configs = literal(symbols.get('configs'), symbols) || {};
  const routes = [...new Map([...staticRoutes(root), ...dynamic].map(r => [r.route, r])).values()];
  const components = {};
  for (const route of routes) {
    if (!/^[A-Za-z0-9_/-]+$/.test(route.component) || route.component.split('/').includes('..')) continue;
    const relative = `src/views/${route.component}.vue`;
    if (components[route.component] || !fs.existsSync(path.join(root, relative))) continue;
    const source = fs.readFileSync(path.join(root, relative), 'utf8');
    try {
      const { descriptor } = parseSfc(source, { filename: relative });
      if (!descriptor.template) throw Error('No template');
      components[route.component] = { source: relative, sha256: hash(source),
        ...templateFacts(descriptor.template.content), ...scriptFacts(descriptor.script?.content || '', relative, root) };
    } catch (error) { components[route.component] = { source: relative, error: String(error.message) }; }
  }
  return { routes, components, configs, config_sha256: hash(configSource) };
}

module.exports = { indexSource, literal, parseScript, symbolsIn, templateFacts };
