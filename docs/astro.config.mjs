// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

// https://astro.build/config
export default defineConfig({
  integrations: [
    starlight({
      title: "linkding",
      logo: {
        src: "./src/assets/logo.svg",
      },
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/sissbruecker/linkding",
        },
      ],
      sidebar: [
        {
          label: "Getting Started",
          items: [
            { label: "Installation", slug: "installation" },
            { label: "Options", slug: "options" },
            { label: "Managed Hosting", slug: "managed-hosting" },
            { label: "Browser Extension", slug: "browser-extension" },
          ],
        },
        {
          label: "Guides",
          items: [
            { label: "Backups", slug: "backups" },
            { label: "Search", slug: "search" },
            { label: "Archiving", slug: "archiving" },
            { label: "Auto Tagging", slug: "auto-tagging" },
            { label: "AI auto-tagging", slug: "ai-auto-tagging" },
            { label: "Keyboard Shortcuts", slug: "shortcuts" },
            { label: "How To", slug: "how-to" },
            { label: "Troubleshooting", slug: "troubleshooting" },
            { label: "Admin", slug: "admin" },
            { label: "REST API", slug: "api" },
          ],
        },
        {
          label: "Resources",
          items: [
            { label: "Community", slug: "community" },
            { label: "Acknowledgements", slug: "acknowledgements" },
          ],
        },
      ],
      customCss: ["./src/styles/custom.css"],
      editLink: {
        baseUrl: "https://github.com/sissbruecker/linkding/edit/master/docs/",
      },
    }),
  ],
});
