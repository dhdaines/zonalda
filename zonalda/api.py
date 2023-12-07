"""
ZOnage AdéLois Démystifié pour les Adélois.e.s

API pour applications web
"""

import json
import logging
import os

import dotenv
import httpx
import shapely  # type: ignore
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import Zonalda, MunicipalityError

LOGGER = logging.getLogger("zonalda-api")
zonalda = Zonalda()
api = FastAPI()
dotenv.load_dotenv()
if "GEOAPIFY_API_KEY" not in os.environ:
    raise RuntimeError("Veuillez définir GEOAPIFY_API_KEY dans .env ou l'environnement")
logging.basicConfig(level=logging.INFO)


class District(BaseModel):
    numero: int
    conseiller: str


class Collecte(BaseModel):
    jour: str
    couleur: str


class Zone(BaseModel):
    zone: str
    milieu: str
    description: str
    geometry: dict


class Emplacement(BaseModel):
    district: District
    collecte: Collecte
    zone: Zone

    @classmethod
    def from_wgs84(self, latitude: float, longitude: float) -> "Emplacement":
        district, zone, collecte = zonalda(latitude, longitude)
        return self(
            district=District(numero=district["id"], conseiller=district["Conseiller"]),
            collecte=Collecte(jour=collecte["jour"], couleur=collecte["couleur"]),
            zone=Zone(
                zone=zone["ZONE"],
                milieu=zone["Types"],
                description=zone["Descr_Type"],
                # FIXME: thoroughly unnecessary JSON parsing
                geometry=json.loads(shapely.to_geojson(zone["geometry"])),
            ),
        )


@api.exception_handler(MunicipalityError)
async def municipality_error_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=404)


@api.get("/g/{latitude},{longitude}")
async def ll(latitude: float, longitude: float):
    return Emplacement.from_wgs84(latitude, longitude)


GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/autocomplete"
ADDRESS_CACHE = {}
client = httpx.AsyncClient()


@api.get("/geoloc")
async def geoloc(
    text: str,
    apiKey: str,
    type: str | None = None,
    limit: str | None = None,
    lang: str | None = None,
    filter: str | None = None,
    bias: str | None = None,
):
    if text in ADDRESS_CACHE:
        LOGGER.info("Cache hit for '%s'", text)
        return JSONResponse(ADDRESS_CACHE[text])
    params = {
        "text": text,
        "apiKey": os.environ["GEOAPIFY_API_KEY"],
    }
    if type is not None:
        params["type"] = type
    if limit is not None:
        params["limit"] = limit
    if lang is not None:
        params["lang"] = lang
    if filter is not None:
        params["filter"] = filter
    if bias is not None:
        params["bias"] = bias
    r = await client.get(GEOAPIFY_URL, params=params)
    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code, detail="Échec de requête Geoapify"
        )
    ADDRESS_CACHE[text] = r.json()
    return JSONResponse(ADDRESS_CACHE[text])


app = FastAPI()
app.mount("/api", api)
middleware_args: dict[str, str | list[str]]
if os.getenv("DEVELOPMENT", False):
    LOGGER.info(
        "Running in development mode, will allow requests from http://localhost:*"
    )
    # Allow requests from localhost dev servers
    middleware_args = dict(
        allow_origin_regex="http://localhost(:.*)?",
    )
else:
    # Allow requests *only* from ZONALDA app (or otherwise configured site name)
    middleware_args = dict(
        allow_origins=[
            os.getenv("ORIGIN", "https://dhdaines.github.io/zonalda"),
        ],
    )
app.add_middleware(
    CORSMiddleware,
    allow_methods=["GET", "OPTIONS"],
    **middleware_args
)
