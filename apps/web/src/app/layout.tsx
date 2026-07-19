import type { Metadata } from 'next';
import { DM_Sans, Fraunces } from 'next/font/google';

import { Toaster } from '@/components/ui/toaster';
import './globals.css';

const display = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

const sans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'Dream Home Estate — Find the home you have been dreaming of',
    template: '%s · Dream Home Estate',
  },
  description:
    'Dream Home Estate helps you discover beautiful homes for sale and rent — while agents list once and publish live to Instagram and X.',
  openGraph: {
    title: 'Dream Home Estate',
    description: 'Find your dream home. Agents list once and publish everywhere that matters.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable}`}>
      <body className="min-h-dvh font-sans antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
        >
          Skip to content
        </a>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
