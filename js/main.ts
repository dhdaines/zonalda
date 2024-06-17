import { Map, View } from "ol";
import VectorSource from "ol/source/Vector.js";
import { Tile as TileLayer, Vector as VectorLayer } from "ol/layer.js";
import OSM from "ol/source/OSM";
import { fromLonLat, toLonLat } from "ol/proj.js";
import { ZONALDA_API_URL, ALEXI_URL, COLLECTES_URL, COLLECTE_ZONE_URL } from "./config";
import { GeocoderAutocomplete } from '@geoapify/geocoder-autocomplete';
import { Feature as GeoJSONFeature, Point as GeoJSONPoint, Position as GeoJSONPosition } from "geojson";
import { circular } from "ol/geom/Polygon";
import GeoJSON from "ol/format/GeoJSON";
import Feature, { FeatureLike } from "ol/Feature";
import Point from "ol/geom/Point";

const sainteAdeleLonLat = [-74.13575955519771, 45.95173098477338];
const sainteAdeleBBox = [-74.24500706506886, 45.91083041569574, -73.97918840416655, 46.03278941847226];

const tile = new TileLayer({
  source: new OSM(),
});
const source = new VectorSource<Feature>({
  features: [
    new Feature(new Point(fromLonLat(sainteAdeleLonLat))),
  ],
  attributions: `Géomatique: <a target="_blank" href="https://lespaysdenhaut.com/">MRC des Pays-d'en-haut</a>`,
}
);
const geoloc = new VectorLayer({
  source: source,
});

const view = new View({
    center: fromLonLat(sainteAdeleLonLat),
    zoom: 16,
});

function getCurrentPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    const options = {
      enableHighAccuracy: true,
    };
    navigator.geolocation.getCurrentPosition(resolve, reject, options);
  });
}

const [lon1, lat1, lon2, lat2] = sainteAdeleBBox;
const adresse = document.getElementById("adresse");
if (adresse === null)
  throw "Element not found: adresse";
const autocomplete = new GeocoderAutocomplete(
  adresse,
  "APIKEY", {
  debounceDelay: 250,
  lang: "fr",
  skipIcons: true,
  placeholder: "Chercher une adresse ou cliquez sur la carte...",
  filter: {
    rect: { lon1, lat1, lon2, lat2 }
  },
  });
// @ts-ignore
autocomplete.geocoderUrl = `${ZONALDA_API_URL}/geoloc`;

let zonage = {
  categorie_milieu: {},
  milieu: {},
}

window.addEventListener("load", async () => {
  const response = await fetch(`${ALEXI_URL}/zonage.json`);
  if (response.ok) {
    zonage = await response.json();
  }
});

function categorieTexte(info) {
  if (info === null)
    return "inconnu";
  const { zone, milieu, description } = info;
  const [categorie, souscategorie] = milieu.split(".");
  const cat = zonage.categorie_milieu[categorie];
  if (cat !== undefined) {
    console.log(cat)
    const { titre, url } = cat;
    return `<a target="_blank" href="${ALEXI_URL}/${url}">${categorie} ${titre}</a>`;
  }
  else
    return categorie;
}

function milieuTexte(info) {
  if (info === null)
    return "inconnu";
  const { zone, milieu, description } = info;
  const mil = zonage.milieu[milieu];
  if (mil !== undefined) {
    const { titre, url } = mil;
    return `<a target="_blank" href="${ALEXI_URL}/${url}">${milieu} ${description}</a>`;
  }
  else
    return `${milieu} ${description}\n`;
}

function collecteTexte(info) {
  if (info === null)
    return "inconnue";
  const { couleur, jour } = info;
  if (couleur in COLLECTE_ZONE_URL)
    return `${jour} (zone ${couleur}) <a href="${COLLECTE_ZONE_URL[couleur]}">(calendrier PDF)</a>`;
  else
    return `${jour} <a target="_blank" href="${COLLECTES_URL}">(calendrier PDF)</a>`;
}

function conseilTexte(info) {
  if (info === null)
    return "inconnu";
  return `conseillier: <a href="mailto:district${info.numero}@vdsa.ca">${info.conseiller}</a>`;
}

const geoformat = new GeoJSON();
const zonesource = new VectorSource();
const zonelayer = new VectorLayer<any>({  // stfu tsc
  source: zonesource,
});
function updateInfo(info) {
  const infoDiv = document.getElementById("info");
  if (infoDiv === null)
    throw "Element not found: info";
  const { zone, district, collecte } = info;
  infoDiv.innerHTML = `<table>
<tr><td>District</td><td>${district.numero} (${conseilTexte(district)})<td></tr>
<tr><td>Zone</td><td>${zone.zone ?? "inconnue"}</td></tr>
<tr><td>Catégorie</td><td>${categorieTexte(zone)}<td></tr>
<tr><td>Milieu</td><td>${milieuTexte(zone)}<td></tr>
<tr><td>Collecte</td><td>${collecteTexte(collecte)}<td></tr>
</table>`;
  zonesource.clear(true);
  zonesource.addFeature(new Feature(geoformat.readGeometry(zone.geometry, {
    dataProjection: "EPSG:4326",
    featureProjection: view.getProjection()
  })));
  view.fit(zonesource.getExtent(), {
    maxZoom: 16,
    duration: 500,
  });
}

function infoError(txt: string) {
  const infoDiv = document.getElementById("info");
  if (infoDiv === null)
    throw "Element not found: info";
  infoDiv.innerHTML = `<p>${txt}</p>`;
}

async function getInfo(coords: GeoJSONPosition) {
  const [lon, lat] = coords;
  const url = `${ZONALDA_API_URL}/g/${lat},${lon}`;
  const response = await fetch(url);
  if (response.ok) {
    const info = await response.json();
    updateInfo(info);
  }
  else if (response.status == 404) {
    infoError(`L'endroit choisi ne se situe pas à Sainte-Adèle.  Veuillez réessayer.`);
  }
  else {
    infoError(`Les informations n’ont pu être trouvées pour l'endroit choisi à cause
d'un problème avec la base géomatique.  Veuillez réessayer un autre
endroit à proximité.`);
  }
}

autocomplete.on('select', async (location: GeoJSONFeature) => {
  const pos = location.geometry as GeoJSONPoint;
  source.clear(true);
  // FIXME: OL almost certainly has a method for this
  const projPos = fromLonLat(pos.coordinates);
  source.addFeature(new Feature(new Point(projPos)));
  view.animate({ center: projPos });
  getInfo(pos.coordinates);
});

async function geolocateMe() {
  const pos = await getCurrentPosition();
  const coords = [pos.coords.longitude, pos.coords.latitude];
  const accuracy = circular(coords, pos.coords.accuracy);
  const projAcc = accuracy.transform("EPSG:4326", view.getProjection());
  const projPos = fromLonLat(coords);
  source.clear(true);
  source.addFeature(new Feature(projAcc));
  source.addFeature(new Feature(new Point(fromLonLat(coords))));
  view.animate({center: projPos});
  autocomplete.setValue("");
  getInfo(coords);
}

const locate = document.getElementById("locate");
if (locate === null)
  throw "Element not found: locate";
locate.addEventListener("click", geolocateMe);

const map = new Map({
  target: "map",
  layers: [tile, zonelayer, geoloc],
  view: view,
});

map.on("click", async (evt) => {
  source.clear(true);
  source.addFeature(new Feature(new Point(evt.coordinate)));
  view.animate({center: evt.coordinate});
  autocomplete.setValue("");
  const coords = toLonLat(evt.coordinate);
  getInfo(coords);
});
