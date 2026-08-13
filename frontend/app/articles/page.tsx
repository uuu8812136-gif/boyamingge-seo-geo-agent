import type { Metadata } from 'next';
import ArticlesPageClient from '@/components/ArticlesPageClient';
import { fetchArticles } from '@/lib/api';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: '门窗选购指南',
  description: '防盗门、断桥铝、封阳台、隔音窗与旧窗改造选购与安装说明。',
  alternates: { canonical: '/articles' },
};

export default async function ArticlesPage() {
  const articles = await fetchArticles();
  return <ArticlesPageClient articles={articles} />;
}
