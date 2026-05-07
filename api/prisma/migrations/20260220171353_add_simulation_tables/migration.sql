-- CreateTable
CREATE TABLE "OptimizerRun" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL DEFAULT 'mahavelona',
    "runId" TEXT NOT NULL,
    "simulatedTime" TIMESTAMP(3) NOT NULL,
    "realTime" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "status" TEXT NOT NULL,
    "solver" TEXT NOT NULL,
    "solveTimeSec" DOUBLE PRECISION NOT NULL,
    "curtailmentRate" DOUBLE PRECISION,
    "totalRevenueAriary" DOUBLE PRECISION,
    "totalCurtailmentKwh" DOUBLE PRECISION,
    "totalDemandServedKwh" DOUBLE PRECISION,
    "blackoutHours" INTEGER NOT NULL DEFAULT 0,
    "priceSchedule" JSONB,
    "batterySchedule" JSONB,
    "pvForecast" JSONB,
    "demandForecast" JSONB,
    "errorMessage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "OptimizerRun_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SimulationState" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL DEFAULT 'mahavelona',
    "isRunning" BOOLEAN NOT NULL DEFAULT false,
    "isPaused" BOOLEAN NOT NULL DEFAULT false,
    "timeAcceleration" DOUBLE PRECISION NOT NULL DEFAULT 60,
    "simulatedTime" TIMESTAMP(3) NOT NULL,
    "startedAt" TIMESTAMP(3),
    "batterySocKwh" DOUBLE PRECISION NOT NULL,
    "batterySocPct" DOUBLE PRECISION NOT NULL,
    "currentPvKw" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "currentDemandKw" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "currentPriceAriary" DOUBLE PRECISION NOT NULL DEFAULT 1750,
    "currentChargeKw" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "currentCurtailKw" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "activeRunId" TEXT,
    "totalEnergyKwh" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "totalCurtailKwh" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "totalRevenueAr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SimulationState_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SimTelemetry" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL DEFAULT 'mahavelona',
    "simulatedTime" TIMESTAMP(3) NOT NULL,
    "pvKw" DOUBLE PRECISION NOT NULL,
    "demandKw" DOUBLE PRECISION NOT NULL,
    "priceAriary" DOUBLE PRECISION NOT NULL,
    "socKwh" DOUBLE PRECISION NOT NULL,
    "socPct" DOUBLE PRECISION NOT NULL,
    "chargeKw" DOUBLE PRECISION NOT NULL,
    "curtailKw" DOUBLE PRECISION NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "SimTelemetry_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "OptimizerRun_runId_key" ON "OptimizerRun"("runId");

-- CreateIndex
CREATE INDEX "OptimizerRun_siteId_simulatedTime_idx" ON "OptimizerRun"("siteId", "simulatedTime");

-- CreateIndex
CREATE UNIQUE INDEX "SimulationState_siteId_key" ON "SimulationState"("siteId");

-- CreateIndex
CREATE INDEX "SimTelemetry_siteId_simulatedTime_idx" ON "SimTelemetry"("siteId", "simulatedTime");
