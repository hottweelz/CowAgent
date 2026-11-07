// Run with node docs/channel-icon-typecheck/render_fixture.mjs.
// No CowAgent backend or production configuration is loaded.
import { createServer } from '../../desktop/node_modules/vite/dist/node/index.js'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
// Tailwind's existing content globs are relative to the desktop package.
process.chdir(path.join(repo, 'desktop'))
const names = ['weixin', 'feishu', 'dingtalk', 'wecom_bot', 'qq', 'wechatcom_app',
  'wechat_kf', 'wechatmp', 'telegram', 'slack', 'discord', 'fixture_unknown']
const channels = names.map(name => ({
  name, label: { en: name, zh: name }, icon: '', color: '', active: true,
  login_status: 'logged_in', fields: [],
}))
const server = await createServer({
  configFile: path.join(repo, 'desktop/vite.config.ts'),
  server: { host: '127.0.0.1', port: 0, strictPort: false },
  plugins: [{ name: 'isolated-channel-fixture', configureServer(vite) {
    vite.middlewares.use(async (req, res, next) => {
      const url = new URL(req.url, 'http://127.0.0.1')
      if (url.pathname === '/api/channels' && req.method === 'GET') {
        const available = req.headers.referer?.includes('available=1')
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ status: 'success', channels: channels.map(c => ({ ...c, active: !available })) }))
      } else if (url.pathname.startsWith('/api/')) {
        res.writeHead(403); res.end('Fixture forbids mutations and other APIs')
      } else if (url.pathname === '/__channels') {
        const entry = '/@fs/' + path.join(repo, 'desktop/tests/channel-icons-fixture.tsx')
        const html = `<!doctype html><html><head><title>Isolated channel icon check</title></head>
          <body><div id="root"></div><script type="module">localStorage.setItem('cow_lang','en')</script>
          <script type="module" src="${entry}"></script></body></html>`
        res.setHeader('Content-Type', 'text/html')
        res.end(await vite.transformIndexHtml(req.url, html))
      } else next()
    })
  } }],
})
await server.listen()
console.log(JSON.stringify({ url: `http://127.0.0.1:${server.httpServer.address().port}/__channels` }))
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, async () => { await server.close(); process.exit(0) })
