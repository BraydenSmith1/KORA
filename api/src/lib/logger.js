import winston from 'winston';

/**
 * KORA Logger
 *
 * Structured logging with support for:
 * - Console output (development)
 * - JSON format (production)
 * - Axiom integration (when AXIOM_TOKEN is set)
 *
 * Log levels: error, warn, info, http, debug
 */

const { combine, timestamp, printf, colorize, json, errors } = winston.format;

// Environment config
const LOG_LEVEL = process.env.LOG_LEVEL || (process.env.NODE_ENV === 'production' ? 'info' : 'debug');
const AXIOM_TOKEN = process.env.AXIOM_TOKEN;
const AXIOM_DATASET = process.env.AXIOM_DATASET || 'kora-logs';
const NODE_ENV = process.env.NODE_ENV || 'development';

// Custom format for console (development)
const consoleFormat = printf(({ level, message, timestamp, ...meta }) => {
  const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
  return `${timestamp} [${level}] ${message}${metaStr}`;
});

// Create transports array
const transports = [];

// Console transport (always enabled in development, minimal in production)
if (NODE_ENV !== 'production') {
  transports.push(
    new winston.transports.Console({
      format: combine(
        colorize(),
        timestamp({ format: 'HH:mm:ss' }),
        consoleFormat
      ),
    })
  );
} else {
  // JSON format for production console
  transports.push(
    new winston.transports.Console({
      format: combine(
        timestamp(),
        json()
      ),
    })
  );
}

// Axiom transport (production with token)
// Uses dynamic import since @axiomhq/winston may not be installed
if (AXIOM_TOKEN) {
  import('@axiomhq/winston')
    .then(({ WinstonTransport: AxiomTransport }) => {
      logger.add(
        new AxiomTransport({
          dataset: AXIOM_DATASET,
          token: AXIOM_TOKEN,
          orgId: process.env.AXIOM_ORG_ID,
        })
      );
      console.log(`[Logger] Axiom transport enabled for dataset: ${AXIOM_DATASET}`);
    })
    .catch((err) => {
      console.warn('[Logger] Failed to initialize Axiom transport:', err.message);
    });
}

// Create the logger
const logger = winston.createLogger({
  level: LOG_LEVEL,
  format: combine(
    errors({ stack: true }),
    timestamp(),
    json()
  ),
  defaultMeta: {
    service: 'kora-api',
    environment: NODE_ENV,
  },
  transports,
});

// Add convenience methods with context
logger.withContext = (context) => {
  return {
    error: (message, meta = {}) => logger.error(message, { ...context, ...meta }),
    warn: (message, meta = {}) => logger.warn(message, { ...context, ...meta }),
    info: (message, meta = {}) => logger.info(message, { ...context, ...meta }),
    http: (message, meta = {}) => logger.http(message, { ...context, ...meta }),
    debug: (message, meta = {}) => logger.debug(message, { ...context, ...meta }),
  };
};

// Request logging middleware
logger.requestMiddleware = () => {
  return (req, res, next) => {
    const start = Date.now();
    const requestId = req.headers['x-request-id'] || `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Attach request ID for tracking
    req.requestId = requestId;
    res.setHeader('x-request-id', requestId);

    // Log on response finish
    res.on('finish', () => {
      const duration = Date.now() - start;
      const logLevel = res.statusCode >= 500 ? 'error' : res.statusCode >= 400 ? 'warn' : 'http';

      logger[logLevel]('HTTP Request', {
        requestId,
        method: req.method,
        path: req.path,
        statusCode: res.statusCode,
        duration,
        userAgent: req.headers['user-agent'],
        ip: req.ip || req.connection.remoteAddress,
        userId: req.user?.id || req.headers['x-user-id'],
      });
    });

    next();
  };
};

// Optimizer-specific logging
logger.optimizer = {
  runStarted: (runId, siteId, params) => {
    logger.info('Optimizer run started', {
      event: 'optimizer.run.started',
      runId,
      siteId,
      params,
    });
  },

  runCompleted: (runId, siteId, result) => {
    logger.info('Optimizer run completed', {
      event: 'optimizer.run.completed',
      runId,
      siteId,
      solver: result.solver,
      solveTimeSec: result.solveTimeSec,
      status: result.status,
      curtailmentRate: result.curtailmentRate,
      blackoutHours: result.blackoutHours,
    });
  },

  runFailed: (runId, siteId, error) => {
    logger.error('Optimizer run failed', {
      event: 'optimizer.run.failed',
      runId,
      siteId,
      error: error.message,
      stack: error.stack,
    });
  },
};

// Simulation-specific logging
logger.simulation = {
  started: (simId, siteId, config) => {
    logger.info('Simulation started', {
      event: 'simulation.started',
      simId,
      siteId,
      timeAcceleration: config.timeAcceleration,
      startHour: config.startHour,
    });
  },

  tick: (simId, state) => {
    logger.debug('Simulation tick', {
      event: 'simulation.tick',
      simId,
      simulatedTime: state.simulatedTime,
      socPct: state.socPct,
      priceAriary: state.priceAriary,
    });
  },

  stopped: (simId, summary) => {
    logger.info('Simulation stopped', {
      event: 'simulation.stopped',
      simId,
      totalSteps: summary.totalSteps,
      totalEnergyKwh: summary.totalEnergyKwh,
      totalRevenueAr: summary.totalRevenueAr,
    });
  },
};

// Named exports for specific loggers
export const optimizerLogger = logger.optimizer;
export const simulationLogger = logger.simulation;
export const requestMiddleware = logger.requestMiddleware;

// Default export
export default logger;
