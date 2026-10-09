/* =====================================================================
   timeseries.js - Xử lý biểu đồ Chart.js và Tương tác Dự báo Giá Cổ phiếu
   ===================================================================== */
document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById("stockChart").getContext("2d");
    let chartInstance = null;

    function buildChartData(histDates, histPrices, forecastDates, forecastPrices, symbol, unit) {
        // Tạo trục nhãn thời gian kết hợp
        const allLabels = [...histDates, ...forecastDates];
        
        // Chuỗi dữ liệu thực tế (các điểm tương lai để giá trị null)
        const actualSeries = [...histPrices, ...Array(forecastDates.length).fill(null)];
        
        // Chuỗi dữ liệu dự báo: bắt đầu nối tiếp từ điểm thực tế cuối cùng để tạo đường liền mạch
        const lastActualPrice = histPrices[histPrices.length - 1];
        const forecastSeries = [
            ...Array(histPrices.length - 1).fill(null),
            lastActualPrice,
            ...forecastPrices
        ];

        return {
            labels: allLabels,
            datasets: [
                {
                    label: `Giá đóng cửa thực tế (${symbol})`,
                    data: actualSeries,
                    borderColor: "#334155",
                    backgroundColor: "transparent",
                    borderWidth: 2,
                    pointRadius: 2.5,
                    pointHoverRadius: 5,
                    pointBackgroundColor: "#334155",
                    tension: 0.1,
                    order: 2
                },
                {
                    label: "Đường dự báo RNN (LSTM Tối ưu)",
                    data: forecastSeries,
                    borderColor: "#2563eb",
                    backgroundColor: "transparent",
                    borderWidth: 2.2,
                    borderDash: [5, 5],
                    pointRadius: 4.5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: "#2563eb",
                    pointBorderColor: "#ffffff",
                    pointBorderWidth: 1.5,
                    tension: 0.1,
                    order: 1
                }
            ]
        };
    }

    function initChart(histDates, histPrices, forecastDates, forecastPrices, symbol, unit) {
        const data = buildChartData(histDates, histPrices, forecastDates, forecastPrices, symbol, unit);

        chartInstance = new Chart(ctx, {
            type: "line",
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: "index"
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            usePointStyle: true,
                            font: { family: "'Inter', sans-serif", size: 12, weight: "500" },
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.9)",
                        titleFont: { family: "'Inter', sans-serif", size: 13, weight: "bold" },
                        bodyFont: { family: "'Inter', sans-serif", size: 12 },
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || "";
                                if (context.parsed.y !== null) {
                                    return `${label}: ${context.parsed.y.toFixed(2)} ${unit}`;
                                }
                                return null;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            maxTicksLimit: 12,
                            font: { family: "'Inter', sans-serif", size: 11 }
                        }
                    },
                    y: {
                        grid: { color: "#f1f5f9" },
                        ticks: {
                            font: { family: "'Inter', sans-serif", size: 11 },
                            callback: function (val) {
                                return val + " " + unit;
                            }
                        }
                    }
                }
            }
        });
    }

    // Khởi tạo biểu đồ từ dữ liệu nạp sẵn trong HTML
    if (typeof initialHistDates !== "undefined" && initialHistDates.length > 0) {
        initChart(initialHistDates, initialHistPrices, initialForecastDates, initialForecastPrices, initialSymbol, initialUnit);
    }

    // Xử lý gửi biểu mẫu AJAX
    const form = document.getElementById("forecastForm");
    const btnSubmit = document.getElementById("btnSubmit");

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        
        const symbol = document.getElementById("symbolSelect").value;
        const steps = parseInt(document.getElementById("stepsSelect").value);
        const source = document.getElementById("sourceSelect").value;

        // Trạng thái Loading
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Đang tính toán...`;

        try {
            const resp = await fetch("/api/timeseries/forecast", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ symbol, steps, source })
            });
            const res = await resp.json();

            if (res.success) {
                const hist = res.hist;
                const fc = res.forecast;

                // 1. Cập nhật các thẻ KPI
                document.getElementById("kpiLastPrice").textContent = `${hist.last_price} ${hist.unit}`;
                document.getElementById("kpiLastDate").textContent = `Phiên ngày: ${hist.last_date}`;

                document.getElementById("kpiTargetTitle").textContent = `Giá dự báo cuối kỳ (T+${steps})`;
                document.getElementById("kpiFinalPrice").textContent = `${fc.final_price} ${hist.unit}`;
                document.getElementById("kpiT1Price").textContent = `Phiên T+1: ${fc.t1_price} ${hist.unit}`;

                document.getElementById("kpiDiffTitle").textContent = `Biến động cả kỳ (${steps} ngày)`;
                const diffElem = document.getElementById("kpiDiffTotal");
                const sign = fc.diff_total >= 0 ? "+" : "";
                diffElem.textContent = `${sign}${fc.diff_total} ${hist.unit}`;
                diffElem.className = `stat-value ${fc.diff_total >= 0 ? "text-success" : "text-danger"}`;
                
                const pctSign = fc.pct_total >= 0 ? "+" : "";
                const pctT1Sign = fc.pct_t1 >= 0 ? "+" : "";
                document.getElementById("kpiPctSubtext").textContent = 
                    `${pctSign}${fc.pct_total}% (T+1: ${pctT1Sign}${fc.pct_t1}%)`;

                document.getElementById("kpiTrendTitle").textContent = `Xu hướng kỳ ${steps} ngày`;
                const badge = document.getElementById("kpiTrendBadge");
                const isUp = fc.trend_total === "Tăng";
                badge.className = `trend-badge ${isUp ? "up" : "down"}`;
                badge.innerHTML = `<i class="fa-solid ${isUp ? "fa-arrow-trend-up" : "fa-arrow-trend-down"} me-1"></i><span>${fc.trend_total}</span>`;
                document.getElementById("kpiTrendSubtext").textContent = `Phiên T+1: ${fc.trend_t1}`;

                // 2. Cập nhật tiêu đề Card
                document.getElementById("titleSymbol").textContent = symbol;

                // 3. Cập nhật biểu đồ
                const newChartData = buildChartData(hist.dates, hist.prices, fc.forecast_dates, fc.forecast_prices, symbol, hist.unit);
                chartInstance.data = newChartData;
                chartInstance.options.scales.y.ticks.callback = function (val) {
                    return val + " " + hist.unit;
                };
                chartInstance.update();

                // 4. Cập nhật Bảng dữ liệu chi tiết
                const tbody = document.getElementById("forecastTableBody");
                tbody.innerHTML = "";
                fc.forecast_prices.forEach((p, idx) => {
                    const diff = (p - hist.last_price).toFixed(2);
                    const pct = ((diff / hist.last_price) * 100).toFixed(2);
                    const isPos = diff >= 0;
                    const diffSign = isPos ? "+" : "";
                    const pctSign = isPos ? "+" : "";
                    
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td class="ps-3 fw-bold text-primary">T+${idx + 1}</td>
                        <td>${fc.forecast_dates[idx]}</td>
                        <td class="fw-bold">${p} ${hist.unit}</td>
                        <td class="${isPos ? "text-success" : "text-danger"} fw-semibold">
                            ${diffSign}${diff} ${hist.unit}
                        </td>
                        <td class="${isPos ? "text-success" : "text-danger"}">
                            ${pctSign}${pct}%
                        </td>
                        <td>
                            <span class="badge ${isPos ? "bg-success-subtle text-success border border-success-subtle" : "bg-danger-subtle text-danger border border-danger-subtle"}">
                                ${isPos ? "Tăng giá" : "Giảm giá"}
                            </span>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (err) {
            console.error("Lỗi dự báo:", err);
            alert("Đã xảy ra lỗi trong quá trình dự báo: " + err.message);
        } finally {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = `<i class="fa-solid fa-bolt"></i> <span>Thực Hiện Dự Báo</span>`;
        }
    });
});
