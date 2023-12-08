#!/usr/bin/env python3

"""
Réparer les polygones invalides dans le fichier de zonage.
"""

from shapely.validation import explain_validity, make_valid
import geopandas

zonage = geopandas.read_file("zonalda/zonage.geojson")
invalid = zonage.loc[~zonage.geometry.is_valid]
for idx, zone in invalid.iterrows():
    print(idx, explain_validity(zone.geometry))
    fixed_zone = make_valid(zone.geometry)
    zonage.geometry.iloc[idx] = fixed_zone
with open("zonalda/zonage-valid.geojson", "wt") as outfh:
    outfh.write(zonage.to_json(indent=2, ensure_ascii=False))
