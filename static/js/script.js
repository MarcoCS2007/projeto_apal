// ===================================================
// APAL - SCRIPT GLOBAL E ACESSIBILIDADE
// ===================================================

const GEMINI_API_KEY = "AQ.Ab8RN6IbFNK35QDYzePUpmP14T9Geg6NmoeGVu0TqesmaAYEsQ";
const GROQ_API_KEY = "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";

document.addEventListener('DOMContentLoaded', () => {

    // ---------------------------------------------------
    // 1. WIDGET, BACKDROP E PAINEL DE ACESSIBILIDADE
    // ---------------------------------------------------
    const openBtn = document.getElementById('open-access-float');
    const closeBtn = document.getElementById('close-access');
    const accessPanel = document.getElementById('accessibility-panel');
    const backdrop = document.getElementById('modal-backdrop');

    function sincronizarPainelAcesso(aberto) {
        if (!accessPanel || !openBtn) {
            return;
        }
        accessPanel.classList.toggle('hidden', !aberto);
        openBtn.classList.toggle('expanded', aberto);
        openBtn.setAttribute('aria-expanded', aberto ? 'true' : 'false');
    }

    if (openBtn && accessPanel) {
        openBtn.addEventListener('mouseenter', () => openBtn.classList.add('expanded'));
        openBtn.addEventListener('mouseleave', () => {
            if (accessPanel.classList.contains('hidden')) {
                openBtn.classList.remove('expanded');
            }
        });

        openBtn.addEventListener('click', () => {
            sincronizarPainelAcesso(accessPanel.classList.contains('hidden'));
        });

        closeBtn?.addEventListener('click', () => {
            sincronizarPainelAcesso(false);
        });
    }

    document.querySelectorAll('.nav-inst-menu').forEach((menu) => {
        document.addEventListener('click', (event) => {
            if (!menu.contains(event.target)) {
                menu.removeAttribute('open');
            }
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                menu.removeAttribute('open');
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            sincronizarPainelAcesso(false);
        }
    });

    // Fechar modais ao clicar no fundo escurecido (Backdrop)
    if (backdrop) {
        backdrop.addEventListener('click', () => {
            fecharModalIA();
            sincronizarPainelAcesso(false);
        });
    }

    // ---------------------------------------------------
    // 2. FERRAMENTAS VISUAIS DE ACESSIBILIDADE (CORRIGIDAS)
    // ---------------------------------------------------
    const btnAumentar = document.getElementById('btn-aumentar');
    const btnDiminuir = document.getElementById('btn-diminuir');
    const btnEscuro = document.getElementById('btn-escuro');
    const btnClaro = document.getElementById('btn-claro');
    const btnSatAlta = document.getElementById('btn-sat-alta');
    const btnSatBaixa = document.getElementById('btn-sat-baixa');
    const btnZoom = document.getElementById('btn-zoom');

    // Aumentar Tamanho da Fonte
    btnAumentar?.addEventListener('click', () => {
        const root = document.documentElement;
        const currentSize = parseFloat(window.getComputedStyle(root).fontSize) || 16;
        const newSize = currentSize + 2;
        root.style.fontSize = newSize + 'px';
        document.body.style.fontSize = newSize + 'px';
    });

    // Diminuir Tamanho da Fonte
    btnDiminuir?.addEventListener('click', () => {
        const root = document.documentElement;
        const currentSize = parseFloat(window.getComputedStyle(root).fontSize) || 16;
        if (currentSize > 11) {
            const newSize = currentSize - 2;
            root.style.fontSize = newSize + 'px';
            document.body.style.fontSize = newSize + 'px';
        }
    });

    // Contraste Escuro
    btnEscuro?.addEventListener('click', () => {
        document.documentElement.classList.remove('tema-claro');
        document.body.classList.remove('tema-claro');
        
        const ehEscuro = document.body.classList.toggle('tema-escuro');
        document.documentElement.classList.toggle('tema-escuro', ehEscuro);

        if (ehEscuro) {
            document.body.style.backgroundColor = '#121824';
            document.body.style.color = '#ffffff';
        } else {
            document.body.style.backgroundColor = '';
            document.body.style.color = '';
        }
    });

    // Contraste Claro
    btnClaro?.addEventListener('click', () => {
        document.documentElement.classList.remove('tema-escuro');
        document.body.classList.remove('tema-escuro');
        
        const ehClaro = document.body.classList.toggle('tema-claro');
        document.documentElement.classList.toggle('tema-claro', ehClaro);

        document.body.style.backgroundColor = '';
        document.body.style.color = '';
    });

    // Saturação Alta
    btnSatAlta?.addEventListener('click', () => {
        document.body.classList.remove('sat-baixa');
        const ativado = document.body.classList.toggle('sat-alta');
        document.documentElement.style.filter = ativado ? 'saturate(250%)' : '';
    });

    // Saturação Baixa / Monocromático
    btnSatBaixa?.addEventListener('click', () => {
        document.body.classList.remove('sat-alta');
        const ativado = document.body.classList.toggle('sat-baixa');
        document.documentElement.style.filter = ativado ? 'grayscale(100%)' : '';
    });

    // Zoom na Tela
    btnZoom?.addEventListener('click', () => {
        const zoomAtivo = document.body.classList.toggle('zoom-ativo');
        if (zoomAtivo) {
            document.body.style.zoom = "1.15";
            document.body.style.transform = "scale(1.02)";
            document.body.style.transformOrigin = "top center";
        } else {
            document.body.style.zoom = "1.0";
            document.body.style.transform = "none";
        }
    });

    // ---------------------------------------------------
    // 3. LEITOR DE VOZ NATIVO (TEXT-TO-SPEECH)
    // ---------------------------------------------------
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
            .replace(/•/g, '')
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

            alert("Modo Leitura por Clique Ativado!\n\nClique sobre qualquer texto da página para ouvir o conteúdo.\n\nPara sair, clique novamente no botão ou aperte a tecla ESC.");
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
        if (e.key === 'Escape') {
            pararFalaCompletamente();
            desativarModoLeituraPorClique();
            desativarModoSelecaoIA();
            fecharModalIA();
        }
    });

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

    // ---------------------------------------------------
    // 4. INTEGRAÇÃO COM IA E ASSISTENTE
    // ---------------------------------------------------
    const btnSimplificarIA = document.getElementById('btn-simplificar-ia');
    const btnSignificadoIA = document.getElementById('btn-significado-ia');
    const aiModal = document.getElementById('ai-modal');
    const closeAiModal = document.getElementById('close-ai-modal');
    const aiResponseContent = document.getElementById('ai-response-content');

    let iaSelectionModeAtivo = false;
    let promptAtualIA = "";
    let modoAtualIA = ""; 

    function ativarModoSelecaoIA(promptInstrucao, modo) {
        iaSelectionModeAtivo = true;
        promptAtualIA = promptInstrucao;
        modoAtualIA = modo;

        accessPanel?.classList.add('hidden');
        document.body.classList.add('ia-select-mode');

        if (modo === "significado") {
            alert("Modo IA Ativado!\n\nCLIQUE sobre a palavra ou termo que deseja consultar.");
        } else {
            alert("Modo IA Ativado!\n\nCLIQUE sobre o parágrafo que você deseja simplificar.");
        }
    }

    function desativarModoSelecaoIA() {
        iaSelectionModeAtivo = false;
        promptAtualIA = "";
        modoAtualIA = "";
        document.body.classList.remove('ia-select-mode');
    }

    function abrirModalIA() {
        if (aiModal) aiModal.classList.remove('hidden');
        if (backdrop) backdrop.classList.add('active');
    }

    function fecharModalIA() {
        if (aiModal) aiModal.classList.add('hidden');
        if (backdrop) backdrop.classList.remove('active');
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

        desativarModoSelecaoIA();

        if (textoExtraido && textoExtraido.trim().length > 0) {
            chamarIA(promptAtualIA, textoExtraido.trim());
        }
    }, true);

    closeAiModal?.addEventListener('click', fecharModalIA);

    function formatarTextoIA(texto) {
        let html = texto
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        return `<div class="ai-card-body" style="padding: 0.5rem 0;"><p style="line-height: 1.6; color: var(--texto-escuro);">${html}</p></div>`;
    }

async function chamarGemini(promptInstrucao, textoSelecionado) {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`;
        
        // Contexto fixo do seu sistema para guiar a IA
        const contextoAPAL = "Contexto do Sistema: Você é o assistente de acessibilidade do APAL (Aqui Pode, Aqui é Legal), um sistema da Prefeitura Municipal de Vitória da Conquista para licenciamento, fiscalização e gestão de comerciantes ambulantes. Sempre explique os termos ou textos clicados relacionando-os ao contexto de um sistema de prefeitura para ambulantes, licenças e comércio de rua.";

        const promptCompleto = `${contextoAPAL}\n\n${promptInstrucao}\n\nResponda em texto simples, direto, sem saudações e sem perguntas.\n\nTexto/Termo selecionado: "${textoSelecionado}"`;

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: promptCompleto }] }],
                generationConfig: { temperature: 0.2, maxOutputTokens: 180 }
            })
        });

        const data = await response.json();
        if (data.candidates && data.candidates[0]?.content?.parts[0]?.text) {
            return data.candidates[0].content.parts[0].text;
        }
        throw new Error(data.error ? data.error.message : 'Resposta vazia do Gemini');
    }

async function chamarGroq(promptInstrucao, textoSelecionado) {
        if (GROQ_API_KEY.includes("COLE_AQUI")) throw new Error("Chave do Groq não configurada.");
        
        // Contexto fixo do seu sistema para guiar a IA também no Groq
        const contextoAPAL = "Contexto do Sistema: Você é o assistente de acessibilidade do APAL (Aqui Pode, Aqui é Legal), um sistema da Prefeitura Municipal de Vitória da Conquista para licenciamento, fiscalização e gestão de comerciantes ambulantes. Sempre explique os termos ou textos clicados relacionando-os ao contexto de um sistema de prefeitura para ambulantes, licenças e comércio de rua.";

        const promptCompleto = `${contextoAPAL}\n\n${promptInstrucao}\n\nResponda em texto simples, direto, sem saudações e sem perguntas.\n\nTexto/Termo: "${textoSelecionado}"`;

        const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${GROQ_API_KEY}`
            },
            body: JSON.stringify({
                model: 'llama-3.3-70b-versatile',
                temperature: 0.2,
                max_tokens: 180,
                messages: [{ role: 'user', content: promptCompleto }]
            })
        });

        const data = await response.json();
        if (data.choices && data.choices[0]?.message?.content) {
            return data.choices[0].message.content;
        }
        throw new Error(data.error ? data.error.message : 'Resposta vazia do Groq');
    }

    async function chamarIA(promptInstrucao, textoSelecionado) {
        if (!aiModal || !aiResponseContent) return;

        abrirModalIA();
        aiResponseContent.innerHTML = '<p style="color: var(--texto-cinza); font-weight: 500;">Processando explicação com IA, aguarde...</p>';

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
            const respostaExemplo = modoAtualIA === "significado" 
                ? `<strong>Significado de "${textoSelecionado}":</strong> Significa o registro ou autorização oficial concedida pelo município para o exercício da atividade comercial no espaço público.`
                : `<strong>Texto Simplificado:</strong> Este trecho explica as regras de cadastro e os documentos que o comerciante precisa apresentar para conseguir a sua licença de trabalho.`;

            aiResponseContent.innerHTML = formatarTextoIA(respostaExemplo);
        }
    }

    btnSimplificarIA?.addEventListener('click', () => {
        ativarModoSelecaoIA("Reescreva o texto a seguir utilizando linguagem muito simples e fácil de entender.", "simplificar");
    });

    btnSignificadoIA?.addEventListener('click', () => {
        ativarModoSelecaoIA("Explique o significado do termo a seguir em português simples, com no máximo 2 a 3 frases claras.", "significado");
    });

    // ---------------------------------------------------
    // 5. SANFONA (ACCORDION) DA CENTRAL DE AJUDA / FAQ
    // ---------------------------------------------------
    const faqQuestions = document.querySelectorAll('.faq-question');
    faqQuestions.forEach(question => {
        question.addEventListener('click', () => {
            const faqItem = question.parentElement;
            document.querySelectorAll('.faq-item').forEach(item => {
                if (item !== faqItem) item.classList.remove('active');
            });
            faqItem.classList.toggle('active');
        });
    });

    // ---------------------------------------------------
    // 6. MOSTRAR / OCULTAR SENHA (LOGIN E CADASTRO)
    // ---------------------------------------------------
    document.querySelectorAll('.btn-toggle-password').forEach(btn => {
        btn.addEventListener('click', () => {
            const wrapper = btn.closest('.input-password-wrapper');
            const input = wrapper ? wrapper.querySelector('input') : null;
            if (!input) return;

            const ehSenha = input.getAttribute('type') === 'password';
            input.setAttribute('type', ehSenha ? 'text' : 'password');

            const icone = btn.querySelector('i');
            if (icone) {
                icone.setAttribute('data-lucide', ehSenha ? 'eye-off' : 'eye');
                if (window.lucide) lucide.createIcons();
            }
        });
    });

    // ==========================================
    // 7. DROPDOWNS PERSONALIZADOS + API DO IBGE
    // ==========================================

    const customSelects = new Map();

    function normalizarBusca(texto) {
        return String(texto || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();
    }

    function obterTextoAtualDoSelect(select) {
        if (!select) return '';

        const opcaoSelecionada = select.options[select.selectedIndex];
        if (opcaoSelecionada) return opcaoSelecionada.textContent.trim();

        return 'Selecione...';
    }

    function fecharDropdownPersonalizado(controle) {
        if (!controle) return;

        controle.menu.hidden = true;
        controle.trigger.setAttribute('aria-expanded', 'false');
        controle.search.value = '';
    }

    function fecharTodosDropdowns(exceto = null) {
        customSelects.forEach(controle => {
            if (controle !== exceto) {
                fecharDropdownPersonalizado(controle);
            }
        });
    }

    function renderizarOpcoesDropdown(controle, termo = '') {
        if (!controle) return;

        const { select, optionsBox } = controle;
        const busca = normalizarBusca(termo);

        optionsBox.replaceChildren();

        const opcoes = Array.from(select.options).filter(opcao => {
            if (opcao.disabled || opcao.value === '') return false;

            if (!busca) return true;

            return normalizarBusca(opcao.textContent).includes(busca);
        });

        if (opcoes.length === 0) {
            const vazio = document.createElement('div');
            vazio.className = 'custom-select-empty';
            vazio.textContent = 'Nenhuma opção encontrada.';
            optionsBox.appendChild(vazio);
            return;
        }

        const fragment = document.createDocumentFragment();

        opcoes.forEach(opcao => {
            const botao = document.createElement('button');
            botao.type = 'button';
            botao.className = 'custom-select-option';
            botao.setAttribute('role', 'option');
            botao.dataset.value = opcao.value;
            botao.textContent = opcao.textContent;

            const selecionada = select.value === opcao.value;
            botao.setAttribute('aria-selected', String(selecionada));
            botao.classList.toggle('is-selected', selecionada);

            botao.addEventListener('click', () => {
                select.value = opcao.value;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                sincronizarDropdownPersonalizado(select);
                fecharDropdownPersonalizado(controle);
                controle.trigger.focus();
            });

            fragment.appendChild(botao);
        });

        optionsBox.appendChild(fragment);
    }

    function sincronizarDropdownPersonalizado(selectOuId) {
        const select = typeof selectOuId === 'string'
            ? document.getElementById(selectOuId)
            : selectOuId;

        if (!select) return;

        const controle = customSelects.get(select.id);
        if (!controle) return;

        controle.value.textContent = obterTextoAtualDoSelect(select);
        controle.trigger.disabled = Boolean(select.disabled);
        controle.trigger.setAttribute('aria-disabled', String(Boolean(select.disabled)));

        if (select.disabled) {
            fecharDropdownPersonalizado(controle);
        }

        renderizarOpcoesDropdown(controle, controle.search.value);
    }

    function definirPlaceholderSelect(select, texto) {
        if (!select) return;

        let placeholder = Array.from(select.options).find(opcao => opcao.value === '');

        if (!placeholder) {
            placeholder = new Option(texto, '', true, true);
            placeholder.disabled = true;
            select.prepend(placeholder);
        }

        placeholder.textContent = texto;

        if (!select.value) {
            placeholder.selected = true;
        }

        sincronizarDropdownPersonalizado(select);
    }

    function inicializarDropdownPersonalizado(wrapper) {
        const sourceId = wrapper.dataset.sourceSelect;
        const select = document.getElementById(sourceId);
        const trigger = wrapper.querySelector('.custom-select-trigger');
        const value = wrapper.querySelector('.custom-select-value');
        const menu = wrapper.querySelector('.custom-select-menu');
        const search = wrapper.querySelector('.custom-select-search');
        const optionsBox = wrapper.querySelector('.custom-select-options');

        if (!select || !trigger || !value || !menu || !search || !optionsBox) {
            return;
        }

        const controle = {
            wrapper,
            select,
            trigger,
            value,
            menu,
            search,
            optionsBox
        };

        customSelects.set(select.id, controle);

        trigger.addEventListener('click', () => {
            if (trigger.disabled || select.disabled) return;

            const vaiAbrir = menu.hidden;

            fecharTodosDropdowns(controle);

            if (!vaiAbrir) {
                fecharDropdownPersonalizado(controle);
                return;
            }

            menu.hidden = false;
            trigger.setAttribute('aria-expanded', 'true');
            search.value = '';
            renderizarOpcoesDropdown(controle);

            requestAnimationFrame(() => {
                search.focus();
            });
        });

        trigger.addEventListener('keydown', event => {
            if (trigger.disabled || select.disabled) return;

            if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();

                if (menu.hidden) {
                    trigger.click();
                }
            }
        });

        search.addEventListener('input', () => {
            renderizarOpcoesDropdown(controle, search.value);
        });

        search.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
                event.preventDefault();
                fecharDropdownPersonalizado(controle);
                trigger.focus();
                return;
            }

            if (event.key === 'ArrowDown') {
                const primeiraOpcao = optionsBox.querySelector('.custom-select-option');
                if (primeiraOpcao) {
                    event.preventDefault();
                    primeiraOpcao.focus();
                }
            }
        });

        optionsBox.addEventListener('keydown', event => {
            const opcaoAtual = event.target.closest('.custom-select-option');
            if (!opcaoAtual) return;

            if (event.key === 'Escape') {
                event.preventDefault();
                fecharDropdownPersonalizado(controle);
                trigger.focus();
                return;
            }

            if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;

            const opcoes = Array.from(optionsBox.querySelectorAll('.custom-select-option'));
            const indiceAtual = opcoes.indexOf(opcaoAtual);
            const deslocamento = event.key === 'ArrowDown' ? 1 : -1;
            const proximoIndice = Math.max(0, Math.min(opcoes.length - 1, indiceAtual + deslocamento));

            event.preventDefault();
            opcoes[proximoIndice]?.focus();
        });

        select.addEventListener('change', () => {
            sincronizarDropdownPersonalizado(select);
        });

        sincronizarDropdownPersonalizado(select);
    }

    document.querySelectorAll('[data-custom-select]').forEach(inicializarDropdownPersonalizado);

    document.addEventListener('click', event => {
        if (!event.target.closest('[data-custom-select]')) {
            fecharTodosDropdowns();
        }
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            fecharTodosDropdowns();
        }
    });

    let ufsCache = [];

    async function carregarEstados() {
        const selectsEstado = [
            document.getElementById('estado-nascimento'),
            document.getElementById('estado-input'),
            document.getElementById('estado-ponto')
        ].filter(Boolean);

        selectsEstado.forEach(select => {
            select.disabled = true;
            select.replaceChildren(new Option('Carregando Estados...', '', true, true));
            select.options[0].disabled = true;
            sincronizarDropdownPersonalizado(select);
        });

        try {
            const res = await fetch(
                'https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome'
            );

            if (!res.ok) {
                throw new Error(`Erro HTTP: ${res.status}`);
            }

            ufsCache = await res.json();

            selectsEstado.forEach(select => {
                const fragment = document.createDocumentFragment();
                const placeholder = new Option('Selecione o Estado...', '', true, true);
                placeholder.disabled = true;
                fragment.appendChild(placeholder);

                ufsCache.forEach(uf => {
                    fragment.appendChild(
                        new Option(`${uf.nome} (${uf.sigla})`, uf.sigla)
                    );
                });

                select.replaceChildren(fragment);
                select.disabled = false;
                if (select.dataset.valorInicial) {
                    select.value = select.dataset.valorInicial;
                }
                sincronizarDropdownPersonalizado(select);
            });

            if (estadoAtualSelect?.dataset.valorInicial && cidadeAtualSelect) {
                window.carregarCidades(
                    'estado-input',
                    'cidade-input',
                    cidadeAtualSelect.dataset.valorInicial || null
                );
            }

        } catch (error) {
            console.error('Erro ao buscar estados no IBGE:', error);

            selectsEstado.forEach(select => {
                select.disabled = true;
                select.replaceChildren(new Option('Não foi possível carregar os Estados', '', true, true));
                select.options[0].disabled = true;
                sincronizarDropdownPersonalizado(select);
            });
        }
    }

    window.carregarCidades = async function(
        idEstado,
        idCidade,
        cidadeSelecionada = null
    ) {
        const selectEstado = document.getElementById(idEstado);
        const selectCidade = document.getElementById(idCidade);

        if (!selectEstado || !selectCidade) return;

        const siglaUF = selectEstado.value;

        if (!siglaUF) {
            selectCidade.disabled = true;
            selectCidade.replaceChildren(new Option('Selecione o Estado primeiro...', '', true, true));
            selectCidade.options[0].disabled = true;
            sincronizarDropdownPersonalizado(selectCidade);
            return;
        }

        selectCidade.disabled = true;
        selectCidade.replaceChildren(new Option('Carregando cidades...', '', true, true));
        selectCidade.options[0].disabled = true;
        sincronizarDropdownPersonalizado(selectCidade);

        try {
            const res = await fetch(
                `https://servicodados.ibge.gov.br/api/v1/localidades/estados/${encodeURIComponent(siglaUF)}/municipios`
            );

            if (!res.ok) {
                throw new Error(`Erro HTTP: ${res.status}`);
            }

            const cidades = await res.json();
            cidades.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));

            const fragment = document.createDocumentFragment();
            const placeholder = new Option('Selecione a Cidade...', '', true, true);
            placeholder.disabled = true;
            fragment.appendChild(placeholder);

            cidades.forEach(cidade => {
                fragment.appendChild(new Option(cidade.nome, cidade.nome));
            });

            selectCidade.replaceChildren(fragment);
            selectCidade.disabled = false;

            if (cidadeSelecionada) {
                selectCidade.value = cidadeSelecionada;
            }

            sincronizarDropdownPersonalizado(selectCidade);

        } catch (error) {
            console.error('Erro ao carregar cidades do IBGE:', error);

            selectCidade.disabled = true;
            selectCidade.replaceChildren(new Option('Não foi possível carregar as cidades', '', true, true));
            selectCidade.options[0].disabled = true;
            sincronizarDropdownPersonalizado(selectCidade);
        }
    };

    const estadoNascimentoSelect = document.getElementById('estado-nascimento');
    const cidadeNascimentoSelect = document.getElementById('cidade-nascimento');
    const estadoAtualSelect = document.getElementById('estado-input');
    const cidadeAtualSelect = document.getElementById('cidade-input');
    const estadoPontoSelect = document.getElementById('estado-ponto');
    const cidadePontoSelect = document.getElementById('cidade-ponto');

    estadoNascimentoSelect?.addEventListener('change', () => {
        window.carregarCidades('estado-nascimento', 'cidade-nascimento');
    });

    estadoAtualSelect?.addEventListener('change', () => {
        window.carregarCidades('estado-input', 'cidade-input');
    });

    estadoPontoSelect?.addEventListener('change', () => {
        window.carregarCidades('estado-ponto', 'cidade-ponto');
    });

    // ==========================================
    // 8. BUSCA AUTOMÁTICA DE ENDEREÇO PELO CEP
    // ==========================================

    function somenteDigitos(valor) {
        return String(valor || '').replace(/\D/g, '');
    }

    function mascararCEP(valor) {
        const numeros = somenteDigitos(valor).slice(0, 8);

        if (numeros.length <= 5) {
            return numeros;
        }

        return `${numeros.slice(0, 5)}-${numeros.slice(5)}`;
    }

    function atualizarStatusCEP(idStatus, mensagem, tipo = 'normal') {
        const status = document.getElementById(idStatus);
        if (!status) return;

        status.textContent = mensagem;

        if (tipo === 'erro') {
            status.style.color = '#B42318';
        } else if (tipo === 'sucesso') {
            status.style.color = '#027A48';
        } else {
            status.style.color = 'var(--azul-vibrante, #1D4ED8)';
        }
    }

    async function preencherEstadoECidadePorCEP(idEstado, idCidade, uf, cidade) {
        const estado = document.getElementById(idEstado);
        const cidadeSelect = document.getElementById(idCidade);

        if (!estado || !cidadeSelect || !uf) return;

        const possuiUF = Array.from(estado.options).some(opcao => opcao.value === uf);

        if (!possuiUF) {
            await carregarEstados();
        }

        estado.value = uf;
        sincronizarDropdownPersonalizado(estado);

        await window.carregarCidades(idEstado, idCidade, cidade || null);

        if (cidade) {
            cidadeSelect.value = cidade;
            sincronizarDropdownPersonalizado(cidadeSelect);
        }
    }

    function consultarViaCEPComJSONP(cep) {
        return new Promise((resolve, reject) => {
            const callbackName = `__apalViaCEP_${Date.now()}_${Math.random().toString(36).slice(2)}`;
            const script = document.createElement('script');
            let timeoutId;

            const limpar = () => {
                clearTimeout(timeoutId);
                script.remove();
                try {
                    delete window[callbackName];
                } catch (_) {
                    window[callbackName] = undefined;
                }
            };

            window[callbackName] = dados => {
                limpar();

                if (!dados || dados.erro) {
                    reject(new Error('CEP não encontrado'));
                    return;
                }

                resolve(dados);
            };

            script.onerror = () => {
                limpar();
                reject(new Error('Falha ao consultar o ViaCEP'));
            };

            timeoutId = setTimeout(() => {
                limpar();
                reject(new Error('Tempo esgotado na consulta do CEP'));
            }, 8000);

            script.src = `https://viacep.com.br/ws/${encodeURIComponent(cep)}/json/?callback=${encodeURIComponent(callbackName)}`;
            document.head.appendChild(script);
        });
    }

    async function consultarViaCEP(cep) {
        // Primeiro tenta fetch. Se a página estiver sendo aberta diretamente como
        // arquivo local e o navegador bloquear a requisição, usa JSONP como fallback.
        try {
            const response = await fetch(
                `https://viacep.com.br/ws/${encodeURIComponent(cep)}/json/`,
                { cache: 'no-store' }
            );

            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const dados = await response.json();

            if (!dados || dados.erro) {
                throw new Error('CEP não encontrado');
            }

            return dados;
        } catch (erroFetch) {
            console.warn('Consulta ViaCEP via fetch falhou; tentando JSONP.', erroFetch);
            return consultarViaCEPComJSONP(cep);
        }
    }

    async function buscarEnderecoPorCEP(config) {
        const {
            inputId,
            statusId,
            enderecoId,
            bairroId,
            estadoId,
            cidadeId
        } = config;

        const cepInput = document.getElementById(inputId);
        if (!cepInput) return;

        const cep = somenteDigitos(cepInput.value);

        if (cep.length !== 8) {
            return;
        }

        atualizarStatusCEP(statusId, 'Buscando endereço...');

        try {
            const dados = await consultarViaCEP(cep);
            const endereco = document.getElementById(enderecoId);
            const bairro = document.getElementById(bairroId);

            // CEPs gerais podem não retornar logradouro ou bairro.
            // O usuário continua podendo completar esses campos manualmente.
            if (endereco && dados.logradouro) {
                endereco.value = dados.logradouro;
            }

            if (bairro && dados.bairro) {
                bairro.value = dados.bairro;
            }

            await preencherEstadoECidadePorCEP(
                estadoId,
                cidadeId,
                dados.uf,
                dados.localidade
            );

            atualizarStatusCEP(statusId, '', 'sucesso');
        } catch (error) {
            console.warn('Não foi possível localizar o CEP:', error);
            atualizarStatusCEP(statusId, '', 'erro');
        }
    }

    function configurarBuscaAutomaticaCEP(config) {
        const input = document.getElementById(config.inputId);
        if (!input) return;

        let temporizador = null;
        let ultimoCepBuscado = '';

        const solicitarBusca = () => {
            const cep = somenteDigitos(input.value);

            if (cep.length !== 8 || cep === ultimoCepBuscado) {
                return;
            }

            ultimoCepBuscado = cep;
            buscarEnderecoPorCEP(config);
        };

        input.addEventListener('input', () => {
            input.value = mascararCEP(input.value);

            clearTimeout(temporizador);

            if (somenteDigitos(input.value).length === 8) {
                temporizador = setTimeout(solicitarBusca, 250);
            } else {
                ultimoCepBuscado = '';
            }
        });

        input.addEventListener('blur', solicitarBusca);
    }

    configurarBuscaAutomaticaCEP({
        inputId: 'cep-input',
        statusId: 'cep-residencial-status',
        enderecoId: 'endereco-input',
        bairroId: 'bairro-input',
        estadoId: 'estado-input',
        cidadeId: 'cidade-input'
    });

    configurarBuscaAutomaticaCEP({
        inputId: 'cep-ponto',
        statusId: 'cep-ponto-status',
        enderecoId: 'endereco-ponto',
        bairroId: 'bairro-ponto',
        estadoId: 'estado-ponto',
        cidadeId: 'cidade-ponto'
    });

// ==========================================
// 9. CPF
// VALIDAÇÃO DOS DÍGITOS VERIFICADORES
// ==========================================

const cpfInput =
    document.getElementById(
        'cpf-cadastro'
    );

const cpfErroTexto =
    document.getElementById(
        'cpf-erro-texto'
    );


function validarCPF(cpfBruto) {

    const cpf =
        String(cpfBruto || '')
            .replace(/\D/g, '');

    // CPF precisa ter exatamente 11 números
    if (cpf.length !== 11) {
        return false;
    }

    // Recusa sequências:
    // 00000000000
    // 11111111111
    // etc.
    if (/^(\d)\1{10}$/.test(cpf)) {
        return false;
    }


    // ----------------------------
    // PRIMEIRO DÍGITO VERIFICADOR
    // ----------------------------

    let soma = 0;

    for (
        let i = 0;
        i < 9;
        i++
    ) {

        soma +=
            Number(cpf.charAt(i)) *
            (10 - i);

    }

    let resto =
        (soma * 10) % 11;

    if (
        resto === 10 ||
        resto === 11
    ) {
        resto = 0;
    }

    if (
        resto !==
        Number(cpf.charAt(9))
    ) {
        return false;
    }


    // ----------------------------
    // SEGUNDO DÍGITO VERIFICADOR
    // ----------------------------

    soma = 0;

    for (
        let i = 0;
        i < 10;
        i++
    ) {

        soma +=
            Number(cpf.charAt(i)) *
            (11 - i);

    }

    resto =
        (soma * 10) % 11;

    if (
        resto === 10 ||
        resto === 11
    ) {
        resto = 0;
    }

    if (
        resto !==
        Number(cpf.charAt(10))
    ) {
        return false;
    }

    return true;
}


// ==========================================
// MÁSCARA DO CPF
// ==========================================

function mascararCPF(valor) {

    return String(valor || '')

        .replace(/\D/g, '')

        .slice(0, 11)

        .replace(
            /(\d{3})(\d)/,
            '$1.$2'
        )

        .replace(
            /(\d{3})(\d)/,
            '$1.$2'
        )

        .replace(
            /(\d{3})(\d{1,2})$/,
            '$1-$2'
        );
}


// ==========================================
// VERIFICAR O CPF DIGITADO
// ==========================================

function checarCPFInput() {

    if (!cpfInput) {
        return true;
    }

    cpfInput.value =
        mascararCPF(
            cpfInput.value
        );

    const cpfLimpo =
        cpfInput.value
            .replace(/\D/g, '');


    // Campo vazio:
    // deixa o required cuidar
    if (
        cpfLimpo.length === 0
    ) {

        cpfInput.setCustomValidity('');

        cpfInput.style.borderColor =
            '';

        cpfInput.style.backgroundColor =
            '';

        if (cpfErroTexto) {

            cpfErroTexto.style.display =
                'none';

        }

        return true;
    }


    // Enquanto ainda está digitando
    if (
        cpfLimpo.length < 11
    ) {

        cpfInput.setCustomValidity(
            'Digite os 11 números do CPF.'
        );

        cpfInput.style.borderColor =
            '#EF4444';

        cpfInput.style.backgroundColor =
            '#FEF2F2';

        if (cpfErroTexto) {

            cpfErroTexto.textContent =
                'Digite todos os 11 números do CPF.';

            cpfErroTexto.style.display =
                'block';

        }

        return false;
    }


    const valido =
        validarCPF(
            cpfInput.value
        );


    if (valido) {

        cpfInput.setCustomValidity('');

        cpfInput.style.borderColor =
            '';

        cpfInput.style.backgroundColor =
            '';

        if (cpfErroTexto) {

            cpfErroTexto.style.display =
                'none';

        }

    } else {

        cpfInput.setCustomValidity(
            'CPF inválido. Verifique os números digitados.'
        );

        cpfInput.style.borderColor =
            '#EF4444';

        cpfInput.style.backgroundColor =
            '#FEF2F2';

        if (cpfErroTexto) {

            cpfErroTexto.textContent =
                'CPF inválido. Verifique os números digitados.';

            cpfErroTexto.style.display =
                'block';

        }

    }

    return valido;
}


if (cpfInput) {

    cpfInput.addEventListener(
        'input',
        checarCPFInput
    );

    cpfInput.addEventListener(
        'blur',
        checarCPFInput
    );

}


// Deixa disponível para o JS
// específico do formulário
window.validarCPF =
    validarCPF;

window.checarCPFInput =
    checarCPFInput;


// ==========================================
// 10. NÃO POSSUO NIS
// ==========================================

const checkNoNis =
    document.getElementById(
        'check-no-nis'
    );

const nisInput =
    document.getElementById(
        'req-nis'
    );


function atualizarCampoNis() {

    if (
        !checkNoNis ||
        !nisInput
    ) {
        return;
    }

    if (checkNoNis.checked) {

        // Limpa o que estava digitado
        nisInput.value = '';

        // Desabilita realmente
        nisInput.disabled = true;

        // Marca visualmente
        nisInput.setAttribute(
            'aria-disabled',
            'true'
        );

    } else {

        nisInput.disabled = false;

        nisInput.removeAttribute(
            'aria-disabled'
        );

    }

}


if (
    checkNoNis &&
    nisInput
) {

    checkNoNis.addEventListener(
        'change',
        atualizarCampoNis
    );

    atualizarCampoNis();

}



    // ==========================================
    // 11. CNPJ + OPÇÃO "NÃO POSSUO MEI"
    // ==========================================

    const checkNoCnpjCadastro = document.getElementById('check-no-cnpj');
    const cnpjContainerCadastro = document.getElementById('cnpj-container');
    const cnpjInputCadastro = document.getElementById('pj-cnpj');
    const cnpjErroTexto = document.getElementById('cnpj-erro-texto');

    function validarCNPJ(cnpjBruto) {
        const cnpj = somenteDigitos(cnpjBruto);

        if (cnpj.length !== 14) {
            return false;
        }

        if (/^(\d)\1{13}$/.test(cnpj)) {
            return false;
        }

        function calcularDigito(base, pesos) {
            const soma = base
                .split('')
                .reduce((total, digito, indice) => {
                    return total + Number(digito) * pesos[indice];
                }, 0);

            const resto = soma % 11;
            return resto < 2 ? 0 : 11 - resto;
        }

        const primeiroDigito = calcularDigito(
            cnpj.slice(0, 12),
            [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        );

        if (primeiroDigito !== Number(cnpj.charAt(12))) {
            return false;
        }

        const segundoDigito = calcularDigito(
            cnpj.slice(0, 13),
            [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        );

        return segundoDigito === Number(cnpj.charAt(13));
    }

    function mascararCNPJ(valor) {
        return somenteDigitos(valor)
            .slice(0, 14)
            .replace(/^(\d{2})(\d)/, '$1.$2')
            .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
            .replace(/\.(\d{3})(\d)/, '.$1/$2')
            .replace(/(\d{4})(\d)/, '$1-$2');
    }

    function limparAvisoCNPJ() {
        if (!cnpjInputCadastro) return;

        cnpjInputCadastro.setCustomValidity('');
        cnpjInputCadastro.style.borderColor = '';
        cnpjInputCadastro.style.backgroundColor = '';

        if (cnpjErroTexto) {
            cnpjErroTexto.style.display = 'none';
        }
    }

    function checarCNPJInput() {
        if (!cnpjInputCadastro || checkNoCnpjCadastro?.checked) {
            limparAvisoCNPJ();
            return true;
        }

        cnpjInputCadastro.value = mascararCNPJ(cnpjInputCadastro.value);

        const cnpjLimpo = somenteDigitos(cnpjInputCadastro.value);

        if (cnpjLimpo.length === 0) {
            limparAvisoCNPJ();
            return !cnpjInputCadastro.required;
        }

        if (cnpjLimpo.length < 14) {
            cnpjInputCadastro.setCustomValidity('Digite os 14 números do CNPJ.');
            cnpjInputCadastro.style.borderColor = '#EF4444';
            cnpjInputCadastro.style.backgroundColor = '#FEF2F2';

            if (cnpjErroTexto) {
                cnpjErroTexto.textContent = 'Digite todos os 14 números do CNPJ.';
                cnpjErroTexto.style.display = 'block';
            }

            return false;
        }

        const valido = validarCNPJ(cnpjLimpo);

        if (valido) {
            limparAvisoCNPJ();
        } else {
            cnpjInputCadastro.setCustomValidity(
                'CNPJ inválido. Verifique os números digitados.'
            );
            cnpjInputCadastro.style.borderColor = '#EF4444';
            cnpjInputCadastro.style.backgroundColor = '#FEF2F2';

            if (cnpjErroTexto) {
                cnpjErroTexto.textContent =
                    'CNPJ inválido. Verifique os números digitados.';
                cnpjErroTexto.style.display = 'block';
            }
        }

        return valido;
    }

    function atualizarCamposCNPJ() {
        if (!checkNoCnpjCadastro || !cnpjContainerCadastro) {
            return;
        }

        const desabilitar = checkNoCnpjCadastro.checked;
        const campos = cnpjContainerCadastro.querySelectorAll(
            'input, select, textarea'
        );

        campos.forEach(campo => {
            campo.disabled = desabilitar;
        });

        cnpjContainerCadastro.setAttribute(
            'aria-disabled',
            String(desabilitar)
        );

        cnpjContainerCadastro.style.opacity = desabilitar ? '0.55' : '';
        cnpjContainerCadastro.style.pointerEvents = desabilitar ? 'none' : '';

        if (desabilitar) {
            limparAvisoCNPJ();
        }
    }

    cnpjInputCadastro?.addEventListener('input', () => {
        cnpjInputCadastro.value = mascararCNPJ(cnpjInputCadastro.value);
        checarCNPJInput();
    });

    cnpjInputCadastro?.addEventListener('blur', checarCNPJInput);

    checkNoCnpjCadastro?.addEventListener('change', atualizarCamposCNPJ);

    atualizarCamposCNPJ();

    window.validarCNPJ = validarCNPJ;
    window.checarCNPJInput = checarCNPJInput;

   // ==========================================
    // 12. PAÍS DE ORIGEM E REGRAS DE NACIONALIDADE
    // ==========================================

    const paisOrigemSelect = document.getElementById('pais-origem') || document.getElementById('nacionalidade-select');
    const estadoNascSelect = document.getElementById('estado-nascimento');
    const cidadeNascSelect = document.getElementById('cidade-nascimento');

    function aplicarRegraNacionalidade() {
        if (!paisOrigemSelect) return;

        const ehBrasil = paisOrigemSelect.value === 'Brasil';

        if (estadoNascSelect) {
            estadoNascSelect.disabled = !ehBrasil;
            estadoNascSelect.required = ehBrasil;

            if (!ehBrasil) {
                estadoNascSelect.value = '';
                estadoNascSelect.replaceChildren(new Option('Não aplicável (Estrangeiro)', '', true, true));
            } else {
                carregarEstados();
            }
        }

        if (cidadeNascSelect) {
            cidadeNascSelect.disabled = true; // Habilita somente após escolher a UF
            cidadeNascSelect.required = ehBrasil;

            if (!ehBrasil) {
                cidadeNascSelect.value = '';
                cidadeNascSelect.replaceChildren(new Option('Não aplicável (Estrangeiro)', '', true, true));
            } else {
                cidadeNascSelect.replaceChildren(new Option('Selecione o Estado primeiro...', '', true, true));
            }
        }
    }

   paisOrigemSelect?.addEventListener('change', aplicarRegraNacionalidade);

    // ---> GATILHO: Inicia a busca no IBGE ao carregar a página <---
    if (estadoNascSelect || document.getElementById('estado-input') || document.getElementById('estado-ponto')) {
        carregarEstados().then(() => {
            aplicarRegraNacionalidade();
        });
    } else {
        aplicarRegraNacionalidade();
    }

    // ==========================================
    // MÁSCARA E BLOQUEIO DE LETRAS NO TELEFONE
    // ==========================================

    function mascararTelefone(valor) {
        // Remove tudo que NÃO for número e limita a 11 dígitos
        let num = String(valor || '').replace(/\D/g, '').slice(0, 11);

        if (num.length <= 10) {
            return num.replace(/^(\d{2})(\d)/g, '($1) $2')
                      .replace(/(\d{4})(\d)/, '$1-$2');
        }
        return num.replace(/^(\d{2})(\d)/g, '($1) $2')
                  .replace(/(\d{5})(\d)/, '$1-$2');
    }

    const telPrincipal = document.getElementById('req-tel');
    const telSecundario = document.getElementById('req-tel-2');

    [telPrincipal, telSecundario].forEach(input => {
        if (input) {
            input.addEventListener('input', (e) => {
                e.target.value = mascararTelefone(e.target.value);
            });
        }
    });


    // ==========================================
    // 13. NAVEGAÇÃO ENTRE AS ETAPAS DO CADASTRO
    // ==========================================

    const cadastroForm = document.getElementById('cadastro-form');
    const stepperServidor = cadastroForm?.dataset.serverStepper === 'true';
    const etapasFormulario = Array.from(document.querySelectorAll('.form-step'));
    const passosStepper = Array.from(document.querySelectorAll('.stepper-step'));
    const stepperProgress = document.getElementById('stepper-progress');
    const errorCard = document.getElementById('error-card');
    const errorMessage = document.getElementById('error-message');
    const checkNoCnpj = document.getElementById('check-no-cnpj');
    const cnpjContainer = document.getElementById('cnpj-container');

    let etapaAtual = Number(cadastroForm?.dataset.etapaAtual || 1) || 1;
    const totalEtapas = etapasFormulario.length || 6;

    function ocultarErroEtapa() {
        if (errorCard) {
            errorCard.style.display = 'none';
        }
    }

    function mostrarErroEtapa(mensagem) {
        if (errorMessage) {
            errorMessage.textContent = mensagem;
        }

        if (errorCard) {
            errorCard.style.display = 'flex';
            errorCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    function atualizarStepper(numeroEtapa) {
        passosStepper.forEach((passo, indice) => {
            const numeroPasso = indice + 1;
            passo.classList.toggle('active', numeroPasso === numeroEtapa);
            passo.classList.toggle('completed', numeroPasso < numeroEtapa);
        });

        if (stepperProgress && totalEtapas > 1) {
            const percentual = ((numeroEtapa - 1) / (totalEtapas - 1)) * 100;
            stepperProgress.style.width = `${percentual}%`;
        }
    }

    function mostrarEtapa(numeroEtapa, rolar = true) {
        const destino = document.getElementById(`step-${numeroEtapa}`);
        if (!destino) return;

        etapasFormulario.forEach(etapa => {
            etapa.classList.toggle('active', etapa === destino);
        });

        etapaAtual = numeroEtapa;
        ocultarErroEtapa();
        fecharTodosDropdowns();
        atualizarStepper(numeroEtapa);

        const card = document.querySelector('.form-card');
        if (rolar && card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    function campoDeveSerIgnorado(campo, numeroEtapa) {
        if (!campo || campo.disabled) return true;

        // Na etapa de empresa, o usuário pode declarar que não possui CNPJ/MEI.
        if (
            numeroEtapa === 3 &&
            checkNoCnpj?.checked &&
            cnpjContainer?.contains(campo)
        ) {
            return true;
        }

        return false;
    }

    function focarCampoInvalido(campo) {
        if (!campo) return;

        // Os selects País/UF/Cidade ficam ocultos porque o usuário interage
        // com o dropdown personalizado. Nesse caso, focamos o botão visível.
        const controleCustomizado = customSelects.get(campo.id);
        if (controleCustomizado?.trigger) {
            controleCustomizado.trigger.focus();
            return;
        }

        if (typeof campo.focus === 'function') {
            campo.focus({ preventScroll: true });
            campo.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    function validarEtapa(numeroEtapa) {
        const etapa = document.getElementById(`step-${numeroEtapa}`);
        if (!etapa) return false;

        ocultarErroEtapa();

        // Mantém a validação específica dos dígitos verificadores do CPF.
        if (numeroEtapa === 1 && typeof window.checarCPFInput === 'function') {
            window.checarCPFInput();
        }

        if (
            numeroEtapa === 3 &&
            !checkNoCnpj?.checked &&
            typeof window.checarCNPJInput === 'function'
        ) {
            window.checarCNPJInput();
        }

        const campos = Array.from(
            etapa.querySelectorAll('input, select, textarea')
        );

        let primeiroInvalido = null;

        for (const campo of campos) {
            if (campoDeveSerIgnorado(campo, numeroEtapa)) continue;

            if (!campo.checkValidity()) {
                primeiroInvalido = campo;
                break;
            }
        }

        if (primeiroInvalido) {
            mostrarErroEtapa(
                'Por favor, preencha corretamente todos os campos obrigatórios desta etapa antes de continuar.'
            );
            focarCampoInvalido(primeiroInvalido);
            return false;
        }

        return true;
    }

    for (let numero = 1; numero < totalEtapas; numero++) {
        const botaoProximo = document.getElementById(`btn-next-${numero}`);

        botaoProximo?.addEventListener('click', () => {
            if (stepperServidor) return;
            if (!validarEtapa(numero)) return;
            mostrarEtapa(numero + 1);
        });
    }

    for (let numero = 2; numero <= totalEtapas; numero++) {
        const botaoVoltar = document.getElementById(`btn-prev-${numero}`);

        botaoVoltar?.addEventListener('click', () => {
            if (stepperServidor) return;
            mostrarEtapa(numero - 1);
        });
    }

// ==========================================
    // 14. TELA DE CONFIRMAÇÃO E SALVAMENTO DE PROTOCOLO
    // ==========================================

    const successScreen = document.getElementById('success-screen');
    const stepperContainer = document.getElementById('stepper');
    const heroTitle = document.getElementById('hero-title');
    const heroSubtitle = document.getElementById('hero-subtitle');
    const protocoloEl = document.getElementById('protocolo-gerado');

    function gerarIdentificadorTemporario() {
        const ano = new Date().getFullYear();
        const sufixo = Math.floor(100000 + Math.random() * 900000);
        return `APAL-${ano}-${sufixo}`;
    }

    function exibirTelaSucessoCadastro(protocoloOficial = '', dadosComprovante = null) {
        if (!cadastroForm || !successScreen) return;

        // 1. Determina ou recupera os dados do protocolo
        let dadosFinais = dadosComprovante;

        if (!dadosFinais) {
            const tipoSelect = document.getElementById('tipo-comercio');
            dadosFinais = {
                protocolo: protocoloOficial || gerarIdentificadorTemporario(),
                nome: document.getElementById('req-nome')?.value || 'Não informado',
                cpf: document.getElementById('cpf-cadastro')?.value || 'Não informado',
                comercio: (tipoSelect && tipoSelect.selectedIndex >= 0) 
                    ? tipoSelect.options[tipoSelect.selectedIndex].text 
                    : 'Comércio Ambulante'
            };
            
            // Grava o comprovante no localStorage para não sumir ao clicar no botão 'Voltar'
            localStorage.setItem('apal_ultimo_comprovante', JSON.stringify(dadosFinais));
            localStorage.removeItem('apal_cadastro_rascunho'); // Limpa o rascunho temporário
        }

        // 2. Preenche a tela de confirmação com os dados
        if (protocoloEl) protocoloEl.textContent = dadosFinais.protocolo;
        
        const resumoNome = document.getElementById('resumo-nome');
        const resumoCpf = document.getElementById('resumo-cpf');
        const resumoComercio = document.getElementById('resumo-comercio');

        if (resumoNome) resumoNome.textContent = dadosFinais.nome;
        if (resumoCpf) resumoCpf.textContent = dadosFinais.cpf;
        if (resumoComercio) resumoComercio.textContent = dadosFinais.comercio;

        // 3. Oculta o formulário e exibe o comprovante
        cadastroForm.style.display = 'none';
        if (stepperContainer) stepperContainer.style.display = 'none';
        if (typeof ocultarErroEtapa === 'function') ocultarErroEtapa();

        if (heroTitle) heroTitle.textContent = 'Requerimento Concluído com Sucesso!';
        if (heroSubtitle) heroSubtitle.textContent = 'Seu pedido foi protocolado e os dados cadastrais foram vinculados com segurança.';

        successScreen.style.setProperty('display', 'block', 'important');
        window.scrollTo({ top: 0, behavior: 'smooth' });

        if (window.lucide) lucide.createIcons();
    }

    // RESTAURA O COMPROVANTE CASO O USUÁRIO CLIQUE EM VOLTAR NO NAVEGADOR
    function verificarComprovanteExistente() {
        const comprovanteSalvo = localStorage.getItem('apal_ultimo_comprovante');
        if (comprovanteSalvo) {
            try {
                const dados = JSON.parse(comprovanteSalvo);
                exibirTelaSucessoCadastro(dados.protocolo, dados);
            } catch (e) {
                console.error('Erro ao restaurar comprovante:', e);
            }
        }
    }

    // Executa a verificação assim que entra na página
    if (!stepperServidor) {
        verificarComprovanteExistente();
    }

    // Função global para quando o usuário quiser fazer um novo cadastro do zero
    window.iniciarNovoCadastro = function() {
        localStorage.removeItem('apal_ultimo_comprovante');
        localStorage.removeItem('apal_cadastro_rascunho');
        window.location.reload();
    };

    window.exibirSucessoCadastro = exibirTelaSucessoCadastro;

    // Ações dos botões de Imprimir e Compartilhar
  // Ações dos botões de Imprimir e Compartilhar
    document.getElementById('btn-imprimir-pdf')?.addEventListener('click', () => {
        // 1. FORÇA O PREENCHIMENTO ANTES DE IMPRIMIR
        if (typeof preencherDocumentoOficial === 'function') {
            preencherDocumentoOficial();
        }
        // 2. ABRE A TELA DE IMPRESSÃO LOGO EM SEGUIDA
        setTimeout(() => { window.print(); }, 100);
    });

    document.getElementById('btn-compartilhar')?.addEventListener('click', async () => {
        const protocoloTexto = protocoloEl ? protocoloEl.textContent : 'APAL';
        const dados = {
            title: 'Comprovante APAL',
            text: `Requerimento protocolado no APAL. Protocolo: ${protocoloTexto}`,
            url: window.location.href
        };
        if (navigator.share) {
            try { await navigator.share(dados); } catch (_) {}
        } else {
            navigator.clipboard.writeText(`Protocolo APAL: ${protocoloTexto}`);
            alert('Número do protocolo copiado!');
        }
    });

    // Envio do Formulário
    cadastroForm?.addEventListener('submit', event => {
        if (stepperServidor) {
            if (typeof validarEtapa === 'function' && !validarEtapa(etapaAtual)) {
                event.preventDefault();
            }
            return;
        }
        event.preventDefault();

        for (let numero = 1; numero <= totalEtapas; numero++) {
            if (typeof validarEtapa === 'function' && !validarEtapa(numero)) {
                if (typeof mostrarEtapa === 'function') mostrarEtapa(numero);
                return;
            }
        }

        exibirTelaSucessoCadastro();
    });
// ==========================================
    // 15. CREDENCIAL E ANIMAÇÕES EXTRAS
    // ==========================================
    
    // Garante que os ícones do Lucide apareçam nos cartões novos
    if (window.lucide) {
        lucide.createIcons();
    }

    // Botão de Imprimir Credencial
    const btnImprimir = document.getElementById('btn-imprimir-cred');
    btnImprimir?.addEventListener('click', () => {
        window.print();
    });

    // Botão de Compartilhar Credencial
    const btnCompartilharCred = document.getElementById('btn-compartilhar-cred');
    btnCompartilharCred?.addEventListener('click', async () => {
        const dadosCompartilhamento = {
            title: 'Credencial Digital - APAL',
            text: 'Confira a minha credencial oficial de comerciante ambulante emitida pela Prefeitura de Vitória da Conquista (APAL).',
            url: window.location.href
        };

        if (navigator.share) {
            try {
                await navigator.share(dadosCompartilhamento);
            } catch (err) {
                console.log('Compartilhamento cancelado');
            }
        } else {
            navigator.clipboard.writeText(window.location.href);
            alert('Link da credencial copiado para a área de transferência!');
        }
    });

    // Configuração do Observador de Rolagem (Scroll Animation)
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.15 
    };

    const scrollObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const elementosAnimados = document.querySelectorAll('.feature-card, .step-card, .cta-banner');
    
    elementosAnimados.forEach((elemento, index) => {
        elemento.style.opacity = '0';
        elemento.style.transform = 'translateY(40px)';
        const delay = (index % 4) * 0.15; 
        elemento.style.transition = `opacity 0.6s ease ${delay}s, transform 0.6s cubic-bezier(0.4, 0, 0.2, 1) ${delay}s`;
        scrollObserver.observe(elemento);
    });

    // Ativa transições suaves para as requisições assíncronas do HTMX
    if (typeof htmx !== 'undefined') {
        htmx.config.globalViewTransitions = true; 
    }

// ==========================================
// FIM DO DOMContentLoaded (ÚNICO)
// ==========================================

// ==========================================
// SALVAR E RESTAURAR PROGRESSO DO FORMULÁRIO
// ==========================================

const CHAVE_STORAGE = 'apal_cadastro_rascunho';

// 1. Salva os campos do formulário no localStorage
function salvarProgressoFormulario() {
    const form = document.getElementById('cadastro-form');
    if (!form) return;

    const dados = {
        etapaAtual: typeof etapaAtual !== 'undefined' ? etapaAtual : 1
    };

    // Salva inputs, selects e textareas
    const campos = form.querySelectorAll('input, select, textarea');
    campos.forEach(campo => {
        if (!campo.id) return;

        if (campo.type === 'checkbox') {
            dados[campo.id] = campo.checked;
        } else if (campo.type !== 'file' && campo.type !== 'password') {
            // Arquivos e senhas não são salvos por questões de segurança do navegador
            dados[campo.id] = campo.value;
        }
    });

    localStorage.setItem(CHAVE_STORAGE, JSON.stringify(dados));
}

// 2. Restaura o progresso salvo quando o usuário entra na página
function restaurarProgressoFormulario() {
    const salvo = localStorage.getItem(CHAVE_STORAGE);
    if (!salvo) return;

    try {
        const dados = JSON.parse(salvo);

        // Preenche cada campo salvo
        Object.keys(dados).forEach(id => {
            if (id === 'etapaAtual') return;

            const campo = document.getElementById(id);
            if (campo) {
                if (campo.type === 'checkbox') {
                    campo.checked = dados[id];
                    campo.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    campo.value = dados[id];
                    campo.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });

        // Volta automaticamente para a etapa onde o usuário parou
        if (dados.etapaAtual && typeof mostrarEtapa === 'function') {
            mostrarEtapa(dados.etapaAtual, false);
        }
    } catch (e) {
        console.warn('Erro ao restaurar rascunho:', e);
    }
}

// 3. Apaga o rascunho quando o formulário for enviado com sucesso
function limparProgressoSalvo() {
    localStorage.removeItem(CHAVE_STORAGE);
}

const form = document.getElementById('cadastro-form');
if (form) {
    // Salva automaticamente enquanto o usuário digita ou altera opções
    form.addEventListener('input', salvarProgressoFormulario);
    form.addEventListener('change', salvarProgressoFormulario);

    // Restaura o rascunho salvo assim que abre a página
    restaurarProgressoFormulario();
}

// ============================================================
// PREENCHIMENTO AUTOMÁTICO DO FORMULÁRIO OFICIAL (CORRIGIDO)
// ============================================================

function preencherDocumentoOficial() {
    let dadosSalvos = {};
    try {
        const comprovante = localStorage.getItem('apal_ultimo_comprovante');
        const rascunho = localStorage.getItem('apal_cadastro_rascunho');
        dadosSalvos = JSON.parse(comprovante || rascunho || '{}');
    } catch (e) {
        console.warn('Erro ao ler rascunho:', e);
    }

    const getValorCampo = (idsPossiveis) => {
        for (const id of idsPossiveis) {
            const el = document.getElementById(id);
            if (el) {
                if (el.tagName === 'SELECT') {
                    if (el.selectedIndex >= 0 && el.options[el.selectedIndex].value) {
                        return el.options[el.selectedIndex].text;
                    }
                } else if (el.value && el.value.trim() !== '') {
                    return el.value.trim();
                }
            }
        }
        
        for (const id of idsPossiveis) {
            if (dadosSalvos[id]) return dadosSalvos[id];
        }

        return '-';
    };

    const setTxt = (idTarget, valor) => {
        const el = document.getElementById(idTarget);
        if (el) {
            el.textContent = (valor && valor !== '-') ? valor : 'Não informado';
        }
    };

    const marcarCheck = (idTarget, condicao) => {
        const el = document.getElementById(idTarget);
        if (el) {
            const textoLimpo = el.textContent.replace(/\([ Xx]\)/, '').trim();
            el.textContent = `${condicao ? '(X)' : '( )'} ${textoLimpo}`;
        }
    };

    // --- MAPEAMENTO COM OS IDs REAIS DO SEU HTML ---

    // 1. Dados Pessoais
    setTxt('pdf-nome', getValorCampo(['req-nome']));
    setTxt('pdf-cpf', getValorCampo(['cpf-cadastro']));
    setTxt('pdf-rg', getValorCampo(['req-rg']));
    setTxt('pdf-nacionalidade', getValorCampo(['pais-origem']) !== '-' ? getValorCampo(['pais-origem']) : 'Brasileira');
    setTxt('pdf-estado-civil', getValorCampo(['req-estado-civil']));

    // 2. Endereço Residencial
    setTxt('pdf-endereco', getValorCampo(['endereco-input']));
    setTxt('pdf-numero', getValorCampo(['numero-input']));
    setTxt('pdf-bairro', getValorCampo(['bairro-input']));
    setTxt('pdf-complemento', getValorCampo(['complemento-input']));
    setTxt('pdf-cep', getValorCampo(['cep-input']));
    setTxt('pdf-tel', getValorCampo(['req-tel']));
    setTxt('pdf-email', getValorCampo(['req-email']));

    // 3. Pessoa Jurídica
    const cnpjVal = getValorCampo(['pj-cnpj']);
    setTxt('pdf-pj-cnpj', cnpjVal !== '-' ? cnpjVal : 'Não se aplica');
    setTxt('pdf-pj-razao', getValorCampo(['pj-razao']));
    setTxt('pdf-pj-fantasia', getValorCampo(['pj-fantasia']));
    setTxt('pdf-pj-insc', getValorCampo(['pj-inscricao']));

    // 4. Atuação Pretendida & Categorias
    const catText = getValorCampo(['categoria-equipamento']).toUpperCase();
    marcarCheck('pdf-cat-pret-a', catText.includes('A'));
    marcarCheck('pdf-cat-pret-b', catText.includes('B'));
    marcarCheck('pdf-cat-pret-c', catText.includes('C'));

    const tipoComercioText = getValorCampo(['especie-mercadoria', 'tipo-comercio']);
    setTxt('pdf-mercadoria-pretendida', tipoComercioText);
    setTxt('pdf-ponto-op1', getValorCampo(['endereco-ponto']));
    setTxt('pdf-ponto-op2', getValorCampo(['opcao-local-2']));
    setTxt('pdf-ponto-op3', 'N/A');
    
    const metragem = getValorCampo(['metragem-utilizada']);
    setTxt('pdf-area-pretendida', metragem !== '-' ? `${metragem} m²` : '-');
    
    setTxt('pdf-horario-pretendida', getValorCampo(['horario-atuacao']) !== '-' ? getValorCampo(['horario-atuacao']) : 'Horário Comercial');

    // 5. Data por extenso
    const hoje = new Date();
    const meses = [
        'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
    ];
    const dataFormatada = `${hoje.getDate()} de ${meses[hoje.getMonth()]} de ${hoje.getFullYear()}`;

    document.querySelectorAll('.pdf-data-extenso').forEach(el => {
        el.textContent = dataFormatada;
    });
}

});

