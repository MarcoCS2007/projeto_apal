// =========================================
// INICIALIZAÇÃO DO VLIBRAS (Governo Federal)
// =========================================
new window.VLibras.Widget('https://vlibras.gov.br/app');

// =========================================
// LÓGICA GLOBAL DO SISTEMA
// =========================================

document.addEventListener('DOMContentLoaded', () => {
    
    // -----------------------------------------
    // 1. Painel e Botão de Acessibilidade
    // -----------------------------------------
    const btnAcessibilidade = document.getElementById('open-access-float');
    const painelAcessibilidade = document.getElementById('accessibility-panel');
    const btnFechar = document.getElementById('close-access');
    const body = document.body;

    if (painelAcessibilidade && btnAcessibilidade) {
        
        btnAcessibilidade.addEventListener('click', () => {
            painelAcessibilidade.classList.toggle('hidden');
            btnAcessibilidade.classList.toggle('expanded'); 
        });

        if (btnFechar) {
            btnFechar.addEventListener('click', () => {
                painelAcessibilidade.classList.add('hidden');
                btnAcessibilidade.classList.remove('expanded'); 
            });
        }

        let tamanhoAtual = 100;
        const btnAumentar = document.getElementById('btn-aumentar');
        const btnDiminuir = document.getElementById('btn-diminuir');

        if (btnAumentar) {
            btnAumentar.addEventListener('click', () => {
                tamanhoAtual += 10;
                document.documentElement.style.fontSize = tamanhoAtual + '%';
            });
        }
        
        if (btnDiminuir) {
            btnDiminuir.addEventListener('click', () => {
                tamanhoAtual -= 10;
                document.documentElement.style.fontSize = tamanhoAtual + '%';
            });
        }

        const limparFiltros = () => {
            body.classList.remove('tema-escuro', 'tema-claro', 'sat-alta', 'sat-baixa', 'zoom-ativo');
        };

        const btnEscuro = document.getElementById('btn-escuro');
        const btnClaro = document.getElementById('btn-claro');
        const btnSatAlta = document.getElementById('btn-sat-alta');
        const btnSatBaixa = document.getElementById('btn-sat-baixa');
        const btnZoom = document.getElementById('btn-zoom');

        if (btnEscuro) {
            btnEscuro.addEventListener('click', () => {
                const ativo = body.classList.contains('tema-escuro');
                limparFiltros();
                if (!ativo) body.classList.add('tema-escuro');
            });
        }

        if (btnClaro) {
            btnClaro.addEventListener('click', () => {
                const ativo = body.classList.contains('tema-claro');
                limparFiltros();
                if (!ativo) body.classList.add('tema-claro');
            });
        }

        if (btnSatAlta) {
            btnSatAlta.addEventListener('click', () => {
                const ativo = body.classList.contains('sat-alta');
                limparFiltros();
                if (!ativo) body.classList.add('sat-alta');
            });
        }

        if (btnSatBaixa) {
            btnSatBaixa.addEventListener('click', () => {
                const ativo = body.classList.contains('sat-baixa');
                limparFiltros();
                if (!ativo) body.classList.add('sat-baixa');
            });
        }

        if (btnZoom) {
            btnZoom.addEventListener('click', () => {
                body.classList.toggle('zoom-ativo');
            });
        }
    }

    // -----------------------------------------
    // 2. Lógica de Login Inteligente por Perfil
    // -----------------------------------------
    const loginForm = document.getElementById('login-form');
    const perfilSelect = document.getElementById('perfil-select');

    if (loginForm && perfilSelect) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault(); 
            const perfilEscolhido = perfilSelect.value;

            switch (perfilEscolhido) {
                case 'gestor':
                    alert('Autenticado com sucesso! Entrando na Visão do Gestor...');
                    window.location.href = 'dashboard.html';
                    break;
                case 'fiscal':
                    alert('Autenticado com sucesso! Entrando no Módulo de Fiscalização...');
                    window.location.href = 'fiscalizacao.html';
                    break;
                case 'master':
                    alert('Autenticado com sucesso! Entrando no Painel Master/TI...');
                    window.location.href = 'admin.html';
                    break;
                case 'ambulante':
                default:
                    alert('Autenticado com sucesso! Carregando sua Credencial Digital...');
                    window.location.href = 'credencial.html';
                    break;
            }
        });
    }

    // -----------------------------------------
    // 3. Sistema de Notificações Flutuantes (Toast)
    // -----------------------------------------
    function mostrarNotificacao(mensagem, tipo = 'erro') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast-alert ${tipo === 'aviso' ? 'warning' : ''}`;
        
        const icone = tipo === 'aviso' ? 'warning' : 'error';
        toast.innerHTML = `<span class="material-icons">${icone}</span> <span>${mensagem}</span>`;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // -----------------------------------------
    // 4. Validador Oficial de CPF com Toast
    // -----------------------------------------
    const cpfInputCadastro = document.getElementById('cpf-cadastro');

    function validarCPF(cpf) {
        cpf = cpf.replace(/\D/g, '');
        
        if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;

        let soma = 0;
        let resto;

        for (let i = 1; i <= 9; i++) {
            soma += parseInt(cpf.substring(i - 1, i)) * (11 - i);
        }
        resto = (soma * 10) % 11;
        if ((resto === 10) || (resto === 11)) resto = 0;
        if (resto !== parseInt(cpf.substring(9, 10))) return false;

        soma = 0;
        for (let i = 1; i <= 10; i++) {
            soma += parseInt(cpf.substring(i - 1, i)) * (12 - i);
        }
        resto = (soma * 10) % 11;
        if ((resto === 10) || (resto === 11)) resto = 0;
        if (resto !== parseInt(cpf.substring(10, 11))) return false;

        return true;
    }

    if (cpfInputCadastro) {
        cpfInputCadastro.addEventListener('blur', () => {
            const valorCpf = cpfInputCadastro.value;
            if (valorCpf.trim() !== '') {
                if (!validarCPF(valorCpf)) {
                    mostrarNotificacao('CPF inválido ou inexistente! Verifique os números.', 'erro');
                    cpfInputCadastro.value = ''; 
                    cpfInputCadastro.focus();    
                }
            }
        });
    }

    // -----------------------------------------
    // 5. Busca Automática de Endereço por CEP (ViaCEP)
    // -----------------------------------------
    const cepInput = document.getElementById('cep-input');
    const enderecoInput = document.getElementById('endereco-input');
    const bairroInput = document.getElementById('bairro-input');
    const cidadeInput = document.getElementById('cidade-input');
    const estadoInput = document.getElementById('estado-input');

    if (cepInput) {
        cepInput.addEventListener('input', () => {
            const cepLimpo = cepInput.value.replace(/\D/g, '');

            if (cepLimpo.length === 8) {
                enderecoInput.value = 'Buscando...';
                bairroInput.value = 'Buscando...';
                cidadeInput.value = 'Buscando...';
                estadoInput.value = '...';

                fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.erro) {
                            enderecoInput.value = data.logradouro || '';
                            bairroInput.value = data.bairro || '';
                            cidadeInput.value = data.localidade || '';
                            estadoInput.value = data.uf || '';
                            
                            const numeroInput = document.getElementById('numero-input');
                            if (numeroInput) numeroInput.focus();
                        } else {
                            mostrarNotificacao('CEP não encontrado na base de dados.', 'aviso');
                            limparCamposCep();
                        }
                    })
                    .catch(error => {
                        console.error('Erro ao buscar o CEP:', error);
                        mostrarNotificacao('Erro ao consultar o CEP. Verifique sua conexão.', 'erro');
                        limparCamposCep();
                    });
            }
        });
    }

    function limparCamposCep() {
        if (enderecoInput) enderecoInput.value = '';
        if (bairroInput) bairroInput.value = '';
        if (cidadeInput) cidadeInput.value = '';
        if (estadoInput) estadoInput.value = '';
    }

    // -----------------------------------------
    // 6. Cascata Dinâmica: Nacionalidade e Naturalidade (IBGE + Países)
    // -----------------------------------------
    const selectNacionalidade = document.getElementById('nacionalidade-select');
    const selectEstadoNasc = document.getElementById('estado-nascimento');
    const selectCidadeNasc = document.getElementById('cidade-nascimento');

    if (selectNacionalidade && selectEstadoNasc && selectCidadeNasc) {
        
        let cacheEstadosIBGE = [];

        // Correção específica: garante espaço suficiente abaixo no clique para estado e cidade abrirem para baixo sem saltos bruscos
        [selectEstadoNasc, selectCidadeNasc].forEach(select => {
            select.addEventListener('mousedown', () => {
                const rect = select.getBoundingClientRect();
                if (rect.bottom > window.innerHeight - 300) {
                    window.scrollBy({ top: 150, behavior: 'smooth' });
                }
            });
        });

        // 1. Lista de Países
        const listaPaises = [
            "Brasil", "Afeganistão", "África do Sul", "Albânia", "Alemanha", "Andorra", "Angola", 
            "Antígua e Barbuda", "Arábia Saudita", "Argélia", "Argentina", "Armênia", "Austrália", 
            "Áustria", "Azerbaijão", "Bahamas", "Bahrein", "Bangladesh", "Barbados", "Bélgica", 
            "Belize", "Benin", "Bielorrússia", "Bolívia", "Bósnia e Herzegovina", "Botsuana", 
            "Brunei", "Bulgária", "Burquina Fasso", "Burundi", "Butão", "Cabo Verde", "Camarões", 
            "Camboja", "Canadá", "Catar", "Cazaquistão", "Chade", "Chile", "China", "Chipre", 
            "Colômbia", "Comores", "Congo", "Coreia do Norte", "Coreia do Sul", "Costa do Marfim", 
            "Costa Rica", "Croácia", "Cuba", "Dinamarca", "Djibuti", "Dominica", "Egito", 
            "El Salvador", "Emirados Árabes Unidos", "Equador", "Eritreia", "Eslováquia", "Eslovênia", 
            "Espanha", "Estados Unidos", "Estônia", "Eswatini", "Etiópia", "Fiji", "Filipinas", 
            "Finlândia", "França", "Gabão", "Gâmbia", "Gana", "Geórgia", "Granada", "Grécia", 
            "Guatemala", "Guiana", "Guiné", "Guiné-Bissau", "Guiné Equatorial", "Haiti", "Honduras", 
            "Hungria", "Iêmen", "Ilhas Marechal", "Índia", "Indonésia", "Irã", "Iraque", "Irlanda", 
            "Islândia", "Israel", "Itália", "Jamaica", "Japão", "Jordânia", "Kuwait", "Laos", 
            "Lesoto", "Letônia", "Líbano", "Libéria", "Líbia", "Liechtenstein", "Lituânia", 
            "Luxemburgo", "Macedônia do Norte", "Madagáscar", "Malásia", "Malavi", "Maldivas", 
            "Mali", "Malta", "Marrocos", "Maurício", "Mauritânia", "México", "Micronésia", 
            "Moçambique", "Moldávia", "Mônaco", "Mongólia", "Montenegro", "Namíbia", "Nauru", 
            "Nepal", "Nicarágua", "Níger", "Nigéria", "Noruega", "Nova Zelândia", "Omã", "Países Baixos", 
            "Palau", "Palestina", "Panamá", "Papua-Nova Guiné", "Paquistão", "Paraguai", "Peru", 
            "Polônia", "Portugal", "Quênia", "Quirguistão", "Quiribati", "Reino Unido", "República Centro-Africana", 
            "República Checa", "República Democrática do Congo", "República Dominicana", "Romênia", 
            "Ruanda", "Rússia", "Ilhas Salomão", "Samoa", "San Marino", "Santa Lúcia", "São Cristóvão e Neves", 
            "São Tomé e Príncipe", "São Vicente e Granadinas", "Seicheles", "Senegal", "Serra Leoa", 
            "Sérvia", "Singapura", "Síria", "Somália", "Sri Lanka", "Sudão", "Sudão do Sul", "Suécia", 
            "Suíça", "Suriname", "Tailândia", "Taiwan", "Tanzânia", "Tajiquistão", "Timor-Leste", 
            "Togo", "Tonga", "Trinidad e Tobago", "Tunísia", "Turcomenistão", "Turquia", "Tuvalu", 
            "Ucrânia", "Uganda", "Uruguai", "Uzbequistão", "Vanuatu", "Vaticano", "Venezuela", "Vietnã", "Zâmbia", "Zimbábue"
        ];

        selectNacionalidade.innerHTML = '<option value="" disabled>Selecione o país...</option>';
        
        listaPaises.forEach(pais => {
            const option = document.createElement('option');
            option.value = pais;
            option.textContent = pais;
            if (pais === 'Brasil') {
                option.selected = true;
            }
            selectNacionalidade.appendChild(option);
        });

        // 2. Carregar e guardar Estados do IBGE em cache
        fetch('https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome')
            .then(response => response.json())
            .then(estados => {
                cacheEstadosIBGE = estados;
                preencherSelectEstados();
            })
            .catch(error => console.error('Erro ao carregar estados do IBGE:', error));

        function preencherSelectEstados() {
            selectEstadoNasc.innerHTML = '<option value="" disabled selected>Selecione o Estado...</option>';
            cacheEstadosIBGE.forEach(estado => {
                const option = document.createElement('option');
                option.value = estado.sigla;
                option.textContent = estado.nome;
                selectEstadoNasc.appendChild(option);
            });
        }

        // 3. Carregar Cidades quando o Estado for alterado
        selectEstadoNasc.addEventListener('change', () => {
            const siglaUf = selectEstadoNasc.value;
            if (!siglaUf) return;

            selectCidadeNasc.innerHTML = '<option value="" disabled selected>Carregando cidades...</option>';
            selectCidadeNasc.disabled = true;

            fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${siglaUf}/municipios?orderBy=nome`)
                .then(response => response.json())
                .then(cidades => {
                    selectCidadeNasc.innerHTML = '<option value="" disabled selected>Selecione a cidade...</option>';
                    cidades.forEach(cidade => {
                        const option = document.createElement('option');
                        option.value = cidade.nome;
                        option.textContent = cidade.nome;
                        selectCidadeNasc.appendChild(option);
                    });
                    selectCidadeNasc.disabled = false;
                })
                .catch(error => {
                    console.error('Erro ao carregar cidades:', error);
                    selectCidadeNasc.innerHTML = '<option value="" disabled selected>Erro ao carregar cidades</option>';
                });
        });

        // 4. Controlar ativação de Estado e Cidade baseado na Nacionalidade
        function controlarCamposNacionalidade() {
            const paisEscolhido = selectNacionalidade.value;

            if (paisEscolhido === 'Brasil') {
                selectEstadoNasc.disabled = false;
                selectEstadoNasc.required = true;

                if (selectEstadoNasc.options.length <= 1 && cacheEstadosIBGE.length > 0) {
                    preencherSelectEstados();
                }

                if (selectEstadoNasc.value === '') {
                    selectCidadeNasc.innerHTML = '<option value="" disabled selected>Primeiro selecione o Estado...</option>';
                    selectCidadeNasc.disabled = true;
                }
            } else {
                selectEstadoNasc.innerHTML = '<option value="" disabled selected>Não aplicável (Estrangeiro)</option>';
                selectEstadoNasc.value = '';
                selectEstadoNasc.disabled = true;
                selectEstadoNasc.required = false;

                selectCidadeNasc.innerHTML = '<option value="" disabled selected>Não aplicável (Estrangeiro)</option>';
                selectCidadeNasc.value = '';
                selectCidadeNasc.disabled = true;
                selectCidadeNasc.required = false;
            }
        }

        selectNacionalidade.addEventListener('change', controlarCamposNacionalidade);
        controlarCamposNacionalidade();
    }

    // -----------------------------------------
    // 7. Lógica do Menu Sanfona (FAQ)
    // -----------------------------------------
    const faqItems = document.querySelectorAll('.faq-item');
    
    if (faqItems.length > 0) {
        faqItems.forEach(item => {
            const questionBtn = item.querySelector('.faq-question');
            if (questionBtn) {
                questionBtn.addEventListener('click', () => {
                    if (item.classList.contains('active')) {
                        item.classList.remove('active');
                    } else {
                        faqItems.forEach(i => i.classList.remove('active'));
                        item.classList.add('active');
                    }
                });
            }
        });
    }

});