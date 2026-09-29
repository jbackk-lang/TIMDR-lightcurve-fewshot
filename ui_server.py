"""Local-only astronomy UI. Uploaded measurements stay in memory on this computer."""
import argparse,json,secrets,threading,webbrowser
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from ui_import import inspect_text,parse_table
from ui_analysis import analyze,search_period,json_safe

ROOT=Path(__file__).resolve().parent

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address):
        self.token=secrets.token_hex(24);self.busy=threading.Lock()
        super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,code,body,mime='application/json; charset=utf-8'):
        if not isinstance(body,bytes):body=json.dumps(json_safe(body),ensure_ascii=False,allow_nan=False).encode()
        self.send_response(code);self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(body)
    def host_ok(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def do_GET(self):
        if not self.host_ok():self.send(403,{'error':'Niedozwolony adres hosta.'});return
        routes={'/':('web/index.html','text/html; charset=utf-8'),'/app.js':('web/app.js','text/javascript; charset=utf-8'),
                '/style.css':('web/style.css','text/css; charset=utf-8'),'/api/references':('examples/ogle_references.json','application/json; charset=utf-8'),
                '/api/examples':('examples/ui_examples.json','application/json; charset=utf-8')}
        path=urlsplit(self.path).path
        if path not in routes:self.send(404,{'error':'Nie ma takiej strony.'});return
        file,mime=routes[path]
        try:
            body=(ROOT/file).read_bytes()
            if path=='/':body=body.replace(b'__TOKEN__',self.server.token.encode())
            self.send(200,body,mime)
        except OSError:self.send(500,{'error':'Brakuje pliku interfejsu lub przykładów OGLE.'})
    def do_POST(self):
        origin=self.headers.get('Origin')
        valid_origins=[f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}']
        if not self.host_ok() or (origin and origin not in valid_origins) or self.headers.get('X-Local-Token')!=self.server.token:
            self.send(403,{'error':'Odśwież stronę otwartą lokalnie.'});return
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:length=0
        if length<=0 or length>6_000_000:self.send(413,{'error':'Plik jest zbyt duży (limit 5 MB).'});return
        if not self.server.busy.acquire(blocking=False):self.send(429,{'error':'Trwa poprzednia analiza. Poczekaj na wynik.'});return
        try:
            payload=json.loads(self.rfile.read(length))
            if not isinstance(payload,dict):raise ValueError('Nieprawidłowe dane wejściowe.')
            if self.path=='/api/inspect':
                result=inspect_text(payload.get('text',''));result.pop('rows',None)
            elif self.path=='/api/analyze':result=analyze(payload)
            elif self.path=='/api/period':
                a,stats,_=parse_table(payload.get('text',''),payload.get('mapping',{}),payload.get('time_unit','days'),payload.get('band',''),payload.get('object',''))
                result=search_period(a,payload.get('pmin',.2),payload.get('pmax',30));result['import_stats']=stats
            else:self.send(404,{'error':'Nieznane żądanie.'});return
            self.send(200,result)
        except (ValueError,TypeError,KeyError,OverflowError) as e:self.send(400,{'error':str(e)})
        except Exception as e:
            print('Analysis error:',type(e).__name__,str(e),flush=True)
            self.send(500,{'error':'Analiza nie powiodła się. Sprawdź instalację zależności i obecność modeli; szczegóły są w terminalu.'})
        finally:self.server.busy.release()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8767);p.add_argument('--no-browser',action='store_true');a=p.parse_args()
    server=Server(('127.0.0.1',a.port));url=f'http://127.0.0.1:{server.server_port}'
    print('TIMDR — pracownia krzywych blasku:',url,flush=True)
    print('Zatrzymaj: Ctrl+C. Pomiary nie opuszczają komputera.',flush=True)
    if not a.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
