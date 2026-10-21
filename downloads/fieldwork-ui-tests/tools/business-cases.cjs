function caseCollector(pages) {
  const cases = [];
  const pageMap = new Map(pages.map(page => [page.route, page]));
  function add(key, route, title, steps, expected, options = {}) {
    const page = pageMap.get(route);
    if (!page) throw new Error(`Unknown business route: ${route}`);
    cases.push({ id: `BIZ-${key}`, title, route, platforms: ['h5', 'mp-weixin'], priority: 'P0',
      category: 'business', automation: 'manual', verification: 'not_executed',
      requires_auth: true, requires_fixture: true, risk: 'write',
      preconditions: ['使用专用测试账号、同一隔离批次新建数据；记录创建返回的真实 ID',
        '仓库及商品必须在核准白名单中；不操作历史订单、客户、固定审批节点'],
      steps: steps.split('；'), expected: expected.split('；'),
      evidence: [{ path: page.source, line: page.rootLine || 1 }],
      expectation_basis: 'UI source + user-confirmed business rules; runtime verification required', ...options });
  }
  return { cases, add };
}

function loginCases(add) {
  for (const [id, title, steps, expected] of [
    ['normal', '有效账号登录', '使用专用测试账号登录；服务启用验证码时由人工填写；进入工作台并读取个人信息', '成功获取会话且身份正确；密码经公钥加密后提交；不记录密码、验证码和Token'],
    ['invalid', '错误账号或密码', '使用专用账号和一次错误密码；提交一次；观察登录结果', '停留登录页并明确提示；不残留失败会话；不得反复尝试触发账号锁定'],
    ['captcha', '验证码启停、刷新与失效', '在测试环境切换验证码配置；检查必填；刷新后提交旧验证码再提交新验证码', '开启才显示并必填；旧验证码被拒绝；刷新uuid与图片同步；不绕过验证'],
    ['public-key', '登录公钥接口失败和重复提交', '模拟公钥读取失败；恢复后快速重复点击登录', '失败不发送明文密码且loading恢复；正常时只发起一次登录；错误不会误显示成功']
  ]) add(`login-${id}`, 'pages/login/index', title, steps, expected,
    { requires_auth: false, requires_fixture: false, risk: 'session', preconditions: ['仅专用测试账号；不在用例或日志中写入真实凭据；验证码人工完成'] });
}

function customerCases(add) {
  const customers = [['terminal', 'business', '前端客户'], ['direct', 'directly', '直营客户'], ['kol', 'kol', 'KOL客户']];
  for (const [key, folder, label] of customers) {
    const base = `pages/subpages/customer/${folder}`;
    add(`${key}-create`, `${base}/form`, `${label}新增与详情回读`,
      '按字段规则填写有效数据，名称使用自然业务名称加批次时间戳；选择字典、客户经理和位置；提交并记录客户ID；打开本次客户详情',
      'HTTP与业务结果均成功；详情字段与输入一致；审批存在时为待审批，无审批时按配置生效');
    add(`${key}-edit`, `${base}/form`, `${label}编辑及返回刷新`,
      '从本轮客户详情进入编辑；仅修改本轮客户联系人和备注；保存后返回列表再打开详情',
      'ID不变且修改持久化；列表与详情一致；返回保持筛选与滚动位置');
    for (const decision of ['通过', '拒绝']) add(`${key}-approve-${decision === '通过' ? 'pass' : 'reject'}`, `${base}/info`,
      `${label}审批${decision}`, `创建本轮客户并读取详情审批信息；使用当前节点真实审批人登录；审批${decision}并回读客户和审批日志`,
      decision === '通过' ? '客户审批通过且可正常使用；审批人、节点与日志一致；重复提交不重复执行' : '客户被拒绝且不能被当作审批通过客户使用；拒绝原因与日志保留');
    add(`${key}-resubmit`, `${base}/info`, `${label}拒绝后修改并重新提交`,
      '创建并拒绝本轮客户；修改符合规则的内容；重新提交；读取新的审批节点',
      '新一轮审批启动；旧审批日志保留；不得沿用旧节点ID审批');
    add(`${key}-delete-cancel`, `${base}/info`, `${label}删除取消`,
      '打开本轮未关联业务的客户；点击删除；在二次确认中取消；重新查看列表与详情',
      '没有删除请求或业务变更；客户仍存在');
    add(`${key}-delete`, `${base}/info`, `${label}删除与关联限制`,
      '删除本轮可删除客户并回读；另建关联本轮订单的客户后尝试删除',
      '允许删除的数据在列表不再出现；存在关联时按已确认业务规则拒绝且不破坏关联',
      { expectation_basis: 'UI source; referenced-record deletion rule requires product confirmation' });
    add(`${key}-cooperation`, `${base}/index`, `${label}合作状态包含匹配`,
      '准备至少两个合作状态的本轮客户；选择其中一个状态过滤；逐条核对返回记录',
      '每条记录的合作状态集合包含所选值即通过，不要求整个字段字符串等于单个值；无匹配时为空列表', { risk: 'read' });
  }
}

function salesCases(add) {
  const salesForm = 'pages/subpages/business/salesOrder/form';
  const salesInfo = 'pages/subpages/business/salesOrder/info';
  for (const warehouse of ['总仓', '直营仓']) for (const customer of ['前端客户', '直营客户', 'KOL客户']) {
    const key = `${warehouse === '总仓' ? 'head' : 'direct'}-${customer === '前端客户' ? 'terminal' : customer === '直营客户' ? 'direct' : 'kol'}`;
    add(`sales-${key}-pass`, salesInfo, `${warehouse}销售给${customer}：审批、锁库和扣库`,
      `记录${warehouse}商品实际/锁定/可用库存；给本轮${customer}创建正数量销售订单；审批前回读库存；读取详情审批并由真实审批人通过；读取关联出入库订单；有待确认单则由对应仓管确认，无则直接回读；核对订单及库存`,
      '审批前库存不因本销售单锁定；审批通过后锁库；待确认时实际量不变、可用量按数量减少；确认后或自动完成时实际量扣减且锁定释放；订单与库存流水一致，不将自动完成硬编码为待确认状态');
    add(`sales-${key}-reject`, salesInfo, `${warehouse}销售给${customer}：审批拒绝`,
      '记录初始库存；创建本轮订单；查询审批节点并拒绝；回读库存和订单',
      '订单被拒绝；实际、锁定、可用库存均与基线一致；无完成的出入库单');
    add(`sales-${key}-oversell`, salesForm, `${warehouse}销售给${customer}：超可用库存与无库存商品`,
      '准备库存固定的白名单商品；分别选择超过可用量的数量和仓库无库存的商品；提交并回读订单和库存',
      '页面限制或服务业务拒绝均可，但必须包含正确原因；不生成成功订单；库存不变；SQL异常、未登录等不算预期业务拒绝');
  }
  add('sales-sellout', salesInfo, '销售刚好卖完、可用为0但实际不为0',
    '使用会生成待确认单的组合；订单数量等于可用库存；审批通过但不确认；读取库存；同商品再次下单；确认原订单；再次读取库存',
    '待确认时可用=0、实际>0、锁定=销售量；新单因可用不足拒绝；确认后实际扣减、锁定释放、可用不负数');
  add('sales-zero-negative', salesForm, '销售数量0、负数、小数与重复提交',
    '分别输入0、负数、规格不支持的小数；在有效订单提交时快速重复点击；查询本批次订单',
    '非法数量不产生有效订单且库存不变；重复点击只生成一单或返回明确幂等拒绝；不能把服务接受非法量改成通过');
  add('sales-gift-price', salesForm, '销售商品、赠品与金额汇总',
    '添加不同单价的多个商品和赠品；修改数量、移除一项；分别选择直营及非直营客户',
    '总数量含赠品；金额按计价规则精确至2位且不多计赠品；直营客户金额展示遵循页面分支');
}

function purchaseCases(add) {
  const purchase = 'pages/subpages/business/purchaseOrder/info';
  for (const decision of ['通过', '拒绝']) add(`purchase-${decision === '通过' ? 'pass' : 'reject'}`, purchase, `采购审批${decision}及库存节点`,
    `记录白名单库存；新建采购单并上传有效凭证；读取详情审批流程；有审批时由节点审批人${decision}；查询是否生成待确认入库单；需要确认时由仓管确认；逐节点读取库存`,
    decision === '通过' ? '存在待确认单时确认后才增加实际与可用库存；没有确认环节时按业务流程直接入库；每个节点只增加一次' : '有审批的采购拒绝后库存不变；无审批配置时本拒绝分支标记不适用，不伪造节点');
  add('purchase-no-approval', purchase, '采购无审批流程与重复确认',
    '在已核准无审批配置中创建采购单；查看真实关联入库单并完成需要的确认；重复确认',
    '不伪造审批；有待确认单则确认后入库，无则直接入库；重复操作不重复增加库存');
  add('purchase-voucher', 'pages/subpages/business/purchaseOrder/form', '采购凭证类型、上传失败与重试',
    '上传有效图片、PDF；尝试超限类型和体积；模拟上传失败后重试；移除凭证',
    '类型及数量限制符合页面和服务配置；失败有提示且不能引用未成功文件；删除后提交不残留旧URL');
}

function returnCases(add) {
  const returns = 'pages/subpages/business/returnOrder/info';
  for (const type of ['关联原销售单', '直接退货']) {
    const key = type === '直接退货' ? 'direct' : 'related';
    add(`return-${key}-pass`, returns, `${type}：审批及入库确认`,
      `使用本轮完成销售单及收货仓库记录库存；创建${type}退货；读详情审批信息；有审批时通过，无审批不伪造；读取待确认入库单；存在时由收货仓管确认；回读库存`,
      '有审批先通过；有待确认单确认后才增加库存，无则直接入库；完好退货实际/可用增加正确且只增加一次');
    add(`return-${key}-reject`, returns, `${type}：审批拒绝与库存不变`,
      '在有审批配置中创建本轮退货单；读取当前节点并拒绝；核对库存与关联单',
      '拒绝后不入库；实际与可用库存不变；不会出现已完成入库单');
    add(`return-${key}-quantity`, 'pages/subpages/business/returnOrder/form', `${type}：异常退货数量`,
      '分别输入0、负数、超过可退数量；针对本轮销售重复退货；查看订单和库存',
      '不合法退货被明确拒绝；累计退货不超过可退量；不出现SQL异常和重复入库');
  }
  add('return-related-fields', 'pages/subpages/business/returnOrder/form', '关联退货切换为直接退货后的字段清理',
    '先选择本轮销售单；切换直接退货并选择另一客户和仓库；再切回关联退货',
    '客户、仓库、商品和可退量随模式重新计算；不带上一次模式隐藏字段提交');
}

function conversionCases(add) {
  const convert = 'pages/subpages/warehouse/inventoryConvert';
  const conversionRows = [
    ['ratio', '固定装箱规格换算', '选择装箱规格为1*N的源商品与1*1目标商品；输入源数量Q；提交一次；回读两种商品库存', '目标量必须=Q*N；源实际/可用减Q、目标加Q*N；无需审批或确认且立即生效'],
    ['stock', '拆箱超库存及可用为0', '使用库存不足或已全部锁定的源商品；尝试转换', '明确库存不足拒绝；实际、锁定、可用与目标库存均不变'],
    ['target', '非1*1目标、同商品与不匹配规格', '尝试选择非1*1、同源商品、与源不匹配的目标商品', '不能成功转换不合法组合；不得接受人为目标数量绕过固定比例'],
    ['bad-spec', '缺失或异常装箱规格', '使用缺失、非数字、零、负值及非整数装箱规格的测试商品', '页面禁止提交或返回清晰错误；不产生库存变更'],
    ['boundary', '拆箱刚好耗尽及重复点击', '源数量等于可用量；快速连续提交；查询流水和库存', '源不为负且只转换一次；目标累计量与有效流水一致'],
    ['lifecycle', '销售、退货、拆箱连续库存核对', '完成一次拆箱；销售转换后的商品并按真实流程审批确认；对本轮销售退货并按真实流程入库', '每个节点实际/可用/锁定均与独立台账一致；最终库存守恒，无重复扣加']
  ];
  for (const [id, title, steps, expected] of conversionRows) add(`convert-${id}`, convert, title, steps, expected);
}

function visitCases(add) {
  const visit = 'pages/subpages/visitPlan/visitReport';
  const visitRows = [
    ['normal', '正常签到、上报和签退', '创建本轮拜访计划；真实定位在范围内签到；按要求上报库存/陈列/其他；满足最短时长后签退', '签到与签退时间位置正确；步骤状态及拜访记录一致'],
    ['distance', '超距签到与异常签退', '使用专用定位测试环境在范围外签到或签退；填写异常说明和留证', '异常有标识；必填说明与留证校验生效；记录可只读回看'],
    ['duration', '最短拜访时间与倒计时', '签到后立即尝试签退；前后台切换；超过规定时长后再次签退', '时长未到禁止正常签退；倒计时不重置、不漂移；时长满足后可操作'],
    ['offline', '上报断网、恢复与重复操作', '上报时断网；恢复网络后重试；连续点击签到/上报/签退', '失败不显示业务成功；恢复后不丢失输入；无重复记录和重复附件'],
    ['readonly', '完成记录只读及步骤文案', '完成本轮拜访后重开记录；查看未填写步骤与异常记录', '已签退未填步骤显示未填写；历史记录不可误编辑；异常证据保留']
  ];
  for (const [id, title, steps, expected] of visitRows) add(`visit-${id}`, visit, title, steps, expected, { native: true });
  add('visit-plan', 'pages/subpages/visitPlan/addPlan', '拜访计划批量客户、日期与路线',
    '选择本轮客户和拜访人员；选择日期和路线；批量创建；回读计划；从详情返回列表',
    '计划数量与客户选择一致；人员、日期与路线正确；返回不重复加载、不丢失位置');
  add('online-visit', 'pages/subpages/onlineVisit/form', '电话及微信线上拜访',
    '分别选电话和微信方式；填写本轮客户、时间和记录；测试必填缺失后有效提交',
    '缺失字段有提示；保存与详情一致；取消拨号、离开微信不会自动报告拜访成功', { native: true });
}

function activityCases(add) {
  const activities = [
    ['scheme', 'pages/subpages/activityApply/scheme/detail', '活动方案审批通过与拒绝', '由管理端创建本轮模板及类型业务工作流；创建活动方案；详情读取审批；分别通过和拒绝', '节点及审批人来自详情；通过后才进入后续可执行状态；拒绝不派生有效任务'],
    ['apply', 'pages/subpages/activityApply/apply/form', '活动申请动态字段及条件必填', '选择不同本轮活动类型；切换条件字段；填写有效值及空值；提交申请', '动态字段与所选模板一致；隐藏字段不残留；条件必填生效'],
    ['apply-approval', 'pages/subpages/activityApply/apply/detail', '活动申请审批与撤回重提', '创建本轮申请；按实际节点分别通过/拒绝；在允许状态撤回并重提', '审批与任务状态同步；不使用过期节点；重复操作不重复派任务'],
    ['execute', 'pages/subpages/activityApply/execute/report', '活动执行上报与时间窗口', '准备未开始/可执行/逾期/已完成任务；上传要求证据；提交并回看', '只有合法状态允许提交；必填证据生效；重复提交不重复完成'],
    ['payment', 'pages/subpages/activityApply/payment/report', '活动兑付凭证与金额', '使用本轮满足条件任务；填写金额和凭证；测试0、负数、超额、重复兑付', '金额与额度规则一致；非法值拒绝；有效兑付只记账一次，不进行真实支付'],
    ['old-activity', 'pages/subpages/activity/applyActivity', '活动中心旧入口与新活动流程一致性', '从活动中心申请本轮活动；在新活动申请列表和详情查询', '入口间记录关联正确；模板、参与客户和审批信息一致']
  ];
  for (const [id, route, title, steps, expected] of activities) add(`activity-${id}`, route, title, steps, expected);
}

function supportingCases(add) {
  const supervisionRows = [
    ['create', 'create', '督办任务发布与人员多选', '选择本轮任务接收员工、截止时间与报告要求；提交任务', '每个员工收到准确任务；必填校验生效；截止时间前后状态正确'],
    ['report', 'report', '督办上报、附件及重复提交', '本轮接收人打开任务；上传合法附件并上报；重复提交；回看详情', '报告关联本轮任务；附件可访问；无重复完成和错误关联'],
    ['return', 'detail', '督办详情返回刷新及超期处理', '查看本轮任务；从上报页返回详情；跨截止时间刷新', '详情刷新一次且列表状态一致；超期与已完成区分正确']
  ];
  for (const [id, page, title, steps, expected] of supervisionRows) add(`supervision-${id}`, `pages/subpages/supervision/${page}`, title, steps, expected);
  add('notifications', 'pages/subpages/messageCenter/index', '消息已读、待办和审批跳转',
    '产生本轮业务通知；打开消息；切换待办及审批；进入关联本轮单据后返回',
    '跳转ID和业务类型正确；徽标与已读状态同步；不将历史未读消息批量标为已读');
  add('profile-logout', 'pages/profile/index', '退出登录及会话清理',
    '使用专用测试账号；退出登录；返回受保护页面；重新登录另一角色',
    '清理旧会话并回登录页；不同角色不残留旧菜单、组织或缓存', { requires_fixture: false, risk: 'session' });
  add('statistics', 'pages/data/index', '统计范围、时间区间和下钻',
    '使用固定测试时区和本轮数据；切换今日/月度/自选区间；进入客户及订单明细',
    '汇总与相同条件明细一致；区间边界不重复/漏计；下钻携带条件且返回保持状态', { risk: 'read' });
  for (const [id, route, title, steps, expected] of [
    ['camera', 'pages/subpages/common/watermark-camera', '相机权限、定位水印与连续拍照', '真机分别允许/拒绝相机及定位权限；前后台切换；连续拍照并返回上报页', '拒绝可恢复且不误上传；照片水印时间位置准确；分包切换不崩溃、无持续内存上涨'],
    ['map', 'pages/subpages/common/map', '地图选点、取消及隐私授权', '真机允许/拒绝定位；搜索并选点；取消选择；返回客户表单', '坐标与地址一致且取消不覆盖原位置；授权提示符合平台规则']
  ]) add(`native-${id}`, route, title, steps, expected,
    { platforms: ['mp-weixin-real-device'], automation: 'manual_native', native: true, risk: 'native' });
}

function businessCases(pages) {
  const { cases, add } = caseCollector(pages);
  for (const generate of [loginCases, customerCases, salesCases, purchaseCases, returnCases,
    conversionCases, visitCases, activityCases, supportingCases]) generate(add);
  return cases;
}

module.exports = { businessCases };
