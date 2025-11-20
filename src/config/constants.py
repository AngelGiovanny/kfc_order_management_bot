# Store validation
STORE_CODE_RANGE = ('K002', 'K999')

# Document types
DOCUMENT_TYPES = {
    'factura': 'F',
    'nota_credito': 'N',
    'comanda': 'C'
}

# Límites de re-impresión
REPRINT_LIMITS = {
    'factura': 1,
    'nota_credito': 1,
    'comanda': 2
}

# URL patterns
URL_PATTERNS = {
    'factura': '/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=F&',
    'nota_credito': '/pos/facturacion/impresion/impresion_factura.php?cfac_id={cfac_id}&tipo_comprobante=N&',
    'comanda': '/PoS/ordenpedido/impresion/imprimir_ordenpedido.php?odp_id={odp_id}&tipoServicio=2&canalImpresion=0&guardaOrden=0&numeroCuenta=1'
}

# User states
USER_STATES = {
    'GET_STORE_CODE': 'get_store_code',
    'MAIN_MENU': 'main_menu',
    'GET_ORDER_STATUS': 'get_order_status',
    'GET_ORDER_AUDIT': 'get_order_audit',
    'GET_INVOICE_ID': 'get_invoice_id',
    'GET_COMANDA_ID': 'get_comanda_id',
    'GET_CFAC_ID': 'get_cfac_id',  # ← Asegúrate de que esta constante exista
    'SUBREPRINT_MENU': 'subreprint_menu',
    'GET_REPRINT_ID': 'get_reprint_id',
    'GET_REPRINT_REASON': 'get_reprint_reason'
}