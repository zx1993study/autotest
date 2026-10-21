const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { indexSource } = require('./source-index.cjs');
const { businessCases } = require('./business-cases.cjs');

const output = path.resolve(__dirname, '..');
const source = process.argv[2];
if (!source) throw new Error('Usage: node tools/generate.cjs <FieldNovaMini source directory>');
const index = indexSource(path.resolve(source));
const revision = execFileSync('git', ['-C', source, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const cases = [];
const fixturePages = /\/(info|detail|employee-details|productDetail|inventoryConvert|visitReport|report|activityReport|displayReport|paymentReport)(\/|$)/;
const nativePages = /\/(map|watermark-camera)$/;

function caseFor(page, suffix, data) {
  return { id: `MINI-${String(index.pages.indexOf(page) + 1).padStart(3, '0')}-${suffix}`,
    title: `${page.title}：${suffix}`, route: page.route, platforms: ['h5', 'mp-weixin'],
    priority: 'P1', category: 'render', automation: 'manual', verification: 'not_executed',
    requires_auth: page.route !== 'pages/login/index', requires_fixture: fixturePages.test(page.route),
    risk: 'read', evidence: [{ path: page.source, line: page.rootLine || 1 }],
    preconditions: ['专用测试环境；已登录具有对应功能权限的账号', '依赖ID从本批次测试数据中获取，不使用固定历史ID'],
    ...data };
}

for (const page of index.pages) {
  const native = nativePages.test(page.route);
  cases.push(caseFor(page, '页面呈现', {
    automation: native ? 'manual_native' : page.selector && !page.navigationContextRequired ? 'scripted' : 'manual',
    category: 'render', selector: page.selector,
    steps: [`打开 /${page.route} 并等待页面根元素`, '确认没有重定向到登录或其他页面'],
    expected: ['路由正确且页面根元素可见；此项仅验证呈现，不代表业务正确'],
    operations: page.selector && !native ? [{ action: 'visible', selector: page.selector }] : [],
    platforms: native ? ['mp-weixin-real-device'] : ['h5', 'mp-weixin']
  }));
  if (page.search) {
    const fields = (page.search.fields || []).filter(Boolean);
    cases.push(caseFor(page, '条件查询合并场景', {
      category: 'query', fields, priority: 'P0',
      evidence: [...caseFor(page, '', {}).evidence, { path: 'src/config/mobileSearchConfig.ts', line: 1 }],
      steps: ['准备本批次正反例及可核对的非空基线',
        `先单独验证关键字及全部条件：${fields.map(field => `${field.label}(${field.key})`).join('、')}`,
        '再组合多个条件，翻页，清空条件并返回列表；整个流程保存在一个场景中'],
      expected: ['HTTP成功和业务成功之外，还要逐条核对筛选条件；多选字段按包含关系比较',
        '非空正例必须命中预期ID；反例不得混入；空结果不能凭空判定过滤正确',
        '改变条件重置分页；清空恢复基线；过期请求不覆盖新条件结果'],
      expectation_basis: 'Actual MobileUnifiedSearch configuration; test values require fixtures'
    }));
  }
  for (const [ruleIndex, rule] of page.rules.entries()) {
    const field = page.elements.find(element => element.prop === rule.field);
    cases.push(caseFor(page, `字段校验-${rule.field}-${ruleIndex + 1}`, {
      category: 'validation', field: rule.field, source_rule: rule,
      title: `${page.title}：${field?.label || rule.field} / ${rule.message}`,
      evidence: [{ path: page.source, line: rule.line }],
      preconditions: ['除被测字段外，其余必填及条件字段均有效；编辑模式仅使用本批次记录'],
      steps: rule.max ? [`分别输入${rule.max - 1}、${rule.max}、${rule.max + 1}个字符并触发校验`]
        : rule.required ? ['单独清空被测字段并失焦/提交；随后输入有效值再次校验']
          : ['按源码自定义规则准备不合法值、合法值及允许为空的边界；分别验证条件启用和禁用；单独触发该字段校验'],
      expected: [`不合法值显示“${rule.message}”并阻止无效业务提交；有效边界可通过该字段校验`],
      expectation_basis: rule.custom ? 'Custom validator in source; do not infer required from message alone' : 'Declarative form rule in source'
    }));
  }
}

const login = index.pages.find(page => page.route === 'pages/login/index');
for (const [suffix, username, password] of [
  ['空账号密码', '', ''], ['仅账号', 'test-user', ''], ['仅密码', '', 'Demo!2468'],
  ['全空白账号', '   ', 'Demo!2468'], ['全空白密码', 'test-user', '   ']
]) cases.push(caseFor(login, suffix, {
  category: 'client_guard', automation: 'scripted', requires_fixture: false, requires_auth: false,
  steps: [`设置账号和密码为${suffix}组合`, '观察登录按钮，不提交登录请求'],
  expected: ['登录按钮禁用；不产生登录请求'],
  operations: [{ action: 'input', selector: '#username', value: username },
    { action: 'input', selector: '#password', value: password },
    { action: 'disabled', selector: '.login-button' }]
}));
cases.push(caseFor(login, '密码显隐', {
  category: 'client_guard', automation: 'scripted', requires_fixture: false, requires_auth: false,
  steps: ['输入非真实密码样例', '点击一次显隐按钮，再点击一次'],
  expected: ['默认隐藏；一次点击显示，再次隐藏；内容不丢失、不自动提交'],
  operations: [{ action: 'input', selector: '#password', value: 'Demo!2468' },
    { action: 'password_mode', selector: '#password', masked: true },
    { action: 'click', selector: '.password-toggle' },
    { action: 'password_mode', selector: '#password', masked: false },
    { action: 'click', selector: '.password-toggle' },
    { action: 'password_mode', selector: '#password', masked: true }]
}));

for (const [route, selector, message] of [
  ['pages/subpages/business/salesOrder/form', '.confirm-btn', '请选择客户'],
  ['pages/subpages/business/returnOrder/form', '.confirm-btn', '请选择客户']
]) {
  const page = index.pages.find(item => item.route === route);
  if (!page.messages.some(item => item.text === message)) throw new Error(`Missing guard: ${route}`);
  cases.push(caseFor(page, '空表单提交拦截', {
    category: 'client_guard', automation: 'scripted', requires_fixture: false,
    steps: ['打开全新空表单', '不选择客户，点击提交'], expected: [`提示“${message}”；不创建订单`],
    operations: [{ action: 'click', selector }, { action: 'toast', text: message }]
  }));
}
cases.push(...businessCases(index.pages));

const metadata = { schema_version: 1, project_name: '外勤小星', project_id: 10,
  source: { repository: 'https://github.com/dpush-io/FieldNovaMini', revision,
    route_config_sha256: index.routeConfigSha256 },
  execution_status: 'generated_not_executed',
  coverage: { miniapp: 'source-derived', h5: 'FieldNovaMini H5, not management admin',
    admin: 'pending_repository_access', service: 'pending_repository_access' },
  pages: index.pages.length, cases: cases.length,
  scripted_cases: cases.filter(item => item.automation === 'scripted').length,
  manual_cases: cases.filter(item => item.automation !== 'scripted').length };

function save(name, value) {
  fs.writeFileSync(path.join(output, name), JSON.stringify(value, null, 2) + '\n', 'utf8');
}
save('catalog.json', { metadata, cases });
save('source-inventory.json', { metadata, ...index });
save('page-inputs.json', { revision, pages: index.pages.filter(page => page.elements.some(element => element.model || element.prop)).map(page => ({
  route: page.route, source: page.source, fields: page.elements.filter(element => element.prop || element.model).map(element => ({
    name: element.prop || element.model, model: element.model || null, label: element.label || element.placeholder || element.prop || element.model,
    placeholder: element.placeholder || null, value: null,
    control: element.tag, repeated: element.repeated,
    sensitive: /password|secret|token/i.test(element.prop || element.model || ''),
    manual: page.route === 'pages/login/index' && element.model === 'form.code',
    rules: page.rules.filter(rule => rule.field === (element.prop || element.model?.split('.').at(-1))),
    selector_status: 'source_only_not_runtime_verified', source_line: element.line
  }))
})) });
save('fixtures.example.json', { approved_for_test: false, batch_id: '', pages: Object.fromEntries(
  index.pages.filter(page => fixturePages.test(page.route)).map(page => [page.route,
    { approved_for_test: false, batch_id: '', params: Object.fromEntries(page.parameters.map(key => [key, ''])) }])) });
const escape = value => String(value).replaceAll('|', '\\|').replaceAll('\n', ' ');
const lines = ['# 外勤小星页面与小程序测试用例', '',
  `源码：${metadata.source.repository} @ ${revision}`, '',
  `已注册页面 ${metadata.pages}；用例 ${metadata.cases}；可脚本执行 ${metadata.scripted_cases}；人工/待数据适配 ${metadata.manual_cases}。`,
  '', '状态均为“未执行”。H5 指小程序同源 H5，不是管理端；管理端及服务端等待源码访问。', '',
  '## 页面覆盖', '', '| 页面 | 路由 | 页面定位 | 查询条件数 | 字段规则数 |', '| --- | --- | --- | --- | --- |'];
for (const page of index.pages) lines.push(`| ${escape(page.title)} | ${page.route} | ${page.selector || '待适配'} | ${page.search?.fields?.length || 0} | ${page.rules.length} |`);
lines.push('', '## 用例明细', '');
for (const item of cases) {
  lines.push(`### ${item.id} ${item.title}`, '',
    `- 平台：${item.platforms.join(', ')}；级别：${item.priority}；执行：${item.automation}；风险：${item.risk}`,
    `- 路由：\`/${item.route}\``, `- 前置：${item.preconditions.join('；')}`,
    `- 步骤：${item.steps.map((step, number) => `${number + 1}. ${step}`).join('；')}`,
    `- 预期：${item.expected.join('；')}`,
    `- 依据：${item.evidence.map(ref => `${ref.path}:${ref.line}`).join(', ')}`, '');
}
fs.writeFileSync(path.join(output, 'cases.md'), lines.join('\n') + '\n', 'utf8');
process.stdout.write(JSON.stringify(metadata, null, 2) + '\n');
