import "./style.css";
import { Map, View } from "ol";
import VectorSource from "ol/source/Vector.js";
import { Tile as TileLayer, Vector as VectorLayer } from "ol/layer.js";
import OSM from "ol/source/OSM";
import { fromLonLat, toLonLat } from "ol/proj.js";
import { ZONALDA_API_URL, GEOAPIFY_API_KEY } from "./config";
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
if (adresse == null)
  throw "Element not found: adresse";
const autocomplete = new GeocoderAutocomplete(
  adresse,
  GEOAPIFY_API_KEY, {
  lang: "fr",
  debounceDelay: 500,
  skipIcons: true,
  placeholder: "Chercher une adresse ou cliquez sur la carte...",
  filter: {
    rect: { lon1, lat1, lon2, lat2 }
  },
});

const zonesource = new VectorSource<FeatureLike>();
const zonelayer = new VectorLayer();
const geoformat = new GeoJSON();
function updateInfo(info) {
  const infoDiv = document.getElementById("info");
  if (infoDiv == null)
    throw "Element not found: info";
  const { zone, milieu, description, geometry } = info.zone;
  infoDiv.innerHTML = `
District: ${info.district.numero}<br>
Conseiller: ${info.district.conseiller}<br>
Zone: ${zone} (${milieu} ${description})<br>
Jour de collecte: ${info.collecte.jour}<br>
`;
  /*
  zonesource.clear(true);
  const feats = geoformat.readFeatures(geometry);
  console.log(feats);
  zonesource.addFeatures(feats);
  */
}

async function getInfo(coords: GeoJSONPosition) {
  const [lon, lat] = coords;
  const url = `${ZONALDA_API_URL}/ll/${lat},${lon}`;
  const response = await fetch(url);
  if (response.ok) {
    const info = await response.json();
    updateInfo(info);
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
if (locate == null)
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
