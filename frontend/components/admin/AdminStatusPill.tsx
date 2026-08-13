type Props = {
  children: React.ReactNode;
  tone?: 'neutral' | 'good' | 'warn' | 'info' | 'bad';
};

export default function AdminStatusPill({ children, tone = 'neutral' }: Props) {
  return <span className={`admin-pill admin-pill--${tone}`}>{children}</span>;
}
