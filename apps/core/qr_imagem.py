from io import BytesIO


def renderizar_qr_png(payload, box_size=8, border=2):
    """Gera PNG do QR a partir do hash HMAC da licença (item 8)."""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    imagem = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()
