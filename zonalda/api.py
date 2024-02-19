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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from . import MunicipalityError, Zonalda

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
    district: District | None
    collecte: Collecte | None
    zone: Zone | None
    point: tuple[float, float]

    @classmethod
    def from_wgs84(self, latitude: float, longitude: float) -> "Emplacement":
        """
        Chercher les informations géomatiques pour un emplacement GPS.
        """
        district, zone, collecte = zonalda(latitude, longitude)
        return self(
            district=District(numero=district["id"], conseiller=district["Conseiller"])
            if district is not None
            else None,
            collecte=Collecte(jour=collecte["jour"], couleur=collecte["couleur"])
            if collecte is not None
            else None,
            zone=Zone(
                zone=zone["ZONE"],
                milieu=zone["Types"],
                description=zone["Descr_Type"],
                # FIXME: thoroughly unnecessary JSON parsing
                geometry=json.loads(shapely.to_geojson(zone["geometry"])),
            )
            if zone is not None
            else None,
            point=(longitude, latitude),
        )

    @classmethod
    def from_zone(self, zone: str) -> "Emplacement":
        """
        Localiser le centroïde d'une zone et retourner les autres informations.
        """
        latitude, longitude = zonalda[zone]
        return self.from_wgs84(latitude, longitude)


@api.exception_handler(MunicipalityError)
async def municipality_error_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=404)


@api.get("/g/{latitude},{longitude}")
async def ll(latitude: float, longitude: float):
    return Emplacement.from_wgs84(latitude, longitude)


@api.get("/z/{zone}")
async def zz(zone: str):
    try:
        return Emplacement.from_zone(zone)
    except KeyError:
        return None


GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/autocomplete"
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
    return JSONResponse(r.json())


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
            os.getenv("ORIGIN", "https://dhdaines.github.io"),
        ],
    )
app.add_middleware(CORSMiddleware, allow_methods=["GET", "OPTIONS"], **middleware_args)
