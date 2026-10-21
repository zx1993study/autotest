const assert = require('node:assert/strict');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function poll(check, timeout = 10000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (await check()) return;
    await delay(100);
  }
  throw new Error('Condition did not become true within timeout');
}

function disabled(value) {
  if (![true, false, 'true', 'false', 0, 1, '0', '1'].includes(value)) throw new Error('Expected a native boolean property');
  return value === true || value === 'true' || value === 1 || value === '1';
}

class SourcePage {
  constructor(program, route) {
    this.program = program;
    this.route = route;
  }

  async open(params) {
    const query = new URLSearchParams(params).toString();
    this.page = await this.program.reLaunch(`/${this.route}${query ? '?' + query : ''}`);
    await this.assertRoute();
  }

  async assertRoute() {
    const page = await this.program.currentPage();
    assert.equal(page.path.replace(/^\//, ''), this.route, 'Unexpected route or login redirect');
  }

  async element(selector) {
    let matches = [];
    await poll(async () => { matches = await this.page.$$(selector); return matches.length > 0; });
    assert.equal(matches.length, 1, `Ambiguous selector: ${selector}`);
    return matches[0];
  }

  async execute(operation) {
    if (operation.action === 'toast') {
      await poll(async () => await this.program.callUniMethod('getStorageSync', '__fw_ui_toast__') === operation.text);
      return;
    }
    const element = await this.element(operation.selector);
    if (operation.action === 'visible') {
      const size = await element.size();
      assert.ok(size.width > 0 && size.height > 0, 'Element has no visible size');
    } else if (operation.action === 'input') {
      await element.input(operation.value);
    } else if (operation.action === 'click') {
      await element.tap();
    } else if (operation.action === 'disabled') {
      await poll(async () => disabled(await element.property('disabled')));
    } else if (operation.action === 'password_mode') {
      await poll(async () => disabled(await element.property('password')) === operation.masked);
    } else {
      throw new Error(`Unsupported operation: ${operation.action}`);
    }
  }
}

module.exports = { SourcePage, poll, disabled };
