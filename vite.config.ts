import type { UserConfig, PreviewServer, ViteDevServer } from "vite";

function myPlugin() {
    return {
        name: 'fix-tiles',
        configureServer(server: ViteDevServer) {
            server.middlewares.use((req, res, next) => {
                if (req.originalUrl.match(/\.pbf$/)) {
                    res.setHeader('Content-Encoding', 'gzip');
                }
                next();
            });
        },
        configurePreviewServer(server: PreviewServer) {
            server.middlewares.use((req, res, next) => {
                if (req.originalUrl.match(/\.pbf$/)) {
                    res.setHeader('Content-Encoding', 'gzip');
                }
                next();
            });
        },
    };
}

export default {
plugins: [myPlugin()],
} satisfies UserConfig;
