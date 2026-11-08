L.Browser.any3d = false;

let mapInstance = null;
let heatLayer = null;    
let clusterLayer = null; 
let legendControl = null;
let currentData = []; 

let currentChartData = [];
let currentChartType = 'weekly';

const ZONE_VIEWS = {
    'europe': { center: [53.0, 10.0], zoom: 4 }, 
    'med':    { center: [38.0, 15.0], zoom: 5 },
    'manche': { center: [50.0, 0.0], zoom: 6 },
    'atl':    { center: [46.0, -5.0], zoom: 5 }
};

const GRADIENT_SST = { 0.0: '#313695', 0.2: '#4575b4', 0.4: '#74add1', 0.6: '#fdae61', 0.8: '#f46d43', 1.0: '#a50026' };
const GRADIENT_SSS = { 0.0: '#f7fbff', 0.4: '#deebf7', 0.6: '#9ecae1', 0.8: '#3182bd', 1.0: '#08519c' };
const GRADIENT_CHL = { 0.0: '#ffffe5', 0.2: '#d9f0a3', 0.5: '#78c679', 0.8: '#238443', 1.0: '#005a32' };

document.addEventListener('DOMContentLoaded', () => {
    const isMapPage = document.getElementById('map');
    const isChartPage = document.getElementById('mainChart');

    if (isMapPage) {
        const southWest = L.latLng(25.0, -35.0);
        const northEast = L.latLng(75.0, 45.0);
        const bounds = L.latLngBounds(southWest, northEast);

        mapInstance = L.map('map', {
            preferCanvas: true, 
            renderer: L.canvas(),
            maxBounds: bounds, 
            maxBoundsViscosity: 1.0, 
            minZoom: 3, 
            maxZoom: 18 // CHANGEMENT ICI : Zoom débloqué à l'initialisation
        }).setView(ZONE_VIEWS['europe'].center, ZONE_VIEWS['europe'].zoom);
        
        L.tileLayer('https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png', {
            attribution: '© Openstreetmap France | © OpenStreetMap contributors',
            maxZoom: 19, // CHANGEMENT ICI : Supporte le zoom profond
            crossOrigin: true 
        }).addTo(mapInstance);

        ['zoneSelect', 'indicatorSelect'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', () => {
                    if (id === 'zoneSelect') {
                        const z = ZONE_VIEWS[el.value];
                        if (z) mapInstance.flyTo(z.center, z.zoom);
                    }
                    resetFavBtn();
                    if (document.getElementById('mapStart').value) updateMapData();
                });
            }
        });
    }

    if (isMapPage || isChartPage) {
        fetch('/api/available-dates')
            .then(res => res.json())
            .then(dates => {
                if (!dates || dates.length === 0) return;

                const selectorPairs = [
                    ['mapStart', 'mapEnd'],
                    ['startWeek', 'endWeek'],
                    ['startCorr', 'endCorr'],
                    ['startDist', 'endDist']
                ];

                selectorPairs.forEach(pair => {
                    const startEl = document.getElementById(pair[0]);
                    const endEl = document.getElementById(pair[1]);

                    if (startEl && endEl) {
                        startEl.innerHTML = '';
                        endEl.innerHTML = '';

                        dates.forEach(date => {
                            const label = formatDateFr(date);
                            const opt1 = document.createElement('option'); opt1.value = date; opt1.innerText = label;
                            startEl.appendChild(opt1);
                            
                            const opt2 = document.createElement('option'); opt2.value = date; opt2.innerText = label;
                            endEl.appendChild(opt2);
                        });

                        startEl.value = dates[dates.length - 1]; 
                        endEl.value = dates[0]; 

                        if (isMapPage && pair[0] === 'mapStart') {
                            startEl.addEventListener('change', updateMapData);
                            endEl.addEventListener('change', updateMapData);

                            const params = new URLSearchParams(window.location.search);
                            const pZone = params.get('zone');
                            const pInd = params.get('indicator');
                            const pStart = params.get('start');
                            const pEnd = params.get('end');

                            if (pZone && pInd && pStart && pEnd) {
                                const zoneSel = document.getElementById('zoneSelect');
                                const indSel = document.getElementById('indicatorSelect');
                                
                                if (zoneSel) zoneSel.value = pZone;
                                if (indSel) indSel.value = pInd;
                                startEl.value = pStart;
                                endEl.value = pEnd;

                                if (ZONE_VIEWS[pZone]) {
                                    mapInstance.setView(ZONE_VIEWS[pZone].center, ZONE_VIEWS[pZone].zoom);
                                }
                            }

                            updateMapData(); 
                        }
                    }
                });

                if (isChartPage) {
                    switchTab('weekly');
                    setTimeout(() => updateWeeklyChart(), 100);
                }
            })
            .catch(() => {});
    }
});

function formatDateFr(dateStr) {
    if (!dateStr) return "";
    const parts = dateStr.split('-'); 
    return `${parts[2]}/${parts[1]}/${parts[0]}`; 
}

function getUnit(label) {
    if (label.includes('Temp') || label.includes('SST')) return '°C';
    if (label.includes('Sal') || label.includes('SSS')) return 'PSU';
    if (label.includes('Chl')) return 'mg/m³';
    return '';
}

function getColor(label) {
    if (label.includes('Temp') || label.includes('SST')) return '#f39c12'; 
    if (label.includes('Sal') || label.includes('SSS')) return '#3498db';  
    if (label.includes('Chl')) return '#2ecc71';                           
    return '#9b59b6'; 
}

function switchTab(tab) {
    currentChartType = tab;
    const w = document.getElementById('controls-weekly');
    const c = document.getElementById('controls-correlation');
    const d = document.getElementById('controls-distribution');
    if(w) w.style.display = (tab === 'weekly') ? 'block' : 'none';
    if(c) c.style.display = (tab === 'correlation') ? 'block' : 'none';
    if(d) d.style.display = (tab === 'distribution') ? 'block' : 'none';
    
    const bw = document.getElementById('btn-week');
    const bc = document.getElementById('btn-corr');
    const bd = document.getElementById('btn-dist');
    if(bw) bw.style.background = (tab === 'weekly') ? '#3498db' : '#95a5a6';
    if(bc) bc.style.background = (tab === 'correlation') ? '#3498db' : '#95a5a6';
    if(bd) bd.style.background = (tab === 'distribution') ? '#3498db' : '#95a5a6';
    
    const pm = document.getElementById('perf-metrics');
    if(pm) pm.innerHTML = "";
}

function showPerf(time) {
    const div = document.getElementById('perf-metrics');
    if(div) div.innerHTML = `<i class="fa-solid fa-bolt"></i> Serveur: <b>${time} ms</b>`;
}

function updateWeeklyChart() {
    if (!checkDates('startWeek', 'endWeek')) return;
    toggleLoader(true);
    const start = document.getElementById('startWeek').value;
    const end = document.getElementById('endWeek').value;
    const sel = document.getElementById('indWeekly');
    const label = sel.options[sel.selectedIndex].text;
    const unit = getUnit(label);
    const color = getColor(label);
    const cleanLabel = label.split('(')[0].trim();
    
    fetch(`/api/stats/weekly?start=${start}&end=${end}&ind=${encodeURIComponent(label)}`)
        .then(r => r.json())
        .then(resp => {
            if(!resp.results) { throw new Error("Format invalide"); }
            const data = resp.results;
            currentChartData = data;
            showPerf(resp.time);
            
            if(data.length === 0) {
                document.getElementById('mainChart').innerHTML = "<div style='text-align:center; padding-top:100px;'>Pas de données sur cette période.</div>";
                return;
            }
            
            const trace = {
                x: data.map(row => row.Date_Semaine),
                y: data.map(row => row.Moyenne),
                type: 'scatter', mode: 'lines+markers', name: cleanLabel, 
                line: { color: color, width: 3 }
            };
            
            const layout = { 
                title: `Évolution : ${label}`, 
                xaxis: { title: 'Date', automargin: true, tickangle: -45 }, 
                yaxis: { title: `${cleanLabel} (${unit})` },
                margin: { b: 150, l: 70, r: 40, t: 50 }, 
                autosize: true
            };
           Plotly.newPlot('mainChart', [trace], layout, {responsive: true, displayModeBar: false});
        })
        .finally(() => toggleLoader(false));
}

function updateCorrelationChart() {
    if (!checkDates('startCorr', 'endCorr')) return;
    toggleLoader(true);
    const start = document.getElementById('startCorr').value;
    const end = document.getElementById('endCorr').value;
    const s1 = document.getElementById('ind1');
    const s2 = document.getElementById('ind2');
    const l1 = s1.options[s1.selectedIndex].text;
    const l2 = s2.options[s2.selectedIndex].text;
    const u1 = getUnit(l1);
    const u2 = getUnit(l2);
    const c1 = getColor(l1);
    const c2 = getColor(l2);
    const cleanL1 = l1.split('(')[0].trim();
    const cleanL2 = l2.split('(')[0].trim();

    fetch(`/api/stats/correlation?start=${start}&end=${end}&ind1=${encodeURIComponent(l1)}&ind2=${encodeURIComponent(l2)}`)
        .then(r => r.json())
        .then(resp => {
            if(!resp.results) throw new Error("Données invalides");
            const data = resp.results;
            currentChartData = data;
            showPerf(resp.time);
            
            if(data.length === 0) {
                document.getElementById('mainChart').innerHTML = "<div style='text-align:center; padding-top:100px;'>Pas de données communes.</div>";
                return;
            }
            const dates = data.map(d => d.date);
            const trace1 = { x: dates, y: data.map(d => d.val1), name: cleanL1, type: 'scatter', mode: 'lines', line: {color: c1} };
            const trace2 = { x: dates, y: data.map(d => d.val2), name: cleanL2, type: 'scatter', mode: 'lines', line: {color: c2}, yaxis: 'y2' };
            
            const layout = {
                title: `${l1} vs ${l2}`,
                xaxis: { title: 'Date', automargin: true, tickangle: -45 },
                yaxis: { title: {text: `${cleanL1} (${u1})`, font:{color: c1}} },
                yaxis2: { title: {text: `${cleanL2} (${u2})`, font:{color: c2}}, overlaying: 'y', side: 'right', showgrid: false },
                legend: { orientation: 'h', y: 1.1 }, 
                margin: { b: 150, l: 70, r: 70, t: 80 }, 
                autosize: true
            };
          Plotly.newPlot('mainChart', [trace1, trace2], layout, {responsive: true, displayModeBar: false});
        })
        .finally(() => toggleLoader(false));
}

function updateDistributionChart() {
    if (!checkDates('startDist', 'endDist')) return;
    toggleLoader(true);
    const start = document.getElementById('startDist').value;
    const end = document.getElementById('endDist').value;
    const sel = document.getElementById('indDist');
    const label = sel.options[sel.selectedIndex].text;
    const unit = getUnit(label);
    const color = getColor(label);
    const cleanLabel = label.split('(')[0].trim();

    fetch(`/api/stats/distribution?start=${start}&end=${end}&ind=${encodeURIComponent(label)}`)
        .then(r => r.json())
        .then(resp => {
            if(!resp.results) throw new Error("Erreur données");
            const data = resp.results;
            currentChartData = data;
            showPerf(resp.time);
            
            if(data.length === 0) {
                document.getElementById('mainChart').innerHTML = "<div style='text-align:center; padding-top:100px;'>Pas de données.</div>";
                return;
            }
            const trace = { x: data, type: 'histogram', marker: { color: color }, name: cleanLabel };
            const layout = { 
                title: `Distribution : ${label}`,
                xaxis: { title: {text: `${cleanLabel} (${unit})`, font: { size: 14, color: '#333' }}, automargin: true },
                yaxis: { title: "Nombre de mesures" },
                bargap: 0.05,
                margin: { b: 150, l: 70, r: 40, t: 60 },
                autosize: true
            };
           Plotly.newPlot('mainChart', [trace], layout, {responsive: true, displayModeBar: false});
        })
        .finally(() => toggleLoader(false));
}

function toggleLoader(show) {
    const loader = document.getElementById('loader');
    if (loader) loader.style.display = show ? 'flex' : 'none';
}

function resetFavBtn() {
    const btn = document.getElementById('favBtn');
    const msgBox = document.getElementById('msgBox');
    if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-heart"></i> <span>Ajouter aux favoris</span>';
        btn.disabled = false; 
    }
    if (msgBox) msgBox.innerHTML = '';
}

function downloadCsv(content, filename) {
    const blob = new Blob(['\uFEFF' + content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportData(format, type) {
    if (!type && currentChartData) {
        if (format === 'pdf') {
            const container = document.getElementById('chart-container');
            const originalHeight = container.style.height; 
            container.style.height = "600px"; 
            Plotly.Plots.resize('mainChart'); 
            const opt = {
                margin: 10,
                filename: `oceanview_chart_${currentChartType}.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' }
            };
            toggleLoader(true);
            html2pdf().set(opt).from(container).save()
                .catch(() => alert('Impossible de générer le PDF.'))
                .finally(() => {
                    container.style.height = originalHeight;
                    Plotly.Plots.resize('mainChart');
                    toggleLoader(false);
                });
            return;
        }
        if (currentChartData.length === 0) { alert("Aucune donnée."); return; }
        let csv = "";
        if (currentChartType === 'weekly') {
            csv += "Date;Moyenne\n";
            currentChartData.forEach(r => csv += `${r.Date_Semaine};${r.Moyenne}\n`);
        } else if (currentChartType === 'correlation') {
            csv += "Date;Val1;Val2\n";
            currentChartData.forEach(r => csv += `${r.date};${r.val1};${r.val2}\n`);
        } else {
            csv += "Valeur\n";
            currentChartData.forEach(v => csv += `${v}\n`);
        }
        downloadCsv(csv, `export_${currentChartType}.csv`);
        return;
    }

    if (type === 'map') {
        if (!currentData || currentData.length === 0) {
            alert("Veuillez attendre le chargement des données.");
            return;
        }
        if (format === 'csv') {
            let csvContent = "Latitude;Longitude;Valeur;Intensité\n";
            csvContent += currentData.map(row => {
                return `${row[0]};${row[1]};${row[2]};${row[3]}`;
            }).join('\n');
            downloadCsv(csvContent, 'oceanview_export_map.csv');
        }
        if (format === 'pdf') {
            const element = document.getElementById('map-container');
            element.classList.add('pdf-mode'); 
            const opt = { 
                margin: 0, 
                filename: `oceanview_map.pdf`, 
                image: { type: 'jpeg', quality: 0.98 }, 
                html2canvas: { scale: 2, useCORS: true }, 
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' } 
            };
            toggleLoader(true);
            if(mapInstance) mapInstance.invalidateSize();
            setTimeout(() => {
                html2pdf().set(opt).from(element).save()
                    .catch(() => alert('Impossible de générer le PDF.'))
                    .finally(() => {
                    element.classList.remove('pdf-mode'); 
                    toggleLoader(false); 
                    if(mapInstance) mapInstance.invalidateSize();
                });
            }, 2000);
        }
    }
}

function updateMapData() {
    if (!checkDates('mapStart', 'mapEnd')) return;
    const start = document.getElementById('mapStart').value;
    const end = document.getElementById('mapEnd').value;
    const indicator = document.getElementById('indicatorSelect').value;
    const zone = document.getElementById('zoneSelect').value;

    toggleLoader(true);
    fetch(`/api/data?start=${start}&end=${end}&indicator=${indicator}&zone=${zone}`)
        .then(res => res.json())
        .then(data => { currentData = data; drawMapPoints(data, indicator); })
        .catch(() => { alert("Erreur de chargement."); })
        .finally(() => toggleLoader(false));
}

function drawMapPoints(data, indicatorSelected) {
    if (heatLayer) mapInstance.removeLayer(heatLayer);
    if (clusterLayer) { clusterLayer.clearLayers(); mapInstance.removeLayer(clusterLayer); }
    if (legendControl) mapInstance.removeControl(legendControl);

    const radio = document.querySelector('input[name="viewMode"]:checked');
    const mode = radio ? radio.value : 'heat';

    if (mode === 'cluster') {
        // --- CHANGEMENT ICI : Zoom libre pour les Clusters ---
        mapInstance.setMaxZoom(18);

        clusterLayer = L.markerClusterGroup({
            chunkedLoading: true 
        });
        
        const markers = data.map(p => {
            const marker = L.marker([p[0], p[1]]); 
            marker.bindPopup(`<b>Val:</b> ${p[2]}`); 
            return marker;
        });
        
        clusterLayer.addLayers(markers);
        mapInstance.addLayer(clusterLayer);
    } else {
        // --- CHANGEMENT ICI : Zoom bloqué pour la Heatmap ---
        if (mapInstance.getZoom() > 7) {
            mapInstance.setZoom(7);
        }
        mapInstance.setMaxZoom(7);

        let heatPoints = data.map(p => [p[0], p[1], p[3]]); 
        let gradientCfg = GRADIENT_SST;
        let maxLegendVal = 30; 

        if (indicatorSelected.includes('SSS')) { 
            gradientCfg = GRADIENT_SSS; 
            maxLegendVal = 40; 
        }
        else if (indicatorSelected.includes('Chl')) { 
            gradientCfg = GRADIENT_CHL; 
            maxLegendVal = 5; 
        }
        
        heatLayer = L.heatLayer(heatPoints, { 
            radius: 15,       
            blur: 15,         
            maxZoom: 7,      
            max: 5.0,         
            minOpacity: 0.4,
            gradient: gradientCfg 
        });

        mapInstance.addLayer(heatLayer);
        updateLegend(indicatorSelected, gradientCfg, maxLegendVal);
    }
}

function updateLegend(indicator, gradientCfg, maxVal) {
    if (legendControl) mapInstance.removeControl(legendControl);

    legendControl = L.control({position: 'bottomright'});
    legendControl.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'info legend');
        div.style.background = "white"; div.style.padding = "10px"; div.style.borderRadius = "5px";
        let title = "Valeur";
        if (indicator.includes('SST')) title = "Température (°C)";
        if (indicator.includes('SSS')) title = "Salinité (PSU)";
        if (indicator.includes('Chl')) title = "Chlorophylle (mg/m³)";
        div.innerHTML = `<strong>${title}</strong><br>`;
        let gradientCSS = "linear-gradient(to right";
        for (const [pos, color] of Object.entries(gradientCfg)) { gradientCSS += `, ${color} ${pos*100}%`; }
        gradientCSS += ")";
        div.innerHTML += `<div style="height: 15px; background: ${gradientCSS}; margin-bottom: 5px; border:1px solid #ccc; width: 100px;"></div><div style="display: flex; justify-content: space-between; font-size: 0.8em;"><span>0</span><span>${maxVal}</span></div>`;
        return div;
    };
    legendControl.addTo(mapInstance);
}

function toggleFavorite() {
    const zone = document.getElementById('zoneSelect').value;
    const indicator = document.getElementById('indicatorSelect').value;
    const startDate = document.getElementById('mapStart').value;
    const endDate = document.getElementById('mapEnd').value;
    const btn = document.getElementById('favBtn');
    const msgBox = document.getElementById('msgBox');

    fetch('/api/favoris/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ zone: zone, indicator: indicator, start_date: startDate, end_date: endDate })
    })
    .then(response => {
        if (response.status === 401) { alert("Vous devez être connecté pour ajouter des favoris."); return null; }
        return response.json();
    })
    .then(data => {
        if (!data) return;
        if (data.status === 'added') {
            msgBox.innerHTML = '<span style="color: #2ecc71;">Favori ajouté avec succès !</span>';
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Sauvegardé';
        } else if (data.status === 'exists') {
            msgBox.innerHTML = '<span style="color: #f39c12;">Cette zone est déjà dans vos favoris !</span>';
        } else {
            msgBox.innerText = "Erreur : " + (data.error || "Inconnue");
        }
        setTimeout(() => { msgBox.innerHTML = ''; }, 3000);
    })
    .catch(() => {});
}

function checkDates(startId, endId) {
    const startVal = document.getElementById(startId).value;
    const endVal = document.getElementById(endId).value;
    if (startVal > endVal) {
        alert("Erreur de date :\nLa date de début ne peut pas être après la date de fin !");
        return false; 
    }
    return true; 
}
