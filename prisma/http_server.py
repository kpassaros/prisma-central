"""Servidor local sem dependências. Não é um servidor de produção."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from .service import ApiError,Service

class DemoServer(ThreadingHTTPServer):
    daemon_threads=True

def make_server(data='data',port=8787):
    service=Service(data)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass  # Não registrar URLs ou valores de contatos.
        def process(self):
            parts=urlsplit(self.path)
            try:
                if len(self.path)>8192:
                    raise ApiError(414,'uri_too_long','URL longa demais.')
                body=service.dispatch(parts.path,parse_qs(parts.query,keep_blank_values=True),self.command)
                status=200
            except ApiError as exc:
                status,body=exc.status,exc.payload()
            except Exception:
                status,body=500,{'error':{'code':'internal_error','message':'Erro local na demo.'},'synthetic':True}
            raw=json.dumps(body,ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            if status==405:
                self.send_header('Allow','GET, HEAD')
            self.end_headers()
            if self.command!='HEAD':
                self.wfile.write(raw)
        do_GET=do_HEAD=do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=process
    # Deliberadamente sem opção 0.0.0.0. O modo demo é local e sem autenticação.
    return DemoServer(('127.0.0.1',port),Handler)

def serve(data='data',port=8787):
    server=make_server(data,port)
    print(f'Prisma Demo sintético: http://127.0.0.1:{server.server_port} — Ctrl+C para parar.',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
