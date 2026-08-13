import { PRODUCT_SPECS } from '@/lib/site';

export default function ProductGrid() {
  return (
    <div className="spec-grid">
      {PRODUCT_SPECS.map((item) => (
        <div key={item.name} className="spec-item">
          <h3>{item.name}</h3>
          <p>{item.desc}</p>
        </div>
      ))}
    </div>
  );
}
