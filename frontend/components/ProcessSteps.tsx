import { PROCESS_STEPS } from '@/lib/site';

export default function ProcessSteps() {
  return (
    <ol className="process-steps">
      {PROCESS_STEPS.map((item) => (
        <li key={item.step} className="process-step">
          <span className="process-num">{item.step}</span>
          <div>
            <h3>{item.title}</h3>
            <p>{item.desc}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
