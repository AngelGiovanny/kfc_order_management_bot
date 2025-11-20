import pandas as pd
import io
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from src.utils.logger import logger
from collections import Counter, defaultdict

# Intentar importar matplotlib, pero hacerlo opcional
try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib no está instalado. Las gráficas no estarán disponibles.")


class ReportService:
    # Configuración de rutas
    REPORT_BASE_DIR = "reportes"

    @classmethod
    def _get_report_directory(cls, date: datetime = None) -> str:
        """Obtiene la ruta de directorio organizada por año/mes/día"""
        if date is None:
            date = datetime.now()

        year_dir = os.path.join(cls.REPORT_BASE_DIR, str(date.year))
        month_dir = os.path.join(year_dir, f"{date.month:02d}")
        day_dir = os.path.join(month_dir, f"{date.day:02d}")

        # Crear directorios si no existen
        os.makedirs(day_dir, exist_ok=True)

        return day_dir

    @classmethod
    def _save_report_file(cls, content: bytes, filename: str, date: datetime = None) -> str:
        """Guarda un archivo de reporte en la estructura organizada"""
        try:
            report_dir = cls._get_report_directory(date)
            file_path = os.path.join(report_dir, filename)

            with open(file_path, 'wb') as f:
                f.write(content)

            logger.info(f"📁 Reporte guardado: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error guardando reporte {filename}: {str(e)}")
            return None

    @staticmethod
    def generate_usage_report(activity_records: Dict) -> Dict:
        """Genera reporte completo de uso del bot"""
        try:
            total_users = len(activity_records)
            total_activities = sum(len(records) for records in activity_records.values())

            # Análisis por hora del día
            hourly_usage = defaultdict(int)
            user_activities = defaultdict(list)
            store_activities = defaultdict(int)
            action_types = defaultdict(int)

            for user_id, records in activity_records.items():
                for record in records:
                    # Parsear el registro
                    parts = record.split(' - ')
                    if len(parts) >= 2:
                        timestamp_str = parts[0]
                        activity_str = parts[1]

                        # Extraer hora
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            hourly_usage[timestamp.hour] += 1
                        except:
                            pass

                        # Analizar tipo de acción
                        if 'Tienda:' in activity_str:
                            action_types['store_access'] += 1
                            # Extraer código de tienda
                            store_parts = activity_str.split('Tienda: ')
                            if len(store_parts) > 1:
                                store_code = store_parts[1].strip()
                                store_activities[store_code] += 1
                        elif 'Verificar estado' in activity_str:
                            action_types['check_status'] += 1
                        elif 'Auditoria' in activity_str:
                            action_types['audit'] += 1
                        elif 'Re-Impresion' in activity_str:
                            action_types['reprint'] += 1
                        elif 'Generar imagen' in activity_str:
                            action_types['generate_image'] += 1

            # Usuarios más activos
            user_activity_count = {
                user_id: len(records)
                for user_id, records in activity_records.items()
            }
            top_users = dict(sorted(
                user_activity_count.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])

            # Tiendas más activas
            top_stores = dict(sorted(
                store_activities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])

            return {
                'summary': {
                    'total_users': total_users,
                    'total_activities': total_activities,
                    'avg_activities_per_user': total_activities / total_users if total_users > 0 else 0,
                    'report_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'hourly_usage': dict(hourly_usage),
                'action_breakdown': dict(action_types),
                'top_users': top_users,
                'top_stores': top_stores,
                'store_activities': dict(store_activities)
            }

        except Exception as e:
            logger.error(f"Error generando reporte de uso: {str(e)}")
            return {}

    @classmethod
    def generate_excel_report(cls, activity_records: Dict, report_data: Dict, save_file: bool = True) -> io.BytesIO:
        """Genera reporte en Excel con múltiples hojas y opción de guardar"""
        try:
            output = io.BytesIO()

            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Hoja 1: Resumen ejecutivo
                summary_data = {
                    'Métrica': [
                        'Total de Usuarios',
                        'Total de Actividades',
                        'Promedio Actividades por Usuario',
                        'Período del Reporte'
                    ],
                    'Valor': [
                        report_data['summary']['total_users'],
                        report_data['summary']['total_activities'],
                        round(report_data['summary']['avg_activities_per_user'], 2),
                        report_data['summary']['report_generated_at']
                    ]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)

                # Hoja 2: Actividad por Usuario
                user_data = []
                for user_id, records in activity_records.items():
                    user_data.append({
                        'User ID': user_id,
                        'Total Actividades': len(records),
                        'Primera Actividad': records[0].split(' - ')[0] if records else 'N/A',
                        'Última Actividad': records[-1].split(' - ')[0] if records else 'N/A'
                    })

                if user_data:
                    df_users = pd.DataFrame(user_data)
                    df_users.to_excel(writer, sheet_name='Actividad por Usuario', index=False)

                # Hoja 3: Uso por Hora
                hourly_data = {
                    'Hora': list(report_data['hourly_usage'].keys()),
                    'Total Actividades': list(report_data['hourly_usage'].values())
                }
                df_hourly = pd.DataFrame(hourly_data)
                df_hourly.to_excel(writer, sheet_name='Uso por Hora', index=False)

                # Hoja 4: Tipos de Acción
                action_data = {
                    'Tipo de Acción': list(report_data['action_breakdown'].keys()),
                    'Cantidad': list(report_data['action_breakdown'].values())
                }
                df_actions = pd.DataFrame(action_data)
                df_actions.to_excel(writer, sheet_name='Tipos de Acción', index=False)

                # Hoja 5: Actividad por Tienda
                if report_data['store_activities']:
                    store_data = {
                        'Código Tienda': list(report_data['store_activities'].keys()),
                        'Total Actividades': list(report_data['store_activities'].values())
                    }
                    df_stores = pd.DataFrame(store_data)
                    df_stores.to_excel(writer, sheet_name='Actividad por Tienda', index=False)

                # Ajustar formato de columnas
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    worksheet.set_column('A:Z', 20)

            output.seek(0)

            # Guardar archivo localmente si se solicita
            if save_file:
                filename = f"reporte_avanzado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                cls._save_report_file(output.getvalue(), filename)
                output.seek(0)  # Reset stream para re-enviar

            return output

        except Exception as e:
            logger.error(f"Error generando Excel: {str(e)}")
            return io.BytesIO()

    @classmethod
    def generate_detailed_txt_report(cls, activity_records: Dict, report_data: Dict, save_file: bool = True) -> str:
        """Genera reporte detallado en formato TXT con opción de guardar"""
        try:
            report_lines = []
            report_lines.append("=" * 60)
            report_lines.append("REPORTE DETALLADO DE USO - KFC ORDER MANAGEMENT BOT")
            report_lines.append("=" * 60)
            report_lines.append(f"Generado: {report_data['summary']['report_generated_at']}")
            report_lines.append("")

            # Resumen ejecutivo
            report_lines.append("RESUMEN EJECUTIVO:")
            report_lines.append("-" * 30)
            report_lines.append(f"Total Usuarios Únicos: {report_data['summary']['total_users']}")
            report_lines.append(f"Total Actividades: {report_data['summary']['total_activities']}")
            report_lines.append(f"Promedio Act/Usuario: {report_data['summary']['avg_activities_per_user']:.2f}")
            report_lines.append("")

            # Distribución por acción
            report_lines.append("DISTRIBUCIÓN POR TIPO DE ACCIÓN:")
            report_lines.append("-" * 35)
            for action, count in report_data['action_breakdown'].items():
                percentage = (count / report_data['summary']['total_activities']) * 100
                report_lines.append(f"{action}: {count} ({percentage:.1f}%)")
            report_lines.append("")

            # Top usuarios
            report_lines.append("TOP 10 USUARIOS MÁS ACTIVOS:")
            report_lines.append("-" * 35)
            for i, (user_id, count) in enumerate(report_data['top_users'].items(), 1):
                report_lines.append(f"{i}. User {user_id}: {count} actividades")
            report_lines.append("")

            # Top tiendas
            if report_data['top_stores']:
                report_lines.append("TOP 10 TIENDAS MÁS ACTIVAS:")
                report_lines.append("-" * 35)
                for i, (store, count) in enumerate(report_data['top_stores'].items(), 1):
                    report_lines.append(f"{i}. {store}: {count} actividades")
                report_lines.append("")

            # Uso por hora
            report_lines.append("ACTIVIDAD POR HORA DEL DÍA:")
            report_lines.append("-" * 35)
            for hour in sorted(report_data['hourly_usage'].keys()):
                count = report_data['hourly_usage'][hour]
                report_lines.append(f"Hora {hour:02d}:00 - {count} actividades")

            report_lines.append("")
            report_lines.append("=" * 60)

            report_content = "\n".join(report_lines)

            # Guardar archivo localmente si se solicita
            if save_file:
                filename = f"reporte_detallado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                cls._save_report_file(report_content.encode('utf-8'), filename)

            return report_content

        except Exception as e:
            logger.error(f"Error generando reporte TXT: {str(e)}")
            return "Error generando reporte"

    @classmethod
    def generate_usage_chart(cls, report_data: Dict, save_file: bool = True) -> io.BytesIO:
        """Genera gráficas de uso con opción de guardar"""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib no disponible. Saltando generación de gráficas.")
            return io.BytesIO()

        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Reporte de Uso - KFC Order Management Bot', fontsize=16, fontweight='bold')

            # Gráfica 1: Tipos de acción
            actions = list(report_data['action_breakdown'].keys())
            counts = list(report_data['action_breakdown'].values())
            ax1.pie(counts, labels=actions, autopct='%1.1f%%', startangle=90)
            ax1.set_title('Distribución de Tipos de Acción')

            # Gráfica 2: Uso por hora
            hours = list(report_data['hourly_usage'].keys())
            hour_counts = list(report_data['hourly_usage'].values())
            ax2.bar(hours, hour_counts, color='skyblue', alpha=0.7)
            ax2.set_title('Actividad por Hora del Día')
            ax2.set_xlabel('Hora')
            ax2.set_ylabel('Número de Actividades')
            ax2.grid(True, alpha=0.3)

            # Gráfica 3: Top tiendas (si hay datos)
            if report_data['top_stores']:
                stores = list(report_data['top_stores'].keys())[:8]
                store_counts = list(report_data['top_stores'].values())[:8]
                ax3.bar(stores, store_counts, color='lightgreen', alpha=0.7)
                ax3.set_title('Top 8 Tiendas Más Activas')
                ax3.tick_params(axis='x', rotation=45)
                ax3.set_ylabel('Actividades')
            else:
                ax3.text(0.5, 0.5, 'No hay datos de tiendas',
                         horizontalalignment='center', verticalalignment='center',
                         transform=ax3.transAxes)
                ax3.set_title('Actividad por Tienda')

            # Gráfica 4: Resumen numérico
            summary_data = [
                report_data['summary']['total_users'],
                report_data['summary']['total_activities'],
                report_data['summary']['avg_activities_per_user']
            ]
            summary_labels = ['Usuarios', 'Actividades', 'Promedio/Usuario']
            bars = ax4.bar(summary_labels, summary_data, color=['lightcoral', 'gold', 'lightblue'])
            ax4.set_title('Métricas Principales')
            ax4.set_ylabel('Cantidad')

            # Añadir valores en las barras
            for bar, value in zip(bars, summary_data):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width() / 2., height,
                         f'{value:.1f}' if isinstance(value, float) else f'{value}',
                         ha='center', va='bottom')

            plt.tight_layout()

            # Guardar en buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            # Guardar archivo localmente si se solicita
            if save_file:
                filename = f"grafica_uso_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                cls._save_report_file(buf.getvalue(), filename)
                buf.seek(0)  # Reset stream para re-enviar

            return buf

        except Exception as e:
            logger.error(f"Error generando gráficas: {str(e)}")
            return io.BytesIO()

    @classmethod
    def generate_daily_auto_report(cls, activity_records: Dict) -> Dict:
        """Genera y guarda automáticamente reporte diario"""
        try:
            report_data = cls.generate_usage_report(activity_records)

            if not report_data:
                return {}

            # Generar y guardar todos los formatos
            excel_buffer = cls.generate_excel_report(activity_records, report_data, save_file=True)
            txt_report = cls.generate_detailed_txt_report(activity_records, report_data, save_file=True)
            chart_buffer = cls.generate_usage_chart(report_data, save_file=True)

            logger.info("✅ Reporte diario automático generado y guardado")
            return report_data

        except Exception as e:
            logger.error(f"Error generando reporte diario automático: {str(e)}")
            return {}