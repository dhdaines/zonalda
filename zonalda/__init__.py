"""
ZOnage AdéLois Démystifié pour les Adélois.e.s

Module pour géolocaliser zonage, districts, et autres choses
"""

import argparse
import logging
from pathlib import Path

import geopandas  # type: ignore
from pandas import Series
from shapely import Point  # type: ignore

VERSION = "0.0.2"
THISDIR = Path(__file__).parent
LOGGER = logging.getLogger("zonalda")


class MunicipalityError(RuntimeError):
    pass


class Zonalda:
    """Base d'informations géomatiques pertinentes aux citoyens"""

    def __init__(self):
        self.ville = geopandas.read_file(THISDIR / "sainte-adele.geojson").iloc[0]
        self.districts = geopandas.read_file(THISDIR / "districts.geojson")
        zonage = geopandas.read_file(THISDIR / "zonage.geojson")
        self.zonage = zonage.assign(ZONE=zonage["ZONE"].str.replace(" ", ""))
        self.collectes = geopandas.read_file(THISDIR / "collectes.geojson")

    def __getitem__(self, name: str) -> tuple[
        Series | None,
        Series | None,
        Series | None,
    ]:
        """Trouver les informations pour une zone."""
        zones = self.zonage.loc[self.zonage["ZONE"] == name]
        if zones.empty:
            raise KeyError("Zone not found: %s" % name)
        zone = zones.iloc[0]
        district, collecte = None, None
        districts = self.districts.loc[self.districts.contains(zone.geometry)]
        if len(districts) == 0:
            districts = self.districts.loc[self.districts.intersects(zone.geometry)]
        if len(districts) > 1:
            LOGGER.warning("Plusieurs districts trouvé pour %s: %s", name, districts)
        if len(districts):
            district = districts.iloc[0]
        collectes = self.collectes.loc[self.collectes.contains(zone.geometry)]
        if len(collectes) == 0:
            collectes = self.collectes.loc[self.collectes.intersects(zone.geometry)]
        if len(collectes) > 1:
            LOGGER.warning(
                "Plusieurs zones de collectes trouvé pour %s: %s", name, collectes
            )
        if len(collectes):
            collecte = collectes.iloc[0]
        return district, zone, collecte

    def __call__(self, latitude: float, longitude: float) -> tuple[
        Series | None,
        Series | None,
        Series | None,
    ]:
        """Chercher les informations citoyennes pour un emplacement."""
        p = Point(longitude, latitude)
        if not self.ville.geometry.contains(p):
            raise MunicipalityError(
                "Emplacement %s ne se trouve pas à Sainte-Adèle" % p
            )
        district, zone, collecte = None, None, None
        districts = self.districts.loc[self.districts.contains(p)]
        if len(districts) > 1:
            LOGGER.warning("Plusieurs districts trouvé pour %s: %s", p, districts)
        if len(districts):
            district = districts.iloc[0]
        zones = self.zonage.loc[self.zonage.contains(p)]
        if len(zones) > 1:
            LOGGER.warning("Plusieurs zones trouvé pour %s: %s", p, zones)
        if len(zones):
            zone = zones.iloc[0]
        collectes = self.collectes.loc[self.collectes.contains(p)]
        if len(collectes) > 1:
            LOGGER.warning(
                "Plusieurs zones de collectes trouvé pour %s: %s", p, collectes
            )
        if len(collectes):
            collecte = collectes.iloc[0]
        return district, zone, collecte


def main():
    """CLI Entry point"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "geoloc", help="Géolocalisation (latitute et longitude séparés par une virgule)"
    )
    args = parser.parse_args()
    logging.basicConfig()
    latitude, longitude = args.geoloc.split(",")
    z = Zonalda()
    district, zone, collecte = z(latitude, longitude)
    print(
        f"""Emplacement: {latitude},{longitude}
District: {district['id']}
Conseiller: {district['Conseiller']}
Jour de collecte: {collecte['jour']}
Zone: {zone['ZONE']} ({zone['Types']} {zone['Descr_Type']})
"""
    )
