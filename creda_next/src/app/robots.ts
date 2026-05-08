import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || 'https://creda.app';
  return {
    rules: [
      {
        userAgent: '*',
        allow: ['/', '/auth/sign-in', '/auth/sign-up'],
        disallow: [
          '/dashboard',
          '/portfolio',
          '/chat',
          '/budget',
          '/goals',
          '/settings',
          '/admin',
          '/api/',
        ],
      },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
