"""
ZOnage AdéLois Démystifié pour les Adélois.e.s

API pour applications web
"""

from fastapi import FastAPI
from pydantic import BaseModel

from . import Zonalda

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


@api.get("/{geoloc}")
async def root(geoloc: str):
    latitude, longitude = geoloc.split(",")
    district, zone, collecte = zonalda(latitude, longitude)
    return {
        "district": District(numero=district["id"], conseiller=district["Conseiller"]),
        "collecte": Collecte(jour=collecte["jour"], couleur=collecte["couleur"]),
        "zone": Zone(
            zone=zone["ZONE"], milieu=zone["Types"], description=zone["Descr_Type"]
        ),
    }


app = FastAPI()
app.mount("/api", api)
