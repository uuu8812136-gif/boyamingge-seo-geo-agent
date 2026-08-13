import { NextResponse } from 'next/server';
import { customerServiceStoreHealth } from '@/lib/customer-service-store';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    return NextResponse.json(await customerServiceStoreHealth(), { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { status: 'not_ready', error: error instanceof Error ? error.message : '客服存储不可用' },
      { status: 503 },
    );
  }
}
