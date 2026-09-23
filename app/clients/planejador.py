import json
import os

import httpx
from fastapi import HTTPException, Response

BASE_URL = os.getenv("SECONDARY_API_URL", "http://localhost:8001").rstrip("/")
TEMPO = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))

async def requisitar(metodo, caminho, corpo=None, token=None, parametros=None):
    headers = {"Authorization": f"Bearer {token.credentials}"} if token else {}
    parametros = {chave: valor for chave, valor in (parametros or {}).items() if valor is not None}

    try:
        async with httpx.AsyncClient(timeout=TEMPO) as cliente:
            resposta = await cliente.request(
                metodo,
                BASE_URL + caminho,
                json=corpo,
                params=parametros,
                headers=headers,
            )
    except httpx.TimeoutException:
        raise HTTPException(
            504, "Tempo de resposta do serviço de planejamento esgotado."
        )
    except httpx.HTTPError:
        raise HTTPException(
            503, "Serviço de planejamento temporariamente indisponível."
        )

    if resposta.status_code == 204:
        return Response(status_code=204)

    try:
        dados = resposta.json()
    except ValueError:
        dados = {"detail": "Resposta inválida do serviço de planejamento."}

    return Response(
        content=json.dumps(dados, default=str),
        status_code=resposta.status_code,
        media_type="application/json",
    )
    
