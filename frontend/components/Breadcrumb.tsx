import Link from 'next/link';

type Crumb = { name: string; href?: string };

export default function Breadcrumb({ items }: { items: Crumb[] }) {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost';
  const itemListElement = items.map((item, idx) => ({
    '@type': 'ListItem',
    position: idx + 1,
    name: item.name,
    ...(item.href ? { item: `${siteUrl}${item.href}` } : {}),
  }));

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            itemListElement,
          }),
        }}
      />
      <nav className="breadcrumb" aria-label="面包屑导航">
        <ol>
          {items.map((item, idx) => (
            <li key={idx}>
              {item.href ? (
                <Link href={item.href}>{item.name}</Link>
              ) : (
                <span>{item.name}</span>
              )}
              {idx < items.length - 1 && <span className="sep">/</span>}
            </li>
          ))}
        </ol>
      </nav>
    </>
  );
}
