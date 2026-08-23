(function () {
    const el = document.getElementById("mapa-cidade");
    const form = document.getElementById("mapa-cidade-filtros");
    const painel = document.getElementById("mapa-cidade-painel");
    if (!el || typeof L === "undefined") return;

    const dadosUrl =
        (form && form.getAttribute("data-url")) ||
        el.getAttribute("data-url") ||
        "/gestor/mapa/dados.json";

    const centro = [-14.8661, -40.839];
    const mapa = L.map(el, { doubleClickZoom: false }).setView(centro, 14);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapa);

    const camada = L.layerGroup().addTo(mapa);
    let debounceTimer = null;
    let pontoSelecionadoId = null;
    let dadosAtuais = { pontos: [] };

    const COR_BAIXA = [37, 99, 235];
    const COR_ALTA = [127, 29, 29];
    const COR_ZERO = [191, 219, 254];

    function hexRgb(rgb) {
        return (
            "#" +
            rgb
                .map(function (n) {
                    const h = Math.round(n).toString(16);
                    return h.length === 1 ? "0" + h : h;
                })
                .join("")
        );
    }

    function corPorVolume(volume, volumeMax) {
        if (!volume || volume <= 0) return hexRgb(COR_ZERO);
        const t = volumeMax > 0 ? Math.min(1, volume / volumeMax) : 0;
        const rgb = COR_BAIXA.map(function (c, i) {
            return c + (COR_ALTA[i] - c) * t;
        });
        return hexRgb(rgb);
    }

    function raioPorVolume(volume) {
        return Math.min(400, 80 + Number(volume || 0) * 30);
    }

    function escapeHtml(texto) {
        return String(texto || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function rotuloAtuacao(tipo) {
        if (tipo === "fixo") return "Fixo";
        if (tipo === "movel") return "Itinerante";
        if (tipo === "eventual") return "Eventual";
        return tipo || "—";
    }

    function atualizarKpis(dados) {
        const kpiPontos = document.getElementById("mapa-kpi-pontos");
        const kpiAmb = document.getElementById("mapa-kpi-ambulantes");
        const kpiMax = document.getElementById("mapa-kpi-max");
        const comGeo = (dados.pontos || []).filter(function (p) {
            return p.lat != null && p.lng != null;
        }).length;
        if (kpiPontos) kpiPontos.textContent = String(comGeo);
        if (kpiAmb) kpiAmb.textContent = String(dados.total_ambulantes || 0);
        if (kpiMax) kpiMax.textContent = String(dados.volume_max || 0);
    }

    function fecharPainel() {
        if (!painel) return;
        painel.hidden = true;
        painel.setAttribute("aria-hidden", "true");
        painel.classList.remove("is-open");
        pontoSelecionadoId = null;
        document.querySelectorAll(".mapa-cidade-marker-num.is-selected").forEach(function (n) {
            n.classList.remove("is-selected");
        });
    }

    function abrirPainel(ponto) {
        if (!painel || !ponto) return;
        pontoSelecionadoId = ponto.id;

        const titulo = document.getElementById("mapa-painel-titulo");
        const endereco = document.getElementById("mapa-painel-endereco");
        const badge = document.getElementById("mapa-painel-badge");
        const count = document.getElementById("mapa-painel-count");
        const lista = document.getElementById("mapa-painel-lista");
        const vazio = document.getElementById("mapa-painel-vazio");

        if (titulo) titulo.textContent = ponto.nome || "Ponto";
        if (endereco) {
            endereco.textContent =
                (ponto.logradouro || "") +
                (ponto.bairro ? " — " + ponto.bairro : "");
        }

        if (badge) {
            badge.textContent = ponto.status_ocupacao || "—";
            badge.className = "badge";
            if (ponto.status_ocupacao === "Livre") badge.classList.add("success");
            else if (ponto.status_ocupacao === "Ocupado") badge.classList.add("danger");
            else if (ponto.status_ocupacao === "Reservado") badge.classList.add("purple");
            else badge.classList.add("warning");
        }

        const ambulantes = ponto.ambulantes || [];
        if (count) {
            count.textContent =
                ambulantes.length === 1
                    ? "1 ambulante no filtro"
                    : ambulantes.length + " ambulantes no filtro";
        }

        if (lista) {
            lista.innerHTML = "";
            ambulantes.forEach(function (amb) {
                const item = document.createElement("a");
                item.className = "mapa-cidade-ambulante";
                item.href = amb.dossie_url || "#";
                item.setAttribute("role", "listitem");
                const badgeClass =
                    amb.situacao === "ativo" ? "badge success" : "badge warning";
                item.innerHTML =
                    '<div class="mapa-cidade-ambulante-texto">' +
                    "<strong>" +
                    escapeHtml(amb.nome) +
                    "</strong>" +
                    (amb.apelido
                        ? '<span class="mapa-cidade-ambulante-apelido">' +
                          escapeHtml(amb.apelido) +
                          "</span>"
                        : "") +
                    '<span class="mapa-cidade-ambulante-meta">' +
                    escapeHtml(rotuloAtuacao(amb.tipo_atuacao)) +
                    "</span>" +
                    "</div>" +
                    '<div class="mapa-cidade-ambulante-lado">' +
                    '<span class="' +
                    badgeClass +
                    '">' +
                    escapeHtml(amb.situacao_label) +
                    "</span>" +
                    '<span class="mapa-cidade-ambulante-cta">Ver dossiê</span>' +
                    "</div>";
                lista.appendChild(item);
            });
        }

        if (vazio) vazio.hidden = ambulantes.length > 0;
        if (lista) lista.hidden = ambulantes.length === 0;

        painel.hidden = false;
        painel.setAttribute("aria-hidden", "false");
        requestAnimationFrame(function () {
            painel.classList.add("is-open");
        });

        document.querySelectorAll(".mapa-cidade-marker-num").forEach(function (n) {
            n.classList.toggle(
                "is-selected",
                String(n.getAttribute("data-ponto-id")) === String(ponto.id)
            );
        });

        if (typeof lucide !== "undefined" && lucide.createIcons) {
            lucide.createIcons();
        }

        setTimeout(function () {
            mapa.invalidateSize();
        }, 220);
    }

    function selecionarPonto(ponto) {
        abrirPainel(ponto);
        if (ponto.lat != null && ponto.lng != null) {
            mapa.panTo([ponto.lat, ponto.lng], { animate: true });
        }
    }

    function desenhar(dados) {
        dadosAtuais = dados || { pontos: [] };
        camada.clearLayers();
        const volumeMax = Number(dados.volume_max || 0);
        const latLngs = [];
        let pontoAberto = null;

        (dados.pontos || []).forEach(function (ponto) {
            if (ponto.lat == null || ponto.lng == null) return;
            const latLng = [ponto.lat, ponto.lng];
            latLngs.push(latLng);
            const volume = Number(ponto.volume || 0);
            const cor = corPorVolume(volume, volumeMax);
            const selecionado = String(ponto.id) === String(pontoSelecionadoId);
            if (selecionado) pontoAberto = ponto;

            const circle = L.circle(latLng, {
                radius: raioPorVolume(volume),
                color: cor,
                weight: selecionado ? 2 : 1,
                opacity: 0.9,
                fillColor: cor,
                fillOpacity: selecionado ? 0.45 : 0.35,
            }).addTo(camada);

            const icone = L.divIcon({
                className: "mapa-cidade-marker",
                html:
                    '<span class="mapa-cidade-marker-num' +
                    (selecionado ? " is-selected" : "") +
                    '" data-ponto-id="' +
                    ponto.id +
                    '" style="background:' +
                    cor +
                    '">' +
                    volume +
                    "</span>",
                iconSize: [34, 34],
                iconAnchor: [17, 17],
            });

            const marker = L.marker(latLng, { icon: icone }).addTo(camada);

            function onSelect(e) {
                if (e && e.originalEvent) {
                    L.DomEvent.stopPropagation(e);
                    L.DomEvent.preventDefault(e);
                }
                selecionarPonto(ponto);
            }

            circle.on("click", onSelect);
            marker.on("click", onSelect);
            marker.on("dblclick", onSelect);
            circle.on("dblclick", onSelect);
        });

        atualizarKpis(dados);

        if (pontoAberto) {
            abrirPainel(pontoAberto);
        } else if (pontoSelecionadoId != null) {
            fecharPainel();
        }

        if (latLngs.length === 1) {
            mapa.setView(latLngs[0], 15);
        } else if (latLngs.length > 1 && pontoSelecionadoId == null) {
            mapa.fitBounds(latLngs, { padding: [40, 40] });
        } else if (!latLngs.length) {
            mapa.setView(centro, 14);
        }

        setTimeout(function () {
            mapa.invalidateSize();
        }, 150);
    }

    function queryAtual() {
        if (!form) return "";
        const params = new URLSearchParams(new FormData(form));
        return params.toString();
    }

    function carregar() {
        const qs = queryAtual();
        const url = qs ? dadosUrl + "?" + qs : dadosUrl;
        fetch(url, { headers: { Accept: "application/json" } })
            .then(function (resp) {
                if (!resp.ok) throw new Error("Falha ao carregar mapa");
                return resp.json();
            })
            .then(desenhar)
            .catch(function () {
                atualizarKpis({ pontos: [], total_ambulantes: 0, volume_max: 0 });
            });
    }

    function agendarCarregar() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(carregar, 300);
    }

    if (form) {
        form.addEventListener("submit", function (ev) {
            ev.preventDefault();
            carregar();
        });
        form.querySelectorAll("select").forEach(function (sel) {
            sel.addEventListener("change", agendarCarregar);
        });
    }

    const btnFechar = document.getElementById("mapa-painel-fechar");
    if (btnFechar) {
        btnFechar.addEventListener("click", function () {
            fecharPainel();
            setTimeout(function () {
                mapa.invalidateSize();
            }, 220);
        });
    }

    document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape" && painel && !painel.hidden) {
            fecharPainel();
        }
    });

    mapa.on("click", function () {
        // Clique no mapa vazio fecha o painel (demo limpa).
        if (painel && !painel.hidden) fecharPainel();
    });

    carregar();
    window.addEventListener("resize", function () {
        mapa.invalidateSize();
    });
})();
