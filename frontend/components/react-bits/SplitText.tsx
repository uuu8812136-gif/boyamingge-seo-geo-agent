'use client';

import { motion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';

type SplitTextProps = {
  text: string;
  className?: string;
  delay?: number; // 每个字符延迟（毫秒）
  duration?: number; // 单字符动画时长（秒）
  y?: number;
  blur?: boolean;
  tag?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span';
  once?: boolean;
};

/**
 * 字符逐个进场动画（自写，不依赖 GSAP SplitText 付费插件）。
 * 中文按字符拆分，每个字符独立动画。
 * 克制：一次性触发，不循环闪烁。
 */
export default function SplitText({
  text,
  className = '',
  delay = 40,
  duration = 0.6,
  y = 30,
  blur = false,
  tag = 'h1',
  once = true,
}: SplitTextProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          if (once) observer.unobserve(ref.current as Element);
        } else if (!once) {
          setInView(false);
        }
      },
      { threshold: 0.2 },
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [once]);

  const chars = Array.from(text); // 支持 emoji 和中文字符
  const Tag = tag as React.ElementType;

  return (
    <Tag ref={ref} className={className} style={{ overflow: 'hidden', display: 'inline-block' }}>
      {chars.map((char, i) => (
        <motion.span
          key={i}
          style={{ display: 'inline-block', willChange: 'transform, opacity, filter' }}
          initial={{ opacity: 0, y, filter: blur ? 'blur(8px)' : 'blur(0px)' }}
          animate={
            inView
              ? { opacity: 1, y: 0, filter: 'blur(0px)' }
              : { opacity: 0, y, filter: blur ? 'blur(8px)' : 'blur(0px)' }
          }
          transition={{
            duration,
            delay: (i * delay) / 1000,
            ease: [0.22, 1, 0.36, 1],
          }}
        >
          {char === ' ' ? ' ' : char}
        </motion.span>
      ))}
    </Tag>
  );
}
