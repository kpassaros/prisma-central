import argparse
import json
import sys
from .generator import generate
from .http_server import serve
from .extractor import extract
from .validation import check

def main():
    parser=argparse.ArgumentParser(description='Prisma Demo — somente dados sintéticos e loopback.')
    subs=parser.add_subparsers(dest='command',required=True)
    g=subs.add_parser('generate');g.add_argument('--out',default='data');g.add_argument('--customers',type=int,default=120)
    g.add_argument('--seed',type=int,default=42);g.add_argument('--unavailable',choices=['none','core','crm','omnichannel'],default='none')
    g.add_argument('--force',action='store_true')
    s=subs.add_parser('serve');s.add_argument('--data',default='data');s.add_argument('--port',type=int,default=8787)
    s.add_argument('--engine',choices=['standard','fastapi'],default='standard')
    e=subs.add_parser('extract');e.add_argument('--base-url',default='http://127.0.0.1:8787');e.add_argument('--out',default='snapshots')
    c=subs.add_parser('check');c.add_argument('--data',default='data')
    p=subs.add_parser('panel');p.add_argument('--snapshots',default='snapshots');p.add_argument('--port',type=int,default=8790)
    args=parser.parse_args()
    try:
        if args.command=='generate':result=generate(args.out,args.customers,args.seed,args.unavailable,args.force)
        elif args.command=='check':result=check(args.data)
        elif args.command=='extract':result=extract(args.base_url,args.out)
        elif args.command=='panel':
            if not 1<=args.port<=65535:raise ValueError('Porta deve estar entre 1 e 65535.')
            from .panel import serve_panel
            serve_panel(args.snapshots,args.port)
            return 0
        else:
            if not 1<=args.port<=65535:raise ValueError('Porta deve estar entre 1 e 65535.')
            if args.engine=='standard':serve(args.data,args.port)
            else:
                try:
                    import uvicorn
                    from .fastapi_app import create_app
                except ImportError as exc:
                    raise ValueError('Instale requirements-api.txt para usar FastAPI.') from exc
                uvicorn.run(create_app(args.data),host='127.0.0.1',port=args.port,access_log=False)
            return 0
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError) as exc:
        print('Prisma Demo: '+str(exc),file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
