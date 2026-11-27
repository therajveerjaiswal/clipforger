import { NextRequest, NextResponse } from 'next/server';

function resolveBackendUrl(): string {
  const raw = (
    process.env.BACKEND_API_URL ||
    process.env.NEXT_PUBLIC_BACKEND_API_URL ||
    'http://localhost:8000'
  )
    .trim()
    .replace(/\/+$/, '');
  if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
    const scheme = raw.startsWith('localhost') || raw.startsWith('127.0.0.1') ? 'http' : 'https';
    return `${scheme}://${raw}`;
  }
  return raw;
}

export async function POST(req: NextRequest) {
  try {
    const signature = req.headers.get('x-razorpay-signature');
    if (!signature) {
      return NextResponse.json({ error: 'Missing Razorpay signature' }, { status: 400 });
    }

    const rawBody = await req.text();
    const backendUrl = resolveBackendUrl();

    const res = await fetch(`${backendUrl}/api/v1/payments/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Razorpay-Signature': signature,
      },
      body: rawBody,
    });

    const text = await res.text();
    try {
      const data = JSON.parse(text);
      return NextResponse.json(data, { status: res.status });
    } catch {
      return NextResponse.json({ detail: text }, { status: res.status });
    }
  } catch (error: any) {
    console.error('Webhook forwarder error:', error);
    return NextResponse.json(
      { error: 'Webhook processing failed', detail: error.message },
      { status: 500 }
    );
  }
}
