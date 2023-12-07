"""
ZOnage AdéLois Démystifié pour les Adélois.e.s

API pour applications web
"""

import json

import shapely  # type: ignore
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import Zonalda, MunicipalityError

zonalda = Zonalda()
api = FastAPI()


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


@api.get("/ll/{latitude},{longitude}")
async def ll(latitude: float, longitude: float):
    return Emplacement.from_wgs84(latitude, longitude)


@api.get("/g/{gps}")
async def gps(gps: str):
    parts = [float(x) for x in gps.split(",")]
    if len(parts) != 2:
        raise HTTPException(status_code=404, detail=f"Invalid GPS coordinates {gps}")
    return Emplacement.from_wgs84(*parts)


app = FastAPI()
app.mount("/api", api)
app.add_middleware(
    CORSMiddleware,
    allow_methods=["GET", "OPTIONS"],
    allow_origin_regex="http://localhost(:.*)?",
)
