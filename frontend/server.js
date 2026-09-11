const path = require("path");
const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();
const PORT = Number(process.env.PORT || 3000);
const API_URL = process.env.API_URL || "http://127.0.0.1:8000";
const publicDir = path.join(__dirname, "public");

app.use(
  "/api",
  createProxyMiddleware({
    target: API_URL,
    changeOrigin: true,
    pathRewrite: { "^/api": "" },
    timeout: 180000,
    proxyTimeout: 180000,
  })
);

app.get("/", (_req, res) => {
  res.sendFile(path.join(publicDir, "login.html"));
});

app.get("/app", (_req, res) => {
  res.sendFile(path.join(publicDir, "index.html"));
});

app.use(express.static(publicDir, { index: false }));

app.listen(PORT, () => {
  console.log(`Website  http://localhost:${PORT}`);
  console.log(`API      ${API_URL}  (proxied via /api)`);
});
