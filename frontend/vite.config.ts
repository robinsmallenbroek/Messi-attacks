import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages serves project sites under /<repo-name>/, so the build needs
// the same base path.  Dev server (localhost:5173) ignores this base.
export default defineConfig({
  plugins: [react()],
  base: "/Messi-attacks/",
  server: { port: 5173 },
});
