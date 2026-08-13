'use client';

import dynamic from 'next/dynamic';

const Threads = dynamic(() => import('./Threads'), { ssr: false });

export default Threads;
