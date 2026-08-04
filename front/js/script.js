// =========================================
// PONTO LEGAL VCA - SCRIPT GLOBAL E ACESSIBILIDADE
// =========================================

const GEMINI_API_KEY = "AQ.Ab8RN6KUJwsSIEy_0dwFEqI6hAyjocrkx2k15LrKi6ZwAOgzsQ";
const GROQ_API_KEY = "COLE_AQUI_SUA_NOVA_CHAVE_GROQ"; // Troque pela sua chave do Groq se for utilizar

document.addEventListener('DOMContentLoaded', () => {

    // -----------------------------------------
    // 1. WIDGET E PAINEL DE ACESSIBILIDADE
    // -----------------------------------------
    const openBtn = document.getElementById('open-access-float');
    const closeBtn = document.getElementById('close-access');
    const accessPanel = document.getElementById('accessibility-panel');

    if (openBtn && accessPanel) {
        openBtn.addEventListener('mouseenter', () => openBtn.classList.add('expanded'));
        openBtn.addEventListener('mouseleave', () => {
            if (accessPanel.classList.contains('hidden')) {
                openBtn.classList.remove('expanded');
            }
        });

        openBtn.addEventListener('click', () => {
            accessPanel.classList.toggle('hidden');
            openBtn.classList.add('expanded');
        });

        closeBtn?.addEventListener('click', () => {
            accessPanel.classList.add('hidden');
            openBtn.classList.remove('expanded');
        });
    }

    // -----------------------------------------
    // 2. FERRAMENTAS VISUAIS
    // -----------------------------------------
    const btnAumentar = document.getElementById('btn-aumentar');
    const btnDiminuir = document.getElementById('btn-diminuir');
    const btnEscuro = document.getElementById('btn-escuro');
    const btnClaro = document.getElementById('btn-claro');
    const btnSatAlta = document.getElementById('btn-sat-alta');
    const btnSatBaixa = document.getElementById('btn-sat-baixa');
    const btnZoom = document.getElementById('btn-zoom');

    btnAumentar?.addEventListener('click', () => {
        const currentSize = parseFloat(window.getComputedStyle(document.body).fontSize);
        document.body.style.fontSize = (currentSize + 2) + 'px';
    });

    btnDiminuir?.addEventListener('click', () => {
        const currentSize = parseFloat(window.getComputedStyle(document.body).fontSize);
        if (currentSize > 10) {
            document.body.style.fontSize = (currentSize - 2) + 'px';
        }
    });

    btnEscuro?.addEventListener('click', () => {
        document.body.classList.remove('tema-claro');
        document.body.classList.toggle('tema-escuro');
    });

    btnClaro?.addEventListener('click', () => {
        document.body.classList.remove('tema-escuro');
        document.body.classList.toggle('tema-claro');
    });

    btnSatAlta?.addEventListener('click', () => {
        document.body.classList.remove('sat-baixa');
        document.body.classList.toggle('sat-alta');
    });

    btnSatBaixa?.addEventListener('click', () => {
        document.body.classList.remove('sat-alta');
        document.body.classList.toggle('sat-baixa');
    });

    btnZoom?.addEventListener('click', () => {
        document.body.classList.toggle('zoom-ativo');
    });

    // -----------------------------------------
    // 3. LEITOR DE VOZ NATIVO
    // -----------------------------------------
    const btnLerTexto = document.getElementById('btn-ler-texto');
    const btnLerClique = document.getElementById('btn-ler-clique');
    const btnPararLeitura = document.getElementById('btn-parar-leitura');

    let leituraSelectionModeAtivo = false;
    let idFalaAtual = 0; 

    function limparEstiloBotaoLeitura() {
        if (btnLerTexto) {
            btnLerTexto.style.backgroundColor = '';
            btnLerTexto.style.borderColor = '';
        }
    }

    function falarTextoAcessivel(textoParaFalar) {
        if (!('speechSynthesis' in window)) return;

        idFalaAtual++;
        const idDestaFala = idFalaAtual;

        window.speechSynthesis.cancel();

        const textoLimpo = textoParaFalar
            .replace(/\*\*/g, '')
            .replace(/\*/g, '')
            .replace(/#/g, '')
            .replace(/-/g, '')
            .trim();

        if (!textoLimpo) return;

        setTimeout(() => {
            if (idDestaFala !== idFalaAtual) return;
            const mensagem = new SpeechSynthesisUtterance(textoLimpo);
            mensagem.lang = 'pt-BR';
            mensagem.rate = 1.0;
            window.speechSynthesis.speak(mensagem);
        }, 60);
    }

    function pararFalaCompletamente() {
        idFalaAtual++; 
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    }

    if (btnLerTexto) {
        btnLerTexto.addEventListener('click', () => {
            if (!('speechSynthesis' in window)) {
                alert('Seu navegador não suporta a leitura de voz nativa.');
                return;
            }

            if (window.speechSynthesis.speaking) {
                pararFalaCompletamente();
                limparEstiloBotaoLeitura();
                return;
            }

            const textoSelecionado = window.getSelection().toString().trim();
            const textoPrincipal = document.querySelector('main')?.innerText;
            const textoParaLer = textoSelecionado || textoPrincipal || document.body.innerText;
            falarTextoAcessivel(textoParaLer);
        });
    }

    if (btnLerClique) {
        btnLerClique.addEventListener('click', () => {
            if (!('speechSynthesis' in window)) {
                alert('Seu navegador não suporta a leitura de voz nativa.');
                return;
            }

            if (leituraSelectionModeAtivo) {
                desativarModoLeituraPorClique();
                return;
            }

            leituraSelectionModeAtivo = true;
            accessPanel?.classList.add('hidden');
            document.body.classList.add('leitura-select-mode');
            btnLerClique.classList.add('access-option-ativo');

            alert("Modo Leitura por Clique Ativado!\n\nClique em quantos parágrafos ou trechos quiser, cada clique vai ler aquele trecho.\n\nPara sair do modo, clique novamente neste botão ou aperte ESC.");
        });
    }

    function desativarModoLeituraPorClique() {
        leituraSelectionModeAtivo = false;
        document.body.classList.remove('leitura-select-mode');
        btnLerClique?.classList.remove('access-option-ativo');
    }

    if (btnPararLeitura) {
        btnPararLeitura.addEventListener('click', () => {
            pararFalaCompletamente();
            limparEstiloBotaoLeitura();
            desativarModoLeituraPorClique();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && leituraSelectionModeAtivo) {
            pararFalaCompletamente();
            desativarModoLeituraPorClique();
        }
    });

    // INTERCEPTADOR DE CLIQUE - LEITURA
    document.addEventListener('click', (e) => {
        if (!leituraSelectionModeAtivo) return;

        if (e.target.closest('#access-widget-container') || 
            e.target.closest('#accessibility-panel') || 
            e.target.closest('#ai-modal')) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        const textoClicado = (e.target.innerText || e.target.textContent || '').trim();

        if (textoClicado) {
            falarTextoAcessivel(textoClicado);
        }
    }, true);

    // -----------------------------------------
    // 4. INTEGRAÇÃO IA COM MODO "CLIQUE PARA SELECIONAR"
    // -----------------------------------------
    const btnSimplificarIA = document.getElementById('btn-simplificar-ia');
    const btnSignificadoIA = document.getElementById('btn-significado-ia');
    const aiModal = document.getElementById('ai-modal');
    const closeAiModal = document.getElementById('close-ai-modal');
    const aiResponseContent = document.getElementById('ai-response-content');

    let iaSelectionModeAtivo = false;
    let promptAtualIA = "";
    let modoAtualIA = ""; 

    function ativarModoSelecao(promptInstrucao, modo) {
        iaSelectionModeAtivo = true;
        promptAtualIA = promptInstrucao;
        modoAtualIA = modo;

        accessPanel?.classList.add('hidden');
        document.body.classList.add('ia-select-mode');

        if (modo === "significado") {
            alert("Modo IA Ativado!\n\nAgora, apenas CLIQUE em cima da palavra que você deseja saber o significado.");
        } else {
            alert("Modo IA Ativado!\n\nAgora, apenas CLIQUE no texto/parágrafo que você deseja simplificar.");
        }
    }

    function desativarModoSelecao() {
        iaSelectionModeAtivo = false;
        promptAtualIA = "";
        modoAtualIA = "";
        document.body.classList.remove('ia-select-mode');
    }

    function obterPalavraClicada(x, y) {
        let range;

        if (document.caretRangeFromPoint) {
            range = document.caretRangeFromPoint(x, y);
        } else if (document.caretPositionFromPoint) {
            const pos = document.caretPositionFromPoint(x, y);
            if (pos) {
                range = document.createRange();
                range.setStart(pos.offsetNode, pos.offset);
                range.setEnd(pos.offsetNode, pos.offset);
            }
        }

        if (!range || !range.startContainer || range.startContainer.nodeType !== Node.TEXT_NODE) {
            return null;
        }

        const texto = range.startContainer.textContent;
        let start = range.startOffset;
        let end = range.startOffset;

        while (start > 0 && /\S/.test(texto[start - 1])) start--;
        while (end < texto.length && /\S/.test(texto[end])) end++;

        return texto.slice(start, end).replace(/[.,;:!?()"'“”]/g, '').trim();
    }

    // INTERCEPTADOR DE CLIQUE - IA
    document.addEventListener('click', (e) => {
        if (!iaSelectionModeAtivo) return;

        if (e.target.closest('#access-widget-container') || 
            e.target.closest('#accessibility-panel') || 
            e.target.closest('#ai-modal')) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        let textoExtraido;

        if (modoAtualIA === "significado") {
            textoExtraido = obterPalavraClicada(e.clientX, e.clientY);
            if (!textoExtraido) {
                textoExtraido = (e.target.innerText || e.target.textContent || '').trim();
            }
        } else {
            textoExtraido = e.target.innerText || e.target.textContent;
        }

        desativarModoSelecao();

        if (textoExtraido && textoExtraido.trim().length > 0) {
            chamarIA(promptAtualIA, textoExtraido.trim());
        }
    }, true);

    closeAiModal?.addEventListener('click', () => {
        aiModal?.classList.add('hidden');
    });

    function formatarTextoIA(texto) {
        let html = texto
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        return `<div class="ai-card-body"><p>${html}</p></div>`;
    }

    function montarInstrucaoSistema(promptInstrucao) {
        return `${promptInstrucao} Responda apenas com o conteúdo pedido, em texto puro, sem markdown, sem saudação, sem introdução, sem perguntas de volta, sem oferecer ajuda adicional, sem repetir o termo recebido, e nunca responda apenas com um sinônimo ou uma tradução isolada.`;
    }

    async function chamarGemini(promptInstrucao, textoSelecionado) {
        const response = await fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-goog-api-key': GEMINI_API_KEY
            },
            body: JSON.stringify({
                systemInstruction: {
                    parts: [{ text: montarInstrucaoSistema(promptInstrucao) }]
                },
                contents: [{
                    parts: [{ text: textoSelecionado }]
                }],
                generationConfig: {
                    temperature: 0,
                    maxOutputTokens: 120
                }
            })
        });

        const data = await response.json();

        if (data.candidates && data.candidates[0]?.content?.parts[0]?.text) {
            return data.candidates[0].content.parts[0].text;
        }

        if (data.error) {
            throw new Error(`Google Gemini falhou: ${data.error.message}`);
        }

        throw new Error('Resposta vazia do Gemini');
    }

    async function chamarGroq(promptInstrucao, textoSelecionado) {
        if (GROQ_API_KEY.includes("COLE_AQUI")) {
            throw new Error("Chave do Groq não configurada no código.");
        }

        const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${GROQ_API_KEY}`
            },
            body: JSON.stringify({
                model: 'llama-3.3-70b-versatile',
                temperature: 0,
                max_tokens: 120,
                messages: [
                    { role: 'system', content: montarInstrucaoSistema(promptInstrucao) },
                    { role: 'user', content: textoSelecionado }
                ]
            })
        });

        const data = await response.json();

        if (data.choices && data.choices[0]?.message?.content) {
            return data.choices[0].message.content;
        }

        if (data.error) {
            throw new Error(`Groq falhou: ${data.error.message}`);
        }

        throw new Error('Resposta vazia do Groq');
    }

    async function chamarIA(promptInstrucao, textoSelecionado) {
        if (!aiModal || !aiResponseContent) return;

        aiModal.classList.remove('hidden');
        aiResponseContent.innerHTML = '<p style="color: var(--texto-cinza);">Processando, aguarde...</p>';

        try {
            let respostaIA;
            try {
                respostaIA = await chamarGemini(promptInstrucao, textoSelecionado);
            } catch (erroGemini) {
                console.warn('Gemini falhou, tentando Groq como fallback...', erroGemini);
                respostaIA = await chamarGroq(promptInstrucao, textoSelecionado);
            }

            aiResponseContent.innerHTML = formatarTextoIA(respostaIA);
            
        } catch (error) {
            console.error('Erro detalhado da API:', error);
            
            let mensagemVisual = "Falha na conexão com o serviço de acessibilidade.";
            const msgErro = error.message.toLowerCase();
            
            if (msgErro.includes("api key") || msgErro.includes("não configurada") || msgErro.includes("unauthorized")) {
                mensagemVisual = "<strong>Erro de Configuração:</strong> As chaves da Inteligência Artificial estão inválidas ou ausentes no sistema.";
            } else if (msgErro.includes("quota") || msgErro.includes("429")) {
                mensagemVisual = "<strong>Limite Atingido:</strong> O limite de uso da Inteligência Artificial esgotou. Tente novamente mais tarde.";
            } else {
                mensagemVisual = `<strong>Erro Técnico:</strong> ${error.message}`;
            }

            aiResponseContent.innerHTML = `<div class="ai-card-body"><p style="color: #DC2626;">${mensagemVisual}</p></div>`;
        }
    }

    btnSimplificarIA?.addEventListener('click', () => {
        const prompt = "Reescreva o texto a seguir usando palavras extremamente simples, mantendo o sentido original.";
        ativarModoSelecao(prompt, "simplificar");
    });

    btnSignificadoIA?.addEventListener('click', () => {
        const prompt = "Explique o termo a seguir como se estivesse explicando para alguém que nunca ouviu essa palavra e tem dificuldade de entendimento. Não dê apenas um sinônimo ou uma tradução, explique o que ele significa e, se fizer sentido, dê um exemplo curto de uso. Use no máximo 2 a 3 frases simples.";
        ativarModoSelecao(prompt, "significado");
    });

    // -----------------------------------------
    // 5. ACCORDION DO FAQ (EXPANDIR/RECOLHER RESPOSTAS)
    // -----------------------------------------
    const faqQuestions = document.querySelectorAll('.faq-question');

    faqQuestions.forEach(question => {
        question.addEventListener('click', () => {
            const faqItem = question.parentElement;

            // Fecha as outras perguntas abertas para manter o layout limpo
            document.querySelectorAll('.faq-item').forEach(item => {
                if (item !== faqItem) {
                    item.classList.remove('active');
                }
            });

            // Alterna o estado (aberto/fechado) da pergunta clicada
            faqItem.classList.toggle('active');
        });
    });

});