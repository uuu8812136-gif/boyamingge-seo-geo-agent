'use client';

type Props = {
  markdown: string;
};

/** 简易 Markdown 预览（标题、段落），供后台内容预览 */
export default function MarkdownPreview({ markdown }: Props) {
  const lines = markdown.split('\n');
  return (
    <article className="md-preview">
      {lines.map((line, i) => {
        if (line.startsWith('### ')) {
          return <h4 key={i}>{line.slice(4)}</h4>;
        }
        if (line.startsWith('## ')) {
          return <h3 key={i}>{line.slice(3)}</h3>;
        }
        if (line.startsWith('# ')) {
          return <h2 key={i}>{line.slice(2)}</h2>;
        }
        if (line.startsWith('- ')) {
          return <li key={i}>{line.slice(2)}</li>;
        }
        if (line.trim() === '') {
          return <br key={i} />;
        }
        return <p key={i}>{line}</p>;
      })}
    </article>
  );
}
