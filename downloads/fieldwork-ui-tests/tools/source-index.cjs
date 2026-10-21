const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { createRequire } = require('node:module');

function dependencies() {
  const local = createRequire(path.resolve(__dirname, '../package.json'));
  try { return { ts: local('typescript'), vue: local('@vue/compiler-sfc') }; }
  catch {
    const workspace = createRequire(path.resolve(__dirname, '../../../frontend/package.json'));
    return { ts: workspace('typescript'), vue: workspace('@vue/compiler-sfc') };
  }
}

const { ts, vue } = dependencies();
const textOf = node => node && (node.text ?? node.getText());
const hash = source => crypto.createHash('sha256').update(source).digest('hex');

function walk(node, visit) {
  visit(node);
  ts.forEachChild(node, child => walk(child, visit));
}

function literal(node, symbols = new Map(), seen = new Set()) {
  if (!node) return null;
  if (ts.isAsExpression(node) || ts.isParenthesizedExpression(node)) return literal(node.expression, symbols, seen);
  if (ts.isStringLiteralLike(node)) return node.text;
  if (ts.isNumericLiteral(node)) return Number(node.text);
  if (node.kind === ts.SyntaxKind.TrueKeyword) return true;
  if (node.kind === ts.SyntaxKind.FalseKeyword) return false;
  if (ts.isIdentifier(node) && symbols.has(node.text) && !seen.has(node.text)) {
    return literal(symbols.get(node.text), symbols, new Set([...seen, node.text]));
  }
  if (ts.isArrayLiteralExpression(node)) return node.elements.flatMap(item => {
    const value = literal(ts.isSpreadElement(item) ? item.expression : item, symbols, seen);
    return ts.isSpreadElement(item) ? (Array.isArray(value) ? value : []) : [value];
  });
  if (!ts.isObjectLiteralExpression(node)) return null;
  const result = {};
  for (const item of node.properties) {
    if (ts.isSpreadAssignment(item)) Object.assign(result, literal(item.expression, symbols, seen) || {});
    if (ts.isPropertyAssignment(item)) result[textOf(item.name)] = literal(item.initializer, symbols, seen);
    if (ts.isShorthandPropertyAssignment(item)) result[item.name.text] = literal(item.name, symbols, seen);
  }
  return result;
}

function parseScript(source, filename) {
  return ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
}

function symbolsIn(ast) {
  const symbols = new Map();
  walk(ast, node => {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name)) symbols.set(node.name.text, node.initializer);
  });
  return symbols;
}

function staticAttribute(node, name) {
  return node.props.find(prop => prop.type === 6 && prop.name === name)?.value?.content;
}

function directive(node, name) {
  return node.props.find(prop => prop.type === 7 && prop.name === name)?.exp?.content;
}

function templateFacts(ast) {
  const nodes = [];
  function visit(node, repeated = false) {
    if (node.type === 1) {
      repeated ||= node.props.some(prop => prop.type === 7 && prop.name === 'for');
      const classes = (staticAttribute(node, 'class') || '').split(/\s+/).filter(Boolean);
      nodes.push({ tag: node.tag, classes, id: staticAttribute(node, 'id'),
        label: staticAttribute(node, 'label'), prop: staticAttribute(node, 'prop'),
        placeholder: staticAttribute(node, 'placeholder'), model: directive(node, 'model'), repeated,
        line: node.loc.start.line });
    }
    for (const child of node.children || []) visit(child, repeated);
    for (const branch of node.branches || []) visit(branch, repeated);
  }
  visit(ast);
  const root = nodes.find(node => node.classes.length && !node.repeated);
  return { selector: root ? `.${root.classes[0]}` : null, elements: nodes.filter(node =>
    node.model || node.prop || node.placeholder || node.id), rootLine: root?.line };
}

function scriptFacts(source, filename, offset) {
  const ast = parseScript(source, filename);
  const symbols = symbolsIn(ast);
  const line = node => offset + ast.getLineAndCharacterOfPosition(node.getStart()).line;
  const rules = [];
  const parameters = new Set();
  const imports = [];
  const lineEvidence = [];
  walk(ast, node => {
    if (ts.isImportDeclaration(node)) {
      const module = node.moduleSpecifier.text;
      if (module.includes('/api/') || module.startsWith('./api/')) imports.push(module);
    }
    if (ts.isPropertyAccessExpression(node) && ts.isPropertyAccessExpression(node.expression)
      && node.expression.name.text === 'options') parameters.add(node.name.text);
    if (ts.isCallExpression(node) && node.expression.getText(ast) === 'onLoad') {
      const callback = node.arguments[0];
      const param = callback?.parameters?.[0]?.name?.getText(ast);
      if (param) walk(callback, child => {
        if (ts.isPropertyAccessExpression(child) && child.expression.getText(ast) === param) parameters.add(child.name.text);
      });
    }
    if (ts.isStringLiteralLike(node) && /请|不能|不得|确认|审批|库存/.test(node.text) && node.text.length < 100) {
      lineEvidence.push({ text: node.text, line: line(node) });
    }
  });
  const rulesNode = symbols.get('rules');
  if (rulesNode && ts.isObjectLiteralExpression(rulesNode)) for (const field of rulesNode.properties) {
    if (!ts.isPropertyAssignment(field) || !ts.isArrayLiteralExpression(field.initializer)) continue;
    for (const rule of field.initializer.elements) {
      const parsed = literal(rule, symbols);
      if (parsed?.message) rules.push({ field: textOf(field.name), message: parsed.message,
        required: parsed.required === true, max: parsed.max, custom: Object.hasOwn(parsed, 'validator'), line: line(rule) });
    }
  }
  const searchMatch = source.match(/mobileSearchConfigs\.([A-Za-z0-9_]+)/);
  return { rules, parameters: [...parameters], apiImports: [...new Set(imports)],
    messages: lineEvidence, searchConfig: searchMatch?.[1] || null };
}

function searchConfigurations(root) {
  const relative = 'src/config/mobileSearchConfig.ts';
  if (!fs.existsSync(path.join(root, relative))) return {};
  const ast = parseScript(fs.readFileSync(path.join(root, relative), 'utf8'), relative);
  const symbols = symbolsIn(ast);
  return literal(symbols.get('mobileSearchConfigs'), symbols) || {};
}

function indexSource(root) {
  const raw = fs.readFileSync(path.join(root, 'src/pages.json'), 'utf8');
  const result = ts.parseConfigFileTextToJson('pages.json', raw);
  if (result.error) throw new Error('Unable to parse pages.json as JSONC');
  const config = result.config;
  const routes = [...config.pages, ...(config.subPackages || []).flatMap(group =>
    group.pages.map(page => ({ ...page, path: `${group.root}/${page.path}` })))];
  const searches = searchConfigurations(root);
  const pages = routes.map(route => {
    const relative = `src/${route.path}.vue`;
    const content = fs.readFileSync(path.join(root, relative), 'utf8');
    const { descriptor, errors } = vue.parse(content, { filename: relative });
    if (errors.length || !descriptor.template) throw new Error(`Invalid page: ${relative}`);
    const script = descriptor.scriptSetup || descriptor.script;
    const facts = scriptFacts(script?.content || '', relative, script?.loc.start.line || 1);
    return { route: route.path, title: route.style?.navigationBarTitleText || route.path,
      source: relative, sha256: hash(content), ...templateFacts(descriptor.template.ast),
      ...facts, navigationContextRequired: content.includes('productStore.getSelectedProduct'),
      search: facts.searchConfig ? searches[facts.searchConfig] : null };
  });
  const registered = new Set(pages.map(page => page.source));
  const orphanPages = [];
  function files(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const full = path.join(directory, entry.name);
      if (entry.isDirectory()) files(full);
      else if (entry.name.endsWith('.vue')) {
        const relative = path.relative(root, full).replaceAll('\\', '/');
        if (!registered.has(relative) && !relative.includes('/components/')) orphanPages.push(relative);
      }
    }
  }
  files(path.join(root, 'src/pages'));
  return { pages, orphanPages, routeConfigSha256: hash(raw) };
}

module.exports = { indexSource, literal, parseScript, symbolsIn, templateFacts };
