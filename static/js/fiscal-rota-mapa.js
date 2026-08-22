(function () {
    const el = document.getElementById("rota-mapa");
    if (!el || typeof L === "undefined") return;

    let paradas = [];
    const scriptData = document.getElementById("rota-paradas-data");
    try {
        if (scriptData) {
            paradas = JSON.parse(scriptData.textContent || "[]");
        } else {
            paradas = JSON.parse(el.getAttribute("data-paradas") || "[]");
        }
    } catch (_erro) {
        paradas = [];
    }

    const proximaId = el.getAttribute("data-proxima-id");
    const centro = [-14.8661, -40.839];
    const mapa = L.map(el).setView(centro, 14);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapa);

    const cores = {
        PENDENTE: "#0EA5E9",
        CONCLUIDA: "#10B981",
        PULADA: "#94A3B8",
    };

    const latLngs = [];
    let proximaLatLng = null;

    paradas.forEach(function (parada) {
        if (parada.lat == null || parada.lng == null) return;
        const latLng = [parada.lat, parada.lng];
        latLngs.push(latLng);
        const ehProxima = proximaId && String(parada.id) === String(proximaId);
        if (ehProxima) proximaLatLng = latLng;
        const cor = ehProxima ? "#F59E0B" : cores[parada.status] || cores.PENDENTE;
        const icone = L.divIcon({
            className: "rota-marker" + (ehProxima ? " rota-marker-proxima" : ""),
            html:
                '<span class="rota-marker-num" style="background:' +
                cor +
                (ehProxima ? ";transform:scale(1.2)" : "") +
                '">' +
                parada.ordem +
                "</span>",
            iconSize: [ehProxima ? 34 : 28, ehProxima ? 34 : 28],
            iconAnchor: [ehProxima ? 17 : 14, ehProxima ? 17 : 14],
        });
        const marker = L.marker(latLng, { icon: icone }).addTo(mapa);
        marker.bindPopup(
            "<strong>#" +
                parada.ordem +
                " — " +
                (parada.ambulante || "") +
                "</strong><br>" +
                (parada.endereco || parada.ponto || "Sem ponto") +
                "<br><em>" +
                (ehProxima ? "Próxima parada" : parada.status || "") +
                "</em>"
        );
        if (ehProxima) marker.openPopup();
    });

    if (latLngs.length > 1) {
        L.polyline(latLngs, {
            color: "#0369A1",
            weight: 3,
            opacity: 0.75,
            dashArray: "6 8",
        }).addTo(mapa);
    }

    if (proximaLatLng) {
        mapa.setView(proximaLatLng, 15);
    } else if (latLngs.length === 1) {
        mapa.setView(latLngs[0], 15);
    } else if (latLngs.length > 1) {
        mapa.fitBounds(latLngs, { padding: [36, 36] });
    }

    setTimeout(function () {
        mapa.invalidateSize();
    }, 200);
    window.addEventListener("resize", function () {
        mapa.invalidateSize();
    });
})();
