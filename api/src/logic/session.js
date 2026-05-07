export function parseThresholds(raw){
  if(!raw) return {};
  if(typeof raw === 'object') return raw;
  try{
    return JSON.parse(raw) || {};
  }catch(_err){
    return {};
  }
}

export function serializeThresholds(obj){
  return obj ?? null;
}

export async function getActiveSession(prisma){
  return prisma.sessionState.findFirst({
    where: { endedAt: null },
    orderBy: [{ createdAt: 'desc' }]
  });
}

export function presentSession(session){
  if(!session) return null;
  return {
    ...session,
    thresholds: parseThresholds(session.thresholds)
  };
}
