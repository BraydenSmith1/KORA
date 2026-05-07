import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

const users = [
  { email: 'alice@example.com', name: 'Alice', regionId: 'region-1' },
  { email: 'bob@example.com', name: 'Bob', regionId: 'region-1' },
  { email: 'kofi@example.com', name: 'Kofi', regionId: 'region-2' },
];

// Mahavelona site configuration (Africa GreenTec pilot)
const sites = [
  {
    id: 'mahavelona',
    name: 'Mahavelona',
    location: 'Madagascar',
    timezone: 'Indian/Antananarivo',
    pvCapacityKwp: 118.5,
    batteryCapacityKwh: 115,
    batteryPowerKw: 54,
    socMinPct: 20,
    socMaxPct: 95,
    etaCharge: 0.94,
    etaDischarge: 0.94,
    peakDemandKw: 53,
    baseDemandKw: 8,
    customerCount: 251,
    priceMinAriary: 1000,
    priceMaxAriary: 2500,
    priceRefAriary: 1750,
    elasticity: 0.6,
    isActive: true,
  },
];

async function main() {
  // Seed sites
  for (const site of sites) {
    const existing = await prisma.site.findUnique({ where: { id: site.id } });
    if (!existing) {
      await prisma.site.create({ data: site });
      console.log(`Created site: ${site.name}`);
    } else {
      console.log(`Site already exists: ${site.name}`);
    }
  }

  // Seed users
  for (const u of users) {
    let user = await prisma.user.findUnique({ where: { email: u.email } });
    if (!user) {
      user = await prisma.user.create({ data: u });
      await prisma.wallet.create({ data: { userId: user.id, balanceCents: 12000 } });
      const asset = await prisma.asset.create({ data: { ownerId: user.id, label: `${u.name}'s Solar`, regionId: u.regionId, capacityKw: 2.5 } });
      await prisma.meter.create({ data: { assetId: asset.id, whTotal: 0 } });
      console.log(`Created user: ${u.email}`);
    }
  }

  console.log('Seed complete.');
}

main().finally(() => prisma.$disconnect());
