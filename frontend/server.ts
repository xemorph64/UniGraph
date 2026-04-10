import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = process.env.PORT || 3000;

  // Health endpoint
  app.get("/health", (req, res) => {
    res.json({
      status: "online",
      frontend: "standalone",
      api_proxy: "handled by vite dev server",
    });
  });

  // API routes - redirect to backend (handled by Vite proxy)
  app.all("/api/*", (req, res) => {
    res.redirect(`http://localhost:8000${req.originalUrl}`);
  });

  const distPath = path.join(process.cwd(), "dist");
  
  // Try to use Vite for dev
  try {
    const { createServer } = await import("vite");
    const vite = await createServer({
      server: { port: PORT },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } catch {
    // Fallback to static
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`\n╔══════════════════════════════════════════════════════════╗`);
    console.log(`║  UniGRAPH Frontend                              ║`);
    console.log(`║  Running on http://localhost:${PORT}                    ║`);
    console.log(`║  API -> Proxied via Vite to localhost:8000     ║`);
    console.log(`╚══════════════════════════════════════════════════════════╝\n`);
  });
}

startServer();