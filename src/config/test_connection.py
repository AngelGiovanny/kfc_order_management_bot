"""
Script para probar conexiones a base de datos
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.connection import db_manager

def test_connection(store_code):
    """Probar conexión a una tienda específica"""
    print(f"🔍 Probando conexión a tienda {store_code}...")

    try:
        with db_manager.get_connection(store_code) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@version as version")
            result = cursor.fetchone()
            print(f"✅ Conexión exitosa a {store_code}")
            print(f"   SQL Server: {result[0]}")
            return True

    except Exception as e:
        print(f"❌ Error conectando a {store_code}: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        store_code = sys.argv[1]
        test_connection(store_code)
    else:
        # Probar algunas tiendas comunes
        test_stores = ['K002', 'K003', 'K010']
        for store in test_stores:
            test_connection(store)