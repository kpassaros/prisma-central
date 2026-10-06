"""Adaptador opcional FastAPI. Instale requirements-api.txt para usá-lo."""
from pathlib import Path
from urllib.parse import parse_qs
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from .service import Service,ApiError

DESCRIPTION='Fontes sintéticas próprias do Prisma. Não conecta serviços da organização. API local somente leitura.'

def create_app(data='data'):
    service=Service(Path(data))
    app=FastAPI(title='Prisma Demo API',version='0.1.0',description=DESCRIPTION,
        contact={'name':'Projeto Prisma — demonstração sintética'})
    @app.exception_handler(ApiError)
    async def api_error(request,exc):
        return JSONResponse(status_code=exc.status,content=exc.payload())
    def endpoint_factory():
        async def endpoint(request:Request):
            return service.dispatch(request.url.path,parse_qs(request.url.query,keep_blank_values=True))
        return endpoint
    def param(name,kind='string',default=None,minimum=None,maximum=None):
        schema={'type':kind}
        if default is not None:schema['default']=default
        if minimum is not None:schema['minimum']=minimum
        if maximum is not None:schema['maximum']=maximum
        return {'in':'query','name':name,'required':False,'schema':schema}
    cursor=[param('limit','integer',25,1,100),param('cursor'),param('updated_since')]
    routes=[('/health','health',[], 'Saúde da API'),
        ('/api/demo/meta','metadata',[],'Manifesto sintético e disponibilidade por fonte'),
        ('/api/demo/core/companies','companies',[],'Empresas fictícias'),
        ('/api/demo/core/customers','core_customers',[param('page','integer',1,1),
            param('page_size','integer',25,1,100),param('company_id'),param('updated_since')],
            'Clientes Core — chave composta empresa/cliente'),
        ('/api/demo/crm/contacts','crm_contacts',cursor,'Contatos CRM — paginação por cursor'),
        ('/api/demo/omnichannel/customers','omni_customers',cursor,'Clientes Omnichannel — envelope próprio'),
        ('/api/demo/omnichannel/conversations','conversations',cursor,'Conversas fictícias'),
        ('/api/demo/omnichannel/conversations/{conversation_id}/messages','messages',
            [param('limit','integer',25,1,100),param('cursor'),
             {'in':'path','name':'conversation_id','required':True,'schema':{'type':'string','pattern':'^DEMO-CONV-[0-9]{5}$'}}],
            'Mensagens geradas do zero')]
    for path,name,parameters,summary in routes:
        endpoint=endpoint_factory();endpoint.__name__=name
        app.add_api_route(path,endpoint,methods=['GET'],summary=summary,operation_id=name,
            openapi_extra={'parameters':parameters},responses={400:{'description':'Parâmetro/cursor inválido'},
                404:{'description':'Não encontrado'},409:{'description':'Base alterada'},503:{'description':'Fonte indisponível'}})
    return app
