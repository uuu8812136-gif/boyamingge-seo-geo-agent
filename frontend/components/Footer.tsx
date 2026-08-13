import Link from 'next/link';
import { SITE } from '@/lib/site';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-inner">
        <div className="footer-col footer-brand-col">
          <p className="footer-brand">{SITE.brandFull}</p>
          <p className="footer-desc">{SITE.description}</p>
          <a href={`tel:${SITE.hotline.replace(/-/g, '')}`} className="footer-phone">
            {SITE.hotlineDisplay}
          </a>
        </div>
        <div className="footer-col">
          <h4>城市门店</h4>
          <ul>
            <li>
              <Link href="/stores" className="footer-highlight-link">查看已开通门店 →</Link>
            </li>
          </ul>
        </div>
        <div className="footer-col">
          <h4>帮助</h4>
          <ul>
            <li><Link href="/articles">选购指南</Link></li>
            <li><Link href="/#process">服务流程</Link></li>
            <li><Link href="/#faq">常见问题</Link></li>
          </ul>
        </div>
        <div className="footer-col">
          <h4>说明</h4>
          <p className="footer-note">
            具体方案与价格以现场测量后出具的正式报价为准。产品质保按国家标准及合同约定执行。
          </p>
        </div>
      </div>
      <div className="footer-copy">
        <div className="container">© 2026 {SITE.brandFull}</div>
      </div>
    </footer>
  );
}
