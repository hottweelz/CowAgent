// Call verifyIcons(page, fixtureUrl, outputDir) with an isolated Playwright page.
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import path from 'node:path'

const expected = [
  ['weixin', 'message-circle'], ['feishu', null], ['dingtalk', 'message-square'],
  ['wecom_bot', 'bot'], ['qq', 'message-circle'], ['wechatcom_app', 'building-2'],
  ['wechat_kf', 'headset'], ['wechatmp', 'message-circle'], ['telegram', null],
  ['slack', 'hash'], ['discord', 'at-sign'], ['fixture_unknown', 'plug'],
]

async function observations(page) {
  return page.locator('span[style*="background-color"] > svg').evaluateAll(icons => icons.map(svg => ({
    name: svg.parentElement.parentElement.innerText.split('\n')[0],
    classes: svg.getAttribute('class'), width: Number(svg.getAttribute('width')),
    height: Number(svg.getAttribute('height')), viewBox: svg.getAttribute('viewBox'),
    color: getComputedStyle(svg).color,
    visibleGeometry: svg.getBBox().width > 0 && svg.getBBox().height > 0,
    path: svg.querySelector('path')?.getAttribute('d'),
  })))
}

export async function verifyIcons(page, fixtureUrl, outputDir) {
  await fs.mkdir(outputDir, { recursive: true })
  const errors = []
  const apiRequests = []
  const onError = error => errors.push(String(error))
  const onRequest = request => {
    if (new URL(request.url()).pathname.startsWith('/api/')) {
      apiRequests.push({ method: request.method(), path: new URL(request.url()).pathname })
    }
  }
  page.on('pageerror', onError)
  page.on('request', onRequest)
  await page.setViewportSize({ width: 1100, height: 1200 })
  await page.goto(fixtureUrl)
  await page.getByText('fixture_unknown', { exact: true }).first().waitFor()
  const cards = await observations(page)
  assert.equal(cards.length, expected.length)
  for (const [index, [name, icon]] of expected.entries()) {
    const actual = cards[index]
    assert.equal(actual.name, name)
    assert.equal(actual.width, 18)
    assert.equal(actual.height, 18)
    assert.ok(actual.visibleGeometry)
    if (icon) assert.ok(actual.classes.split(' ').includes(`lucide-${icon}`))
    else assert.equal(actual.viewBox, '0 0 512 512')
  }
  assert.equal(cards[1].path, cards[8].path)
  await page.screenshot({ path: path.join(outputDir, 'channel-cards-light.png'), scale: 'css' })
  await page.evaluate(() => document.documentElement.classList.add('dark'))
  await page.waitForFunction(() => getComputedStyle(document.querySelector('.bg-base')).backgroundColor === 'rgb(14, 14, 16)')
  assert.deepEqual(await observations(page), cards)
  await page.screenshot({ path: path.join(outputDir, 'channel-cards-dark.png'), scale: 'css' })

  await page.goto(fixtureUrl + '?available=1')
  await page.getByRole('button', { name: 'Add channel', exact: true }).first().click()
  await page.getByRole('button', { name: 'Select a channel...', exact: true }).click()
  const menu = await observations(page)
  assert.equal(menu.length, expected.length)
  assert.ok(menu.every(icon => icon.width === 12 && icon.height === 12 && icon.visibleGeometry))
  await page.getByRole('button', { name: 'telegram (telegram)', exact: true }).click()
  const selected = await observations(page)
  assert.equal(selected.length, 2)
  assert.ok(selected.every(icon => icon.path === cards[8].path))
  assert.equal(selected[0].width, 12)
  assert.equal(selected[1].width, 18)
  await page.screenshot({ path: path.join(outputDir, 'telegram-selected.png'), scale: 'css' })
  await page.getByTitle('Close').click()
  assert.equal(await page.locator('span[style*="background-color"] > svg').count(), 0)
  assert.deepEqual(errors, [])
  assert.ok(apiRequests.length > 0)
  assert.ok(apiRequests.every(request => request.method === 'GET' && request.path === '/api/channels'))
  const result = { passed: true, checkedAt: new Date().toISOString(), browser: page.context().browser().version(),
    cards, dropdownIconCount: menu.length, selectedWidths: selected.map(icon => icon.width),
    pageErrors: errors, themes: ['light', 'dark'], apiRequests,
    channelMutations: apiRequests.filter(request => request.method !== 'GET').length }
  await fs.writeFile(path.join(outputDir, 'rendering.json'), JSON.stringify(result, null, 2) + '\n')
  page.off('pageerror', onError)
  page.off('request', onRequest)
  return result
}
