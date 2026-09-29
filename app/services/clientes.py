def datos_cliente_coinciden(cliente, nombres, apellidos, telefono):
    def normalizar(texto):
        return " ".join(texto.split()).casefold()
    return (
        normalizar(cliente.nombres) == normalizar(nombres)
        and normalizar(cliente.apellidos) == normalizar(apellidos)
        and cliente.telefono.strip() == telefono.strip()
    )
