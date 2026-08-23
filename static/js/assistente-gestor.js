(function () {
    const raiz = document.getElementById("assistente-gestor");
    if (!raiz) return;

    const historico = document.getElementById("assistente-gestor-historico");
    const form = document.getElementById("assistente-gestor-form");
    const campo = document.getElementById("assistente-gestor-pergunta");
    const painelHistorico = document.getElementById("assistente-gestor-historico-panel");
    const listaDocumentos = document.getElementById("assistente-gestor-lista-documentos");
    const listaConversas = document.getElementById("assistente-gestor-lista-conversas");
    const urls = {
        dashboard: raiz.dataset.urlDashboard || "#",
        exportacao: raiz.dataset.urlExportacao || "#",
        ocorrencias: raiz.dataset.urlOcorrencias || "#",
        fila: raiz.dataset.urlFila || "#",
        triagem: raiz.dataset.urlTriagem || "#",
        score: raiz.dataset.urlScore || "#",
        rotas: raiz.dataset.urlRotas || "#",
        rotasResumo: raiz.dataset.urlRotasResumo || "",
    };

    const MAX_PARES = 6;
    const STORAGE_DOCS = "apal_gestor_assistente_docs";
    const STORAGE_CHATS = "apal_gestor_assistente_chats";

    const DOCS_SEED = [
        {
            id: "d1",
            titulo: "Relatório de ocupação e regularização",
            data: "2026-08-15T14:30:00",
            roteiro: "relatorio",
        },
        {
            id: "d2",
            titulo: "Report dos agentes — semana 32",
            data: "2026-08-14T11:05:00",
            roteiro: "agentes",
        },
        {
            id: "d3",
            titulo: "Briefing diário do backoffice",
            data: "2026-08-13T08:15:00",
            roteiro: "briefing",
        },
    ];

    const CHATS_SEED = [
        {
            id: "c1",
            titulo: "Prioridades do dia",
            preview: "O que precisa da minha atenção hoje?",
            data: "2026-08-16T07:42:00",
            roteiro: "briefing",
        },
        {
            id: "c2",
            titulo: "Relatório de ocupação",
            preview: "Monte um relatório de ocupação e regularização",
            data: "2026-08-15T16:20:00",
            roteiro: "relatorio",
        },
        {
            id: "c3",
            titulo: "Autos dos agentes",
            preview: "Resuma os autos lavrados pelos agentes",
            data: "2026-08-14T11:05:00",
            roteiro: "agentes",
        },
    ];

    const BOAS_VINDAS =
        '<div class="assistente-turno assistente-turno-boas-vindas">' +
        '<div class="assistente-balao resposta">' +
        '<span class="assistente-rotulo">Assistente do Gestor</span>' +
        "<p>Olá. Posso montar um briefing do dia, gerar um relatório personalizado, resumir os autos lavrados pelos agentes ou sugerir ações para você autorizar. Escolha uma sugestão ou descreva o que precisa.</p>" +
        "</div></div>";

    const FALLBACK =
        "Posso ajudar com briefing do dia, relatório de ocupação e regularização, resumo dos autos dos agentes, análise de rotas de fiscalização ou ações sugeridas para autorização. Use uma das sugestões acima para ver o que consigo fazer.";

    let cacheRotas = null;

    function buscarResumoRotas() {
        if (!urls.rotasResumo) {
            return Promise.resolve(null);
        }
        if (cacheRotas) {
            return Promise.resolve(cacheRotas);
        }
        return fetch(urls.rotasResumo, { credentials: "same-origin" })
            .then(function (resp) {
                if (!resp.ok) throw new Error("falha");
                return resp.json();
            })
            .then(function (dados) {
                cacheRotas = dados;
                return dados;
            })
            .catch(function () {
                return null;
            });
    }

    function formatarData(iso) {
        const data = new Date(iso);
        if (Number.isNaN(data.getTime())) return "";
        return data.toLocaleString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    function lerLocal(chave) {
        try {
            return JSON.parse(localStorage.getItem(chave) || "[]");
        } catch (_erro) {
            return [];
        }
    }

    function mesclarComSeed(local, seed) {
        const ids = new Set(local.map(function (item) {
            return item.id;
        }));
        const merged = local.slice();
        seed.forEach(function (item) {
            if (!ids.has(item.id)) merged.push(item);
        });
        return merged.sort(function (a, b) {
            return new Date(b.data) - new Date(a.data);
        });
    }

    function lerDocumentos() {
        return mesclarComSeed(lerLocal(STORAGE_DOCS), DOCS_SEED).slice(0, 10);
    }

    function lerConversas() {
        return mesclarComSeed(lerLocal(STORAGE_CHATS), CHATS_SEED).slice(0, 10);
    }

    function registrarDocumento(roteiroKey) {
        const titulos = {
            relatorio: "Relatório de ocupação e regularização",
            agentes: "Report dos agentes — semana atual",
            briefing: "Briefing diário do backoffice",
            rotas: "Análise de rotas de fiscalização",
        };
        const titulo = titulos[roteiroKey];
        if (!titulo) return;

        const local = lerLocal(STORAGE_DOCS);
        const entry = {
            id: "local-doc-" + Date.now(),
            titulo: titulo,
            data: new Date().toISOString(),
            roteiro: roteiroKey,
        };
        localStorage.setItem(
            STORAGE_DOCS,
            JSON.stringify([entry].concat(local).slice(0, 8))
        );
    }

    function registrarConversa(pergunta, roteiroKey) {
        const local = lerLocal(STORAGE_CHATS);
        const titulo = pergunta.length > 48 ? pergunta.slice(0, 48) + "…" : pergunta;
        const entry = {
            id: "local-chat-" + Date.now(),
            titulo: titulo,
            preview: pergunta,
            data: new Date().toISOString(),
            html: historico.innerHTML,
            roteiro: roteiroKey || null,
        };
        const filtrado = local.filter(function (item) {
            return item.preview !== pergunta;
        });
        localStorage.setItem(
            STORAGE_CHATS,
            JSON.stringify([entry].concat(filtrado).slice(0, 8))
        );
    }

    function renderPainelHistorico() {
        if (!listaDocumentos || !listaConversas) return;

        const documentos = lerDocumentos();
        const conversas = lerConversas();

        listaDocumentos.innerHTML = documentos.length
            ? documentos
                  .map(function (item) {
                      return (
                          '<li><button type="button" class="assistente-historico-item" data-tipo="documento" data-roteiro="' +
                          escapar(item.roteiro || "") +
                          '"><strong>' +
                          escapar(item.titulo) +
                          "</strong><small>" +
                          escapar(formatarData(item.data)) +
                          '</small><span>Abrir no chat</span></button></li>'
                      );
                  })
                  .join("")
            : '<li><p class="assistente-historico-vazio">Nenhum documento gerado ainda.</p></li>';

        listaConversas.innerHTML = conversas.length
            ? conversas
                  .map(function (item) {
                      return (
                          '<li><button type="button" class="assistente-historico-item" data-tipo="conversa" data-id="' +
                          escapar(item.id) +
                          '"><strong>' +
                          escapar(item.titulo) +
                          "</strong><small>" +
                          escapar(formatarData(item.data)) +
                          "</small><span>" +
                          escapar(item.preview) +
                          "</span></button></li>"
                      );
                  })
                  .join("")
            : '<li><p class="assistente-historico-vazio">Nenhuma conversa recente.</p></li>';
    }

    function abrirPainelHistorico() {
        if (!painelHistorico) return;
        painelHistorico.classList.remove("hidden");
        painelHistorico.setAttribute("aria-hidden", "false");
        renderPainelHistorico();
        renovarIcones();
    }

    function fecharPainelHistorico() {
        if (!painelHistorico) return;
        painelHistorico.classList.add("hidden");
        painelHistorico.setAttribute("aria-hidden", "true");
    }

    function alternarPainelHistorico() {
        if (!painelHistorico) return;
        if (painelHistorico.classList.contains("hidden")) {
            abrirPainelHistorico();
        } else {
            fecharPainelHistorico();
        }
    }

    function restaurarRoteiro(roteiroKey) {
        const roteiro = ROTEIROS[roteiroKey];
        if (!roteiro) return;
        historico.innerHTML = BOAS_VINDAS;
        anexarTurno(roteiro.pergunta, roteiro.html(), roteiroKey, true);
    }

    function abrirDocumento(roteiroKey) {
        fecharPainelHistorico();
        restaurarRoteiro(roteiroKey);
    }

    function abrirConversa(conversaId) {
        fecharPainelHistorico();
        const conversas = lerConversas();
        const item = conversas.find(function (conversa) {
            return conversa.id === conversaId;
        });
        if (!item) return;

        if (item.html) {
            historico.innerHTML = item.html;
            rolarHistorico();
            renovarIcones();
            return;
        }

        if (item.roteiro) {
            restaurarRoteiro(item.roteiro);
        }
    }

    function escapar(texto) {
        return String(texto)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function htmlPergunta(texto) {
        return (
            '<div class="assistente-turno">' +
            '<div class="assistente-balao pergunta">' +
            '<span class="assistente-rotulo">Você</span>' +
            "<p>" +
            escapar(texto) +
            "</p>" +
            "</div>" +
            "</div>"
        );
    }

    function htmlResposta(corpoHtml) {
        return (
            '<div class="assistente-turno">' +
            '<div class="assistente-balao resposta assistente-balao-rico">' +
            '<span class="assistente-rotulo">Assistente do Gestor</span>' +
            corpoHtml +
            "</div>" +
            "</div>"
        );
    }

    function htmlPensando() {
        return (
            '<div class="assistente-turno assistente-turno-pensando" id="assistente-gestor-pensando">' +
            '<div class="assistente-balao resposta assistente-balao-pensando">' +
            '<span class="assistente-rotulo">Assistente do Gestor</span>' +
            '<div class="assistente-pensando" role="status" aria-live="polite" aria-label="Assistente pensando">' +
            "<span></span><span></span><span></span>" +
            "</div></div></div>"
        );
    }

    function htmlBriefing() {
        return (
            "<p>Priorizei o que mais impacta o fluxo hoje. Há processos parados na fila, documentos aguardando triagem e autos dos agentes sem auditoria.</p>" +
            '<div class="assistente-kpi-grid">' +
            '<div class="assistente-kpi"><strong>5</strong><span>Na fila de análise</span></div>' +
            '<div class="assistente-kpi"><strong>3</strong><span>Docs pendentes</span></div>' +
            '<div class="assistente-kpi"><strong>4</strong><span>Autos sem auditoria</span></div>' +
            '<div class="assistente-kpi"><strong>2</strong><span>Licenças a vencer (30 dias)</span></div>' +
            "</div>" +
            "<p>Recomendo começar pelos autos sem auditoria e pela fila com mais de 5 dias.</p>"
        );
    }

    function htmlRelatorio() {
        return (
            "<p>Montei um relatório personalizado de ocupação e regularização para o período atual.</p>" +
            '<div class="assistente-report-card">' +
            '<div class="assistente-report-header">' +
            "<div>" +
            "<h3>Relatório de ocupação e regularização</h3>" +
            "<small>Período: 01/08/2026 a 16/08/2026 · Gerado pelo Assistente</small>" +
            "</div>" +
            "</div>" +
            '<div class="assistente-kpi-grid">' +
            '<div class="assistente-kpi"><strong>128</strong><span>Ambulantes ativos</span></div>' +
            '<div class="assistente-kpi"><strong>86%</strong><span>Pontos ocupados</span></div>' +
            '<div class="assistente-kpi"><strong>41</strong><span>Licenças emitidas no mês</span></div>' +
            '<div class="assistente-kpi"><strong>12</strong><span>Em análise</span></div>' +
            "</div>" +
            '<div class="table-responsive">' +
            '<table class="data-table assistente-mini-table">' +
            "<thead><tr><th>Indicador</th><th>Valor</th><th>Variação</th></tr></thead>" +
            "<tbody>" +
            "<tr><td>Regularização (fixo)</td><td>74</td><td>+6%</td></tr>" +
            "<tr><td>Regularização (móvel)</td><td>54</td><td>+3%</td></tr>" +
            "<tr><td>Vagas livres</td><td>18</td><td>−2</td></tr>" +
            "<tr><td>Ocorrências no período</td><td>9</td><td>+1</td></tr>" +
            "</tbody></table></div>" +
            '<div class="assistente-card-actions">' +
            '<button type="button" class="btn-submit assistente-btn-print">' +
            '<i data-lucide="printer" aria-hidden="true"></i> Imprimir' +
            "</button>" +
            '<a class="btn-action" href="' +
            escapar(urls.dashboard) +
            '"><i data-lucide="bar-chart-3" aria-hidden="true"></i> Ver dashboard</a>' +
            '<a class="btn-action" href="' +
            escapar(urls.exportacao) +
            '"><i data-lucide="download" aria-hidden="true"></i> Exportar CSV</a>' +
            "</div></div>"
        );
    }

    function htmlAgentes() {
        return (
            "<p>Resumo dos autos lavrados pelos agentes de campo na última semana. Quatro registros ainda aguardam a sua auditoria.</p>" +
            '<div class="assistente-report-card">' +
            '<div class="assistente-report-header"><div><h3>Report dos agentes</h3><small>Últimos 7 dias · Autos de fiscalização</small></div></div>' +
            '<div class="table-responsive">' +
            '<table class="data-table assistente-mini-table">' +
            "<thead><tr><th>Fiscal</th><th>Tipo de auto</th><th>Qtd.</th><th>Status</th></tr></thead>" +
            "<tbody>" +
            "<tr><td>Ana Ferreira</td><td>Irregularidade de horário</td><td>3</td><td>Pendente</td></tr>" +
            "<tr><td>Ana Ferreira</td><td>Falta de credencial</td><td>1</td><td>Em análise</td></tr>" +
            "<tr><td>Carlos Souza</td><td>Advertência</td><td>2</td><td>Procedente</td></tr>" +
            "<tr><td>Carlos Souza</td><td>Irregularidade de ponto</td><td>2</td><td>Pendente</td></tr>" +
            "<tr><td>Juliana Reis</td><td>Comércio sem licença</td><td>1</td><td>Pendente</td></tr>" +
            "</tbody></table></div>" +
            '<div class="assistente-card-actions">' +
            '<a class="btn-submit" href="' +
            escapar(urls.ocorrencias) +
            '"><i data-lucide="clipboard-list" aria-hidden="true"></i> Abrir ocorrências</a>' +
            '<a class="btn-action" href="' +
            escapar(urls.rotas) +
            '"><i data-lucide="route" aria-hidden="true"></i> Ver rotas</a>' +
            "</div></div>"
        );
    }

    function htmlRotas(dados) {
        const d = dados || {};
        const pontos = (d.pontos_sem_ambulante || []).slice(0, 4);
        const listaPontos = pontos.length
            ? "<p>Pontos sem ambulante encontrado: <strong>" +
              escapar(pontos.join(", ")) +
              "</strong>.</p>"
            : "<p>Nenhuma ausência de ambulante destacada nas rotas recentes.</p>";
        const linhas = (d.rotas || [])
            .slice(0, 5)
            .map(function (r) {
                return (
                    "<tr><td>" +
                    escapar(r.titulo || "") +
                    "</td><td>" +
                    escapar(r.fiscal || "") +
                    "</td><td>" +
                    escapar(String(r.paradas_concluidas || 0)) +
                    "/" +
                    escapar(String(r.total_paradas || 0)) +
                    "</td><td>" +
                    escapar(r.status_display || r.status || "") +
                    "</td></tr>"
                );
            })
            .join("");
        return (
            "<p>Analisei as rotas de fiscalização concluídas ou incompletas. Use os números abaixo para decidir reforço de campo ou revisão de pontos.</p>" +
            '<div class="assistente-kpi-grid">' +
            '<div class="assistente-kpi"><strong>' +
            escapar(String(d.concluidas_hoje || 0)) +
            "</strong><span>Encerradas hoje</span></div>" +
            '<div class="assistente-kpi"><strong>' +
            escapar(String(d.em_andamento || 0)) +
            "</strong><span>Em andamento</span></div>" +
            '<div class="assistente-kpi"><strong>' +
            escapar(String(d.sem_ambulante || 0)) +
            "</strong><span>Sem ambulante</span></div>" +
            '<div class="assistente-kpi"><strong>' +
            escapar(String(d.ocorrencias_em_rotas || 0)) +
            "</strong><span>Ocorrências nas rotas</span></div>" +
            "</div>" +
            listaPontos +
            '<div class="assistente-report-card">' +
            '<div class="assistente-report-header"><div><h3>Rotas recentes</h3><small>Dados do sistema · protótipo</small></div></div>' +
            '<div class="table-responsive">' +
            '<table class="data-table assistente-mini-table">' +
            "<thead><tr><th>Rota</th><th>Fiscal</th><th>Paradas</th><th>Status</th></tr></thead>" +
            "<tbody>" +
            (linhas ||
                '<tr><td colspan="4">Nenhuma rota encerrada ainda. Crie e execute uma rota para ver o resumo aqui.</td></tr>') +
            "</tbody></table></div>" +
            '<div class="assistente-card-actions">' +
            '<a class="btn-submit" href="' +
            escapar(urls.rotas) +
            '"><i data-lucide="route" aria-hidden="true"></i> Abrir rotas</a>' +
            '<a class="btn-action" href="' +
            escapar(urls.ocorrencias) +
            '"><i data-lucide="clipboard-list" aria-hidden="true"></i> Ocorrências</a>' +
            "</div></div>"
        );
    }

    function htmlAcoes() {
        return (
            "<p>Com base na fila, nos autos pendentes e nas rotas de campo, estas são as ações que recomendo. Nenhuma é executada sem a sua autorização prévia.</p>" +
            '<div class="assistente-acoes-lista">' +
            cardAcao(
                "auditar-autos",
                "Priorizar autos sem auditoria",
                "4 ocorrências com status Pendente. Abrir a lista de ocorrências para auditar.",
                urls.ocorrencias,
                "Abrir ocorrências"
            ) +
            cardAcao(
                "abrir-fila",
                "Abrir a fila mais antiga",
                "Há 5 requerimentos em análise; 2 com mais de 5 dias. Revisar a fila de parecer.",
                urls.fila,
                "Abrir fila"
            ) +
            cardAcao(
                "analisar-rotas",
                "Revisar rotas de fiscalização",
                "Conferir paradas sem ambulante e rotas incompletas antes de reatribuir o fiscal.",
                urls.rotas,
                "Abrir rotas"
            ) +
            cardAcao(
                "rodar-score",
                "Rodar recuperação mensal de score",
                "Processar +2 pontos para ambulantes elegíveis no período configurado.",
                urls.score,
                "Ir ao processamento"
            ) +
            "</div>"
        );
    }

    function cardAcao(id, titulo, descricao, href, rotuloLink) {
        return (
            '<div class="assistente-acao-card" data-acao-id="' +
            escapar(id) +
            '" data-status="proposta">' +
            "<h4>" +
            escapar(titulo) +
            "</h4>" +
            "<p>" +
            escapar(descricao) +
            "</p>" +
            '<div class="assistente-card-actions">' +
            '<button type="button" class="btn-submit assistente-acao-autorizar">Autorizar</button>' +
            '<button type="button" class="btn-action assistente-acao-recusar">Recusar</button>' +
            '<a class="btn-action assistente-acao-destino" href="' +
            escapar(href) +
            '" hidden>' +
            escapar(rotuloLink) +
            "</a>" +
            "</div>" +
            '<p class="assistente-acao-status" hidden></p>' +
            "</div>"
        );
    }

    const ROTEIROS = {
        briefing: {
            pergunta: "O que precisa da minha atenção hoje?",
            html: htmlBriefing,
        },
        relatorio: {
            pergunta: "Monte um relatório de ocupação e regularização",
            html: htmlRelatorio,
        },
        agentes: {
            pergunta: "Resuma os autos lavrados pelos agentes",
            html: htmlAgentes,
        },
        rotas: {
            pergunta: "Analisar rotas de fiscalização concluídas",
            html: htmlRotas,
            async: true,
        },
        acoes: {
            pergunta: "O que você recomenda que eu autorize agora?",
            html: htmlAcoes,
        },
    };

    let pensando = false;

    const DELAY_PENSAMENTO = {
        briefing: 1400,
        relatorio: 2400,
        agentes: 1900,
        rotas: 1800,
        acoes: 1700,
        fallback: 1200,
        default: 1500,
    };

    function renovarIcones() {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            window.lucide.createIcons();
        }
    }

    function rolarHistorico() {
        historico.scrollTop = historico.scrollHeight;
    }

    function podarHistorico() {
        while (historico.children.length > 1 + MAX_PARES * 2) {
            historico.removeChild(historico.children[1]);
        }
    }

    function limparConversa() {
        if (pensando) return;
        if (
            historico.children.length > 1 &&
            !window.confirm("Limpar todo o histórico desta conversa?")
        ) {
            return;
        }
        historico.innerHTML = BOAS_VINDAS;
        rolarHistorico();
        renovarIcones();
        if (typeof window.mostrarToast === "function") {
            window.mostrarToast("Conversa reiniciada.", "info");
        }
    }

    function aguardarPensamento(roteiroKey, ehFallback) {
        const chave = ehFallback ? "fallback" : roteiroKey || "default";
        const ms = DELAY_PENSAMENTO[chave] || DELAY_PENSAMENTO.default;
        return new Promise(function (resolve) {
            window.setTimeout(resolve, ms);
        });
    }

    function mostrarPensando() {
        historico.insertAdjacentHTML("beforeend", htmlPensando());
        rolarHistorico();
    }

    function removerPensando() {
        const indicador = document.getElementById("assistente-gestor-pensando");
        if (indicador) indicador.remove();
    }

    function definirInterfaceBloqueada(bloqueada) {
        pensando = bloqueada;
        if (campo) campo.disabled = bloqueada;
        const btnEnviar = form ? form.querySelector(".assistente-composer-enviar") : null;
        if (btnEnviar) btnEnviar.disabled = bloqueada;
        raiz.querySelectorAll(".assistente-sugestao").forEach(function (botao) {
            botao.disabled = bloqueada;
        });
    }

    function finalizarTurno(pergunta, corpoHtml, roteiroKey, silenciarHistorico) {
        historico.insertAdjacentHTML("beforeend", htmlResposta(corpoHtml));
        podarHistorico();
        renovarIcones();
        rolarHistorico();
        if (!silenciarHistorico) {
            registrarConversa(pergunta, roteiroKey);
            if (roteiroKey === "relatorio" || roteiroKey === "agentes" || roteiroKey === "briefing" || roteiroKey === "rotas") {
                registrarDocumento(roteiroKey);
            }
        }
    }

    function anexarTurno(pergunta, corpoHtml, roteiroKey, silenciarHistorico) {
        if (pensando) return;

        if (!silenciarHistorico) {
            definirInterfaceBloqueada(true);
        }

        historico.insertAdjacentHTML("beforeend", htmlPergunta(pergunta));
        rolarHistorico();

        if (silenciarHistorico) {
            finalizarTurno(pergunta, corpoHtml, roteiroKey, true);
            return;
        }

        const ehFallback = !roteiroKey;
        mostrarPensando();

        aguardarPensamento(roteiroKey, ehFallback).then(function () {
            removerPensando();
            finalizarTurno(pergunta, corpoHtml, roteiroKey, false);
            definirInterfaceBloqueada(false);
        });
    }

    function resolverRoteiroPorTexto(texto) {
        const normalizado = texto
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");

        if (normalizado.includes("rota") || normalizado.includes("parada") || normalizado.includes("ronda")) {
            return "rotas";
        }
        if (normalizado.includes("atencao") || normalizado.includes("briefing") || normalizado.includes("hoje")) {
            return "briefing";
        }
        if (normalizado.includes("relatorio") || normalizado.includes("ocupacao") || normalizado.includes("regularizacao")) {
            return "relatorio";
        }
        if (normalizado.includes("auto") || normalizado.includes("agente") || normalizado.includes("ocorrenc")) {
            return "agentes";
        }
        if (normalizado.includes("autoriz") || normalizado.includes("recomenda") || normalizado.includes("acao") || normalizado.includes("ações") || normalizado.includes("acoes")) {
            return "acoes";
        }
        return null;
    }

    function corpoDoRoteiro(chave) {
        const roteiro = ROTEIROS[chave];
        if (!roteiro) return Promise.resolve(null);
        if (roteiro.async) {
            return buscarResumoRotas().then(function (dados) {
                return roteiro.html(dados);
            });
        }
        return Promise.resolve(roteiro.html());
    }

    function enviarRoteiro(chave) {
        const roteiro = ROTEIROS[chave];
        if (!roteiro) return;
        corpoDoRoteiro(chave).then(function (html) {
            anexarTurno(roteiro.pergunta, html, chave);
        });
    }

    function enviarTextoLivre(texto) {
        const chave = resolverRoteiroPorTexto(texto);
        if (chave) {
            corpoDoRoteiro(chave).then(function (html) {
                anexarTurno(texto, html, chave);
            });
            return;
        }
        anexarTurno(texto, "<p>" + escapar(FALLBACK) + "</p>", null);
    }

    function enviarMensagem() {
        if (pensando) return;
        const texto = (campo.value || "").trim();
        if (!texto) return;
        enviarTextoLivre(texto);
        campo.value = "";
    }

    raiz.querySelectorAll("[data-roteiro]").forEach(function (botao) {
        botao.addEventListener("click", function () {
            enviarRoteiro(botao.getAttribute("data-roteiro"));
        });
    });

    const btnLimpar = document.getElementById("assistente-gestor-limpar");
    if (btnLimpar) {
        btnLimpar.addEventListener("click", limparConversa);
    }

    const btnHistorico = document.getElementById("assistente-gestor-historico-btn");
    if (btnHistorico) {
        btnHistorico.addEventListener("click", alternarPainelHistorico);
    }

    const btnFecharHistorico = document.getElementById("assistente-gestor-historico-fechar");
    if (btnFecharHistorico) {
        btnFecharHistorico.addEventListener("click", fecharPainelHistorico);
    }

    if (painelHistorico) {
        painelHistorico.addEventListener("click", function (evento) {
            const item = evento.target.closest(".assistente-historico-item");
            if (!item) return;

            const tipo = item.getAttribute("data-tipo");
            if (tipo === "documento") {
                abrirDocumento(item.getAttribute("data-roteiro"));
                return;
            }
            if (tipo === "conversa") {
                abrirConversa(item.getAttribute("data-id"));
            }
        });
    }

    if (form) {
        form.addEventListener("submit", function (evento) {
            evento.preventDefault();
        });

        const btnEnviar = document.getElementById("assistente-gestor-enviar");
        if (btnEnviar) {
            btnEnviar.addEventListener("click", enviarMensagem);
        }

        if (campo) {
            campo.addEventListener("keydown", function (evento) {
                if (evento.key !== "Enter" || evento.shiftKey) return;
                evento.preventDefault();
                enviarMensagem();
            });
        }
    }

    historico.addEventListener("click", function (evento) {
        const printBtn = evento.target.closest(".assistente-btn-print");
        if (printBtn) {
            evento.preventDefault();
            const alvo = printBtn.closest(".assistente-report-card");
            if (!alvo) return;
            raiz.classList.add("assistente-imprimindo");
            alvo.classList.add("assistente-print-alvo");
            window.print();
            window.setTimeout(function () {
                raiz.classList.remove("assistente-imprimindo");
                alvo.classList.remove("assistente-print-alvo");
            }, 300);
            return;
        }

        const card = evento.target.closest(".assistente-acao-card");
        if (!card || card.dataset.status !== "proposta") return;

        const autorizar = evento.target.closest(".assistente-acao-autorizar");
        const recusar = evento.target.closest(".assistente-acao-recusar");
        if (!autorizar && !recusar) return;

        const statusEl = card.querySelector(".assistente-acao-status");
        const destino = card.querySelector(".assistente-acao-destino");
        const botoes = card.querySelectorAll(".assistente-acao-autorizar, .assistente-acao-recusar");

        botoes.forEach(function (b) {
            b.disabled = true;
            b.hidden = true;
        });

        if (autorizar) {
            card.dataset.status = "autorizada";
            card.classList.add("is-autorizada");
            if (statusEl) {
                statusEl.hidden = false;
                statusEl.textContent = "Autorizada. Na versão completa, o sistema executaria após a sua permissão.";
            }
            if (destino) destino.hidden = false;
            if (typeof window.mostrarToast === "function") {
                window.mostrarToast(
                    "Na versão completa, o sistema executaria após a sua permissão.",
                    "success",
                    "Ação autorizada"
                );
            }
            return;
        }

        card.dataset.status = "recusada";
        card.classList.add("is-recusada");
        if (statusEl) {
            statusEl.hidden = false;
            statusEl.textContent = "Recusada. Nenhuma alteração foi aplicada.";
        }
        if (typeof window.mostrarToast === "function") {
            window.mostrarToast("Nenhuma alteração foi aplicada.", "info", "Ação recusada");
        }
    });
})();
