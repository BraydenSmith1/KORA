-- CreateTable
CREATE TABLE "WeatherForecast" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "forecastTime" TIMESTAMP(3) NOT NULL,
    "targetTime" TIMESTAMP(3) NOT NULL,
    "ghi" DOUBLE PRECISION,
    "dni" DOUBLE PRECISION,
    "cloudCover" DOUBLE PRECISION NOT NULL,
    "temperature" DOUBLE PRECISION NOT NULL,
    "humidity" DOUBLE PRECISION,
    "windSpeed" DOUBLE PRECISION,
    "precipitation" DOUBLE PRECISION,
    "source" TEXT NOT NULL DEFAULT 'open-meteo',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "WeatherForecast_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PVForecast" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "forecastTime" TIMESTAMP(3) NOT NULL,
    "horizonHours" INTEGER NOT NULL DEFAULT 24,
    "pvKwArray" JSONB NOT NULL,
    "method" TEXT NOT NULL DEFAULT 'physics',
    "weatherSource" TEXT,
    "modelVersion" TEXT,
    "maeKw" DOUBLE PRECISION,
    "mapePercent" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PVForecast_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "DemandForecast" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "forecastTime" TIMESTAMP(3) NOT NULL,
    "horizonHours" INTEGER NOT NULL DEFAULT 24,
    "demandKwArray" JSONB NOT NULL,
    "method" TEXT NOT NULL DEFAULT 'pattern',
    "dayType" TEXT,
    "priceAdjusted" BOOLEAN NOT NULL DEFAULT false,
    "maeKw" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "DemandForecast_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "OutageRiskAssessment" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "assessmentTime" TIMESTAMP(3) NOT NULL,
    "overallRisk" DOUBLE PRECISION NOT NULL,
    "socRisk" DOUBLE PRECISION NOT NULL,
    "demandRisk" DOUBLE PRECISION NOT NULL,
    "weatherRisk" DOUBLE PRECISION NOT NULL,
    "peakDeficitKw" DOUBLE PRECISION,
    "lowSocHours" INTEGER NOT NULL DEFAULT 0,
    "alertLevel" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "OutageRiskAssessment_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ForecastAccuracy" (
    "id" TEXT NOT NULL,
    "siteId" TEXT NOT NULL,
    "forecastType" TEXT NOT NULL,
    "forecastId" TEXT NOT NULL,
    "targetHour" TIMESTAMP(3) NOT NULL,
    "forecastValue" DOUBLE PRECISION NOT NULL,
    "actualValue" DOUBLE PRECISION NOT NULL,
    "errorKw" DOUBLE PRECISION NOT NULL,
    "errorPercent" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ForecastAccuracy_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "WeatherForecast_siteId_targetTime_idx" ON "WeatherForecast"("siteId", "targetTime");

-- CreateIndex
CREATE INDEX "WeatherForecast_forecastTime_idx" ON "WeatherForecast"("forecastTime");

-- CreateIndex
CREATE INDEX "PVForecast_siteId_forecastTime_idx" ON "PVForecast"("siteId", "forecastTime");

-- CreateIndex
CREATE INDEX "DemandForecast_siteId_forecastTime_idx" ON "DemandForecast"("siteId", "forecastTime");

-- CreateIndex
CREATE INDEX "OutageRiskAssessment_siteId_assessmentTime_idx" ON "OutageRiskAssessment"("siteId", "assessmentTime");

-- CreateIndex
CREATE INDEX "ForecastAccuracy_siteId_forecastType_targetHour_idx" ON "ForecastAccuracy"("siteId", "forecastType", "targetHour");
