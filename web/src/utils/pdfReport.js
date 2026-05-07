import { jsPDF } from 'jspdf';
import 'jspdf-autotable';

/**
 * PDF Report Generator for KORA
 *
 * Generates professional PDF reports for operators showing:
 * - Summary metrics
 * - Performance comparison (KORA vs Baseline)
 * - Detailed run data table
 * - Period comparisons
 */

// KORA brand colors
const COLORS = {
  primary: [16, 185, 129], // #10b981
  dark: [15, 23, 42], // #0f172a
  text: [55, 65, 81], // #374151
  muted: [107, 114, 128], // #6b7280
  success: [22, 163, 74], // #16a34a
  danger: [220, 38, 38], // #dc2626
  warning: [245, 158, 11], // #f59e0b
};

/**
 * Format number with locale formatting
 */
function formatNumber(num, decimals = 0) {
  if (num === null || num === undefined) return '-';
  return Number(num).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format currency (Ariary)
 */
function formatCurrency(value) {
  if (value === null || value === undefined) return '-';
  return `${formatNumber(value)} Ar`;
}

/**
 * Generate a performance report PDF
 *
 * @param {Object} options Report options
 * @param {string} options.siteName Site name
 * @param {string} options.startDate Start date of period
 * @param {string} options.endDate End date of period
 * @param {Object} options.currentMetrics Current period metrics
 * @param {Object} options.previousMetrics Previous period metrics (optional)
 * @param {Array} options.runs Array of run data
 * @returns {jsPDF} The PDF document
 */
export function generatePerformanceReport({
  siteName = 'KORA Site',
  startDate,
  endDate,
  currentMetrics,
  previousMetrics,
  runs = [],
}) {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 20;
  let yPos = margin;

  // Helper to add new page if needed
  const checkPageBreak = (neededHeight = 30) => {
    if (yPos + neededHeight > pageHeight - margin) {
      doc.addPage();
      yPos = margin;
      return true;
    }
    return false;
  };

  // --- HEADER ---
  doc.setFillColor(...COLORS.primary);
  doc.rect(0, 0, pageWidth, 35, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFontSize(24);
  doc.setFont('helvetica', 'bold');
  doc.text('KORA', margin, 18);

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text('Energy Platform', margin + 32, 18);

  doc.setFontSize(12);
  doc.text(`Performance Report`, pageWidth - margin, 15, { align: 'right' });
  doc.setFontSize(10);
  doc.text(siteName, pageWidth - margin, 22, { align: 'right' });
  doc.text(`${startDate} - ${endDate}`, pageWidth - margin, 28, { align: 'right' });

  yPos = 45;

  // --- EXECUTIVE SUMMARY ---
  doc.setTextColor(...COLORS.dark);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text('Executive Summary', margin, yPos);
  yPos += 10;

  // Summary metrics boxes
  const summaryMetrics = [
    {
      label: 'Energy Delivered',
      value: formatNumber(currentMetrics.energyKwh),
      unit: 'kWh',
      change: previousMetrics?.energyKwh
        ? ((currentMetrics.energyKwh - previousMetrics.energyKwh) / previousMetrics.energyKwh * 100).toFixed(1)
        : null,
    },
    {
      label: 'Total Revenue',
      value: formatNumber(currentMetrics.revenueAr / 1000000, 2),
      unit: 'M Ar',
      change: previousMetrics?.revenueAr
        ? ((currentMetrics.revenueAr - previousMetrics.revenueAr) / previousMetrics.revenueAr * 100).toFixed(1)
        : null,
    },
    {
      label: 'Avg Curtailment',
      value: formatNumber(currentMetrics.curtailmentPct, 1),
      unit: '%',
      change: previousMetrics?.curtailmentPct
        ? -((previousMetrics.curtailmentPct - currentMetrics.curtailmentPct) / previousMetrics.curtailmentPct * 100).toFixed(1)
        : null,
      invertColor: true,
    },
    {
      label: 'Blackout Hours',
      value: formatNumber(currentMetrics.blackoutHours),
      unit: 'hrs',
      change: null,
    },
  ];

  const boxWidth = (pageWidth - 2 * margin - 15) / 4;
  const boxHeight = 25;

  summaryMetrics.forEach((metric, i) => {
    const x = margin + i * (boxWidth + 5);

    // Box background
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(x, yPos, boxWidth, boxHeight, 2, 2, 'F');

    // Label
    doc.setTextColor(...COLORS.muted);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'normal');
    doc.text(metric.label.toUpperCase(), x + 4, yPos + 6);

    // Value
    doc.setTextColor(...COLORS.dark);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text(`${metric.value} ${metric.unit}`, x + 4, yPos + 16);

    // Change indicator
    if (metric.change !== null) {
      const changeNum = parseFloat(metric.change);
      const isPositive = metric.invertColor ? changeNum < 0 : changeNum > 0;
      doc.setTextColor(...(isPositive ? COLORS.success : COLORS.danger));
      doc.setFontSize(8);
      doc.text(`${changeNum >= 0 ? '+' : ''}${metric.change}%`, x + 4, yPos + 22);
    }
  });

  yPos += boxHeight + 15;

  // --- PERIOD COMPARISON ---
  if (previousMetrics) {
    checkPageBreak(50);

    doc.setTextColor(...COLORS.dark);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Period Comparison', margin, yPos);
    yPos += 8;

    const comparisonData = [
      ['Metric', 'Current Period', 'Previous Period', 'Change'],
      [
        'Energy Delivered (kWh)',
        formatNumber(currentMetrics.energyKwh),
        formatNumber(previousMetrics.energyKwh),
        `${((currentMetrics.energyKwh - previousMetrics.energyKwh) / previousMetrics.energyKwh * 100).toFixed(1)}%`,
      ],
      [
        'Revenue (Ar)',
        formatCurrency(currentMetrics.revenueAr),
        formatCurrency(previousMetrics.revenueAr),
        `${((currentMetrics.revenueAr - previousMetrics.revenueAr) / previousMetrics.revenueAr * 100).toFixed(1)}%`,
      ],
      [
        'Avg Curtailment (%)',
        formatNumber(currentMetrics.curtailmentPct, 1),
        formatNumber(previousMetrics.curtailmentPct, 1),
        `${-((previousMetrics.curtailmentPct - currentMetrics.curtailmentPct) / previousMetrics.curtailmentPct * 100).toFixed(1)}%`,
      ],
      [
        'Blackout Hours',
        formatNumber(currentMetrics.blackoutHours),
        formatNumber(previousMetrics.blackoutHours),
        currentMetrics.blackoutHours - previousMetrics.blackoutHours,
      ],
    ];

    doc.autoTable({
      startY: yPos,
      head: [comparisonData[0]],
      body: comparisonData.slice(1),
      margin: { left: margin, right: margin },
      styles: {
        fontSize: 9,
        cellPadding: 4,
      },
      headStyles: {
        fillColor: COLORS.primary,
        textColor: [255, 255, 255],
        fontStyle: 'bold',
      },
      alternateRowStyles: {
        fillColor: [248, 250, 252],
      },
    });

    yPos = doc.lastAutoTable.finalY + 15;
  }

  // --- DETAILED RUNS TABLE ---
  checkPageBreak(50);

  doc.setTextColor(...COLORS.dark);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text('Optimization Runs', margin, yPos);
  yPos += 8;

  if (runs.length > 0) {
    const tableData = runs.slice(0, 50).map(run => [
      run.date,
      run.time,
      run.mode,
      formatNumber(run.energyKwh),
      formatCurrency(run.revenueAr),
      `${run.curtailmentPct}%`,
      `${run.blackoutHours || 0}`,
    ]);

    doc.autoTable({
      startY: yPos,
      head: [['Date', 'Time', 'Mode', 'Energy (kWh)', 'Revenue', 'Curtail', 'Blackouts']],
      body: tableData,
      margin: { left: margin, right: margin },
      styles: {
        fontSize: 8,
        cellPadding: 3,
      },
      headStyles: {
        fillColor: COLORS.primary,
        textColor: [255, 255, 255],
        fontStyle: 'bold',
      },
      alternateRowStyles: {
        fillColor: [248, 250, 252],
      },
      columnStyles: {
        0: { cellWidth: 22 },
        1: { cellWidth: 25 },
        2: { cellWidth: 20 },
        3: { cellWidth: 25, halign: 'right' },
        4: { cellWidth: 35, halign: 'right' },
        5: { cellWidth: 18, halign: 'right' },
        6: { cellWidth: 20, halign: 'right' },
      },
      didParseCell: function(data) {
        // Color code curtailment
        if (data.column.index === 5 && data.section === 'body') {
          const val = parseFloat(data.cell.raw);
          if (val < 10) {
            data.cell.styles.textColor = COLORS.success;
          } else if (val > 20) {
            data.cell.styles.textColor = COLORS.danger;
          }
        }
        // Color code mode
        if (data.column.index === 2 && data.section === 'body') {
          if (data.cell.raw === 'KORA') {
            data.cell.styles.textColor = COLORS.primary;
            data.cell.styles.fontStyle = 'bold';
          }
        }
      },
    });

    yPos = doc.lastAutoTable.finalY + 10;

    if (runs.length > 50) {
      doc.setTextColor(...COLORS.muted);
      doc.setFontSize(8);
      doc.text(`Showing 50 of ${runs.length} runs. Export CSV for complete data.`, margin, yPos);
    }
  } else {
    doc.setTextColor(...COLORS.muted);
    doc.setFontSize(10);
    doc.text('No optimization runs in this period.', margin, yPos);
  }

  // --- FOOTER ---
  const footerY = pageHeight - 10;
  doc.setTextColor(...COLORS.muted);
  doc.setFontSize(8);
  doc.text(
    `Generated by KORA Energy Platform on ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}`,
    margin,
    footerY
  );
  doc.text(
    `Page 1 of ${doc.getNumberOfPages()}`,
    pageWidth - margin,
    footerY,
    { align: 'right' }
  );

  return doc;
}

/**
 * Generate and download the PDF report
 */
export function downloadPerformanceReport(options) {
  const doc = generatePerformanceReport(options);
  const filename = `kora-report-${options.startDate}-to-${options.endDate}.pdf`;
  doc.save(filename);
  return filename;
}

export default downloadPerformanceReport;
