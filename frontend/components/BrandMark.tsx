type BrandMarkProps = {
  className?: string;
  title?: string;
};

export default function BrandMark({ className, title = '博雅敏格门窗' }: BrandMarkProps) {
  return (
    <svg className={className} viewBox="0 0 48 48" role="img" aria-label={title} focusable="false">
      <rect width="48" height="48" rx="13" fill="#c45c26" />
      <path d="M14 13.5H34V34.5H14V13.5Z" fill="none" stroke="#fff7ef" strokeWidth="3" strokeLinejoin="round" />
      <path d="M24 14V34" stroke="#fff7ef" strokeWidth="3" strokeLinecap="round" />
      <path d="M15 23.8H33" stroke="#fff7ef" strokeWidth="3" strokeLinecap="round" />
      <path d="M18.5 18.2H21M27 29.7H30.5" stroke="#ffd8bf" strokeWidth="2.3" strokeLinecap="round" />
    </svg>
  );
}
