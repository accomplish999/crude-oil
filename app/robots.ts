import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/archive";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
