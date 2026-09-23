from ..clients.planejador import requisitar

async def encaminhar(metodo, caminho, corpo=None, t=None, parametros=None):
    return await requisitar(metodo, caminho, corpo, token=t, parametros=parametros)
