/**
 * Leitor QR reutilizável para fiscalização em campo (mobile-first).
 * Espera: #btn-ativar-camera, #qr-reader, #qr-status, #qr-placeholder-icon,
 * #qr-scanner-box e opcionalmente #qr-manual.
 * data-redirect-base no #btn-ativar-camera (ou window.APAL_QR_REDIRECT)
 * define a URL base para onde ir com ?qr=...
 */
(function () {
    const botaoCamera = document.getElementById("btn-ativar-camera");
    if (!botaoCamera) return;

    const statusQr = document.getElementById("qr-status");
    const iconeQr = document.getElementById("qr-placeholder-icon");
    const scannerBox = document.getElementById("qr-scanner-box");
    const campoManual = document.getElementById("qr-manual");
    const urlLeitorQr = "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";
    const urlBase =
        botaoCamera.getAttribute("data-redirect-base") ||
        window.APAL_QR_REDIRECT ||
        window.location.pathname;

    let leitor = null;
    let carregandoLeitor = null;
    let cameraAtiva = false;

    function restaurarBotao() {
        botaoCamera.disabled = false;
        botaoCamera.innerHTML = '<i data-lucide="camera"></i> Ativar câmera e leitor';
        if (window.lucide) lucide.createIcons();
    }

    function carregarLeitorQr() {
        if (window.Html5Qrcode) return Promise.resolve();
        if (carregandoLeitor) return carregandoLeitor;
        carregandoLeitor = new Promise(function (resolve, reject) {
            const script = document.createElement("script");
            script.src = urlLeitorQr;
            script.async = true;
            script.onload = function () {
                resolve();
            };
            script.onerror = function () {
                carregandoLeitor = null;
                reject(new Error("Falha ao carregar o leitor de QR."));
            };
            document.body.appendChild(script);
        });
        return carregandoLeitor;
    }

    async function escolherCameraId() {
        const cameras = await Html5Qrcode.getCameras();
        if (!cameras || !cameras.length) {
            throw new Error("Nenhuma câmera encontrada neste dispositivo.");
        }
        const traseira = cameras.find(function (cam) {
            return /back|rear|environment|traseira|posterior/i.test(cam.label || "");
        });
        return (traseira || cameras[cameras.length - 1]).id;
    }

    function montarDestino(texto) {
        const sep = urlBase.indexOf("?") >= 0 ? "&" : "?";
        return urlBase + sep + "qr=" + encodeURIComponent(texto.trim());
    }

    function aoLerQr(texto) {
        if (!texto || !cameraAtiva) return;
        cameraAtiva = false;
        if (statusQr) {
            statusQr.hidden = false;
            statusQr.textContent = "QR lido. Validando credencial...";
        }
        const destino = montarDestino(texto);
        const parar = leitor
            ? leitor.stop().catch(function () {
                  return null;
              })
            : Promise.resolve();
        parar.finally(function () {
            window.location = destino;
        });
    }

    botaoCamera.addEventListener("click", async function () {
        if (cameraAtiva) return;
        if (
            !window.isSecureContext &&
            location.hostname !== "localhost" &&
            location.hostname !== "127.0.0.1"
        ) {
            if (statusQr) {
                statusQr.textContent =
                    "A câmera exige HTTPS. Use o campo abaixo para colar o código.";
            }
            campoManual?.focus();
            if (typeof mostrarToast === "function") {
                mostrarToast("A câmera só funciona em conexão segura (HTTPS).", "warning");
            }
            return;
        }

        botaoCamera.disabled = true;
        botaoCamera.textContent = "Abrindo câmera...";
        if (statusQr) {
            statusQr.hidden = false;
            statusQr.textContent = "Solicitando permissão da câmera...";
        }

        try {
            await carregarLeitorQr();
            if (!window.Html5Qrcode) {
                throw new Error("Biblioteca do leitor indisponível.");
            }

            if (leitor) {
                try {
                    await leitor.stop();
                } catch (_e) {
                    /* leitor ainda não estava ativo */
                }
                leitor = null;
            }
            leitor = new Html5Qrcode("qr-reader", { verbose: false });

            const cameraId = await escolherCameraId();
            if (iconeQr) iconeQr.style.display = "none";
            scannerBox?.classList.add("is-scanning");
            if (statusQr) {
                statusQr.textContent = "Aponte a câmera para o QR da credencial...";
            }

            await leitor.start(
                cameraId,
                {
                    fps: 10,
                    qrbox: function (viewWidth, viewHeight) {
                        const lado = Math.min(
                            240,
                            Math.floor(Math.min(viewWidth, viewHeight) * 0.78)
                        );
                        return { width: lado, height: lado };
                    },
                    aspectRatio: 1,
                },
                aoLerQr
            );

            cameraAtiva = true;
            if (statusQr) statusQr.hidden = true;
            botaoCamera.textContent = "Câmera ativa";
            botaoCamera.disabled = true;
        } catch (erro) {
            cameraAtiva = false;
            scannerBox?.classList.remove("is-scanning");
            if (iconeQr) iconeQr.style.display = "";
            if (statusQr) {
                statusQr.hidden = false;
                statusQr.textContent =
                    "Não foi possível abrir a câmera. Cole o código ou digite CPF/licença abaixo.";
            }
            restaurarBotao();
            campoManual?.focus();
            if (typeof mostrarToast === "function") {
                mostrarToast(
                    (erro && erro.message) ||
                        "Não foi possível abrir a câmera. Use CPF, licença ou cole o código.",
                    "warning"
                );
            }
        }
    });
})();
