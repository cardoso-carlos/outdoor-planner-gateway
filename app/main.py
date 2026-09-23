import json
import os
from datetime import datetime
from enum import StrEnum

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from .controllers.planejador import encaminhar

app = FastAPI(title="Gateway Planejador de Atividades ao Ar Livre")
security = HTTPBearer()
BASE = os.getenv("SECONDARY_API_URL", "http://localhost:8001").rstrip("/")
TEMPO = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))


class TipoAtividade(StrEnum):
    CORRIDA = "CORRIDA"
    CAMINHADA = "CAMINHADA"
    CICLISMO = "CICLISMO"
    TRILHA = "TRILHA"
    OUTRA = "OUTRA"


class Situacao(StrEnum):
    PLANEJADA = "PLANEJADA"
    CONCLUIDA = "CONCLUIDA"
    CANCELADA = "CANCELADA"


class Usuario(BaseModel):
    nome: str = Field(min_length=1)
    email: EmailStr
    senha: str = Field(min_length=8)


class Credenciais(BaseModel):
    email: EmailStr
    senha: str


class Atividade(BaseModel):
    titulo: str = Field(min_length=1)
    tipo_atividade: TipoAtividade
    data_agendada: datetime
    nome_local: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    observacoes: str | None = None
    situacao: Situacao = Situacao.PLANEJADA


class Atualizacao(BaseModel):
    titulo: str | None = Field(None, min_length=1)
    tipo_atividade: TipoAtividade | None = None
    data_agendada: datetime | None = None
    nome_local: str | None = Field(None, min_length=1)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    observacoes: str | None = None
    situacao: Situacao | None = None


async def encaminhar_antigo(m, c, corpo=None, t=None, parametros=None):
    headers = {"Authorization": f"Bearer {t.credentials}"} if t else {}

    try:
        async with httpx.AsyncClient(timeout=TEMPO) as cliente:
            r = await cliente.request(
                m,
                BASE + c,
                json=corpo,
                params=parametros,
                headers=headers,
            )
    except httpx.TimeoutException:
        raise HTTPException(504, "Tempo de resposta do serviço de planejamento esgotado.")
    except httpx.HTTPError:
        raise HTTPException(503, "Serviço de planejamento temporariamente indisponível.")

    if r.status_code == 204:
        return Response(status_code=204)

    try:
        d = r.json()
    except ValueError:
        d = {"detail": "Resposta inválida do serviço de planejamento."}

    return Response(
        content=json.dumps(d, default=str),
        status_code=r.status_code,
        media_type="application/json",
    )


def dados(x):
    return x.model_dump(mode="json")


@app.get("/saude")
async def saude():
    return await encaminhar("GET", "/saude")


@app.post("/api/v1/auth/register", status_code=201)
async def cadastrar(p: Usuario):
    return await encaminhar("POST", "/api/v1/auth/register", dados(p))


@app.post("/api/v1/auth/login")
async def entrar(p: Credenciais):
    return await encaminhar("POST", "/api/v1/auth/login", dados(p))


@app.get("/api/v1/auth/me")
async def eu(t: HTTPAuthorizationCredentials = Depends(security)):
    return await encaminhar("GET", "/api/v1/auth/me", t=t)


@app.post("/api/v1/atividades", status_code=201)
async def criar(p: Atividade, t: HTTPAuthorizationCredentials = Depends(security),):
    return await encaminhar("POST", "/api/v1/atividades", dados(p), t)


@app.get("/api/v1/atividades")
async def listar(
    t: HTTPAuthorizationCredentials = Depends(security),
    pagina: int = Query(1, ge=1),
    tamanho_pagina: int = Query(10, ge=1, le=100),
    tipo_atividade: TipoAtividade | None = None,
    situacao: Situacao | None = None,
    ordenar_por: str = Query(
        "data_agendada",
        pattern="^(data_agendada|criado_em)$",
    ),
    ordem: str = Query("crescente", pattern="^(crescente|decrescente)$"),
):
    parametros = {
        "pagina": pagina,
        "tamanho_pagina": tamanho_pagina,
        "tipo_atividade": tipo_atividade,
        "situacao": situacao,
        "ordenar_por": ordenar_por,
        "ordem": ordem,
    }
    return await encaminhar("GET", "/api/v1/atividades", t=t, parametros=parametros)


@app.get("/api/v1/atividades/{atividade_id}")
async def obter(atividade_id: int, t: HTTPAuthorizationCredentials = Depends(security),):
    return await encaminhar("GET", f"/api/v1/atividades/{atividade_id}", t=t)


@app.put("/api/v1/atividades/{atividade_id}")
async def atualizar(atividade_id: int, p: Atualizacao, t: HTTPAuthorizationCredentials = Depends(security),):
    return await encaminhar(
        "PUT",
        f"/api/v1/atividades/{atividade_id}",
        p.model_dump(mode="json", exclude_unset=True, exclude_none=True),
        t,
    )


@app.delete("/api/v1/atividades/{atividade_id}", status_code=204)
async def excluir(atividade_id: int, t: HTTPAuthorizationCredentials = Depends(security),):
    return await encaminhar("DELETE", f"/api/v1/atividades/{atividade_id}", t=t)


@app.post("/api/v1/atividades/{atividade_id}/avaliacoes", status_code=201)
async def avaliar(atividade_id: int, t: HTTPAuthorizationCredentials = Depends(security),):
    return await encaminhar(
        "POST",
        f"/api/v1/atividades/{atividade_id}/avaliacoes",
        t=t,
    )


@app.get("/api/v1/atividades/{atividade_id}/avaliacoes")
async def avaliacoes(atividade_id: int, t: HTTPAuthorizationCredentials = Depends(security),):
    return await encaminhar(
        "GET",
        f"/api/v1/atividades/{atividade_id}/avaliacoes",
        t=t,
    )
    
