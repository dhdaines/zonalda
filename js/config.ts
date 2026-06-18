const ALEXI_URL = "https://dhdaines.github.io/alexi/vdsa";
let ZONALDA_API_URL = "https://zonalda.ecolingui.ca/api";
const COLLECTES_URL = "https://ville.sainte-adele.qc.ca/upload/images/SA-calendrier-collecte-2023-2024-8-5x11-vertical-CROP.jpg";
const COLLECTE_ZONE_URL = {
  jaune: "https://lespaysdenhaut.com/wp-content/uploads/2023/07/SainteAdele_jaune2023-24.pdf",
  rose: "https://lespaysdenhaut.com/wp-content/uploads/2023/07/SainteAdele_rose-2023-24.pdf",
};


// Use local REST API in development server
if (import.meta.env.DEV)
    ZONALDA_API_URL = "http://localhost:5010/api";

export { ALEXI_URL, ZONALDA_API_URL, COLLECTES_URL, COLLECTE_ZONE_URL };
