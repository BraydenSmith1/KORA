import 'dotenv/config'
import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import crypto from 'crypto';
import { PrismaClient } from '@prisma/client';
import { z } from 'zod';
import { PaymentsAdapter } from './adapters/payments.js';
import { ChainAdapter } from './adapters/chain.js';

const prisma = new PrismaClient();
const pay = new PaymentsAdapter(prisma);
const chain = new ChainAdapter(prisma);

const app = express();
app.use(cors());
app.use(express.json());
app.use(morgan('dev'));

const JWT_SECRET = process.env.JWT_SECRET || 'kora-dev-secret-change-me';
if(!process.env.JWT_SECRET){
  console.warn('[Auth] JWT_SECRET not set; using insecure default. Set JWT_SECRET in .env.');
}

const toNumber = (value) => Number(value ?? 0);
const safeJson = (value) => {
  if(value === null || value === undefined) return null;
  try{
    return JSON.parse(value);
  }catch(_err){
    return null;
  }
};
const startOfToday = () => {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now;
};
const startOfWeek = (date = new Date()) => {
  const d = new Date(date);
  const day = d.getDay(); // 0 (Sun) - 6 (Sat)
  const delta = (day + 6) % 7; // convert to Monday-start
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - delta);
  return d;
};

const sanitizeUser = (user) => {
  if(!user) return null;
  const { passwordHash, ...rest } = user;
  return rest;
};

function hashPassword(password){
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha512').toString('hex');
  return `${salt}:${hash}`;
}

function verifyPassword(password, stored){
  if(!stored) return false;
  const [salt, hash] = stored.split(':');
  if(!salt || !hash) return false;
  const verifyHash = crypto.pbkdf2Sync(password, salt, 100000, 64, 'sha512').toString('hex');
  try{
    return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), Buffer.from(verifyHash, 'hex'));
  }catch(_err){
    return false;
  }
}

function base64UrlEncode(input){
  return Buffer.from(input).toString('base64url');
}

function base64UrlDecode(input){
  return Buffer.from(input, 'base64url').toString('utf8');
}

function signToken(user){
  const header = { alg: 'HS256', typ: 'JWT' };
  const exp = Math.floor(Date.now() / 1000) + (7 * 24 * 60 * 60); // 7 days
  const payload = {
    sub: user.id,
    email: user.email,
    regionId: user.regionId || null,
    exp
  };
  const unsigned = `${base64UrlEncode(JSON.stringify(header))}.${base64UrlEncode(JSON.stringify(payload))}`;
  const signature = crypto.createHmac('sha256', JWT_SECRET).update(unsigned).digest('base64url');
  return `${unsigned}.${signature}`;
}

function verifyToken(token){
  if(!token) return null;
  const parts = token.split('.');
  if(parts.length !== 3) return null;
  const [headerB64, payloadB64, signature] = parts;
  const unsigned = `${headerB64}.${payloadB64}`;
  const expectedSig = crypto.createHmac('sha256', JWT_SECRET).update(unsigned).digest('base64url');
  try{
    if(!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expectedSig))) return null;
  }catch(_err){
    return null;
  }
  let payload;
  try{
    payload = JSON.parse(base64UrlDecode(payloadB64));
  }catch(_err){
    return null;
  }
  if(payload.exp && Date.now() / 1000 > payload.exp) return null;
  return payload;
}

const PILOT_USERS = {
  operator: {
    email: process.env.PILOT_OPERATOR_EMAIL || 'operator@pilot.local',
    password: process.env.PILOT_OPERATOR_PASSWORD || '1',
    name: process.env.PILOT_OPERATOR_NAME || 'Microgrid Operator',
    organization: process.env.PILOT_OPERATOR_MICROGRID || 'Sunset Ridge Microgrid',
    regionId: process.env.PILOT_OPERATOR_REGION || 'region-1',
    initialBalanceCents: 20000
  },
  anchor: {
    email: process.env.PILOT_ANCHOR_EMAIL || 'anchor@pilot.local',
    password: process.env.PILOT_ANCHOR_PASSWORD || '1',
    name: process.env.PILOT_ANCHOR_NAME || 'Anchor Customer',
    organization: process.env.PILOT_ANCHOR_ORG || 'Anchor Clinic',
    regionId: process.env.PILOT_ANCHOR_REGION || 'region-1',
    initialBalanceCents: 0
  }
};

async function ensurePilotUser(role){
  const config = PILOT_USERS[role];
  if(!config) throw new Error(`Unknown pilot role: ${role}`);
  let user = await prisma.user.findUnique({ where: { email: config.email } });
  if(!user){
    user = await prisma.user.create({
      data: {
        email: config.email,
        name: config.name,
        organization: config.organization,
        regionId: config.regionId
      }
    });
  }
  let wallet = await prisma.wallet.findUnique({ where: { userId: user.id } });
  if(!wallet){
    wallet = await prisma.wallet.create({
      data: {
        userId: user.id,
        balanceCents: config.initialBalanceCents
      }
    });
  }
  return user;
}

async function runRegionMatch(regionId){
  const buy = await prisma.request.findMany({
    where: { status: 'OPEN', regionId },
    orderBy: [{ maxPriceCentsPerKwh: 'desc' }, { createdAt: 'asc' }]
  });
  const sell = await prisma.offer.findMany({
    where: { status: 'OPEN', regionId },
    orderBy: [{ priceCentsPerKwh: 'asc' }, { createdAt: 'asc' }]
  });

  let i = 0;
  let j = 0;
  let executed = 0;
  const receipts = [];

  while(i < buy.length && j < sell.length){
    const b = buy[i];
    const s = sell[j];
    if(b.maxPriceCentsPerKwh < s.priceCentsPerKwh){
      j++;
      continue;
    }
    const bRem = Number(b.quantityKwh) - Number(b.filledKwh);
    const sRem = Number(s.quantityKwh) - Number(s.filledKwh);
    const qty = Math.min(bRem, sRem);
    const price = s.priceCentsPerKwh;
    const amountCents = Math.round(qty * price);

    const trade = await prisma.trade.create({
      data: {
        buyerId: b.userId,
        sellerId: s.userId,
        regionId,
        offerId: s.id,
        requestId: b.id,
        priceCentsPerKwh: price,
        quantityKwh: qty,
        amountCents,
        status: 'SETTLED'
      }
    });

    await pay.debit(b.userId, amountCents, `trade_${trade.id}_debit`);
    await pay.credit(s.userId, amountCents, `trade_${trade.id}_credit`);

    try {
      const onchain = await chain.recordTrade(trade.id, { regionId, price, qty, amountCents });
      if(onchain){
        receipts.push({ tradeId: trade.id, ...onchain });
      }
    } catch (e) {
      console.error('chain receipt failed', e);
      receipts.push({ tradeId: trade.id, error: e?.message || String(e) });
    }

    const bNewFilled = Number(b.filledKwh) + qty;
    const sNewFilled = Number(s.filledKwh) + qty;

    await prisma.request.update({
      where: { id: b.id },
      data: {
        filledKwh: bNewFilled,
        status: bNewFilled >= Number(b.quantityKwh) ? 'FILLED' : 'OPEN',
        reservedCents: 0
      }
    });
    await prisma.offer.update({
      where: { id: s.id },
      data: {
        filledKwh: sNewFilled,
        status: sNewFilled >= Number(s.quantityKwh) ? 'FILLED' : 'OPEN'
      }
    });

    executed++;
    if(bNewFilled >= Number(b.quantityKwh)) i++;
    if(sNewFilled >= Number(s.quantityKwh)) j++;
  }

  return { executedTrades: executed, regionId, receipts };
}

async function getCurrentPriceCentsForUser(userId){
  const event = await prisma.eventLog.findFirst({
    where: { type: 'PRICE_UPDATE', refId: userId },
    orderBy: [{ createdAt: 'desc' }]
  });
  if(event){
    const payload = safeJson(event.payload);
    const price = payload?.priceCents ?? payload?.price_cents ?? null;
    if(price !== null && price !== undefined) return Number(price);
  }
  const latestOffer = await prisma.offer.findFirst({
    where: { userId, status: 'OPEN' },
    orderBy: [{ createdAt: 'desc' }]
  });
  if(latestOffer) return Number(latestOffer.priceCentsPerKwh);
  const latestTrade = await prisma.trade.findFirst({
    where: { sellerId: userId },
    orderBy: [{ createdAt: 'desc' }]
  });
  if(latestTrade) return Number(latestTrade.priceCentsPerKwh);
  return null;
}

function getDisplayName(user){
  return user?.name || user?.organization || user?.email || '—';
}

async function resolveAuthUser(req){
  const authHeader = req.header('authorization');
  if(authHeader?.startsWith('Bearer ')){
    const token = authHeader.slice(7);
    try{
      const payload = verifyToken(token);
      if(!payload) throw new Error('token invalid');
      const user = await prisma.user.findUnique({ where: { id: payload.sub } });
      if(user) return user;
    }catch(_err){
      // fall back to legacy header
    }
  }

  const legacyUserId = req.header('x-user-id');
  if(legacyUserId){
    console.warn('[Auth] Using legacy x-user-id header; migrate to Bearer token auth.');
    const user = await prisma.user.findUnique({ where: { id: legacyUserId } });
    if(user) return user;
  }
  return null;
}

async function requireUser(req, res, next){
  const user = await resolveAuthUser(req);
  if(!user) return res.status(401).json({ error: 'Unauthorized' });
  req.user = user;
  next();
}

app.post('/auth/dev-login', async (req, res) => {
  const body = z.object({ email: z.string().email(), name: z.string().optional(), regionId: z.string().optional() }).parse(req.body || {});
  let user = await prisma.user.findUnique({ where: { email: body.email } });
  if(!user){
    user = await prisma.user.create({ data: { email: body.email, name: body.name || body.email.split('@')[0], regionId: body.regionId || 'region-1' } });
    await prisma.wallet.create({ data: { userId: user.id, balanceCents: 10000 } });
  } else if(body.regionId && user.regionId !== body.regionId){
    user = await prisma.user.update({ where: { id: user.id }, data: { regionId: body.regionId } });
  }
  const token = signToken(user);
  res.json({ user: sanitizeUser(user), token, mode: 'dev' });
});

app.post('/auth/register', async (req, res) => {
  const body = z.object({
    email: z.string().email(),
    password: z.string().min(6),
    name: z.string().optional(),
    regionId: z.string().optional()
  }).parse(req.body || {});

  const existing = await prisma.user.findUnique({ where: { email: body.email } });
  if(existing?.passwordHash){
    return res.status(409).json({ error: 'User already exists.' });
  }

  const passwordHash = hashPassword(body.password);
  const user = existing
    ? await prisma.user.update({
        where: { id: existing.id },
        data: {
          passwordHash,
          name: body.name || existing.name,
          regionId: body.regionId || existing.regionId || 'region-1'
        }
      })
    : await prisma.user.create({
        data: {
          email: body.email,
          name: body.name || body.email.split('@')[0],
          regionId: body.regionId || 'region-1',
          passwordHash
        }
      });

  if(!existing){
    await prisma.wallet.create({ data: { userId: user.id, balanceCents: 0 } });
  }

  const token = signToken(user);
  res.json({ user: sanitizeUser(user), token });
});

app.post('/auth/login', async (req, res) => {
  const body = z.object({
    email: z.string().email(),
    password: z.string().min(1)
  }).parse(req.body || {});

  const user = await prisma.user.findUnique({ where: { email: body.email } });
  if(!user || !verifyPassword(body.password, user.passwordHash)){
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  const token = signToken(user);
  res.json({ user: sanitizeUser(user), token });
});

app.post('/auth/pilot-login', async (req, res) => {
  const body = z.object({
    role: z.enum(['operator', 'anchor']),
    password: z.string().min(1)
  }).parse(req.body || {});

  const config = PILOT_USERS[body.role];
  if(!config) return res.status(400).json({ error: 'unsupported role' });
  if(body.password !== config.password){
    return res.status(401).json({ error: 'Invalid password' });
  }

  let user = await ensurePilotUser(body.role);
  if(user.organization !== config.organization || user.regionId !== config.regionId){
    user = await prisma.user.update({
      where: { id: user.id },
      data: {
        organization: config.organization,
        regionId: config.regionId
      }
    });
  }

  res.json({
    user: sanitizeUser(user),
    role: body.role,
    token: signToken(user)
  });
});

app.get('/analytics/overview', async (_req, res) => {
  const [
    users,
    trades,
    tradeAgg,
    openOffers,
    openRequests,
    tradeRegions,
    offerRegions,
    requestRegions,
    sellerAgg,
    buyerAgg,
    recentTradesRaw
  ] = await Promise.all([
    prisma.user.count(),
    prisma.trade.count(),
    prisma.trade.aggregate({
      _sum: { quantityKwh: true, amountCents: true },
      _avg: { priceCentsPerKwh: true }
    }),
    prisma.offer.count({ where: { status: 'OPEN' } }),
    prisma.request.count({ where: { status: 'OPEN' } }),
    prisma.trade.groupBy({
      by: ['regionId'],
      _sum: { amountCents: true, quantityKwh: true },
      _count: { _all: true }
    }),
    prisma.offer.groupBy({
      by: ['regionId'],
      where: { status: 'OPEN' },
      _count: { _all: true },
      _sum: { quantityKwh: true }
    }),
    prisma.request.groupBy({
      by: ['regionId'],
      where: { status: 'OPEN' },
      _count: { _all: true },
      _sum: { quantityKwh: true }
    }),
    prisma.trade.groupBy({
      by: ['sellerId'],
      _sum: { amountCents: true, quantityKwh: true },
      _count: { _all: true },
      orderBy: [{ _sum: { amountCents: 'desc' } }],
      take: 5
    }),
    prisma.trade.groupBy({
      by: ['buyerId'],
      _sum: { amountCents: true, quantityKwh: true },
      _count: { _all: true },
      orderBy: [{ _sum: { amountCents: 'desc' } }],
      take: 5
    }),
    prisma.trade.findMany({
      take: 10,
      orderBy: [{ createdAt: 'desc' }],
      include: {
        buyer: true,
        seller: true
      }
    })
  ]);

  const kwh = Number(tradeAgg._sum.quantityKwh || 0);
  const amountCents = Number(tradeAgg._sum.amountCents || 0);
  const usd = amountCents / 100;
  const avgPriceCents = Number(tradeAgg._avg.priceCentsPerKwh || 0);
  const avgPrice = avgPriceCents / 100;
  const CO2_PER_KWH_TONS = 0.0007; // Rough conversion (tons of CO₂ offset per kWh of clean energy)
  const co2Tons = kwh * CO2_PER_KWH_TONS;

  const participantIds = new Set();
  sellerAgg.forEach(s => s.sellerId && participantIds.add(s.sellerId));
  buyerAgg.forEach(b => b.buyerId && participantIds.add(b.buyerId));
  const participantProfiles = participantIds.size > 0
    ? await prisma.user.findMany({
        where: { id: { in: Array.from(participantIds) } },
        select: { id: true, name: true, email: true, regionId: true }
      })
    : [];
  const participantMap = new Map(participantProfiles.map(p => [p.id, p]));

  const formatParticipant = (id) => {
    if(!id) return { name: '—', regionId: null };
    const entry = participantMap.get(id);
    if(!entry) return { name: '—', regionId: null };
    return { name: entry.name || entry.email || '—', regionId: entry.regionId };
  };

  const topSellers = sellerAgg.map(s => {
    const info = formatParticipant(s.sellerId);
    return {
      userId: s.sellerId,
      name: info.name,
      regionId: info.regionId,
      trades: s._count._all,
      kwh: Number(s._sum.quantityKwh || 0),
      usd: Number(s._sum.amountCents || 0) / 100
    };
  });
  const topBuyers = buyerAgg.map(b => {
    const info = formatParticipant(b.buyerId);
    return {
      userId: b.buyerId,
      name: info.name,
      regionId: info.regionId,
      trades: b._count._all,
      kwh: Number(b._sum.quantityKwh || 0),
      usd: Number(b._sum.amountCents || 0) / 100
    };
  });

  const regionStatsMap = new Map();
  const ensureRegion = (regionId) => {
    const key = regionId || 'unassigned';
    if(!regionStatsMap.has(key)){
      regionStatsMap.set(key, {
        regionId: key,
        trades: 0,
        tradedKwh: 0,
        tradedUsd: 0,
        openOffers: 0,
        openRequests: 0,
        offerKwh: 0,
        requestKwh: 0
      });
    }
    return regionStatsMap.get(key);
  };

  tradeRegions.forEach(r => {
    const stat = ensureRegion(r.regionId);
    stat.trades = r._count._all;
    stat.tradedKwh = Number(r._sum.quantityKwh || 0);
    stat.tradedUsd = Number(r._sum.amountCents || 0) / 100;
  });
  offerRegions.forEach(r => {
    const stat = ensureRegion(r.regionId);
    stat.openOffers = r._count._all;
    stat.offerKwh = Number(r._sum.quantityKwh || 0);
  });
  requestRegions.forEach(r => {
    const stat = ensureRegion(r.regionId);
    stat.openRequests = r._count._all;
    stat.requestKwh = Number(r._sum.quantityKwh || 0);
  });

  const regions = Array.from(regionStatsMap.values()).sort((a, b) => b.tradedUsd - a.tradedUsd);

  const recentTrades = recentTradesRaw.map(t => ({
    id: t.id,
    regionId: t.regionId,
    quantityKwh: Number(t.quantityKwh),
    priceCentsPerKwh: t.priceCentsPerKwh,
    amountUsd: t.amountCents / 100,
    createdAt: t.createdAt,
    buyerName: t.buyer?.name || t.buyer?.email || '—',
    sellerName: t.seller?.name || t.seller?.email || '—'
  }));

  res.json({
    users,
    trades,
    kwh,
    usd,
    avgPrice,
    co2Tons,
    openOffers,
    openRequests,
    regions,
    topSellers,
    topBuyers,
    recentTrades,
    updatedAt: new Date().toISOString()
  });
});
app.get('/me', requireUser, async (req, res) => {
  const wallet = await prisma.wallet.findUnique({ where: { userId: req.user.id } });
  res.json({ user: sanitizeUser(req.user), wallet });
});

app.put('/profile', requireUser, async (req, res) => {
  const body = z.object({
    name: z.string().min(1).optional(),
    regionId: z.string().min(1).optional(),
    phone: z.string().optional(),
    organization: z.string().optional(),
    address: z.string().optional(),
    timezone: z.string().optional(),
    paymentMethod: z.string().optional(),
    payoutDetails: z.string().optional()
  }).parse(req.body || {});

  const { paymentMethod, payoutDetails, ...userFields } = body;
  const userData = Object.fromEntries(Object.entries(userFields).filter(([, value]) => value !== undefined));
  const walletData = Object.fromEntries(
    Object.entries({ paymentMethod, payoutDetails }).filter(([, value]) => value !== undefined)
  );

  const updates = [];
  if(Object.keys(userData).length > 0){
    updates.push(prisma.user.update({ where: { id: req.user.id }, data: userData }));
  } else {
    updates.push(prisma.user.findUnique({ where: { id: req.user.id } }));
  }

  if(Object.keys(walletData).length > 0){
    updates.push(prisma.wallet.upsert({
      where: { userId: req.user.id },
      create: { userId: req.user.id, ...walletData },
      update: walletData
    }));
  } else {
    updates.push(prisma.wallet.findUnique({ where: { userId: req.user.id } }));
  }

  const [user, wallet] = await prisma.$transaction(updates);
  res.json({ user: sanitizeUser(user), wallet });
});

app.get('/assets', requireUser, async (req, res) => {
  const list = await prisma.asset.findMany({ where: { ownerId: req.user.id } , include: { meter: true } });
  res.json(list);
});
app.post('/assets', requireUser, async (req, res) => {
  const body = z.object({ label: z.string().min(1), capacityKw: z.number().optional() }).parse(req.body || {});
  const asset = await prisma.asset.create({ data: { ownerId: req.user.id, label: body.label, regionId: req.user.regionId || 'region-1', capacityKw: body.capacityKw || 1.0 } });
  await prisma.meter.create({ data: { assetId: asset.id, whTotal: 0 } });
  res.json(asset);
});

app.get('/offers', async (req, res) => {
  const regionId = req.query.regionId || undefined;
  const status = (req.query.status || 'OPEN');
  const where = { status, ...(regionId ? { regionId } : {}) };
  const list = await prisma.offer.findMany({ where, orderBy: [{ priceCentsPerKwh: 'asc' }, { createdAt: 'asc' }] });
  res.json(list);
});
app.post('/offers', requireUser, async (req, res) => {
  const body = z.object({ priceCentsPerKwh: z.number().int().positive(), quantityKwh: z.number().positive() }).parse(req.body || {});
  const offer = await prisma.offer.create({ data: { userId: req.user.id, regionId: req.user.regionId || 'region-1', priceCentsPerKwh: body.priceCentsPerKwh, quantityKwh: body.quantityKwh } });
  res.json(offer);
});
app.post('/offers/:id/cancel', requireUser, async (req, res) => {
  const offer = await prisma.offer.findUnique({ where: { id: req.params.id } });
  if(!offer) return res.status(404).json({ error: 'not found' });
  if(offer.userId !== req.user.id) return res.status(403).json({ error: 'forbidden' });
  if(offer.status !== 'OPEN') return res.status(400).json({ error: 'cannot cancel' });
  const upd = await prisma.offer.update({ where: { id: offer.id }, data: { status: 'CANCELLED' } });
  res.json(upd);
});

app.get('/requests', async (req, res) => {
  const regionId = req.query.regionId || undefined;
  const status = (req.query.status || 'OPEN');
  const where = { status, ...(regionId ? { regionId } : {}) };
  const list = await prisma.request.findMany({ where, orderBy: [{ maxPriceCentsPerKwh: 'desc' }, { createdAt: 'asc' }] });
  res.json(list);
});
app.post('/requests', requireUser, async (req, res) => {
  const body = z.object({
    maxPriceCentsPerKwh: z.number().int().positive(),
    quantityKwh: z.number().positive()
  }).parse(req.body || {});

  const reqOrder = await prisma.request.create({
    data: {
      userId: req.user.id,
      regionId: req.user.regionId || 'region-1',
      maxPriceCentsPerKwh: body.maxPriceCentsPerKwh,
      quantityKwh: body.quantityKwh,
      reservedCents: 0
    }
  });
  res.json(reqOrder);
});
app.post('/requests/:id/cancel', requireUser, async (req, res) => {
  const r = await prisma.request.findUnique({ where: { id: req.params.id } });
  if(!r) return res.status(404).json({ error: 'not found' });
  if(r.userId !== req.user.id) return res.status(403).json({ error: 'forbidden' });
  if(r.status !== 'OPEN') return res.status(400).json({ error: 'cannot cancel' });
  const upd = await prisma.request.update({
    where: { id: r.id },
    data: { status: 'CANCELLED', reservedCents: 0 }
  });
  res.json(upd);
});

app.get('/trades', requireUser, async (req, res) => {
  const mine = req.query.mine === 'true';
  let where = {};
  if(mine){
    where = { OR: [{ buyerId: req.user.id }, { sellerId: req.user.id }] };
  }
  const list = await prisma.trade.findMany({ where, orderBy: [{ createdAt: 'desc' }] });
  res.json(list);
});

app.get('/pilot/operator', requireUser, async (req, res) => {
  const regionId = req.user.regionId || 'region-1';
  const todayStart = startOfToday();
  const weekStart = startOfWeek();

  const [anchorUser, priceCents, surplusTodayEntries, surplusHistory, weeklyTrades] = await Promise.all([
    ensurePilotUser('anchor'),
    getCurrentPriceCentsForUser(req.user.id),
    prisma.eventLog.findMany({
      where: {
        type: 'SURPLUS_ENTRY',
        refId: req.user.id,
        createdAt: { gte: todayStart }
      }
    }),
    prisma.eventLog.findMany({
      where: { type: 'SURPLUS_ENTRY', refId: req.user.id },
      orderBy: [{ createdAt: 'desc' }],
      take: 5
    }),
    prisma.trade.findMany({
      where: {
        sellerId: req.user.id,
        createdAt: { gte: weekStart }
      },
      orderBy: [{ createdAt: 'desc' }]
    })
  ]);

  const surplusTodayKwh = surplusTodayEntries.reduce((sum, entry) => {
    const payload = safeJson(entry.payload);
    return sum + toNumber(payload?.surplusKwh);
  }, 0);

  const energySoldWeekKwh = weeklyTrades.reduce((sum, trade) => sum + toNumber(trade.quantityKwh), 0);
  const energySoldWeekValueCents = weeklyTrades.reduce((sum, trade) => sum + Number(trade.amountCents || 0), 0);

  const todaysSales = weeklyTrades.reduce(
    (acc, trade) => {
      if(new Date(trade.createdAt) >= todayStart){
        acc.kwh += toNumber(trade.quantityKwh);
        acc.amountCents += Number(trade.amountCents || 0);
      }
      return acc;
    },
    { kwh: 0, amountCents: 0 }
  );

  const recentSurplus = surplusHistory.map(entry => {
    const payload = safeJson(entry.payload);
    return {
      id: entry.id,
      generatedKwh: toNumber(payload?.generatedKwh),
      localLoadKwh: toNumber(payload?.localLoadKwh),
      surplusKwh: toNumber(payload?.surplusKwh),
      recordedAt: entry.createdAt
    };
  });

  res.json({
    regionId,
    microgridName: req.user.organization || `${regionId} Microgrid`,
    currentPriceCents: priceCents,
    currentPriceUsd: priceCents !== null ? priceCents / 100 : null,
    surplusTodayKwh,
    energySoldWeekKwh,
    energySoldWeekValueCents,
    todaysSales,
    anchorName: getDisplayName(anchorUser),
    recentSurplus,
    generatedAt: new Date().toISOString()
  });
});

app.post('/pilot/operator/price', requireUser, async (req, res) => {
  const body = z.object({
    priceUsd: z.number().positive()
  }).parse(req.body || {});

  const priceCents = Math.round(body.priceUsd * 100);
  const event = await prisma.eventLog.create({
    data: {
      type: 'PRICE_UPDATE',
      refId: req.user.id,
      payload: JSON.stringify({
        userId: req.user.id,
        priceCents,
        priceUsd: body.priceUsd,
        recordedAt: new Date().toISOString()
      })
    }
  });

  res.json({
    priceCents,
    priceUsd: body.priceUsd,
    recordedAt: event.createdAt
  });
});

app.post('/pilot/operator/surplus', requireUser, async (req, res) => {
  const body = z.object({
    generatedKwh: z.number().nonnegative(),
    localLoadKwh: z.number().nonnegative()
  }).parse(req.body || {});

  const surplusKwhRaw = body.generatedKwh - body.localLoadKwh;
  const surplusKwh = surplusKwhRaw > 0 ? surplusKwhRaw : 0;

  const priceCents = await getCurrentPriceCentsForUser(req.user.id);
  if(priceCents === null){
    return res.status(400).json({
      error: 'Set a selling price before recording surplus.'
    });
  }

  const event = await prisma.eventLog.create({
    data: {
      type: 'SURPLUS_ENTRY',
      refId: req.user.id,
      payload: JSON.stringify({
        userId: req.user.id,
        generatedKwh: body.generatedKwh,
        localLoadKwh: body.localLoadKwh,
        surplusKwh,
        recordedAt: new Date().toISOString()
      })
    }
  });

  let offer = null;
  if(surplusKwh > 0){
    offer = await prisma.offer.create({
      data: {
        userId: req.user.id,
        regionId: req.user.regionId || 'region-1',
        priceCentsPerKwh: priceCents,
        quantityKwh: surplusKwh
      }
    });
  }

  const matchSummary = await runRegionMatch(req.user.regionId || 'region-1');

  const todaysSales = await prisma.trade.aggregate({
    _sum: {
      quantityKwh: true,
      amountCents: true
    },
    where: {
      sellerId: req.user.id,
      createdAt: { gte: startOfToday() }
    }
  });

  res.json({
    surplusKwh,
    priceCents,
    eventId: event.id,
    offerId: offer?.id || null,
    matchSummary,
    todaysSales: {
      kwh: toNumber(todaysSales._sum?.quantityKwh),
      amountCents: Number(todaysSales._sum?.amountCents || 0)
    }
  });
});

app.get('/pilot/anchor', requireUser, async (req, res) => {
  const regionId = req.user.regionId || 'region-1';
  const todayStart = startOfToday();
  const weekStart = startOfWeek();

  const [wallet, weeklyTrades, meterHistory, operatorUser] = await Promise.all([
    prisma.wallet.findUnique({ where: { userId: req.user.id } }),
    prisma.trade.findMany({
      where: {
        buyerId: req.user.id,
        createdAt: { gte: weekStart }
      },
      orderBy: [{ createdAt: 'desc' }]
    }),
    prisma.eventLog.findMany({
      where: { type: 'METER_READING', refId: req.user.id },
      orderBy: [{ createdAt: 'desc' }],
      take: 5
    }),
    ensurePilotUser('operator')
  ]);

  const currentBuyPriceCents = await getCurrentPriceCentsForUser(operatorUser.id);

  const energyPurchasedToday = weeklyTrades.reduce(
    (acc, trade) => {
      if(new Date(trade.createdAt) >= todayStart){
        acc.kwh += toNumber(trade.quantityKwh);
        acc.amountCents += Number(trade.amountCents || 0);
      }
      return acc;
    },
    { kwh: 0, amountCents: 0 }
  );

  const weeklySpendCents = weeklyTrades.reduce((sum, trade) => sum + Number(trade.amountCents || 0), 0);
  const weeklyKwh = weeklyTrades.reduce((sum, trade) => sum + toNumber(trade.quantityKwh), 0);

  const walletBalanceCents = wallet ? toNumber(wallet.balanceCents) : 0;
  const balanceOwedCents = walletBalanceCents < 0 ? Math.abs(walletBalanceCents) : 0;

  const recentMeterReadings = meterHistory.map(entry => {
    const payload = safeJson(entry.payload);
    return {
      id: entry.id,
      readingKwh: toNumber(payload?.readingKwh),
      notedAt: entry.createdAt
    };
  });

  res.json({
    regionId,
    buyerName: getDisplayName(req.user),
    currentBuyPriceCents,
    currentBuyPriceUsd: currentBuyPriceCents !== null ? currentBuyPriceCents / 100 : null,
    energyPurchasedToday,
    weeklySpendCents,
    weeklyKwh,
    walletBalanceCents,
    balanceOwedCents,
    recentMeterReadings,
    generatedAt: new Date().toISOString()
  });
});

app.post('/pilot/anchor/meter-reading', requireUser, async (req, res) => {
  const body = z.object({
    readingKwh: z.number().nonnegative(),
    notes: z.string().optional()
  }).parse(req.body || {});

  const operatorUser = await ensurePilotUser('operator');
  const currentPriceCents = await getCurrentPriceCentsForUser(operatorUser.id);

  const todayStart = startOfToday();
  const todaysPurchases = await prisma.trade.aggregate({
    _sum: {
      quantityKwh: true
    },
    where: {
      buyerId: req.user.id,
      createdAt: { gte: todayStart }
    }
  });

  const alreadyPurchasedToday = toNumber(todaysPurchases._sum?.quantityKwh);
  const neededKwhRaw = body.readingKwh - alreadyPurchasedToday;
  const neededKwh = neededKwhRaw > 0 ? neededKwhRaw : 0;

  const event = await prisma.eventLog.create({
    data: {
      type: 'METER_READING',
      refId: req.user.id,
      payload: JSON.stringify({
        userId: req.user.id,
        readingKwh: body.readingKwh,
        notes: body.notes || null,
        recordedAt: new Date().toISOString()
      })
    }
  });

  let request = null;
  if(neededKwh > 0 && currentPriceCents !== null){
    request = await prisma.request.create({
      data: {
        userId: req.user.id,
        regionId: req.user.regionId || 'region-1',
        maxPriceCentsPerKwh: currentPriceCents,
        quantityKwh: neededKwh,
        reservedCents: 0
      }
    });
  }

  const matchSummary = await runRegionMatch(req.user.regionId || 'region-1');

  res.json({
    eventId: event.id,
    requestedKwh: neededKwh,
    requestId: request?.id || null,
    currentPriceCents,
    matchSummary
  });
});

app.get('/pilot/anchor/weekly-balance', requireUser, async (req, res) => {
  const weekStart = startOfWeek();

  const [wallet, purchases, paymentEvents] = await Promise.all([
    prisma.wallet.findUnique({ where: { userId: req.user.id } }),
    prisma.trade.aggregate({
      _sum: { quantityKwh: true, amountCents: true },
      where: {
        buyerId: req.user.id,
        createdAt: { gte: weekStart }
      }
    }),
    prisma.eventLog.findMany({
      where: {
        type: 'PAYMENT_CREDIT',
        refId: req.user.id,
        createdAt: { gte: weekStart }
      }
    })
  ]);

  const walletBalanceCents = wallet ? toNumber(wallet.balanceCents) : 0;
  const purchasesAmountCents = Number(purchases._sum?.amountCents || 0);
  const purchasesKwh = toNumber(purchases._sum?.quantityKwh);

  const paymentsAmountCents = paymentEvents.reduce((sum, entry) => {
    const payload = safeJson(entry.payload);
    return sum + Number(payload?.amountCents || 0);
  }, 0);

  const netDueCents = purchasesAmountCents - paymentsAmountCents - Math.min(walletBalanceCents, 0);
  const balanceOwedCents = walletBalanceCents < 0 ? Math.abs(walletBalanceCents) : 0;

  res.json({
    weekStart: weekStart.toISOString(),
    purchases: {
      kwh: purchasesKwh,
      amountCents: purchasesAmountCents
    },
    payments: {
      amountCents: paymentsAmountCents,
      count: paymentEvents.length
    },
    walletBalanceCents,
    balanceOwedCents,
    remainingDueCents: Math.max(0, netDueCents),
    generatedAt: new Date().toISOString()
  });
});

app.get('/pilot/matching', requireUser, async (req, res) => {
  const regionId = req.user.regionId || 'region-1';

  const [offers, requests] = await Promise.all([
    prisma.offer.findMany({
      where: { status: 'OPEN', regionId },
      orderBy: [{ priceCentsPerKwh: 'asc' }, { createdAt: 'asc' }],
      take: 25
    }),
    prisma.request.findMany({
      where: { status: 'OPEN', regionId },
      orderBy: [{ maxPriceCentsPerKwh: 'desc' }, { createdAt: 'asc' }],
      take: 25
    })
  ]);

  const offerTotals = offers.reduce(
    (acc, offer) => {
      acc.count += 1;
      acc.quantityKwh += toNumber(offer.quantityKwh) - toNumber(offer.filledKwh);
      acc.minPrice = acc.minPrice === null ? offer.priceCentsPerKwh : Math.min(acc.minPrice, offer.priceCentsPerKwh);
      return acc;
    },
    { count: 0, quantityKwh: 0, minPrice: null }
  );

  const requestTotals = requests.reduce(
    (acc, request) => {
      acc.count += 1;
      acc.quantityKwh += toNumber(request.quantityKwh) - toNumber(request.filledKwh);
      acc.maxPrice = acc.maxPrice === null ? request.maxPriceCentsPerKwh : Math.max(acc.maxPrice, request.maxPriceCentsPerKwh);
      return acc;
    },
    { count: 0, quantityKwh: 0, maxPrice: null }
  );

  res.json({
    regionId,
    offers: offers.map((offer) => ({
      id: offer.id,
      userId: offer.userId,
      quantityKwh: toNumber(offer.quantityKwh),
      filledKwh: toNumber(offer.filledKwh),
      priceCentsPerKwh: offer.priceCentsPerKwh,
      createdAt: offer.createdAt
    })),
    requests: requests.map((request) => ({
      id: request.id,
      userId: request.userId,
      quantityKwh: toNumber(request.quantityKwh),
      filledKwh: toNumber(request.filledKwh),
      maxPriceCentsPerKwh: request.maxPriceCentsPerKwh,
      createdAt: request.createdAt
    })),
    stats: {
      offerCount: offerTotals.count,
      availableKwh: offerTotals.quantityKwh,
      lowestAskCentsPerKwh: offerTotals.minPrice,
      requestCount: requestTotals.count,
      requestedKwh: requestTotals.quantityKwh,
      highestBidCentsPerKwh: requestTotals.maxPrice
    },
    generatedAt: new Date().toISOString()
  });
});

app.get('/pilot/settlement', requireUser, async (req, res) => {
  const regionId = req.user.regionId || 'region-1';
  const limit = Math.max(1, Math.min(50, Number(req.query.limit) || 20));

  const trades = await prisma.trade.findMany({
    where: { regionId },
    orderBy: [{ createdAt: 'desc' }],
    take: limit,
    include: {
      buyer: { select: { id: true, name: true, email: true } },
      seller: { select: { id: true, name: true, email: true } }
    }
  });

  const tradeIds = trades.map((trade) => trade.id);
  const receiptEvents = tradeIds.length > 0
    ? await prisma.eventLog.findMany({
        where: {
          refId: { in: tradeIds },
          type: { in: ['CHAIN_RECEIPT', 'CHAIN_RECEIPT_MOCK', 'CHAIN_ERROR'] }
        },
        orderBy: [{ createdAt: 'desc' }]
      })
    : [];

  const receiptMap = new Map();
  receiptEvents.forEach((event) => {
    if(!receiptMap.has(event.refId)){
      const parsed = safeJson(event.payload);
      const payload = parsed?.payload || parsed || null;
      receiptMap.set(event.refId, {
        type: event.type,
        txHash: payload?.txHash || null,
        blockNumber: payload?.blockNumber || null,
        chainId: payload?.chainId || null,
        error: payload?.error || parsed?.error || null,
        createdAt: event.createdAt
      });
    }
  });

  const formatted = trades.map((trade) => ({
    id: trade.id,
    buyerName: trade.buyer?.name || trade.buyer?.email || '—',
    sellerName: trade.seller?.name || trade.seller?.email || '—',
    quantityKwh: toNumber(trade.quantityKwh),
    priceCentsPerKwh: trade.priceCentsPerKwh,
    amountCents: trade.amountCents,
    status: trade.status,
    createdAt: trade.createdAt,
    receipt: receiptMap.get(trade.id) || null
  }));

  res.json({
    regionId,
    trades: formatted,
    generatedAt: new Date().toISOString()
  });
});

app.get('/pilot/ledger', requireUser, async (req, res) => {
  const limit = Math.max(10, Math.min(200, Number(req.query.limit) || 100));
  const period = typeof req.query.period === 'string' ? req.query.period : 'all';
  const relevantTypes = [
    'PAYMENT_DEBIT',
    'PAYMENT_CREDIT',
    'CHAIN_RECEIPT',
    'CHAIN_RECEIPT_MOCK',
    'CHAIN_ERROR',
    'SURPLUS_ENTRY',
    'METER_READING',
    'PRICE_UPDATE'
  ];

  const now = new Date();
  const thisWeekStart = startOfWeek(now);
  let createdAtFilter;
  if(period === 'current'){
    createdAtFilter = { gte: thisWeekStart };
  } else if(period === 'previous'){
    const prevStart = new Date(thisWeekStart);
    prevStart.setDate(prevStart.getDate() - 7);
    createdAtFilter = { gte: prevStart, lt: thisWeekStart };
  }

  const entries = await prisma.eventLog.findMany({
    where: {
      type: { in: relevantTypes },
      ...(createdAtFilter ? { createdAt: createdAtFilter } : {})
    },
    orderBy: [{ createdAt: 'desc' }],
    take: limit
  });

  const operatorUser = await ensurePilotUser('operator');
  const anchorUser = await ensurePilotUser('anchor');

  const userIds = Array.from(new Set(entries.map((entry) => {
    const payload = safeJson(entry.payload);
    if(payload?.userId) return payload.userId;
    if(payload?.payload?.userId) return payload.payload.userId;
    if(entry.refId && entry.type.startsWith('PAYMENT')) return entry.refId;
    return null;
  }).filter(Boolean)));

  const users = userIds.length > 0
    ? await prisma.user.findMany({
        where: { id: { in: userIds } },
        select: { id: true, name: true, email: true, organization: true }
      })
    : [];
  const userMap = new Map(users.map((u) => [u.id, u]));
  userMap.set(operatorUser.id, operatorUser);
  userMap.set(anchorUser.id, anchorUser);

  const formatted = entries.map((entry) => {
    const parsed = safeJson(entry.payload);
    const payload = parsed?.payload || parsed || {};
    const metadata = {
      txHash: parsed?.txHash || payload?.txHash || null,
      blockNumber: parsed?.blockNumber || payload?.blockNumber || null,
      chainId: parsed?.chainId || payload?.chainId || null,
      status: parsed?.status ?? payload?.status ?? null,
      error: parsed?.error || payload?.error || null
    };
    const userId = parsed?.userId || payload?.userId || entry.refId || null;
    const userInfo = userId ? userMap.get(userId) : null;
    const role = userId === operatorUser.id
      ? 'Operator'
      : userId === anchorUser.id
        ? 'Anchor'
        : 'System';

    let kwh = null;
    let priceCents = null;
    let valueCents = null;
    let status = 'Recorded';
    let reference = entry.refId || null;

    if(entry.type === 'CHAIN_RECEIPT' || entry.type === 'CHAIN_RECEIPT_MOCK' || entry.type === 'CHAIN_ERROR'){
      const qty = toNumber(payload.qty ?? payload.quantityKwh ?? (payload.quantityWh ? payload.quantityWh / 1000 : null));
      const price = Number(payload.price ?? payload.priceCentsPerKwh ?? null);
      const amount = Number(payload.amountCents ?? (qty !== null && price !== null ? Math.round(qty * price) : null));
      if(qty !== null) kwh = qty;
      if(price !== null && !Number.isNaN(price)) priceCents = price;
      if(amount !== null && !Number.isNaN(amount)) valueCents = amount;
      status = metadata.error ? 'Error' : (entry.type === 'CHAIN_RECEIPT_MOCK' ? 'Mock receipt' : 'Settled');
      reference = payload.tradeId || entry.refId;
    } else if(entry.type === 'PAYMENT_DEBIT' || entry.type === 'PAYMENT_CREDIT'){
      const amount = Number(payload.amountCents || 0);
      valueCents = amount;
      status = entry.type === 'PAYMENT_DEBIT' ? 'Debit' : 'Credit';
      reference = payload.reference || entry.refId;
    } else if(entry.type === 'SURPLUS_ENTRY'){
      const surplus = toNumber(payload.surplusKwh);
      if(Number.isFinite(surplus)) kwh = surplus;
      status = 'Surplus logged';
    } else if(entry.type === 'METER_READING'){
      const reading = toNumber(payload.readingKwh);
      if(Number.isFinite(reading)) kwh = reading;
      status = 'Meter reading';
    } else if(entry.type === 'PRICE_UPDATE'){
      const price = Number(payload.priceCents || 0);
      if(Number.isFinite(price)) priceCents = price;
      status = 'Price update';
    }

    return {
      id: entry.id,
      type: entry.type,
      refId: reference,
      role,
      kwh,
      priceCents,
      valueCents,
      status,
      txHash: metadata.txHash,
      metadata,
      payload,
      user: userInfo ? {
        id: userInfo.id,
        name: getDisplayName(userInfo),
        email: userInfo.email || null,
        organization: userInfo.organization || null
      } : null,
      createdAt: entry.createdAt
    };
  });

  res.json({
    entries: formatted,
    generatedAt: new Date().toISOString()
  });
});

app.post('/match/run', requireUser, async (req, res) => {
  const regionId = req.user.regionId || 'region-1';
  const summary = await runRegionMatch(regionId);
  res.json(summary);
});

app.get('/wallet', requireUser, async (req, res) => {
  const w = await prisma.wallet.findUnique({ where: { userId: req.user.id } });
  res.json(w);
});
app.post('/wallet/topup', requireUser, async (req, res) => {
  const body = z.object({ amountCents: z.number().int().positive() }).parse(req.body || {});
  await pay.credit(req.user.id, body.amountCents, `topup_${Date.now()}`);
  const w = await prisma.wallet.findUnique({ where: { userId: req.user.id } });
  res.json(w);
});

async function seed(){
  const count = await prisma.user.count();
  if(count > 0) return;
  const u1 = await prisma.user.create({ data: { email: 'demo@gridless.local', name: 'Demo', regionId: 'region-1' } });
  await prisma.wallet.create({ data: { userId: u1.id, balanceCents: 10000 } });
  const u2 = await prisma.user.create({ data: { email: 'east@gridless.local', name: 'East', regionId: 'region-2' } });
  await prisma.wallet.create({ data: { userId: u2.id, balanceCents: 8000 } });
  const a1 = await prisma.asset.create({ data: { ownerId: u1.id, label: 'Clinic Roof', regionId: 'region-1', capacityKw: 3 } });
  await prisma.meter.create({ data: { assetId: a1.id, whTotal: 0 } });
  await prisma.offer.create({ data: { userId: u1.id, regionId: 'region-1', priceCentsPerKwh: 18, quantityKwh: 3 } });
  await prisma.request.create({ data: { userId: u1.id, regionId: 'region-1', maxPriceCentsPerKwh: 25, quantityKwh: 2, reservedCents: 50 } });
  await ensurePilotUser('operator');
  await ensurePilotUser('anchor');
}
seed().catch(e=>console.error('seed error', e));

// Simple root route so visiting the base URL shows something
app.get('/', (req, res) => {
  res.send('Kora API is running ✅');
});

// Health check for UCSD / uptime checks
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'kora-api',
    version: '0.1.0',
  });
});

const PORT = process.env.PORT || 4000;

app.listen(PORT, () => {
  console.log(`Kora API listening on port ${PORT}`);
});
