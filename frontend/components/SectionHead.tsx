import ScrollReveal from '@/components/ScrollReveal';

type Props = {
  eyebrow?: string;
  title: string;
  desc?: string;
  align?: 'center' | 'left';
  reveal?: boolean;
  level?: 1 | 2;
};

export default function SectionHead({ eyebrow, title, desc, align = 'center', reveal = true, level = 2 }: Props) {
  const Heading = level === 1 ? 'h1' : 'h2';
  const inner = (
    <>
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <Heading className="section-title-line">{title}</Heading>
      {desc && <p className="section-desc">{desc}</p>}
    </>
  );

  if (!reveal) {
    return <div className={`section-head section-head--${align}`}>{inner}</div>;
  }

  return (
    <ScrollReveal className={`section-head section-head--${align}`}>
      {inner}
    </ScrollReveal>
  );
}
