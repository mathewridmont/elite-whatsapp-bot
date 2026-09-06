import os, asyncio
from aiohttp import web, WSMsgType
import websockets
PORT=int(os.getenv('PORT','10000')); NOVNC='/usr/share/novnc'
INDEX='''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#070707;color:#eee;font-family:Arial;display:grid;place-items:center;min-height:100vh}.b{width:min(650px,90%);background:#121212;padding:30px;border-radius:22px;text-align:center}.btn{display:block;padding:16px;background:#eee;color:#111;border-radius:12px;text-decoration:none;font-weight:bold;margin:14px 0}.m{color:#999;line-height:1.8}</style><div class="b"><h1>📱 WhatsApp Web</h1><p class="m">Chrome يعمل داخل Render. افتحه وتحكم به مباشرة.</p><a class="btn" href="/browser">فتح Chrome على Render</a></div>'''
BROWSER='''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>html,body{margin:0;height:100%;background:#000}iframe{border:0;width:100%;height:100%}</style><iframe src="/vnc.html"></iframe>'''
VNC='''<!doctype html><html><body style="margin:0;background:#000"><div id="screen" style="width:100vw;height:100vh"></div><script src="/novnc/core/rfb.js"></script><script>const r=new RFB(document.getElementById('screen'),'wss://'+location.host+'/ws');r.scaleViewport=true;r.resizeSession=false;</script></body></html>'''
async def index(r): return web.Response(text=INDEX,content_type='text/html')
async def browser(r): return web.Response(text=BROWSER,content_type='text/html')
async def vnc(r): return web.Response(text=VNC,content_type='text/html')
async def health(r): return web.Response(text='OK')
async def static(r):
    p=os.path.realpath(os.path.join(NOVNC,r.match_info['path']))
    if not p.startswith(os.path.realpath(NOVNC)) or not os.path.isfile(p): return web.Response(status=404)
    return web.FileResponse(p)
async def ws(r):
    client=web.WebSocketResponse(); await client.prepare(r)
    try:
        async with websockets.connect('ws://127.0.0.1:5900') as upstream:
            async def c2u():
                async for m in client:
                    if m.type==WSMsgType.BINARY: await upstream.send(m.data)
                    elif m.type==WSMsgType.TEXT: await upstream.send(m.data)
                    elif m.type==WSMsgType.ERROR: break
            async def u2c():
                async for m in upstream:
                    if isinstance(m,bytes): await client.send_bytes(m)
                    else: await client.send_str(m)
            await asyncio.gather(c2u(),u2c())
    except Exception as e: print('WS',e,flush=True)
    return client
app=web.Application();app.router.add_get('/',index);app.router.add_get('/browser',browser);app.router.add_get('/vnc.html',vnc);app.router.add_get('/ws',ws);app.router.add_get('/health',health);app.router.add_get('/novnc/{path:.*}',static)
web.run_app(app,host='0.0.0.0',port=PORT)
