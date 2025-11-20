# QUERIES OPTIMIZADAS CON MEJOR PERFORMANCE

# Order status verification - QUERY UNIFICADA Y OPTIMIZADA
ORDER_STATUS_QUERY = """
    SELECT 
        codigo_app, 
        estado, 
        cfac_id, 
        medio, 
        fecha_Pedido,
        COALESCE(m.nombres + ' ' + m.apellidos, 'No asignado') as motorizado
    FROM Cabecera_App ca
    LEFT JOIN Motorolo m ON ca.IDMotorolo = m.IDMotorolo
    WHERE ca.codigo_app = ?

    UNION ALL

    SELECT 
        codigo_app,
        estado_maxpoint as estado,
        cfac_id,
        '' as medio,
        GETDATE() as fecha_Pedido,
        'No asignado' as motorizado
    FROM kiosko_cabecera_pedidos 
    WHERE codigo_app = ?
"""

# Order audit - QUERY OPTIMIZADA
ORDER_AUDIT_QUERY = """
    SELECT 
        epa.codigo_app,
        epa.estado,
        epa.fecha,
        COALESCE(m.nombres + ' ' + m.apellidos, 'No asignado') as motorizado
    FROM Estado_Pedido_App epa WITH(NOLOCK)
    LEFT JOIN Cabecera_App ca WITH(NOLOCK) ON epa.codigo_app = ca.codigo_app
    LEFT JOIN Motorolo m WITH(NOLOCK) ON ca.IDMotorolo = m.IDMotorolo
    WHERE epa.codigo_app LIKE ?
    ORDER BY epa.IDEstadoPedido ASC
"""

# Get comanda URL - QUERY DIRECTA
COMANDA_URL_QUERY = """
    SELECT TOP 1 IDCabeceraordenPedido 
    FROM Cabecera_Factura WITH(NOLOCK)
    WHERE cfac_id = ?
"""

# Get associated code - QUERY MEJORADA
ASSOCIATED_CODE_QUERY = """
    SELECT TOP 1 codigo_app 
    FROM Cabecera_App WITH(NOLOCK) 
    WHERE cfac_id = ?

    UNION ALL

    SELECT TOP 1 codigo_app 
    FROM pickup_cabecera_pedidos WITH(NOLOCK) 
    WHERE cfac_id = ?
"""

# Get print data for reprints - QUERY OPTIMIZADA
PRINT_DATA_QUERY = """
    SELECT TOP 1 imp_url, Canal_MovimientoVarchar1 
    FROM Canal_Movimiento WITH(NOLOCK)
    WHERE Canal_MovimientoVarchar3 LIKE ? 
    AND imp_varchar1 LIKE ?
"""

# Validación de tienda rápida
VALIDATE_STORE_QUERY = """
    SELECT TOP 1 1 
    FROM information_schema.tables WITH(NOLOCK) 
    WHERE table_catalog = ?
"""